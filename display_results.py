#!/usr/bin/env python3
"""Display formatted summary of VtoT(2) JSON output"""
import json

# Load the JSON output
with open('sales_call_output.json', 'r', encoding='utf-16') as f:
    data = json.load(f)

print("=" * 80)
print("SALES CALL TRANSCRIPTION SUMMARY")
print("=" * 80)
print()

# Status
status = data.get('status', 'UNKNOWN')
print(f"Status: {status}")
print()

if status == "SUCCESS":
    # Full text
    text = data.get('text', '')
    print(f"Transcribed Text:")
    print("-" * 80)
    print(text)
    print("-" * 80)
    print()
    
    # Word count and statistics
    words = data.get('result', [])
    word_count = len(words)
    
    if word_count > 0:
        confidences = [w.get('conf', 0) for w in words]
        avg_conf = sum(confidences) / len(confidences)
        min_conf = min(confidences)
        max_conf = max(confidences)
        
        # Duration
        if words:
            start_time = words[0].get('start', 0)
            end_time = words[-1].get('end', 0)
            duration = end_time - start_time
        else:
            duration = 0
        
        print(f"Statistics:")
        print(f"  Total Words: {word_count}")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Average Confidence: {avg_conf:.1%}")
        print(f"  Min Confidence: {min_conf:.1%}")
        print(f"  Max Confidence: {max_conf:.1%}")
        print()
        
        # Show first 10 words with timing
        print("First 10 Words (with timestamps and confidence):")
        print("-" * 80)
        for i, word in enumerate(words[:10]):
            w = word.get('word', '')
            start = word.get('start', 0)
            end = word.get('end', 0)
            conf = word.get('conf', 0)
            print(f"{i+1:2d}. [{start:6.2f}s - {end:6.2f}s] '{w}' (confidence: {conf:.1%})")
        
        if word_count > 10:
            print(f"... and {word_count - 10} more words")
        print()
        
        # Low confidence words
        low_conf_words = [w for w in words if w.get('conf', 1) < 0.5]
        if low_conf_words:
            print(f"Low Confidence Words ({len(low_conf_words)} words with confidence < 50%):")
            print("-" * 80)
            for word in low_conf_words[:5]:
                w = word.get('word', '')
                start = word.get('start', 0)
                conf = word.get('conf', 0)
                print(f"  [{start:6.2f}s] '{w}' (confidence: {conf:.1%})")
            if len(low_conf_words) > 5:
                print(f"  ... and {len(low_conf_words) - 5} more")
        
else:
    reason = data.get('reason', 'unknown')
    print(f"Rejection Reason: {reason}")

print()
print("=" * 80)
print(f"Output file: sales_call_output.json")
print("=" * 80)
