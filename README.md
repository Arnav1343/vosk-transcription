# Vosk + Whisper Transcription System

A hybrid voice-to-text transcription system combining **VOSK** for timing/confidence and **Whisper** for semantic accuracy.

## Features

✅ **Hybrid Engine** - Best of both VOSK and Whisper  
✅ **Sentence-Level Output** - Clean sentences with timestamps  
✅ **Punctuation & Capitalization** - Proper formatting via Whisper  
✅ **Parallel Processing** - Both engines run simultaneously  
✅ **Multiple Audio Formats** - WAV, MP3, and more via ffmpeg  
✅ **Confidence Scores** - Quality metrics for each transcription  

## Transcription Scripts

| Script | Engine | Best For |
|--------|--------|----------|
| `VtoT(1).py` | VOSK only | Quick transcription, speaker alternation |
| `VtoT(2).py` | VOSK only | Production use with validation |
| `VtoT(3).py` | **VOSK + Whisper** | Highest accuracy, punctuation |

## Quick Start

```bash
# Install dependencies
pip install vosk openai-whisper

# Run hybrid transcription (recommended)
python "VtoT(3).py" "path/to/audio.wav"
```

## Output Format (VtoT(3))

```json
{
  "text": "Thank you for calling. How can I help you?",
  "sentences": [
    {"sentence": "Thank you for calling.", "start": 0.0, "end": 2.5, "duration": 2.5},
    {"sentence": "How can I help you?", "start": 2.5, "end": 4.5, "duration": 2.0}
  ],
  "metadata": {
    "vosk_confidence": 0.913,
    "sentence_count": 2,
    "status": "SUCCESS"
  }
}
```

## Architecture

```
Audio ─┬─► VOSK ────► timing + confidence (91.3%)
       │
       └─► Whisper ─► text + punctuation + sentences
                              │
                              ▼
                      Combined Output
```

## How It Works

| Model | Purpose |
|-------|---------|
| **Whisper** | Semantic accuracy, punctuation, capitalization |
| **VOSK** | Word timestamps, confidence scores |

Both run **in parallel** using `ThreadPoolExecutor` for faster processing.

## Requirements

- Python 3.8+
- FFmpeg (for audio conversion)
- VOSK model (auto-detected from `vosk-model-*` folders)

### Install FFmpeg

**Windows:** `choco install ffmpeg` or `scoop install ffmpeg`  
**Linux:** `sudo apt install ffmpeg`  
**Mac:** `brew install ffmpeg`

## Development History

| Version | Engine | Key Changes |
|---------|--------|-------------|
| VtoT(1) | VOSK | Basic transcription, MP3 support via ffmpeg |
| VtoT(2) | VOSK | Added validation, rejection metrics, CLI args |
| VtoT(3) | Hybrid | Added Whisper, parallel execution, sentence output |

### Problems Solved

- **pydub Python 3.13 issue** → Direct ffmpeg subprocess
- **Whisper Windows ffmpeg error** → Manual numpy audio loading
- **No punctuation** → Added Whisper for semantic accuracy
- **Slow processing** → Parallel execution with ThreadPoolExecutor

## License

Uses VOSK (Apache 2.0) and OpenAI Whisper (MIT).
