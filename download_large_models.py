#!/usr/bin/env python3
"""
Download larger VOSK models for improved accuracy
Supports vosk-model-en-in-0.5 and vosk-model-en-us-0.22
"""
import urllib.request
import zipfile
import os
import sys

MODELS = {
    "vosk-model-en-in-0.5": {
        "url": "https://alphacephei.com/vosk/models/vosk-model-en-in-0.5.zip",
        "size": "1.0 GB",
        "description": "Indian English model - good for various accents"
    },
    "vosk-model-en-us-0.22": {
        "url": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip",
        "size": "1.8 GB",
        "description": "Large US English model - highest accuracy"
    }
}

def download_with_progress(url, filename):
    """Download file with progress bar"""
    def reporthook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        percent = min(downloaded / total_size * 100, 100) if total_size > 0 else 0
        mb_downloaded = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        print(f"\rProgress: {percent:.1f}% ({mb_downloaded:.1f}MB / {mb_total:.1f}MB)", end='')
    
    print(f"[INFO] Downloading from: {url}")
    urllib.request.urlretrieve(url, filename, reporthook)
    print()  # New line after progress

def extract_zip(zip_path, extract_to="."):
    """Extract ZIP file"""
    print(f"\n[INFO] Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print("[OK] Extraction complete!")

def verify_model(model_dir):
    """Verify model structure"""
    required_dirs = ['am', 'conf', 'graph']
    for dir_name in required_dirs:
        dir_path = os.path.join(model_dir, dir_name)
        if not os.path.exists(dir_path):
            return False
    return True

def main():
    print("=" * 70)
    print("VOSK LARGE MODEL DOWNLOADER")
    print("=" * 70)
    print()
    
    # Show available models
    print("Available models:")
    for i, (name, info) in enumerate(MODELS.items(), 1):
        print(f"{i}. {name}")
        print(f"   Size: {info['size']}")
        print(f"   Description: {info['description']}")
        print()
    
    # Get choice
    choice = input("Select model to download (1-2) or 'both' for all [1]: ").strip()
    
    models_to_download = []
    if choice == 'both':
        models_to_download = list(MODELS.keys())
    elif choice == '2':
        models_to_download = [list(MODELS.keys())[1]]
    else:
        models_to_download = [list(MODELS.keys())[0]]
    
    print()
    for model_name in models_to_download:
        model_info = MODELS[model_name]
        
        # Check if already exists
        if os.path.exists(model_name):
            print(f"[INFO] {model_name} already exists. Verifying...")
            if verify_model(model_name):
                print(f"[OK] {model_name} is valid. Skipping download.")
                continue
            else:
                print(f"[WARNING] {model_name} is incomplete. Re-downloading...")
        
        print(f"\n[1/3] DOWNLOADING {model_name}")
        print(f"Size: {model_info['size']} - This may take several minutes...")
        
        zip_filename = f"{model_name}.zip"
        
        try:
            download_with_progress(model_info['url'], zip_filename)
            print(f"[OK] Download complete!")
            
            print(f"\n[2/3] EXTRACTING")
            extract_zip(zip_filename)
            
            print(f"\n[3/3] VERIFYING")
            if verify_model(model_name):
                print(f"[OK] {model_name} verified successfully!")
            else:
                print(f"[ERROR] {model_name} verification failed!")
                sys.exit(1)
            
            # Cleanup
            print(f"\n[INFO] Cleaning up ZIP file...")
            os.remove(zip_filename)
            print(f"[OK] Cleanup complete")
            
        except Exception as e:
            print(f"\n[ERROR] Failed to download {model_name}: {e}")
            sys.exit(1)
    
    print("\n" + "=" * 70)
    print("SETUP COMPLETE!")
    print("=" * 70)
    print()
    print("Downloaded models:")
    for model_name in models_to_download:
        if os.path.exists(model_name):
            print(f"  - {model_name}")
    print()
    print("VtoT(2).py will automatically use the best available model.")
    print()

if __name__ == "__main__":
    main()
