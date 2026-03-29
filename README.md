# Call Audit Pipeline

A hybrid audio transcription system combining **VOSK** (timing + confidence) and **Whisper** (semantic accuracy + punctuation) — purpose-built for financial call auditing, PII detection, and compliance review.

## Why this exists

Manual call auditing in financial services is slow, inconsistent, and doesn't scale. This pipeline automates transcription with sentence-level timestamps and confidence scoring, enabling downstream compliance checks and QA review at volume.

## What it does

- Transcribes financial service calls from WAV/MP3 with sentence-level timestamps
- Runs VOSK and Whisper in parallel via ThreadPoolExecutor for speed
- Outputs structured JSON with confidence scores, sentence boundaries, and metadata
- Detects PII patterns (account numbers, names, dates) in transcript text
- Supports batch processing for call centre audit workflows

## Architecture
```
Audio ─┬─► VOSK ────► word timing + confidence scores
       │                        │
       └─► Whisper ─► text + punctuation + sentences
                                │
                         Combined JSON output
                                │
                    PII detection + compliance flags
```

## Tech stack

Python · Vosk · OpenAI Whisper · FFmpeg · ThreadPoolExecutor

## Output format
```json
{
  "text": "Thank you for calling. How can I help you today?",
  "sentences": [
    {"sentence": "Thank you for calling.", "start": 0.0, "end": 2.5},
    {"sentence": "How can I help you today?", "start": 2.5, "end": 5.1}
  ],
  "metadata": {
    "vosk_confidence": 0.913,
    "sentence_count": 2,
    "pii_flags": [],
    "status": "SUCCESS"
  }
}
```

## Quickstart
```bash
pip install vosk openai-whisper
# FFmpeg required — brew install ffmpeg / apt install ffmpeg
python src/transcribe.py path/to/call.wav
```

## Project structure
```
src/
  transcribe.py       # main hybrid pipeline
  pii_detector.py     # PII pattern matching
  audio_converter.py  # MP3/WAV handling via FFmpeg
tests/
requirements.txt
```

## Engineering notes

- Solved pydub Python 3.13 incompatibility by switching to direct FFmpeg subprocess calls
- Solved Whisper Windows FFmpeg path issue by loading audio manually via numpy
- Parallel execution cuts transcription time by ~40% vs sequential
