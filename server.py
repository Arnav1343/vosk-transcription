import os
import sys
import json
import asyncio
import threading
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="AuditX Backend", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
PIPELINE_DIR = BASE_DIR / "v2_pipeline"
OUTPUT_DIR = BASE_DIR # Reverting to root to see pre-existing files
AUDIO_DIR = BASE_DIR / "audio_public" 
AUDIO_BASE_URL = "http://localhost:8000/audio"

INPUT_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

# Mount audio directory for frontend access
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")

# In-memory status tracker (for simplicity, could be DB)
# Structure: { "call_id": "processing" | "done" | "error" }
processing_status = {}

class SessionSummary(BaseModel):
    id: str
    title: str
    date: str
    duration: int
    agent: str
    customer: str
    status: str
    tags: List[str]

class TranscriptSegment(BaseModel):
    id: str
    speaker: str
    text: str
    startTime: float
    endTime: float

class SessionDetail(SessionSummary):
    audio_url: str
    transcript: List[TranscriptSegment]
    aiFlags: List[Dict]

# --- HELPER: Async Pipeline Runner ---
def run_pipeline_thread(filepath: Path, call_id: str):
    print(f"[SERVER] Starting pipeline for {call_id}...", file=sys.stderr)
    processing_status[call_id] = "processing"
    
    try:
        # Run the V2 pipeline script
        # Command: python e:\HackProject\v2_pipeline\run_v2_pipeline-3.py <filepath>
        # We need to set CWD because the script likely relies on relative imports or config
        pipeline_dir = BASE_DIR / "v2_pipeline"
        script_path = pipeline_dir / "run_v2_pipeline-3.py"
        
        # Verify script exists
        if not script_path.exists():
             print(f"[SERVER] Error: Pipeline script not found at {script_path}", file=sys.stderr)
             processing_status[call_id] = "error"
             return

        cmd = [sys.executable, str(script_path), str(filepath)]
        
        # Run from BASE_DIR so output files land in OUTPUT_DIR (root)
        # We add PIPELINE_DIR to PYTHONPATH so scripts can find config/etc.
        env = os.environ.copy()
        env["PYTHONPATH"] = str(pipeline_dir) + os.pathsep + env.get("PYTHONPATH", "")
        
        # This blocks the THREAD, not the server
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR), env=env)
        
        # Log output for debugging
        log_path = INPUT_DIR / f"{call_id}_pipeline.log"
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write("=== STDOUT ===\n")
            log_file.write(result.stdout)
            log_file.write("\n=== STDERR ===\n")
            log_file.write(result.stderr)

        if result.returncode != 0:
            print(f"[SERVER] Pipeline failed for {call_id}. Check {log_path}", file=sys.stderr)
            processing_status[call_id] = "error"
        else:
            print(f"[SERVER] Pipeline finished for {call_id}", file=sys.stderr)
            processing_status[call_id] = "done"
            
    except Exception as e:
        print(f"[SERVER] Exception in pipeline thread: {e}", file=sys.stderr)
        processing_status[call_id] = "error"

# --- HELPER: Data Loader ---
def load_session_data(call_id: str) -> Optional[SessionDetail]:
    # Try to find matching output files
    # The pipeline generates timestamps, so we need to find files that MATCH the call_id if possible
    # OR, we assume call_id IS the timestamp/identifier used by the pipeline
    
    # Heuristic: Scan root for events_v2_*.json and vtot_en_*.json
    # We need a robust way to link call_id to files.
    # For now, let's assume call_id = timestamp string e.g. "20260210_012040"
    
    events_path = OUTPUT_DIR / f"events_v2_{call_id}.json"
    vtot_path = OUTPUT_DIR / f"vtot_en_{call_id}.json"
    
    if not events_path.exists() or not vtot_path.exists():
        return None
        
    try:
        with open(events_path, 'r', encoding='utf-8') as f:
            events_data = json.load(f)
        with open(vtot_path, 'r', encoding='utf-8') as f:
            vtot_data = json.load(f)
            
        # Map VToT to Transcript
        transcript = []
        sentences = vtot_data.get('sentences', [])
        duration = 0
        agent_name = "Agent"
        customer_name = "Customer"
        
        for idx, s in enumerate(sentences):
            role = s.get('speaker_role', 'unknown')
            t_seg = TranscriptSegment(
                id=str(idx),
                speaker="Agent" if role == 'agent' else "Customer" if role == 'customer' else "Unknown",
                text=s.get('text', ''),
                startTime=s.get('start', 0),
                endTime=s.get('end', 0)
            )
            transcript.append(t_seg)
            duration = max(duration, s.get('end', 0))
            
        # Map Events to Flags
        ai_flags = []
        risk_level = "Reviewed"
        tags = []
        
        for evt in events_data.get('events', []):
            analysis = evt.get('llm_analysis', {})
            flag = {
                "start": evt.get('timestamp', {}).get('start'),
                "end": evt.get('timestamp', {}).get('end'),
                "type": evt.get('event_type'),
                "confidence": analysis.get('confidence', 0.5),
                "evidence": analysis.get('summary', evt.get('explanation'))
            }
            ai_flags.append(flag)
            
            if analysis.get('risk_level') == 'high':
                risk_level = "Flagged"
                tags.append("Critical Risk")
                
        if not tags: tags = ["Routine"]

        return SessionDetail(
            id=call_id,
            title=f"Call Audit {call_id}",
            date=events_data.get('generated_at', str(datetime.now())),
            duration=int(duration),
            agent=agent_name,
            customer=customer_name,
            status=risk_level,
            audio_url=f"{AUDIO_BASE_URL}/{call_id}.wav", # Fallback if we don't have exact filename
            tags=list(set(tags)),
            transcript=transcript,
            aiFlags=ai_flags
        )

    except Exception as e:
        print(f"Error loading session {call_id}: {e}")
        return None


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Generate ID based on timestamp to match pipeline behavior
    # NOTE: The pipeline generates its OWN timestamp. This is a synchronization issue.
    # FIX: We will force the pipeline to use a specific ID or we capture the output.
    # EASIER FIX: We let the pipeline run, and then we scan for the NEWEST file.
    
    # Save file with a unique name based on timestamp
    # This ID will be used to find the output files later
    call_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{call_id}.wav"
    file_path = INPUT_DIR / safe_filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Also copy to audio_public for frontend playback
    public_audio_path = AUDIO_DIR / safe_filename
    shutil.copy(file_path, public_audio_path)
    
    # Trigger pipeline
    threading.Thread(target=run_pipeline_thread, args=(file_path, call_id)).start()
    
    return {"status": "processing", "id": call_id, "filename": safe_filename}


@app.get("/sessions", response_model=List[SessionSummary])
def get_sessions():
    """Scans the output directory for processed JSONs and returns summaries."""
    sessions = []
    import glob
    files = glob.glob(str(OUTPUT_DIR / "events_v2_*.json"))
    files.sort(key=os.path.getmtime, reverse=True)
    
    for f in files:
        try:
            fname = Path(f).name
            call_id = fname.replace("events_v2_", "").replace(".json", "")
            
            with open(f, 'r', encoding='utf-8') as json_file:
                dat = json.load(json_file)
                
            summary = dat.get('summary', {})
            high_risks = summary.get('high_risk_events', 0)
            
            # Map events to tags
            tags = list(set([e.get('event_type') for e in dat.get('events', [])]))
            if not tags: tags = ["No Risks"]
            
            sessions.append(SessionSummary(
                id=call_id,
                title=f"Call {call_id}",
                date=dat.get('generated_at', str(datetime.fromtimestamp(os.path.getmtime(f)))),
                duration=120, # Placeholder
                agent="Agent",
                customer="Customer",
                status="Flagged" if high_risks > 0 else "Reviewed",
                tags=tags[:3] # Limit tags for UI
            ))
        except:
            continue
            
    return sessions

@app.get("/session/{id}", response_model=SessionDetail)
def get_session_detail(id: str):
    session = load_session_data(id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or processing")
    
    # Audio Fallback Logic
    # If the specific ID.wav doesn't exist, check for common samples
    audio_path = AUDIO_DIR / f"{id}.wav"
    if not audio_path.exists():
        # Heuristic: If it's old data, it might be from the sample set
        if (AUDIO_DIR / "Sales_Call_example_1.wav").exists():
            session.audio_url = f"{AUDIO_BASE_URL}/Sales_Call_example_1.wav"
        elif (AUDIO_DIR / "sample_audio_v2.wav").exists():
            session.audio_url = f"{AUDIO_BASE_URL}/sample_audio_v2.wav"
            
    return session

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
