#!/usr/bin/env python3
"""Script to download and setup Vosk speech recognition model"""
import os, sys, urllib.request, zipfile
from pathlib import Path

MODEL_NAME = "vosk-model-small-en-us-0.15"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"
DOWNLOAD_DIR = "."

def download_file(url, filename):
    """Download file with progress indicator"""
    print(f"Downloading {filename}...")
    print(f"URL: {url}")
    
    def show_progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(downloaded * 100 / total_size, 100)
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            print(f"\rProgress: {percent:.1f}% ({downloaded_mb:.1f}MB / {total_mb:.1f}MB)", end='')
    
    try:
        urllib.request.urlretrieve(url, filename, show_progress)
        print("\n[OK] Download complete!")
        return True
    except Exception as e:
        print(f"\n[FAIL] Download failed: {e}")
        return False

def extract_zip(zip_path, extract_to):
    """Extract ZIP file"""
    print(f"\nExtracting {zip_path}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print("[OK] Extraction complete!")
        return True
    except Exception as e:
        print(f"[FAIL] Extraction failed: {e}")
        return False

def verify_model(model_dir):
    """Verify model structure"""
    print(f"\nVerifying model structure...")
    required = ["am", "conf", "graph"]
    missing = [f for f in required if not os.path.exists(os.path.join(model_dir, f))]
    
    if missing:
        print(f"[FAIL] Missing: {', '.join(missing)}")
        return False
    print("[OK] Model structure verified!")
    return True

def main():
    print("=" * 60)
    print("VOSK MODEL DOWNLOAD AND SETUP")
    print("=" * 60)
    
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    zip_filename = os.path.join(DOWNLOAD_DIR, f"{MODEL_NAME}.zip")
    model_dir = os.path.join(DOWNLOAD_DIR, MODEL_NAME)
    
    if os.path.exists(model_dir):
        print(f"\n[INFO] Model already exists: {model_dir}")
        if verify_model(model_dir):
            print("\n[OK] Model ready to use!")
            return
    
    print("\n[1/3] DOWNLOADING")
    if not download_file(MODEL_URL, zip_filename):
        sys.exit(1)
    
    print("\n[2/3] EXTRACTING")
    if not extract_zip(zip_filename, DOWNLOAD_DIR):
        sys.exit(1)
    
    print("\n[3/3] VERIFYING")
    if not verify_model(model_dir):
        sys.exit(1)
    
    try:
        os.remove(zip_filename)
        print(f"\n[OK] Cleanup complete")
    except:
        pass
    
    print("\n" + "=" * 60)
    print("SETUP COMPLETE!")
    print("=" * 60)
    print(f"\nModel: {os.path.abspath(model_dir)}")
    print("\nReady to use with VtoT(1).py!")

if __name__ == "__main__":
    main()
