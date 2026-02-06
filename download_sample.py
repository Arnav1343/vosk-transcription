#!/usr/bin/env python3
"""Download a sample audio file with speech for testing"""
import urllib.request
import os

def download_sample_audio():
    """Download a sample audio file from Vosk's examples"""
    url = "https://alphacephei.com/vosk/models/test.wav"
    output_file = "sample_speech.wav"
    
    if os.path.exists(output_file):
        print(f"[INFO] Sample audio already exists: {output_file}")
        return output_file
    
    print(f"[INFO] Downloading sample audio from {url}...")
    try:
        urllib.request.urlretrieve(url, output_file)
        print(f"[OK] Downloaded: {output_file}")
        return output_file
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        return None

if __name__ == "__main__":
    audio_file = download_sample_audio()
    if audio_file:
        print(f"\n✓ Ready to transcribe: {audio_file}")
