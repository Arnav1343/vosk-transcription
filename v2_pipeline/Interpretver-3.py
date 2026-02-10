"""Interpret.py v1.2.0 - Behavioral Change Indicator Transformer
Detects deviations from baseline in speech metrics. Text-only, no inference.
Evidence-based indicators only - no emotion or intent inference."""

import json, sys
from typing import Dict, List, Optional

VERSION, ARTIFACT_TYPE = "1.2.0", "behavioral_signal_transform"
GRADE_THRESHOLD, EXTREME_THRESHOLD, LOW_CONF = 0.5, 0.9, 0.3
BASELINE_WINDOW, WARMUP = 5, 5
MIN_WORDS_FOR_BASELINE = 3  # Exclude ultra-short sentences from baseline

def grade(cur: float, base: float) -> float:
    return min(1.0, abs(cur - base) / base) if base else 0.0

def baseline(hist: List[float], w: int = BASELINE_WINDOW) -> Optional[float]:
    return sum(hist[-w:]) / len(hist[-w:]) if hist else None

def detect(idx: int, m: Dict, b: Dict, prev_wc: Optional[int], warmup: bool) -> tuple:
    indicators, speed, pause, conf, wc, filler = [], m['speed'], m['pause'], m['conf'], m['wc'], m['filler']

    if conf > 0 and conf < LOW_CONF:
        return [{"indicator": "data_quality_issue", "grade": round(1-conf, 2), 
                 "evidence": f"avg_acoustic_confidence={conf:.3f} below {LOW_CONF}"}], True

    if not warmup:
        if b.get('speed') and speed > 0:
            g = grade(speed, b['speed'])
            if g >= GRADE_THRESHOLD:
                indicators.append({"indicator": "speed_deviation", "grade": round(g, 2),
                    "evidence": f"speech_speed_wpm={speed} {'above' if speed > b['speed'] else 'below'} baseline={b['speed']:.1f}"})

        if b.get('pause') is not None and pause > b['pause']:
            g = grade(pause, b['pause']) if b['pause'] > 0 else 0.5
            if g >= GRADE_THRESHOLD:
                indicators.append({"indicator": "pause_count_increase", "grade": round(g, 2),
                    "evidence": f"pause_count={pause} above baseline={b['pause']:.1f}"})

        if b.get('filler') is not None and filler > b['filler']:
            g = grade(filler, b['filler']) if b['filler'] > 0 else (0.5 if filler >= 1 else 0)
            if g >= GRADE_THRESHOLD:
                indicators.append({"indicator": "filler_increase", "grade": round(g, 2),
                    "evidence": f"filler_count={filler} above baseline={b['filler']:.1f}"})

        if b.get('wc') and wc > 0:
            g = grade(wc, b['wc'])
            if g >= GRADE_THRESHOLD:
                indicators.append({"indicator": "word_count_deviation", "grade": round(g, 2),
                    "evidence": f"word_count={wc} {'above' if wc > b['wc'] else 'below'} baseline={b['wc']:.1f}"})

        if m['text'] and wc <= 3 and prev_wc and prev_wc >= wc * 2:
            tok = m['text'].lower().split()[0].strip('.,!?') if m['text'].split() else ""
            if tok in {'yes','yeah','okay','ok','sure','right','alright','fine','yep','yup'}:
                g = min(1.0, prev_wc / (wc * 3)) if wc > 0 else 0.5
                if g >= GRADE_THRESHOLD:
                    indicators.append({"indicator": "agreement_pattern", "grade": round(g, 2),
                        "evidence": f"word_count={wc} starts_with='{tok}' prev_word_count={prev_wc}"})

    return indicators, False

def transform(data: Dict) -> Dict:
    sents, out, hist, prev_wc = data.get('sentences', []), [], {'speed':[],'pause':[],'conf':[],'wc':[],'filler':[]}, None

    for idx, s in enumerate(sents):
        sp = s.get('speech', {})
        m = {'wc': sp.get('word_count',0), 'conf': sp.get('confidence',0), 'speed': sp.get('speed_wpm',0),
             'pause': sp.get('pause_count',0), 'filler': sp.get('filler_count',0), 'text': s.get('text','')}

        b = {k: baseline(v) for k, v in hist.items()}
        indicators, low_q = detect(idx, m, b, prev_wc, idx < WARMUP)

        out.append({"sentence_index": idx, "timestamp": {"start": s.get('start',0), "end": s.get('end',0)},
            "measurements": {"word_count": m['wc'], "avg_acoustic_confidence": round(m['conf'],3),
                "speech_speed_wpm": m['speed'], "pause_count": m['pause'], 
                "pause_duration": sp.get('pause_duration',0), "filler_count": m['filler']},
            "indicators": indicators})

        # Only update baselines with valid sentences (not low quality, not extreme, not ultra-short)
        valid_for_baseline = (
            not low_q and 
            not any(i['grade'] > EXTREME_THRESHOLD for i in indicators) and
            m['wc'] >= MIN_WORDS_FOR_BASELINE  # Exclude ultra-short sentences
        )
        if valid_for_baseline:
            if m['speed'] > 0: hist['speed'].append(m['speed'])
            hist['pause'].append(m['pause'])
            if m['conf'] > 0: hist['conf'].append(m['conf'])
            hist['wc'].append(m['wc'])
            hist['filler'].append(m['filler'])
        prev_wc = m['wc']

    return {"artifact_type": ARTIFACT_TYPE, "version": VERSION, "grade_formula": "|cur-base|/base, cap 1.0",
            "grade_threshold": GRADE_THRESHOLD, "baseline_method": f"rolling_avg(w={BASELINE_WINDOW},warmup={WARMUP})",
            "sentences": out}

def main():
    data = None
    if len(sys.argv) >= 2:
        for enc in ['utf-8-sig', 'utf-8', 'utf-16']:
            try:
                with open(sys.argv[1], 'r', encoding=enc) as f: data = json.load(f); break
            except: pass
    else: data = json.load(sys.stdin)
    print(json.dumps(transform(data) if data else {"error": "read_failed"}, indent=2))

if __name__ == "__main__": main()
