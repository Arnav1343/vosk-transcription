#!/usr/bin/env python3
"""Very simple Vosk model loading test"""
import vosk

# Change this path to where your model is located
MODEL_PATH = "./vosk-model-small-en-us-0.15"  # Downloaded model location

print("Testing Vosk Model Loading...")
print(f"Model path: {MODEL_PATH}")
print("-" * 40)

try:
    print("Loading model...")
    model = vosk.Model(MODEL_PATH)
    print("[SUCCESS] Model loaded successfully!")
    print(f"Model object: {model}")
except Exception as e:
    print(f"[ERROR] Failed to load model: {e}")
    print("\nMake sure:")
    print("1. Vosk is installed (pip install vosk)")
    print("2. The model path contains: am/ conf/ graph/ folders")
    print("3. You've extracted the model files correctly")
