#!/usr/bin/env python3
"""Compare VtoT(1) and VtoT(2) outputs"""
import json

# Load both outputs
print("=" * 80)
print("VTOT(1) vs VTOT(2) COMPARISON")
print("=" * 80)
print()

# Load VtoT(1) output
with open('sales_call_vtot1_output.json', 'r', encoding='utf-8') as f:
    vtot1 = json.load(f)

# Load VtoT(2) output  
with open('sales_call_output.json', 'r', encoding='utf-16') as f:
    vtot2 = json.load(f)

print("SCRIPT COMPARISON")
print("-" * 80)
print()

# VtoT(1) Stats
v1_stats = vtot1['metadata']['conversation_stats']
print("VtoT(1) Results:")
print(f"  Status: SUCCESS (always processes)")
print(f"  Speakers: {v1_stats['total_speakers']}")
print(f"  Utterances: {v1_stats['total_utterances']}")
print(f"  Words: {v1_stats['total_words']}")
print(f"  Average Confidence: {v1_stats['average_confidence']:.1%}")
print()

# VtoT(2) Stats
v2_status = vtot2.get('status', 'UNKNOWN')
v2_words = len(vtot2.get('result', []))
if v2_words > 0:
    v2_confidences = [w['conf'] for w in vtot2['result']]
    v2_avg_conf = sum(v2_confidences) / len(v2_confidences)
else:
    v2_avg_conf = 0

print("VtoT(2) Results:")
print(f"  Status: {v2_status}")
print(f"  Speakers: N/A (not tracked)")
print(f"  Utterances: N/A (word-level only)")
print(f"  Words: {v2_words}")
print(f"  Average Confidence: {v2_avg_conf:.1%}")
print()

# Key Differences
print("=" * 80)
print("KEY DIFFERENCES")
print("=" * 80)
print()

differences = [
    ("Output Format", "Multi-section JSON with metadata", "Flat JSON with status"),
    ("Speaker Detection", "✓ Yes (2 speakers)", "✗ No"),
    ("Utterances", "✓ Groups words into 63 utterances", "✗ Only individual words"),
    ("Rejection Logic", "✗ No (always processes)", "✓ Yes (quality-based)"),
    ("Status Field", "✗ No", "✓ Yes (SUCCESS/REJECTED)"),
    ("Statistics", "✓ Yes (detailed)", "✗ No"),
    ("Full Transcript", "✓ Yes (text + formatted)", "✓ Yes (text only)"),
    ("Use Case", "Analysis & reporting", "Quality control & validation"),
]

print(f"{'Feature':<25} {'VtoT(1)':<35} {'VtoT(2)':<35}")
print("-" * 95)
for feature, v1, v2 in differences:
    print(f"{feature:<25} {v1:<35} {v2:<35}")

print()
print("=" * 80)
print("TRANSCRIPTION TEXT COMPARISON")  
print("=" * 80)
print()

v1_text = vtot1['full_transcript']['text']
v2_text = vtot2.get('text', '')

print("VtoT(1) Transcribed Text:")
print("-" * 80)
print(v1_text[:200] + "...")
print()

print("VtoT(2) Transcribed Text:")
print("-" * 80)
print(v2_text[:200] + "...")
print()

# Word count comparison
v1_word_list = v1_text.split()
v2_word_list = v2_text.split()

print("=" * 80)
print("WORD COUNT ANALYSIS")
print("=" * 80)
print()
print(f"VtoT(1) Total Words: {len(v1_word_list)}")
print(f"VtoT(2) Total Words: {len(v2_word_list)}")
print(f"Difference: {abs(len(v1_word_list) - len(v2_word_list))} words")
print()

print("=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print()
print("Use VtoT(1) when:")
print("  • You need speaker identification")
print("  • You want detailed statistics and metadata")
print("  • You need grouped utterances")
print("  • You're doing conversation analysis")
print()
print("Use VtoT(2) when:")
print("  • You need quality control/rejection logic")
print("  • You want simple, standardized output")
print("  • You need explicit SUCCESS/REJECTED status")
print("  • You're building automated pipelines")
print()
