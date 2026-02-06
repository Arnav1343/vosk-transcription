#!/usr/bin/env python3
"""Wrapper to run VtoT(1).py with sales call audio"""
import subprocess
import json
import sys

def run_vtot1_on_sales_call():
    """Run VtoT(1).py on the sales call audio"""
    audio_file = r"C:\Users\arnav\Downloads\Sales Call example 1.wav"
    output_file = "sales_call_vtot1_output.json"
    
    print("[INFO] Running VtoT(1).py on sales call audio...")
    print(f"[INPUT] {audio_file}")
    
    # We need to modify VtoT(1).py to accept command-line arguments
    # For now, let's create a custom version that uses the sales call
    
    # Since VtoT(1).py has hardcoded paths, we'll need to copy and modify it
    print("[INFO] VtoT(1).py uses hardcoded AUDIO_FILE path")
    print("[INFO] Creating wrapper transcription...")
    
    # Import and run transcription directly
    import os
    import wave
    import vosk
    from datetime import datetime
    
    MODEL_PATH = "./vosk-model-small-en-us-0.15"
    
    # Convert to WAV if needed
    wav_file = audio_file
    if audio_file.lower().endswith('.mp3'):
        print("[INFO] Converting MP3 to WAV...")
        import subprocess
        wav_file = "temp_sales_call.wav"
        subprocess.run([
            'ffmpeg', '-i', audio_file,
            '-ar', '16000', '-ac', '1', '-y', wav_file
        ], capture_output=True, shell=True)
    
    # Transcribe
    print("[INFO] Loading Vosk model...")
    model = vosk.Model(MODEL_PATH)
    
    print("[INFO] Transcribing audio...")
    wf = wave.open(wav_file, "rb")
    rec = vosk.KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)
    
    results = []
    frame_count = 0
    total_frames = wf.getnframes()
    
    while True:
        data = wf.readframes(4000)
        if not data:
            break
        frame_count += 4000
        progress = min((frame_count / total_frames) * 100, 100)
        print(f"\rProgress: {progress:.1f}%", end='')
        
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            if result.get('text'):
                results.append(result)
    
    final = json.loads(rec.FinalResult())
    if final.get('text'):
        results.append(final)
    
    wf.close()
    print("\n[OK] Transcription complete")
    
    # Get audio info
    with wave.open(wav_file, "rb") as wf:
        audio_info = {
            "channels": wf.getnchannels(),
            "frame_rate": wf.getframerate(),
            "duration": wf.getnframes() / float(wf.getframerate())
        }
    
    # Format output (VtoT1 style)
    conversation = []
    for idx, result in enumerate(results):
        text = result.get('text', '').strip()
        if not text:
            continue
        
        words = result.get('result', [])
        start_time = words[0].get('start', idx * 2.5) if words else idx * 2.5
        end_time = words[-1].get('end', start_time + 2.0) if words else start_time + 2.0
        speaker = "Speaker_1" if idx % 2 == 0 else "Speaker_2"
        confidence = result.get('confidence', 1.0)
        
        if words and 'conf' in words[0]:
            confidence = sum(w.get('conf', 1.0) for w in words) / len(words)
        
        conversation.append({
            "speaker": speaker,
            "start_time": round(start_time, 2),
            "end_time": round(end_time, 2),
            "duration": round(end_time - start_time, 2),
            "text": text,
            "confidence": round(confidence, 3),
            "word_count": len(text.split())
        })
    
    total_words = sum(c['word_count'] for c in conversation)
    avg_confidence = sum(c['confidence'] for c in conversation) / len(conversation) if conversation else 0
    
    # Count speakers
    speakers = {}
    for c in conversation:
        if c['speaker'] not in speakers:
            speakers[c['speaker']] = {"utterances": 0, "total_words": 0}
        speakers[c['speaker']]['utterances'] += 1
        speakers[c['speaker']]['total_words'] += c['word_count']
    
    output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "model": "vosk-model-small-en-us-0.15",
            "audio_file": audio_file,
            "audio_properties": {
                "duration_seconds": round(audio_info['duration'], 2),
                "sample_rate_hz": audio_info['frame_rate'],
                "channels": audio_info['channels'],
                "format": "WAV"
            },
            "conversation_stats": {
                "total_speakers": len(speakers),
                "total_utterances": len(conversation),
                "total_words": total_words,
                "average_confidence": round(avg_confidence, 3)
            }
        },
        "speakers": speakers,
        "conversation": conversation,
        "full_transcript": {
            "text": " ".join([c['text'] for c in conversation]),
            "formatted": "\n".join([f"[{c['start_time']}s] {c['speaker']}: {c['text']}" for c in conversation])
        }
    }
    
    # Save output
    print(f"\n[INFO] Saving to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Saved successfully!")
    
    # Display summary
    stats = output['metadata']['conversation_stats']
    print("\n" + "=" * 70)
    print("VTOT(1) TRANSCRIPTION COMPLETE")
    print("=" * 70)
    print(f"\nStatistics:")
    print(f"   - Speakers: {stats['total_speakers']}")
    print(f"   - Utterances: {stats['total_utterances']}")
    print(f"   - Words: {stats['total_words']}")
    print(f"   - Average Confidence: {stats['average_confidence']:.1%}")
    print(f"\n[OUTPUT] {output_file}")

if __name__ == "__main__":
    run_vtot1_on_sales_call()
