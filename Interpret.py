"""
Interpret.py - Behavioral Change Indicator Transformer v1.1.0

ARTIFACT TYPE: behavioral_signal_transform
VERSION: 1.1.0

PURPOSE:
    Deterministic transformation of sentence-level speech measurements
    into high-signal, low-noise behavioral deviation indicators.

INPUT: Structured numeric measurements per sentence:
    - word_count
    - avg_acoustic_confidence
    - speech_speed_wpm
    - pause_count
    - pause_duration
    - filler_count

OUTPUT: Sentence-scoped indicators with:
    - Universal grade formula: |current - baseline| / baseline, capped at 1.0
    - Threshold: grade >= 0.5 required to emit
    - Directional constraints per indicator type
    - Data quality guards for low ASR confidence

EMISSION RULES:
    - pause/filler indicators: emit only on INCREASE (decrease not informative)
    - speed indicators: emit on both directions if threshold met
    - confidence < 0.3: flag as data_quality_issue, suppress other indicators

BASELINE STABILIZATION:
    - Freeze baseline during warm-up (first 5 sentences)
    - Exclude extreme deviations (grade > 0.9) from baseline updates
"""

import json
import sys
from typing import Dict, List, Optional

# Version
VERSION = "1.1.0"
ARTIFACT_TYPE = "behavioral_signal_transform"

# Thresholds
GRADE_THRESHOLD = 0.5
EXTREME_DEVIATION_THRESHOLD = 0.9
LOW_CONFIDENCE_THRESHOLD = 0.3

# Baseline parameters
BASELINE_WINDOW = 5
WARMUP_SENTENCES = 5


def compute_grade(current: float, baseline: float) -> float:
    """
    Universal grade formula: |current - baseline| / baseline
    Capped at 1.0. Returns 0.0 if baseline is zero.
    """
    if baseline == 0:
        return 0.0
    return min(1.0, abs(current - baseline) / baseline)


def get_baseline(history: List[float], window: int = BASELINE_WINDOW) -> Optional[float]:
    """Compute rolling average baseline from measurement history."""
    if not history:
        return None
    recent = history[-window:] if len(history) >= window else history
    return sum(recent) / len(recent)


def detect_indicators(
    sentence_idx: int,
    metrics: Dict,
    baselines: Dict[str, float],
    prev_word_count: Optional[int],
    in_warmup: bool
) -> tuple[List[Dict], bool]:
    """
    Detect behavioral indicators for a sentence.
    
    Returns: (list of indicators, is_low_quality)
    """
    indicators = []
    
    word_count = metrics.get('word_count', 0)
    confidence = metrics.get('avg_acoustic_confidence', 0)
    speed = metrics.get('speech_speed_wpm', 0)
    pause_count = metrics.get('pause_count', 0)
    filler_count = metrics.get('filler_count', 0)
    text = metrics.get('text', '')
    
    # --- DATA QUALITY CHECK ---
    # Low ASR confidence indicates audio/recognition issue, not behavior
    if confidence > 0 and confidence < LOW_CONFIDENCE_THRESHOLD:
        indicators.append({
            "indicator": "data_quality_issue",
            "grade": round(1.0 - confidence, 2),
            "evidence": f"avg_acoustic_confidence={round(confidence, 3)} below threshold={LOW_CONFIDENCE_THRESHOLD}"
        })
        return indicators, True  # Flag as low quality, suppress other indicators
    
    # --- SPEED DEVIATION (both directions) ---
    if baselines.get('speed') and speed > 0 and not in_warmup:
        grade = compute_grade(speed, baselines['speed'])
        if grade >= GRADE_THRESHOLD:
            direction = "above" if speed > baselines['speed'] else "below"
            indicators.append({
                "indicator": "speed_deviation",
                "grade": round(grade, 2),
                "evidence": f"speech_speed_wpm={speed} {direction} baseline={round(baselines['speed'], 1)}"
            })
    
    # --- PAUSE_COUNT DEVIATION (increase only) ---
    if baselines.get('pause_count') is not None and not in_warmup:
        if pause_count > baselines['pause_count']:  # Only emit on increase
            grade = compute_grade(pause_count, baselines['pause_count']) if baselines['pause_count'] > 0 else 0.5
            if grade >= GRADE_THRESHOLD:
                indicators.append({
                    "indicator": "pause_count_increase",
                    "grade": round(grade, 2),
                    "evidence": f"pause_count={pause_count} above baseline={round(baselines['pause_count'], 1)}"
                })
    
    # --- FILLER DEVIATION (increase only) ---
    if baselines.get('filler_count') is not None and not in_warmup:
        if filler_count > baselines['filler_count']:  # Only emit on increase
            if baselines['filler_count'] > 0:
                grade = compute_grade(filler_count, baselines['filler_count'])
            else:
                grade = 0.5 if filler_count >= 1 else 0.0
            if grade >= GRADE_THRESHOLD:
                indicators.append({
                    "indicator": "filler_increase",
                    "grade": round(grade, 2),
                    "evidence": f"filler_count={filler_count} above baseline={round(baselines['filler_count'], 1)}"
                })
    
    # --- WORD_COUNT DEVIATION (both directions) ---
    if baselines.get('word_count') and word_count > 0 and not in_warmup:
        grade = compute_grade(word_count, baselines['word_count'])
        if grade >= GRADE_THRESHOLD:
            direction = "above" if word_count > baselines['word_count'] else "below"
            indicators.append({
                "indicator": "word_count_deviation",
                "grade": round(grade, 2),
                "evidence": f"word_count={word_count} {direction} baseline={round(baselines['word_count'], 1)}"
            })
    
    # --- AGREEMENT PATTERN (rigid mechanical rules) ---
    # Emit only if: starts with agreement token, word_count <= 3, follows 2x longer sentence
    if text and word_count <= 3 and prev_word_count is not None and not in_warmup:
        tokens = text.lower().split()
        if tokens:
            first_token = tokens[0].strip('.,!?')
            agreement_tokens = {'yes', 'yeah', 'okay', 'ok', 'sure', 'right', 'alright', 'fine', 'yep', 'yup'}
            
            if first_token in agreement_tokens and prev_word_count >= word_count * 2:
                grade = min(1.0, prev_word_count / (word_count * 3)) if word_count > 0 else 0.5
                if grade >= GRADE_THRESHOLD:
                    indicators.append({
                        "indicator": "agreement_pattern",
                        "grade": round(grade, 2),
                        "evidence": f"word_count={word_count} starts_with='{first_token}' prev_word_count={prev_word_count}"
                    })
    
    return indicators, False


def transform(vtot_output: Dict) -> Dict:
    """Transform VtoT output into sentence-scoped behavioral indicators."""
    sentences = vtot_output.get('sentences', [])
    
    # Measurement histories (for baseline, excluding extreme deviations)
    speed_history = []
    pause_history = []
    confidence_history = []  
    word_count_history = []
    filler_history = []
    
    output_sentences = []
    prev_word_count = None
    
    for idx, sentence in enumerate(sentences):
        speech = sentence.get('speech', {})
        in_warmup = idx < WARMUP_SENTENCES
        
        # Extract metrics
        metrics = {
            'word_count': speech.get('word_count', 0),
            'avg_acoustic_confidence': speech.get('confidence', 0),
            'speech_speed_wpm': speech.get('speed_wpm', 0),
            'pause_count': speech.get('pause_count', 0),
            'pause_duration': speech.get('pause_duration', 0),
            'filler_count': speech.get('filler_count', 0),
            'text': sentence.get('text', '')
        }
        
        # Compute baselines (frozen during warmup)
        baselines = {
            'speed': get_baseline(speed_history),
            'pause_count': get_baseline(pause_history),
            'confidence': get_baseline(confidence_history),
            'word_count': get_baseline(word_count_history),
            'filler_count': get_baseline(filler_history)
        }
        
        # Detect indicators
        indicators, is_low_quality = detect_indicators(
            idx, metrics, baselines, prev_word_count, in_warmup
        )
        
        # Build sentence output
        sentence_output = {
            "sentence_index": idx,
            "timestamp": {
                "start": sentence.get('start', 0),
                "end": sentence.get('end', 0)
            },
            "measurements": {
                "word_count": metrics['word_count'],
                "avg_acoustic_confidence": round(metrics['avg_acoustic_confidence'], 3),
                "speech_speed_wpm": metrics['speech_speed_wpm'],
                "pause_count": metrics['pause_count'],
                "pause_duration": metrics['pause_duration'],
                "filler_count": metrics['filler_count']
            },
            "indicators": indicators
        }
        
        output_sentences.append(sentence_output)
        
        # Update baselines (skip if low quality or extreme deviation)
        if not is_low_quality:
            has_extreme = any(ind['grade'] > EXTREME_DEVIATION_THRESHOLD for ind in indicators)
            
            if not has_extreme:
                if metrics['speech_speed_wpm'] > 0:
                    speed_history.append(metrics['speech_speed_wpm'])
                pause_history.append(metrics['pause_count'])
                if metrics['avg_acoustic_confidence'] > 0:
                    confidence_history.append(metrics['avg_acoustic_confidence'])
                if metrics['word_count'] > 0:
                    word_count_history.append(metrics['word_count'])
                filler_history.append(metrics['filler_count'])
        
        prev_word_count = metrics['word_count']
    
    return {
        "artifact_type": ARTIFACT_TYPE,
        "version": VERSION,
        "grade_formula": "|current - baseline| / baseline, capped at 1.0",
        "grade_threshold": GRADE_THRESHOLD,
        "baseline_method": f"rolling_average(window={BASELINE_WINDOW}, warmup={WARMUP_SENTENCES}, exclude_extreme>{EXTREME_DEVIATION_THRESHOLD})",
        "sentences": output_sentences
    }


def main():
    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
        vtot_output = None
        for encoding in ['utf-8-sig', 'utf-8', 'utf-16']:
            try:
                with open(input_file, 'r', encoding=encoding) as f:
                    vtot_output = json.load(f)
                break
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        if vtot_output is None:
            print(json.dumps({"artifact_type": ARTIFACT_TYPE, "version": VERSION, "error": "could_not_read_file"}))
            sys.exit(1)
    else:
        vtot_output = json.load(sys.stdin)
    
    result = transform(vtot_output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
