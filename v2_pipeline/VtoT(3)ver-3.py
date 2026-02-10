"""VtoT(3).py - Hybrid VOSK + Whisper Transcription with Speaker Diarization
Whisper: meaning (text, sentences). VOSK: speech behavior (timing, confidence, pauses, speed, fillers).
Pyannote: speaker diarization (speaker_id per segment)."""

import json, os, sys, subprocess, tempfile, wave
from pathlib import Path
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor

try:
    import whisper
    from vosk import Model, KaldiRecognizer, SetLogLevel
    # Use configuration-driven Whisper settings
    from config import WHISPER_MODEL, WHISPER_LANGUAGE, WHISPER_TASK, WHISPER_DEVICE
except ImportError as e:
    print(json.dumps({"whisper":{"text":"","language":None,"sentence_count":0},"sentences":[],"status":"ERROR","reason":str(e)}))
    sys.exit(1)

DIARIZATION_AVAILABLE = False
try:
    from pyannote.audio import Pipeline
    import torch
    DIARIZATION_AVAILABLE = True
except ImportError:
    print("[WARN] pyannote.audio not available, diarization disabled", file=sys.stderr)

FILLERS = {'uh','um','er','ah','like','you know','basically','actually'}

HF_TOKEN = os.environ.get("HF_TOKEN", None)

class HybridTranscriptionAgent:
    MIN_WORDS = 3

    def __init__(self, vosk_path: str, model_name: str = None):
        SetLogLevel(-1)
        if not os.path.exists(vosk_path): raise FileNotFoundError(f"VOSK model not found: {vosk_path}")
        print(f"[INFO] Loading VOSK: {vosk_path}", file=sys.stderr)
        self.vosk_model, self.sample_rate = Model(vosk_path), 16000
        
        # Use config if model_name not provided
        actual_model = model_name or WHISPER_MODEL
        
        import contextlib
        print(f"[INFO] Loading Whisper '{actual_model}' ({WHISPER_DEVICE})...", file=sys.stderr)
        with contextlib.redirect_stdout(sys.stderr):
            self.whisper_model = whisper.load_model(actual_model, device=WHISPER_DEVICE)

        # Initialize diarization pipeline
        self.diarization_pipeline = None
        if DIARIZATION_AVAILABLE and HF_TOKEN:
            try:
                import contextlib
                print("[INFO] Loading pyannote diarization model...", file=sys.stderr)
                with contextlib.redirect_stdout(sys.stderr):
                    self.diarization_pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        token=HF_TOKEN
                    )
                # Use CPU
                if self.diarization_pipeline:
                    self.diarization_pipeline.to(torch.device("cpu"))
                    print("[INFO] Diarization model loaded!", file=sys.stderr)
            except Exception as e:
                print(f"[WARN] Failed to load diarization model: {e}", file=sys.stderr)
                self.diarization_pipeline = None

    def _get_diarization(self, audio_path: str) -> List[Dict]:
        """
        Run pyannote speaker diarization on audio file.
        Returns list of segments: [{speaker_id, start, end}, ...]
        """
        if not self.diarization_pipeline:
            return []

        print("[INFO] Running speaker diarization...", file=sys.stderr)

        try:
            # Run diarization
            diarization = self.diarization_pipeline(audio_path)

            # Convert to our format
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    "speaker_id": speaker,
                    "start": turn.start,
                    "end": turn.end
                })

            # Count unique speakers
            speakers = set(s["speaker_id"] for s in segments)
            print(f"[INFO] Found {len(speakers)} speakers, {len(segments)} segments", file=sys.stderr)

            return segments

        except Exception as e:
            print(f"[WARN] Diarization failed: {e}", file=sys.stderr)
            return []

    def _assign_speaker_to_sentences(self, sentences: List[Dict], diarization: List[Dict]) -> List[Dict]:
        """
        Assign speaker_id to each sentence based on time overlap with diarization segments.
        If no diarization available, use heuristic: alternate speakers on pause gaps > 1.5s
        """
        if not diarization:
            # Heuristic speaker detection based on pause gaps
            # Assume call center: 2 speakers alternating (agent/customer)
            current_speaker = 0
            PAUSE_THRESHOLD = 1.5  # seconds - gap that indicates speaker change

            for i, sent in enumerate(sentences):
                if i > 0:
                    prev_end = sentences[i-1].get("end", 0)
                    curr_start = sent.get("start", 0)
                    gap = curr_start - prev_end

                    # If significant pause, likely speaker change
                    if gap > PAUSE_THRESHOLD:
                        current_speaker = 1 - current_speaker  # Toggle between 0 and 1

                sent["speaker_id"] = f"speaker_{current_speaker}"

            return sentences

        for sent in sentences:
            sent_start = sent.get("start", 0)
            sent_end = sent.get("end", 0)
            sent_mid = (sent_start + sent_end) / 2

            # Find best matching speaker segment (by midpoint overlap)
            best_speaker = "unknown"
            for seg in diarization:
                if seg["start"] <= sent_mid <= seg["end"]:
                    best_speaker = seg["speaker_id"]
                    break

            # Fallback: find segment with most overlap
            if best_speaker == "unknown":
                max_overlap = 0
                for seg in diarization:
                    overlap_start = max(sent_start, seg["start"])
                    overlap_end = min(sent_end, seg["end"])
                    overlap = max(0, overlap_end - overlap_start)
                    if overlap > max_overlap:
                        max_overlap = overlap
                        best_speaker = seg["speaker_id"]

            sent["speaker_id"] = best_speaker

        return sentences

    def _convert_wav(self, path: str) -> Optional[str]:
        tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False); tmp.close()
        try:
            r = subprocess.run(['ffmpeg','-y','-i',path,'-ar','16000','-ac','1','-c:a','pcm_s16le','-f','wav',tmp.name], 
                              capture_output=True, timeout=120)
            if r.returncode != 0: os.unlink(tmp.name); return None
            return tmp.name
        except: 
            if os.path.exists(tmp.name): os.unlink(tmp.name)
            return None

    def _vosk(self, wav: str) -> Dict:
        print("[INFO] VOSK transcription...", file=sys.stderr)
        with wave.open(wav, 'rb') as wf:
            rec = KaldiRecognizer(self.vosk_model, wf.getframerate()); rec.SetWords(True)
            results = []
            while (data := wf.readframes(4000)):
                if rec.AcceptWaveform(data):
                    r = json.loads(rec.Result())
                    if 'result' in r: results.extend(r['result'])
            final = json.loads(rec.FinalResult())
            if 'result' in final: results.extend(final['result'])
        return {'words': results, 'word_count': len(results)}

    def _whisper(self, wav: str) -> Dict:
        print("[INFO] Whisper transcription...", file=sys.stderr)
        import contextlib
        try:
            import numpy as np
            with wave.open(wav, 'rb') as wf:
                audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
            
            # Suppress Whisper's "Detected language" print to STDOUT
            with contextlib.redirect_stdout(sys.stderr):
                result = self.whisper_model.transcribe(
                    audio, 
                    fp16=False, 
                    verbose=False,
                    task=WHISPER_TASK
                )
            
            return {'text': result['text'].strip(), 'language': result.get('language','unknown'), 'segments': result.get('segments',[])}
        except Exception as e:
            return {'text': '', 'language': 'en', 'segments': [], 'error': str(e)}

    def _combine(self, vosk: Dict, whisper: Dict, diarization: List[Dict] = None) -> Dict:
        words, segs, sents = vosk.get('words',[]), whisper.get('segments',[]), []

        for idx, seg in enumerate(segs):
            s, e = seg.get('start',0), seg.get('end',0)
            ws = [w for w in words if w.get('start',0) >= s and w.get('end',0) <= e]
            wc = len(ws)
            conf = sum(w.get('conf',0) for w in ws)/wc if ws else 0
            pauses, pause_dur = 0, 0
            for i in range(1, len(ws)):
                gap = ws[i].get('start',0) - ws[i-1].get('end',0)
                if gap > 0.1: pauses += 1; pause_dur += gap
            dur = e - s
            speed = round((wc/dur)*60, 1) if dur > 0 else 0
            fillers = sum(1 for w in ws if w.get('word','').lower() in FILLERS)
            sents.append({
                'sentence_index': idx,  # Stable audit index
                'text': seg.get('text','').strip(), 
                'start': round(s,2), 
                'end': round(e,2),
                'speech': {'word_count':wc, 'confidence':round(conf,3), 'speed_wpm':speed, 
                          'pause_count':pauses, 'pause_duration':round(pause_dur,2), 'filler_count':fillers}
            })

        # Assign speaker_id to each sentence (metadata only, no role inference)
        sents = self._assign_speaker_to_sentences(sents, diarization or [])

        text = whisper.get('text','')
        status = 'REJECTED' if not text else ('REJECTED' if vosk.get('word_count',0) < self.MIN_WORDS else 'SUCCESS')
        reason = 'no_whisper_transcription' if not text else ('insufficient_vosk_words' if status=='REJECTED' else None)

        # Count unique speakers
        speakers = set(s.get('speaker_id', 'unknown') for s in sents)

        return {'whisper': {'text':text, 'language':whisper.get('language','en'), 'sentence_count':len(sents)},
                'diarization': {'enabled': diarization is not None and len(diarization) > 0, 
                               'speaker_count': len(speakers), 'speakers': list(speakers)},
                'sentences': sents, 'status': status, 'reason': reason}

    def transcribe(self, path: str) -> Dict:
        err = lambda r: {'whisper':{'text':'','language':None,'sentence_count':0},'sentences':[],'status':'ERROR','reason':r}
        if not os.path.exists(path): return err('file_not_found')
        print(f"\n[INFO] Processing: {path}", file=sys.stderr)

        # Step 1: Convert audio first (needed for all steps)
        wav = self._convert_wav(path)
        if not wav: return err('audio_preprocessing_failed')

        try:
            # Step 2: Run diarization, VOSK, Whisper in parallel
            with ThreadPoolExecutor(max_workers=3) as ex:
                df = ex.submit(self._get_diarization, wav)
                vf = ex.submit(self._vosk, wav)
                wf = ex.submit(self._whisper, wav)

            diarization = df.result()

            # Step 3: Combine results with diarization
            return self._combine(vf.result(), wf.result(), diarization)
        finally:
            if wav and os.path.exists(wav): 
                try: os.unlink(wav)
                except: pass

def find_model() -> Optional[str]:
    for p in ["vosk-model-en-in-0.5","vosk-model-en-us-0.22","vosk-model-small-en-us-0.15","model",
              "../vosk-model-small-en-us-0.15",
              os.path.expanduser("~/vosk-model-en-in-0.5"),os.path.expanduser("~/vosk-model-en-us-0.22")]:
        if os.path.isdir(p): return p
    return None

def main():
    print(f"[DEBUG] VtoT main started. Args: {sys.argv}", file=sys.stderr)
    err = lambda r: print(json.dumps({'whisper':{'text':'','language':None,'sentence_count':0},'sentences':[],'status':'ERROR','reason':r},indent=2)) or sys.exit(1)
    if len(sys.argv) < 2: 
        print("[DEBUG] No input file provided.", file=sys.stderr)
        err('no_input_file')
    model = find_model()
    print(f"[DEBUG] Found VOSK model: {model}", file=sys.stderr)
    if not model: err('vosk_model_not_found')
    try:
        print("[DEBUG] Initializing HybridTranscriptionAgent...", file=sys.stderr)
        agent = HybridTranscriptionAgent(model, sys.argv[2] if len(sys.argv)>=3 else "base")
        print(f"[DEBUG] Transcribing file: {sys.argv[1]}", file=sys.stderr)
        result = agent.transcribe(sys.argv[1])
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get('status') in ['SUCCESS','WARNING'] else 1)
    except Exception as e:
        print(f"[DEBUG] Caught exception in main: {e}", file=sys.stderr)
        print(json.dumps({'whisper':{'text':'','language':None,'sentence_count':0},'sentences':[],'status':'ERROR','reason':'init_error','error':str(e)},indent=2))
        sys.exit(1)

if __name__ == "__main__": main()
