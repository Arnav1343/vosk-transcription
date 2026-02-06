#!/usr/bin/env python3
"""
Compare transcription quality across all three engines:
- VOSK only (VtoT2)
- Whisper only
- Hybrid (VtoT3)
"""
import subprocess
import json
import sys
import os

def run_transcription(script, audio_file, output_file):
    """Run a transcription script and save output."""
    print(f"\n{'='*70}")
    print(f"Running: {script}")
    print('='*70)
    
    try:
        result = subprocess.run(
            ["python", script, audio_file],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Try to parse JSON
        try:
            if result.stdout:
                data = json.loads(result.stdout)
            else:
                data = {"error": "no_output", "stderr": result.stderr}
        except:
            data = {
                "error": "parse_failed",
                "stdout": result.stdout[:500],
                "stderr": result.stderr[:500]
            }
        
        # Save output
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"[OK] Saved to: {output_file}")
        
        return data
        
    except subprocess.TimeoutExpired:
        print(f"[ERROR] Timeout after 5 minutes")
        return {"error": "timeout"}
    except Exception as e:
        print(f"[ERROR] {e}")
        return {"error": str(e)}

def display_comparison(vosk_result, hybrid_result):
    """Display side-by-side comparison."""
    print("\n" + "="*70)
    print("COMPARISON RESULTS")
    print("="*70)
    
    # VOSK Results
    print("\n[1] VOSK-ONLY (VtoT2)")
    print("-"*70)
    if 'text' in vosk_result:
        text = vosk_result.get('text', '')
        words = vosk_result.get('result', [])
        status = vosk_result.get('status', 'UNKNOWN')
        
        print(f"Status: {status}")
        if words:
            conf = sum(w.get('conf', 0) for w in words) / len(words)
            print(f"Words: {len(words)}")
            print(f"Avg Confidence: {conf:.1%}")
        print(f"Text: {text[:150]}...")
    else:
        print(f"Error: {vosk_result.get('error', 'unknown')}")
    
    # Hybrid Results
    print("\n[2] HYBRID (VOSK + Whisper)")
    print("-"*70)
    if 'text' in hybrid_result:
        text = hybrid_result.get('text', '')
        words = hybrid_result.get('words', [])
        metadata = hybrid_result.get('metadata', {})
        
        print(f"Status: {metadata.get('status', 'UNKNOWN')}")
        print(f"Whisper Model: {metadata.get('model_whisper', 'N/A')}")
        print(f"VOSK Words: {len(words)}")
        print(f"VOSK Confidence: {metadata.get('vosk_confidence', 0):.1%}")
        print(f"Text: {text[:150]}...")
    else:
        print(f"Error: {hybrid_result.get('error', 'unknown')}")
    
    # Comparison
    print("\n" + "="*70)
    print("KEY DIFFERENCES")
    print("="*70)
    
    if 'text' in vosk_result and 'text' in hybrid_result:
        vosk_text = vosk_result.get('text', '')
        hybrid_text = hybrid_result.get('text', '')
        
        print(f"\nVOSK Text ({len(vosk_text)} chars):")
        print(f"  {vosk_text[:200]}")
        print(f"\nHybrid Text ({len(hybrid_text)} chars):")
        print(f"  {hybrid_text[:200]}")
        
        print("\nNOTE:")
        print("  - VOSK: No punctuation, raw acoustic output")
        print("  - Hybrid: Whisper adds punctuation, capitalization, semantic coherence")

def main():
    audio_file = r"C:\Users\arnav\Downloads\Sales Call example 1.wav"
    
    if not os.path.exists(audio_file):
        print(f"[ERROR] Audio file not found: {audio_file}")
        sys.exit(1)
    
    print("="*70)
    print("TRANSCRIPTION ENGINE COMPARISON")
    print("="*70)
    print(f"\nAudio: {audio_file}")
    
    # Run VOSK-only
    vosk_result = run_transcription(
        "VtoT(2).py",
        audio_file,
        "comparison_vosk.json"
    )
    
    # Run Hybrid
    hybrid_result = run_transcription(
        "VtoT(3).py",
        audio_file,
        "comparison_hybrid.json"
    )
    
    # Display comparison
    display_comparison(vosk_result, hybrid_result)
    
    print("\n" + "="*70)
    print("Output files generated:")
    print("  - comparison_vosk.json")
    print("  - comparison_hybrid.json")
    print("="*70)

if __name__ == "__main__":
    main()
