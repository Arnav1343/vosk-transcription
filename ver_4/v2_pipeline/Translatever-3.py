# !/usr/bin/env python3
"""
Translate.py - Text-only translation layer for VtoT pipeline

Reads VtoT(3) output JSON, translates non-English text to English,
preserves all timestamps, confidence scores, and metrics unchanged.

Pipeline: VtoT(3).py → vtot_output.json → Translate.py → vtot_output_en.json

OPTIMIZED: Uses chunked batch translation (~20 sentences per API call)
"""
import json
import sys
import os
from typing import Dict, List

# Use Backboard for high-accuracy LLM translation
from BackboardClient import BackboardWrapper
from config import TRANSLATION_API_KEY, DEFAULT_MODEL

# Language code mapping (Whisper -> Multi-lang full name for LLM)
LANG_FULL_NAMES = {
    'ru': 'Russian', 'pl': 'Polish', 'de': 'German', 'fr': 'French', 
    'es': 'Spanish', 'it': 'Italian', 'pt': 'Portuguese', 'zh': 'Chinese (Simplified)',
    'ja': 'Japanese', 'ko': 'Korean', 'ar': 'Arabic', 'hi': 'Hindi',
    'tr': 'Turkish', 'nl': 'Dutch', 'sv': 'Swedish', 'cs': 'Czech',
    'uk': 'Ukrainian', 'vi': 'Vietnamese', 'th': 'Thai', 'id': 'Indonesian'
}

def looks_like_gibberish(text: str) -> bool:
    """Returns True if text is empty or alphabetic ratio is below 0.6."""
    if not text: return True
    alpha_chars = sum(1 for c in text if c.isalpha())
    return (alpha_chars / len(text)) < 0.6

def apply_financial_corrections(text: str) -> str:
    # LLM usually handles this, kept for deterministic safety.
    return text

BATCH_SIZE = 15 # LLM batches can be smaller for stability
SEPARATOR = " [[[SPLIT]]] "

def llm_translate(texts: List[str], src_lang_code: str, client: BackboardWrapper) -> List[str]:
    """Translate a batch of texts using Backboard LLM."""
    if not texts: return []
    
    src_lang = LANG_FULL_NAMES.get(src_lang_code, src_lang_code)
    combined = SEPARATOR.join(texts)
    
    prompt = f"""You are a professional financial translator. 
Translate the following segments from {src_lang} to English.
Maintain the exact structure and keep the separator "{SEPARATOR}" between segments.
Diarization markers or special terms should be preserved in their English equivalents.

Segments to translate:
{combined}

Respond ONLY with the translated segments, separated by "{SEPARATOR}". No explanations."""

    try:
        response = client.send_message(prompt)
        if response.get("success"):
            translated = response["response"]
            result = translated.split(SEPARATOR)
            
            # Pad or trim to match input size
            if len(result) < len(texts):
                result.extend(texts[len(result):])
            return [r.strip() for r in result[:len(texts)]]
        else:
            print(f"[WARN] LLM Translation failed: {response.get('error')}", file=sys.stderr)
            return texts
    except Exception as e:
        print(f"[WARN] LLM Translation error: {e}", file=sys.stderr)
        return texts


def translate_transcript(input_file: str, output_file: str) -> Dict:
    """
    Translate VtoT output JSON to English using CHUNKED BATCH translation.
    Preserves all metadata, timestamps, and metrics.
    """
    print(f"[INFO] Reading: {input_file}", file=sys.stderr)

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)

    # Get detected language
    whisper_data = data.get('whisper', {})
    detected_lang = whisper_data.get('language', 'en')

    # Gibberish check: if transcription is garbled, force English to skip translation
    if looks_like_gibberish(whisper_data.get("text", "")):
        print(f"[INFO] Transcript identifies as gibberish. Forcing 'en' to skip translation.", file=sys.stderr)
        detected_lang = 'en'

    print(f"[INFO] Detected language: {detected_lang}", file=sys.stderr)

    # Skip translation if already English
    if detected_lang == 'en':
        print("[INFO] Already English, no translation needed", file=sys.stderr)
        data['translation'] = {
            'source_language': 'en',
            'translated': False,
            'translator': None
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return data

    # Setup translator
    client = BackboardWrapper(api_key=TRANSLATION_API_KEY, model=DEFAULT_MODEL)
    client.create_assistant(name="TranslationAssistant", system_prompt="You are a professional financial translator.")

    # Translate main text
    original_text = whisper_data.get('text', '')
    try:
        if original_text:
            response = client.send_message(f"Translate this text to English from {LANG_FULL_NAMES.get(detected_lang, detected_lang)}: {original_text}")
            if response.get("success"):
                whisper_data['text'] = response["response"]
                whisper_data['original_text'] = original_text
    except Exception as e:
        print(f"[WARN] Main text translation failed: {e}", file=sys.stderr)

    # CHUNKED BATCH TRANSLATION
    sentences = data.get('sentences', [])
    total = len(sentences)
    
    # Calculate average sentence length in words
    avg_length = 0
    if total > 0:
        total_words = sum(len(s.get('text', '').split()) for s in sentences)
        avg_length = total_words / total
    
    sentence_translation_enabled = avg_length >= 3
    num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    if sentence_translation_enabled:
        print(f"[INFO] Translating {total} sentences via {DEFAULT_MODEL} in {num_batches} batches... (Avg length: {avg_length:.1f})", file=sys.stderr)
    else:
        print(f"[INFO] Skipping sentence-level translation. Avg length ({avg_length:.1f}) below threshold.", file=sys.stderr)

    translated_count = 0
    skipped_count = 0

    # Store original texts
    original_texts = [s.get('text', '') for s in sentences]

    # Process in batches
    if sentence_translation_enabled:
        for batch_idx in range(num_batches):
            start = batch_idx * BATCH_SIZE
            end = min(start + BATCH_SIZE, total)

            batch_originals = original_texts[start:end]
            batch_translated = llm_translate(batch_originals, detected_lang, client)

            # Update sentences
            for i, (orig, trans) in enumerate(zip(batch_originals, batch_translated)):
                idx = start + i
                sentences[idx]['original_text'] = orig
                sentences[idx]['text'] = trans

                if trans == orig:
                    sentences[idx]['translation_skipped'] = True
                    skipped_count += 1
                else:
                    translated_count += 1

            print(f"[INFO] Batch {batch_idx+1}/{num_batches} done ({end}/{total})", file=sys.stderr)
    else:
        # Mark all as skipped
        for s in sentences:
            s['translation_skipped'] = True
            skipped_count += 1

    # Add translation metadata
    data['translation'] = {
        'source_language': detected_lang,
        'target_language': 'en',
        'translated': True,
        'translator': f"Backboard ({DEFAULT_MODEL})",
        'batch_mode': True,
        'batch_size': BATCH_SIZE,
        'num_batches': num_batches,
        'sentences_translated': translated_count,
        'sentences_skipped': skipped_count
    }

    # Write output
    print(f"[INFO] Writing: {output_file}", file=sys.stderr)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Translation complete: {translated_count} translated, {skipped_count} skipped", file=sys.stderr)

    return data


def main():
    if len(sys.argv) < 2:
        print("Usage: python Translate.py <input.json> [output.json]")
        print("       If output not specified, creates <input>_en.json")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"[ERROR] File not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    # Generate output filename
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_en{ext}"

    result = translate_transcript(input_file, output_file)

    # Print summary to stdout
    print(json.dumps({
        'input': input_file,
        'output': output_file,
        'source_language': result.get('translation', {}).get('source_language'),
        'sentences_translated': result.get('translation', {}).get('sentences_translated', 0),
        'num_batches': result.get('translation', {}).get('num_batches', 0),
        'status': 'SUCCESS'
    }, indent=2))


if __name__ == "__main__":
    main()
