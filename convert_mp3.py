#!/usr/bin/env python3
"""Quick MP3 to WAV converter for Vosk - finds ffmpeg automatically"""
import subprocess
import sys
import os
from pathlib import Path

def find_ffmpeg():
    """Try to find ffmpeg in common installation locations"""
    # Common Windows paths
    common_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        str(Path.home() / "scoop" / "shims" / "ffmpeg.exe"),
    ]
    
    # Check if ffmpeg is in PATH
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=2)
        if result.returncode == 0:
            return 'ffmpeg'
    except:
        pass
    
    # Check common paths
    for path in common_paths:
        if os.path.exists(path):
            print(f"[INFO] Found ffmpeg at: {path}")
            return path
    
    return None

def convert_mp3_to_wav(mp3_file):
    """Convert MP3 to WAV using ffmpeg"""
    ffmpeg_path = find_ffmpeg()
    
    if not ffmpeg_path:
        print("[ERROR] ffmpeg not found!")
        print("[INFO] Please add ffmpeg to your PATH or install it")
        print("  Download: https://ffmpeg.org/download.html")
        return False
    
    wav_file = mp3_file.rsplit('.', 1)[0] + '_converted.wav'
    
    print(f"[INFO] Converting {mp3_file} to {wav_file}...")
    
    try:
        result = subprocess.run([
            ffmpeg_path, '-i', mp3_file,
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',      # Mono
            '-y',            # Overwrite
            wav_file
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"[OK] Converted successfully!")
            print(f"[OK] Output: {wav_file}")
            return True
        else:
            print(f"[ERROR] Conversion failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    mp3_file = "demo_conversation.mp3"
    if len(sys.argv) > 1:
        mp3_file = sys.argv[1]
    
    if not os.path.exists(mp3_file):
        print(f"[ERROR] File not found: {mp3_file}")
        sys.exit(1)
    
    success = convert_mp3_to_wav(mp3_file)
    sys.exit(0 if success else 1)
