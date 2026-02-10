"""run_v2_pipeline.py - Orchestrator for V2 Voice Analytics Pipeline
Audio -> VtoT -> Translate -> TextEXT -> Interpret -> FinContext -> EventProcessor
"""

import subprocess
import os
import sys
import json
from datetime import datetime

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = {
    "vtot": os.path.join(PIPELINE_DIR, "VtoT(3)ver-3.py"),
    "translate": os.path.join(PIPELINE_DIR, "Translatever-3.py"),
    "textext": os.path.join(PIPELINE_DIR, "TextEXTver-3.py"),
    "interpret": os.path.join(PIPELINE_DIR, "Interpretver-3.py"),
    "fincontext": os.path.join(PIPELINE_DIR, "FinContextver-3.py"),
    "processor": os.path.join(PIPELINE_DIR, "EventProcessor-3.py")
}

def run_command(cmd, input_file=None, output_file=None):
    cmd_str = f'"{sys.executable}" ' + ' '.join([f'"{c}"' if ' ' in c or '(' in c or ')' in c else c for c in cmd[1:]])
    print(f"[RUNNING] {cmd_str}")
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = PIPELINE_DIR
        if output_file:
            with open(output_file, 'w') as out:
                subprocess.run(cmd_str, check=True, stdout=out, stderr=subprocess.PIPE, text=True, shell=True, env=env)
        else:
            subprocess.run(cmd_str, check=True, shell=True, env=env)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Step failed: {e}")
        if e.stderr:
            print(f"[STDERR] {e.stderr}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_v2_pipeline.py <audio_path> [hf_token] [product_type] [amount] [customer_type]")
        sys.exit(1)

    audio_path = sys.argv[1]
    hf_token = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("HF_TOKEN")
    
    # Context metadata
    product_type = sys.argv[3] if len(sys.argv) > 3 else "subscription"
    amount = sys.argv[4] if len(sys.argv) > 4 else "49.99"
    customer_type = sys.argv[5] if len(sys.argv) > 5 else "new"

    if hf_token:
        os.environ["HF_TOKEN"] = hf_token

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_vtot = f"vtot_{timestamp}.json"
    out_trans = f"vtot_en_{timestamp}.json"
    out_markers = f"markers_{timestamp}.json"
    out_signals = f"signals_{timestamp}.json"
    out_context = f"context_{timestamp}.json"
    out_final = f"events_v2_{timestamp}.json"

    print("=== STARTING V2 PIPELINE ===")
    
    # 1. Transcription (Hybrid + Diarization)
    if not run_command([sys.executable, SCRIPTS["vtot"], audio_path], output_file=out_vtot): sys.exit(1)
    
    # 2. Translation
    if not run_command([sys.executable, SCRIPTS["translate"], out_vtot, out_trans]): sys.exit(1)
    
    # 3. Behavioral Interpretation
    if not run_command([sys.executable, SCRIPTS["interpret"], out_vtot], output_file=out_signals): sys.exit(1)
    
    # 4. Text Extraction
    if not run_command([sys.executable, SCRIPTS["textext"], out_trans], output_file=out_markers): sys.exit(1)
    
    # 5. Financial Context
    context_args = [f"product_type={product_type}", f"amount={amount}", f"customer_type={customer_type}"]
    if not run_command([sys.executable, SCRIPTS["fincontext"]] + context_args, output_file=out_context): sys.exit(1)
    
    # 6. Final Event Processor (Unified Detection + LLM)
    if not run_command([sys.executable, SCRIPTS["processor"], out_trans, out_signals, out_markers, out_context], output_file=out_final): sys.exit(1)

    print(f"\n[SUCCESS] Pipeline complete. Results saved to: {out_final}")

if __name__ == "__main__":
    main()
