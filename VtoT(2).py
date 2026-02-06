"""
Speech Transcription Agent - VtoT(2).py
A neutral speech-to-text transcription layer using the VOSK engine.
Outputs structured JSON containing only factual speech recognition data.
This agent performs NO interpretation, sentiment analysis, emotion detection,
or business logic. It serves strictly as a data extraction layer.
Output Format:
{
    "text": "verbatim transcription",
    "result": [
        {"word": "hello", "start": 0.0, "end": 0.5, "conf": 0.95},
        ...
    ],
    "status": "SUCCESS" | "REJECTED",
    "reason": "..." (only if rejected)
}
"""
import json
import os
import sys
import subprocess
import tempfile
import wave
from typing import Optional
from pathlib import Path
try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
except ImportError:
    print(json.dumps({
        "text": "",
        "result": [],
        "status": "REJECTED",
        "reason": "vosk_module_not_installed"
    }))
    sys.exit(1)
class SpeechTranscriptionAgent:
    """
    A neutral transcription agent using VOSK speech-to-text.
    
    Responsibilities:
    - Convert audio to text using VOSK
    - Output structured JSON with word-level timing and confidence
    - Reject unclear/corrupted audio with explicit status
    
    Non-responsibilities:
    - No emotion detection
    - No sentiment analysis
    - No stress inference
    - No confidence judgment beyond acoustic scores
    - No business rules or domain-specific logic
    """
    
    # Configuration thresholds for rejection (updated for better quality)
    MIN_AVERAGE_CONFIDENCE = 0.55
    MIN_WORDS_REQUIRED = 3  # Require at least 3 words for valid transcription
    MAX_LOW_CONF_RATIO = 0.6  # Reject if >60% of words have conf < 0.55
    
    def __init__(self, model_path: str):
        """
        Initialize the transcription agent with a VOSK model.
        
        Args:
            model_path: Path to the VOSK model directory
        """
        SetLogLevel(-1)  # Suppress VOSK logs
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at: {model_path}")
        
        self.model = Model(model_path)
        self.sample_rate = 16000  # VOSK requires 16kHz mono audio
    
    def _convert_to_wav(self, input_path: str) -> Optional[str]:
        """
        Convert audio file to 16kHz mono WAV using ffmpeg.
        
        Args:
            input_path: Path to input audio file
            
        Returns:
            Path to converted WAV file, or None if conversion fails
        """
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav.close()
        
        try:
            # Use exact FFmpeg command for VOSK preprocessing:
            # mono, 16-bit PCM, 16kHz sample rate
            cmd = [
                'ffmpeg', '-y', '-i', input_path,
                '-ar', str(self.sample_rate),  # 16000 Hz
                '-ac', '1',                      # Mono
                '-c:a', 'pcm_s16le',            # 16-bit PCM little-endian
                '-f', 'wav',
                temp_wav.name
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120
            )
            
            if result.returncode != 0:
                os.unlink(temp_wav.name)
                return None
                
            return temp_wav.name
            
        except Exception:
            if os.path.exists(temp_wav.name):
                os.unlink(temp_wav.name)
            return None
    
    def _validate_wav_file(self, wav_path: str) -> tuple[bool, str]:
        """
        Validate WAV file for transcription suitability.
        
        Args:
            wav_path: Path to WAV file
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        try:
            with wave.open(wav_path, 'rb') as wf:
                # Check for zero-length audio
                if wf.getnframes() == 0:
                    return False, "zero_length_audio"
                
                # Check duration (at least 0.1 seconds)
                duration = wf.getnframes() / wf.getframerate()
                if duration < 0.1:
                    return False, "audio_too_short"
                
                return True, ""
                
        except Exception as e:
            return False, "corrupted_audio_file"
    
    def _calculate_rejection_metrics(self, result: list) -> tuple[bool, str]:
        """
        Analyze transcription results to determine if rejection is warranted.
        
        Args:
            result: List of word dictionaries from VOSK
            
        Returns:
            Tuple of (should_reject, reason)
        """
        if not result:
            return True, "no_recognizable_speech"
        
        if len(result) < self.MIN_WORDS_REQUIRED:
            return True, "insufficient_recognizable_speech"
        
        # Calculate average confidence
        confidences = [word.get('conf', 0) for word in result]
        avg_confidence = sum(confidences) / len(confidences)
        
        if avg_confidence < self.MIN_AVERAGE_CONFIDENCE:
            return True, "low_average_confidence"
        
        # Check ratio of low-confidence words
        low_conf_count = sum(1 for c in confidences if c < 0.5)
        low_conf_ratio = low_conf_count / len(confidences)
        
        if low_conf_ratio > self.MAX_LOW_CONF_RATIO:
            return True, "excessive_low_confidence_words"
        
        return False, ""
    
    def _validate_timestamps(self, result: list) -> list:
        """
        Ensure timestamps are non-decreasing and properly ordered.
        
        Args:
            result: List of word dictionaries
            
        Returns:
            Validated and corrected result list
        """
        validated = []
        last_end = 0.0
        
        for word_data in result:
            start = word_data.get('start', last_end)
            end = word_data.get('end', start + 0.1)
            
            # Ensure non-decreasing timestamps
            if start < last_end:
                start = last_end
            if end < start:
                end = start + 0.1
            
            validated.append({
                'word': word_data.get('word', ''),
                'start': round(start, 3),
                'end': round(end, 3),
                'conf': round(word_data.get('conf', 0.0), 3)
            })
            
            last_end = end
        
        return validated
    
    def transcribe(self, audio_path: str) -> dict:
        """
        Transcribe audio file to structured JSON.
        
        Args:
            audio_path: Path to audio file (WAV, MP3, or other ffmpeg-supported format)
            
        Returns:
            Dictionary containing transcription results or rejection status
        """
        # Check if input file exists
        if not os.path.exists(audio_path):
            return {
                "text": "",
                "result": [],
                "status": "REJECTED",
                "reason": "input_file_not_found"
            }
        
        # Check file size
        if os.path.getsize(audio_path) == 0:
            return {
                "text": "",
                "result": [],
                "status": "REJECTED",
                "reason": "zero_length_file"
            }
        
        # Convert to WAV if necessary
        wav_path = None
        cleanup_wav = False
        
        if audio_path.lower().endswith('.wav'):
            wav_path = audio_path
        else:
            wav_path = self._convert_to_wav(audio_path)
            cleanup_wav = True
            
            if wav_path is None:
                return {
                    "text": "",
                    "result": [],
                    "status": "REJECTED",
                    "reason": "audio_conversion_failed"
                }
        
        try:
            # Validate WAV file
            is_valid, validation_reason = self._validate_wav_file(wav_path)
            if not is_valid:
                return {
                    "text": "",
                    "result": [],
                    "status": "REJECTED",
                    "reason": validation_reason
                }
            
            # Perform transcription
            all_results = []
            
            with wave.open(wav_path, 'rb') as wf:
                recognizer = KaldiRecognizer(self.model, wf.getframerate())
                recognizer.SetWords(True)  # Enable word-level timestamps
                
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    recognizer.AcceptWaveform(data)
                
                # Get final result
                final_result = json.loads(recognizer.FinalResult())
                
                if 'result' in final_result:
                    all_results.extend(final_result['result'])
            
            # Check for rejection conditions
            should_reject, rejection_reason = self._calculate_rejection_metrics(all_results)
            
            if should_reject:
                # Return partial data with rejection status
                partial_text = ' '.join(word.get('word', '') for word in all_results)
                return {
                    "text": partial_text,
                    "result": [],
                    "status": "REJECTED",
                    "reason": rejection_reason
                }
            
            # Validate and normalize timestamps
            validated_results = self._validate_timestamps(all_results)
            
            # Build final text from validated results
            full_text = ' '.join(word['word'] for word in validated_results)
            
            return {
                "text": full_text,
                "result": validated_results,
                "status": "SUCCESS"
            }
            
        except Exception as e:
            return {
                "text": "",
                "result": [],
                "status": "REJECTED",
                "reason": "transcription_engine_error"
            }
            
        finally:
            # Cleanup temporary WAV file
            if cleanup_wav and wav_path and os.path.exists(wav_path):
                try:
                    os.unlink(wav_path)
                except:
                    pass
def find_vosk_model() -> Optional[str]:
    """
    Attempt to locate a VOSK model in common locations.
    Prefers larger, more accurate models over small models.
    
    Returns:
        Path to model directory, or None if not found
    """
    # Prefer larger, more accurate models (ordered by preference)
    common_paths = [
        # Preferred: Indian English model (good for accents)
        "vosk-model-en-in-0.5",
        os.path.expanduser("~/vosk-model-en-in-0.5"),
        "C:/vosk-model-en-in-0.5",
        os.path.join(os.path.dirname(__file__), "vosk-model-en-in-0.5"),
        
        # Fallback: Large US English model
        "vosk-model-en-us-0.22",
        os.path.expanduser("~/vosk-model-en-us-0.22"),
        "C:/vosk-model-en-us-0.22",
        os.path.join(os.path.dirname(__file__), "vosk-model-en-us-0.22"),
        
        # Last resort: Small model (less accurate)
        "vosk-model-small-en-us-0.15",
        os.path.expanduser("~/vosk-model-small-en-us-0.15"),
        "C:/vosk-model-small-en-us-0.15",
        os.path.join(os.path.dirname(__file__), "vosk-model-small-en-us-0.15"),
        
        # Generic fallback
        "model",
    ]
    
    for path in common_paths:
        if os.path.exists(path) and os.path.isdir(path):
            return path
    
    return None
def main():
    """
    Main entry point for command-line usage.
    
    Usage:
        python VtoT(2).py <audio_file> [model_path]
    """
    if len(sys.argv) < 2:
        print(json.dumps({
            "text": "",
            "result": [],
            "status": "REJECTED",
            "reason": "no_input_file_specified"
        }, indent=2))
        sys.exit(1)
    
    audio_path = sys.argv[1]
    
    # Get model path from argument or auto-detect
    if len(sys.argv) >= 3:
        model_path = sys.argv[2]
    else:
        model_path = find_vosk_model()
        if model_path is None:
            print(json.dumps({
                "text": "",
                "result": [],
                "status": "REJECTED",
                "reason": "vosk_model_not_found"
            }, indent=2))
            sys.exit(1)
    
    try:
        agent = SpeechTranscriptionAgent(model_path)
        result = agent.transcribe(audio_path)
        print(json.dumps(result, indent=2))
        
        # Exit with appropriate code
        if result.get("status") == "REJECTED":
            sys.exit(1)
        sys.exit(0)
        
    except FileNotFoundError as e:
        print(json.dumps({
            "text": "",
            "result": [],
            "status": "REJECTED",
            "reason": "model_not_found"
        }, indent=2))
        sys.exit(1)
        
    except Exception as e:
        print(json.dumps({
            "text": "",
            "result": [],
            "status": "REJECTED",
            "reason": "initialization_error"
        }, indent=2))
        sys.exit(1)
if __name__ == "__main__":
    main()
