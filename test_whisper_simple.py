#!/usr/bin/env python3
"""Simple Whisper test with manual WAV loading"""
import whisper
import wave
import numpy as np
import sys

audio_file = r"C:\Users\arnav\Downloads\Sales Call example 1.wav"

print("Loading Whisper base model...")
model = whisper.load_model("base", device="cpu")

print(f"Loading audio: {audio_file}")
with wave.open(audio_file, 'rb') as wf:
    sample_rate = wf.getframerate()
    frames = wf.readframes(wf.getnframes())
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Audio length: {len(audio)} samples ({len(audio)/sample_rate:.1f} seconds)")

print("\nTranscribing...")
try:
    result = model.transcribe(audio, fp16=False, verbose=False)
    print(f"\nSUCCESS!")
    print(f"Text: {result['text']}")
    print(f"Language: {result.get('language', 'unknown')}")
except Exception as e:
    print(f"\nFAILED: {e}")
    import traceback
    traceback.print_exc()
