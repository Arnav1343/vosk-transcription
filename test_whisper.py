#!/usr/bin/env python3
"""
Test Whisper directly to diagnose the issue
"""
import whisper
import sys

def test_whisper():
    print("="*70)
    print("WHISPER STANDALONE TEST")
    print("="*70)
    print()
    
    audio_file = r"C:\Users\arnav\Downloads\Sales Call example 1.wav"
    
    print(f"[1/2] Loading Whisper base model...")
    model = whisper.load_model("base", device="cpu")
    print("[OK] Model loaded")
    print()
    
    print(f"[2/2] Transcribing audio...")
    print(f"File: {audio_file}")
    
    try:
        result = model.transcribe(
            audio_file,
            language="en",
            fp16=False,
            verbose=True  # Show progress
        )
        
        print()
        print("="*70)
        print("WHISPER RESULT")
        print("="*70)
        print()
        print(f"Text: {result['text']}")
        print(f"Language: {result.get('language', 'unknown')}")
        print(f"Segments: {len(result.get('segments', []))}")
        
        if result.get('segments'):
            print()
            print("First 3 segments:")
            for seg in result['segments'][:3]:
                print(f"  [{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")
        
    except Exception as e:
        print(f"\n[ERROR] Whisper failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_whisper()
