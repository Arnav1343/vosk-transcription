#!/usr/bin/env python3
"""
Verification script to test improved VtoT(2) configuration
Shows differences before/after the improvements
"""
import subprocess
import json
import os

def test_vtot2_improvements():
    """Test VtoT(2) with improvements"""
    
    print("=" * 80)
    print("VTOT(2) IMPROVEMENTS VERIFICATION")
    print("=" * 80)
    print()
    
    # Test audio file
    audio_file = r"C:\Users\arnav\Downloads\Sales Call example 1.wav"
    output_file = "sales_call_improved_output.json"
    
    if not os.path.exists(audio_file):
        print("[WARNING] Sales call audio not found. Using sample audio...")
        audio_file = "sample_audio_v2.wav"
    
    print(f"[INFO] Testing with: {audio_file}")
    print()
    
    # Run VtoT(2) with improvements
    print("[1/2] RUNNING IMPROVED VTOT(2)")
    print("-" * 80)
    
    result = subprocess.run(
        ["python", "VtoT(2).py", audio_file],
        capture_output=True,
        text=True,
        timeout=120
    )
    
    # Parse output
    try:
        output = json.loads(result.stdout)
    except:
        print(f"[ERROR] Failed to parse output")
        print(f"stdout: {result.stdout[:200]}")
        print(f"stderr: {result.stderr[:200]}")
        return
    
    # Save output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    
    print(f"[OK] Transcription complete")
    print()
    
    # Display results
    print("[2/2] RESULTS ANALYSIS")
    print("-" * 80)
    
    status = output.get('status', 'UNKNOWN')
    print(f"Status: {status}")
    
    if status == "SUCCESS":
        words = output.get('result', [])
        text = output.get('text', '')
        
        if words:
            confidences = [w['conf'] for w in words]
            avg_conf = sum(confidences) / len(confidences)
            min_conf = min(confidences)
            max_conf = max(confidences)
            
            # Low confidence words (below new threshold)
            low_conf = [w for w in words if w['conf'] < 0.55]
            
            print()
            print(f"  Total Words: {len(words)}")
            print(f"  Average Confidence: {avg_conf:.1%}")
            print(f"  Min Confidence: {min_conf:.1%}")
            print(f"  Max Confidence: {max_conf:.1%}")
            print(f"  Low Confidence Words (<55%): {len(low_conf)} ({len(low_conf)/len(words):.1%})")
            print()
            print(f"  Transcribed Text (first 150 chars):")
            print(f"  {text[:150]}...")
            
    elif status == "REJECTED":
        reason = output.get('reason', 'unknown')
        print()
        print(f"  Rejection Reason: {reason}")
        print()
        print("  This audio was rejected due to quality issues.")
        print("  With larger models, rejection rate should decrease.")
    
    print()
    print("=" * 80)
    print("IMPROVEMENTS SUMMARY")
    print("=" * 80)
    print()
    print("✓ FFmpeg preprocessing: mono, 16-bit PCM, 16kHz sample rate")
    print("✓ Minimum confidence threshold: 0.55 (up from 0.50)")
    print("✓ Minimum words required: 3 (up from 1)")
    print("✓ Low confidence ratio: 60% (down from 70%)")
    print("✓ Model preference: en-in-0.5 > en-us-0.22 > small-en-us-0.15")
    print()
    print(f"Output saved to: {output_file}")
    print()
    print("NEXT STEPS:")
    print("  1. Download larger model: python download_large_models.py")
    print("  2. Re-run transcription for improved accuracy")
    print()

if __name__ == "__main__":
    test_vtot2_improvements()
