"""VtoT(3).py - Hybrid VOSK + Whisper Transcription
Whisper: meaning (text, sentences). VOSK: speech behavior (timing, confidence, pauses, speed, fillers)."""

import json, os, sys, subprocess, tempfile, wave
from pathlib import Path
from typing import Optional, Dict
from concurrent.futures import ThreadPoolExecutor

try:
    import whisper
    from vosk import Model, KaldiRecognizer, SetLogLevel
except ImportError as e:
    print(json.dumps({"whisper":{"text":"","language":None,"sentence_count":0},"sentences":[],"status":"ERROR","reason":str(e)}))
    sys.exit(1)

FILLERS = {'uh','um','er','ah','like','you know','basically','actually'}

class HybridTranscriptionAgent:
    MIN_WORDS = 3
    
    def __init__(self, vosk_path: str, whisper_model: str = "base"):
        SetLogLevel(-1)
        if not os.path.exists(vosk_path): raise FileNotFoundError(f"VOSK model not found: {vosk_path}")
        print(f"[INFO] Loading VOSK: {vosk_path}", file=sys.stderr)
        self.vosk_model, self.sample_rate = Model(vosk_path), 16000
        print(f"[INFO] Loading Whisper '{whisper_model}' (CPU)...", file=sys.stderr)
        self.whisper_model = whisper.load_model(whisper_model, device="cpu")
    
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
        try:
            import numpy as np
            with wave.open(wav, 'rb') as wf:
                audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
            result = self.whisper_model.transcribe(audio, language="en", fp16=False, verbose=False)
            return {'text': result['text'].strip(), 'language': result.get('language','en'), 'segments': result.get('segments',[])}
        except Exception as e:
            return {'text': '', 'language': 'en', 'segments': [], 'error': str(e)}
    
    def _combine(self, vosk: Dict, whisper: Dict) -> Dict:
        words, segs, sents = vosk.get('words',[]), whisper.get('segments',[]), []
        
        for seg in segs:
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
            sents.append({'text': seg.get('text','').strip(), 'start': round(s,2), 'end': round(e,2),
                'speech': {'word_count':wc, 'confidence':round(conf,3), 'speed_wpm':speed, 
                          'pause_count':pauses, 'pause_duration':round(pause_dur,2), 'filler_count':fillers}})
        
        text = whisper.get('text','')
        status = 'REJECTED' if not text else ('REJECTED' if vosk.get('word_count',0) < self.MIN_WORDS else 'SUCCESS')
        reason = 'no_whisper_transcription' if not text else ('insufficient_vosk_words' if status=='REJECTED' else None)
        return {'whisper': {'text':text, 'language':whisper.get('language','en'), 'sentence_count':len(sents)},
                'sentences': sents, 'status': status, 'reason': reason}
    
    def transcribe(self, path: str) -> Dict:
        err = lambda r: {'whisper':{'text':'','language':None,'sentence_count':0},'sentences':[],'status':'ERROR','reason':r}
        if not os.path.exists(path): return err('file_not_found')
        print(f"\n[INFO] Processing: {path}", file=sys.stderr)
        wav = self._convert_wav(path)
        if not wav: return err('audio_preprocessing_failed')
        try:
            with ThreadPoolExecutor(max_workers=2) as ex:
                vf, wf = ex.submit(self._vosk, wav), ex.submit(self._whisper, wav)
            return self._combine(vf.result(), wf.result())
        finally:
            if wav and os.path.exists(wav): 
                try: os.unlink(wav)
                except: pass

def find_model() -> Optional[str]:
    for p in ["vosk-model-en-in-0.5","vosk-model-en-us-0.22","vosk-model-small-en-us-0.15","model",
              os.path.expanduser("~/vosk-model-en-in-0.5"),os.path.expanduser("~/vosk-model-en-us-0.22")]:
        if os.path.isdir(p): return p
    return None

def main():
    err = lambda r: print(json.dumps({'whisper':{'text':'','language':None,'sentence_count':0},'sentences':[],'status':'ERROR','reason':r},indent=2)) or sys.exit(1)
    if len(sys.argv) < 2: err('no_input_file')
    model = find_model()
    if not model: err('vosk_model_not_found')
    try:
        result = HybridTranscriptionAgent(model, sys.argv[2] if len(sys.argv)>=3 else "base").transcribe(sys.argv[1])
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get('status') in ['SUCCESS','WARNING'] else 1)
    except Exception as e:
        print(json.dumps({'whisper':{'text':'','language':None,'sentence_count':0},'sentences':[],'status':'ERROR','reason':'init_error','error':str(e)},indent=2))
        sys.exit(1)

if __name__ == "__main__": main()
