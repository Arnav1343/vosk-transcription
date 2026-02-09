#!/usr/bin/env python3
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

# Use Google Translate (free, no API key, no Docker)
from deep_translator import GoogleTranslator

# Language code mapping (Whisper -> Google Translate)
LANG_MAP = {
    'ru': 'ru', 'pl': 'pl', 'de': 'de', 'fr': 'fr', 
    'es': 'es', 'it': 'it', 'pt': 'pt', 'zh': 'zh-CN',
    'ja': 'ja', 'ko': 'ko', 'ar': 'ar', 'hi': 'hi',
    'tr': 'tr', 'nl': 'nl', 'sv': 'sv', 'cs': 'cs',
    'uk': 'uk', 'vi': 'vi', 'th': 'th', 'id': 'id'
}

# Financial mistranslation corrections (deterministic, case-insensitive)
FINANCIAL_CORRECTIONS = {
    'principle': 'principal',
    'intrest': 'interest',
    'apr rate': 'APR',
    'overdraught': 'overdraft',
    'morgage': 'mortgage',
    'ammount': 'amount',
    'deposite': 'deposit',
    'withdrawl': 'withdrawal',
    'balence': 'balance',
    'installament': 'installment',
    'comission': 'commission',
    'penality': 'penalty',
}

def apply_financial_corrections(text: str) -> str:
    """Apply deterministic financial term corrections (no paraphrasing)."""
    result = text
    for wrong, correct in FINANCIAL_CORRECTIONS.items():
        # Case-insensitive replacement preserving original case pattern
        import re
        pattern = re.compile(re.escape(wrong), re.IGNORECASE)
        result = pattern.sub(correct, result)
    return result

# Google Translate has ~5000 char limit, so batch ~20 sentences
BATCH_SIZE = 20
SEPARATOR = " |SPLIT| "


def batch_translate(texts: List[str], translator: GoogleTranslator) -> List[str]:
    """Translate a batch of texts in a single API call, with financial corrections."""
    if not texts:
        return texts
    
    combined = SEPARATOR.join(texts)
    
    try:
        translated = translator.translate(combined)
        result = translated.split("|SPLIT|")
        
        # Clean up results and apply financial corrections
        result = [apply_financial_corrections(r.strip()) for r in result]
        
        # Pad if needed
        while len(result) < len(texts):
            result.append(texts[len(result)])
            
        return result[:len(texts)]
    except Exception as e:
        print(f"[WARN] Batch failed: {e}", file=sys.stderr)
        # Return original texts on failure (graceful fallback)
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
    src = LANG_MAP.get(detected_lang, detected_lang)
    translator = GoogleTranslator(source=src, target='en')
    
    # Translate main text
    original_text = whisper_data.get('text', '')
    try:
        if original_text:
            translated_text = translator.translate(original_text)
            whisper_data['text'] = translated_text
            whisper_data['original_text'] = original_text
    except Exception as e:
        print(f"[WARN] Main text translation failed: {e}", file=sys.stderr)
    
    # CHUNKED BATCH TRANSLATION
    sentences = data.get('sentences', [])
    total = len(sentences)
    num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"[INFO] Translating {total} sentences in {num_batches} batches...", file=sys.stderr)
    
    translated_count = 0
    skipped_count = 0
    
    # Store original texts
    original_texts = [s.get('text', '') for s in sentences]
    
    # Process in batches
    for batch_idx in range(num_batches):
        start = batch_idx * BATCH_SIZE
        end = min(start + BATCH_SIZE, total)
        
        batch_originals = original_texts[start:end]
        batch_translated = batch_translate(batch_originals, translator)
        
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
    
    # Add translation metadata
    data['translation'] = {
        'source_language': detected_lang,
        'target_language': 'en',
        'translated': True,
        'translator': 'GoogleTranslator',
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
