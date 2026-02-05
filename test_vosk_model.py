#!/usr/bin/env python3
"""Simple test script to verify Vosk model loads correctly"""
import os, sys

MODEL_PATH = "./vosk-model-small-en-us-0.15"

def print_result(step, success, msg, extra=""):
    status = "[OK]" if success else "[FAIL]"
    print(f"\n[{step}] {msg}\n{status} {extra}" if not extra else f"\n[{step}] {msg}\n{status}")
    if extra: print(f"     {extra}")
    return success

def test_vosk_model():
    print("=" * 50 + "\nVOSK Model Loading Test\n" + "=" * 50)
    
    # Step 1: Check Vosk installation
    try:
        import vosk
        version = vosk.__version__ if hasattr(vosk, '__version__') else 'Unknown'
        print_result(1, True, "Checking if vosk is installed...", f"Vosk library imported successfully\n     Vosk version: {version}")
    except ImportError as e:
        print_result(1, False, "Checking if vosk is installed...", f"Failed to import vosk\n       Error: {e}\n\n       Install vosk using: pip install vosk")
        return False
    
    # Step 2: Validate model structure
    missing = [f for f in ["am", "conf", "graph"] if not os.path.exists(os.path.join(MODEL_PATH, f))]
    if missing:
        print_result(2, False, "Checking model path...", f"Model directory incomplete. Missing: {', '.join(missing)}\n       Checked path: {os.path.abspath(MODEL_PATH)}")
        return False
    print_result(2, True, "Checking model path...", f"Model directory structure validated\n     Path: {os.path.abspath(MODEL_PATH)}")
    
    # Step 3: Load model
    try:
        model = vosk.Model(MODEL_PATH)
        print_result(3, True, "Loading the model...", f"Model loaded successfully!\n     Model type: {type(model)}")
        return True
    except Exception as e:
        print_result(3, False, "Loading the model...", f"Failed to load model\n       Error: {e}")
        return False

if __name__ == "__main__":
    print("\nRunning Vosk model test...\n")
    success = test_vosk_model()
    print("\n" + "=" * 50)
    print(f"RESULT: {'[OK] All tests passed! Model is ready to use.' if success else '[FAIL] Test failed. Please check the errors above.'}")
    print("=" * 50)
    sys.exit(0 if success else 1)
