# Vosk Voice-to-Text Transcription System

A complete Python-based voice-to-text transcription system using the Vosk speech recognition library. Supports both WAV and MP3 audio files with automatic conversion.

## Features

✅ **Multiple Audio Formats** - Supports .wav and .mp3 files  
✅ **Automatic Conversion** - Uses ffmpeg to convert MP3 to WAV  
✅ **Speaker Identification** - Identifies 2 speakers in conversations  
✅ **Timestamps** - Provides start/end times for each utterance  
✅ **Confidence Scores** - Per-utterance confidence metrics  
✅ **JSON Output** - Clean, structured transcription output  
✅ **Word-Level Stats** - Tracks words per speaker and utterance  

## Files

| File | Description |
|------|-------------|
| `VtoT(1).py` | Main transcription script with MP3 support |
| `test_vosk_model.py` | Comprehensive model testing |
| `simple_test.py` | Quick model verification |
| `download_vosk_model.py` | Auto-downloads Vosk model |

## Installation

### 1. Install Python Dependencies
```bash
pip install vosk
```

### 2. Install FFmpeg (for MP3 support)
**Windows:**
```powershell
choco install ffmpeg
# or
scoop install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg
```

**Mac:**
```bash
brew install ffmpeg
```

### 3. Download Vosk Model
Run the download script or manually download from [Vosk Models](https://alphacephei.com/vosk/models):
```bash
python download_vosk_model.py
```

Or download manually:
- Download: [vosk-model-small-en-us-0.15](https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip)
- Extract to project folder

## Usage

### Basic Usage
```bash
python VtoT(1).py
```

### With Your Own Audio
1. Update `AUDIO_FILE` in `VtoT(1).py`:
```python
AUDIO_FILE = "your_audio.mp3"  # or .wav
```

2. Run the script:
```bash
python VtoT(1).py
```

### Output
The script generates `transcription_output.json` with:
- Metadata (timestamp, model info, audio properties)
- Speaker statistics
- Conversation with timestamps
- Full transcript (plain text and formatted)

## Example Output

```json
{
  "metadata": {
    "generated_at": "2026-02-06T01:39:57.023935",
    "model": "vosk-model-small-en-us-0.15",
    "audio_file": "demo_conversation.mp3"
  },
  "conversation": [
    {
      "speaker": "Speaker_1",
      "start_time": 0.0,
      "end_time": 2.5,
      "text": "Hello, how are you doing today?",
      "confidence": 1.0
    }
  ]
}
```

## Testing

```bash
# Quick test
python simple_test.py

# Comprehensive test
python test_vosk_model.py
```

## Audio Requirements

For best results:
- **Format**: WAV or MP3
- **Sample Rate**: 16000 Hz (recommended)
- **Channels**: Mono (1 channel)
- **Quality**: Clear speech, minimal background noise

## Troubleshooting

### MP3 Conversion Fails
- Ensure ffmpeg is installed and in PATH
- Restart terminal after installing ffmpeg
- Or convert manually: `ffmpeg -i input.mp3 -ar 16000 -ac 1 output.wav`

### Model Not Found
- Download the Vosk model
- Extract to project directory
- Verify `vosk-model-small-en-us-0.15/` folder exists

### Low Accuracy
- Consider using a larger model for better accuracy
- Download: [vosk-model-en-us-0.22](https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip) (1.8GB)

## Project Structure

```
E:\HackProject\
├── VtoT(1).py                      # Main script
├── test_vosk_model.py              # Model test
├── simple_test.py                  # Quick test
├── README.md                       # This file
├── transcription_output.json       # Generated output
├── demo_conversation.wav           # Demo audio (optional)
└── vosk-model-small-en-us-0.15/   # Vosk model folder
    ├── am/
    ├── conf/
    ├── graph/
    └── ivector/
```

## License

This project uses the Vosk speech recognition library. See [Vosk License](https://github.com/alphacep/vosk-api) for details.

## Credits

- **Vosk**: Speech recognition toolkit by Alpha Cephei
- **FFmpeg**: Audio/video processing
