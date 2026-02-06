#!/usr/bin/env python3
"""
Wrapper script to run VtoT(2).py and save output to file
Demonstrates the agent's rejection logic and structured output
"""
import subprocess
import json
import sys

def run_vtot2(audio_file, output_file):
    """Run VtoT(2).py and save output to file"""
    print(f"[INFO] Running VtoT(2).py on: {audio_file}")
    
    try:
        result = subprocess.run(
            ["python", "VtoT(2).py", audio_file],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
        except:
            output_data = {
                "text": "",
                "result": [],
                "status": "ERROR",
                "reason": "failed_to_parse_output",
                "raw_output": result.stdout,
                "error": result.stderr
            }
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"[OK] Output saved to: {output_file}")
        print(f"[STATUS] {output_data.get('status', 'UNKNOWN')}")
        
        if output_data.get('status') == 'REJECTED':
            print(f"[REASON] {output_data.get('reason', 'unknown')}")
        elif output_data.get('status') == 'SUCCESS':
            word_count = len(output_data.get('result', []))
            print(f"[SUCCESS] Transcribed {word_count} words")
            print(f"[TEXT] {output_data.get('text', '')[:100]}...")
        
        return output_data
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return None

def main():
    print("=" * 70)
    print("VtoT(2) SPEECH TRANSCRIPTION AGENT - DEMO")
    print("=" * 70)
    print()
    
    # Test with available audio files
    test_cases = [
        ("sample_audio_v2.wav", "vtot2_sample_v2_output.json"),
        ("test_audio.wav", "vtot2_test_audio_output.json"),
    ]
    
    results = []
    for audio_file, output_file in test_cases:
        print(f"\nTest Case: {audio_file}")
        print("-" * 70)
        result = run_vtot2(audio_file, output_file)
        if result:
            results.append((audio_file, output_file, result))
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    
    for audio_file, output_file, result in results:
        status = result.get('status', 'UNKNOWN')
        reason = result.get('reason', '')
        
        print(f"File: {audio_file}")
        print(f"  Status: {status}")
        if reason:
            print(f"  Reason: {reason}")
        if status == 'SUCCESS':
            print(f"  Words: {len(result.get('result', []))}")
            print(f"  Text: {result.get('text', '')[:80]}...")
        print(f"  Output: {output_file}")
        print()

if __name__ == "__main__":
    main()
