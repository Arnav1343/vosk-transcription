"""
Hybrid VOSK + Whisper Transcription Agent - VtoT(3).py
Combines VOSK timing and confidence scores with Whisper semantic accuracy.

Output Format:
{
    "text": "Whisper transcription with punctuation and capitalization",
    "sentences": [
        {"sentence": "Hello, how are you?", "start": 0.0, "end": 2.5, "duration": 2.5}
    ],
    "metadata": {
        "model_whisper": "base",
        "model_vosk": "vosk-model-small-en-us-0.15",
        "vosk_confidence": 0.72,
        "whisper_language": "en",
        "sentence_count": 10,
        "status": "SUCCESS"
    }
}
"""
import json
import os
import sys
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Optional, Dict, List

try:
    import whisper
except ImportError:
    print(json.dumps({
        "text": "",
        "words": [],
        "metadata": {"status": "ERROR", "reason": "whisper_not_installed"}
    }))
    sys.exit(1)

try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
except ImportError:
    print(json.dumps({
        "text": "",
        "words": [],
        "metadata": {"status": "ERROR", "reason": "vosk_not_installed"}
    }))
    sys.exit(1)


class HybridTranscriptionAgent:
    """
    Hybrid transcription combining VOSK (timing/confidence) and Whisper (semantic).
    
    Design:
    - VOSK: Word-level timestamps and confidence scores
    - Whisper: Semantic accuracy, punctuation, capitalization
    - CPU-only operation (batch transcription)
    - Reliability-first approach
    """
    
    # Quality thresholds
    MIN_VOSK_CONFIDENCE = 0.40  # Lower threshold since Whisper provides semantics
    MIN_WORDS_REQUIRED = 3
    
    def __init__(self, vosk_model_path: str, whisper_model: str = "base"):
        """
        Initialize hybrid transcription agent.
        
        Args:
            vosk_model_path: Path to VOSK model directory
            whisper_model: Whisper model name (tiny/base/small/medium/large)
        """
        SetLogLevel(-1)  # Suppress VOSK logs
        
        # Load VOSK model
        if not os.path.exists(vosk_model_path):
            raise FileNotFoundError(f"VOSK model not found: {vosk_model_path}")
        
        print(f"[INFO] Loading VOSK model: {vosk_model_path}", file=sys.stderr)
        self.vosk_model = Model(vosk_model_path)
        self.vosk_model_name = os.path.basename(vosk_model_path)
        self.sample_rate = 16000
        
        # Load Whisper model (CPU-only)
        print(f"[INFO] Loading Whisper model '{whisper_model}' (CPU-only)...", file=sys.stderr)
        self.whisper_model = whisper.load_model(whisper_model, device="cpu")
        self.whisper_model_name = whisper_model
    
    def _convert_to_wav(self, input_path: str) -> Optional[str]:
        """Convert audio to 16kHz mono WAV using FFmpeg."""
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav.close()
        
        try:
            cmd = [
                'ffmpeg', '-y', '-i', input_path,
                '-ar', str(self.sample_rate),  # 16000 Hz
                '-ac', '1',                      # Mono
                '-c:a', 'pcm_s16le',            # 16-bit PCM
                '-f', 'wav',
                temp_wav.name
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            
            if result.returncode != 0:
                os.unlink(temp_wav.name)
                return None
            
            return temp_wav.name
            
        except Exception:
            if os.path.exists(temp_wav.name):
                os.unlink(temp_wav.name)
            return None
    
    def _transcribe_vosk(self, wav_path: str) -> Dict:
        """Get VOSK transcription for timing and confidence."""
        print("[INFO] Running VOSK transcription...", file=sys.stderr)
        
        with wave.open(wav_path, 'rb') as wf:
            recognizer = KaldiRecognizer(self.vosk_model, wf.getframerate())
            recognizer.SetWords(True)
            
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    if 'result' in result:
                        results.extend(result['result'])
            
            # Final result
            final = json.loads(recognizer.FinalResult())
            if 'result' in final:
                results.extend(final['result'])
        
        # Calculate average confidence
        if results:
            avg_conf = sum(w.get('conf', 0) for w in results) / len(results)
        else:
            avg_conf = 0.0
        
        return {
            'words': results,
            'avg_confidence': avg_conf,
            'word_count': len(results)
        }
    
    def _transcribe_whisper(self, wav_path: str) -> Dict:
        """Get Whisper transcription for semantic accuracy."""
        print("[INFO] Running Whisper transcription (this may take a minute)...", file=sys.stderr)
        
        try:
            # Workaround for Windows ffmpeg issue: load audio manually
            # Whisper's internal audio.load_audio() fails with subprocess on Windows
            # So we load the WAV file directly and pass numpy array instead
            import wave
            import numpy as np
            
            with wave.open(wav_path, 'rb') as wf:
                sample_rate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
                
                # Convert bytes to numpy array
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                
                # NOTE: No resampling needed - FFmpeg already preprocessed to 16kHz
                print(f"[INFO] Loaded {len(audio)} samples at {sample_rate}Hz", file=sys.stderr)
            
            # Pass numpy array to Whisper instead of file path
            result = self.whisper_model.transcribe(
                audio,
                language="en",
                fp16=False,  # CPU mode
                verbose=False
            )
            
            return {
                'text': result['text'].strip(),
                'language': result.get('language', 'en'),
                'segments': result.get('segments', [])
            }
        except Exception as e:
            print(f"[ERROR] Whisper transcription failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return {
                'text': '',
                'language': 'en',
                'segments': [],
                'error': str(e)
            }
    
    def _combine_results(self, vosk_result: Dict, whisper_result: Dict) -> Dict:
        """Combine VOSK timing with Whisper semantic text."""
        
        # Primary text from Whisper
        text = whisper_result.get('text', '')
        
        # Sentence-level output from Whisper segments
        segments = whisper_result.get('segments', [])
        sentences = []
        for seg in segments:
            sentences.append({
                'sentence': seg.get('text', '').strip(),
                'start': round(seg.get('start', 0), 2),
                'end': round(seg.get('end', 0), 2),
                'duration': round(seg.get('end', 0) - seg.get('start', 0), 2)
            })
        
        # Metadata
        metadata = {
            'model_whisper': self.whisper_model_name,
            'model_vosk': self.vosk_model_name,
            'vosk_confidence': round(vosk_result.get('avg_confidence', 0), 3),
            'vosk_word_count': vosk_result.get('word_count', 0),
            'whisper_language': whisper_result.get('language', 'en'),
            'sentence_count': len(sentences),
            'status': 'SUCCESS'
        }
        
        # Quality check
        if not text:
            metadata['status'] = 'REJECTED'
            metadata['reason'] = 'no_whisper_transcription'
        elif vosk_result.get('word_count', 0) < self.MIN_WORDS_REQUIRED:
            metadata['status'] = 'REJECTED'
            metadata['reason'] = 'insufficient_vosk_words'
        elif vosk_result.get('avg_confidence', 0) < self.MIN_VOSK_CONFIDENCE:
            metadata['status'] = 'WARNING'
            metadata['reason'] = 'low_vosk_confidence'
        
        return {
            'text': text,
            'sentences': sentences,
            'metadata': metadata
        }
    
    def transcribe(self, audio_path: str) -> Dict:
        """
        Transcribe audio using hybrid VOSK + Whisper approach.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with transcription results
        """
        # Validate input
        if not os.path.exists(audio_path):
            return {
                'text': '',
                'words': [],
                'metadata': {
                    'status': 'ERROR',
                    'reason': 'file_not_found'
                }
            }
        
        print(f"\n[INFO] Processing: {audio_path}", file=sys.stderr)
        
        # ALWAYS preprocess audio to 16kHz mono PCM for best results
        # Both VOSK and Whisper work best with 16kHz audio
        wav_path = None
        cleanup_wav = False
        
        print("[INFO] Preprocessing audio to 16kHz mono PCM...", file=sys.stderr)
        wav_path = self._convert_to_wav(audio_path)
        cleanup_wav = True
        
        if wav_path is None:
            return {
                'text': '',
                'words': [],
                'metadata': {
                    'status': 'ERROR',
                    'reason': 'audio_preprocessing_failed'
                }
            }
        
        try:
            # Run both engines IN PARALLEL for faster processing
            from concurrent.futures import ThreadPoolExecutor
            
            print("[INFO] Running VOSK and Whisper in parallel...", file=sys.stderr)
            
            with ThreadPoolExecutor(max_workers=2) as executor:
                vosk_future = executor.submit(self._transcribe_vosk, wav_path)
                whisper_future = executor.submit(self._transcribe_whisper, wav_path)
                
                # Wait for both to complete
                vosk_result = vosk_future.result()
                whisper_result = whisper_future.result()
            
            # Combine results
            combined = self._combine_results(vosk_result, whisper_result)
            
            print(f"[OK] Transcription complete", file=sys.stderr)
            print(f"[INFO] Status: {combined['metadata']['status']}", file=sys.stderr)
            
            return combined
            
        finally:
            # Cleanup
            if cleanup_wav and wav_path and os.path.exists(wav_path):
                try:
                    os.unlink(wav_path)
                except:
                    pass


def find_vosk_model() -> Optional[str]:
    """Find VOSK model (prefer larger models)."""
    paths = [
        "vosk-model-en-in-0.5",
        "vosk-model-en-us-0.22",
        "vosk-model-small-en-us-0.15",
        "model",
        os.path.expanduser("~/vosk-model-en-in-0.5"),
        os.path.expanduser("~/vosk-model-en-us-0.22"),
        os.path.expanduser("~/vosk-model-small-en-us-0.15"),
    ]
    
    for path in paths:
        if os.path.exists(path) and os.path.isdir(path):
            return path
    
    return None


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(json.dumps({
            'text': '',
            'words': [],
            'metadata': {
                'status': 'ERROR',
                'reason': 'no_input_file'
            }
        }, indent=2))
        sys.exit(1)
    
    audio_path = sys.argv[1]
    
    # Find VOSK model
    vosk_model_path = find_vosk_model()
    if not vosk_model_path:
        print(json.dumps({
            'text': '',
            'words': [],
            'metadata': {
                'status': 'ERROR',
                'reason': 'vosk_model_not_found'
            }
        }, indent=2))
        sys.exit(1)
    
    # Whisper model (default: base)
    whisper_model = sys.argv[2] if len(sys.argv) >= 3 else "base"
    
    try:
        agent = HybridTranscriptionAgent(vosk_model_path, whisper_model)
        result = agent.transcribe(audio_path)
        print(json.dumps(result, indent=2))
        
        # Exit code based on status
        status = result['metadata'].get('status', 'ERROR')
        if status == 'SUCCESS':
            sys.exit(0)
        elif status == 'WARNING':
            sys.exit(0)  # Still usable
        else:
            sys.exit(1)
    
    except Exception as e:
        print(json.dumps({
            'text': '',
            'words': [],
            'metadata': {
                'status': 'ERROR',
                'reason': 'initialization_error',
                'error': str(e)
            }
        }, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
