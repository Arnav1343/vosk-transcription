"""EventProcessor.py v1.1.0 - Unified Event Detection and Interpretation for V2
Enhanced with speaker-id awareness and V2 schema support.
"""

import json
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

VERSION = "1.1.0"
ARTIFACT_TYPE = "unified_event_analysis"


# ============================================================================
# RULE-BASED EVENT DETECTION (Enhanced for V2)
# ============================================================================

class EventDetector:
    """Pure, deterministic, rule-based event detection."""
    
    def __init__(self, vtot_data: Dict, signals_data: Dict, markers_data: Dict, context_data: Dict):
        self.sentences = vtot_data.get('sentences', [])
        self.signals = signals_data.get('sentences', [])
        self.markers = markers_data.get('sentences', [])
        self.context = context_data.get('context', {})
        self.events: List[Dict] = []
    
    def detect(self) -> List[Dict]:
        """Run all detection rules and return events."""
        self._rule_consent_uncertainty()
        self._rule_affordability_signal()
        self._rule_pressure_review()
        self._rule_pii_sensitive_call()
        self._rule_consent_gap()
        return self.events
    
    def _amount_band(self) -> str:
        return self.context.get('amount', {}).get('band', 'unknown')
    
    def _product_sensitivity(self) -> str:
        return self.context.get('product', {}).get('sensitivity', 'unknown')
    
    def _has_marker_type(self, idx: int, marker_type: str) -> bool:
        if idx >= len(self.markers): return False
        return any(m.get('type') == marker_type for m in self.markers[idx].get('markers', []))
    
    def _has_marker_category(self, idx: int, category: str) -> bool:
        if idx >= len(self.markers): return False
        return any(m.get('category') == category for m in self.markers[idx].get('markers', []))
    
    def _has_indicator(self, idx: int, indicator: str) -> bool:
        if idx >= len(self.signals): return False
        return any(i.get('indicator') == indicator for i in self.signals[idx].get('indicators', []))
    
    def _get_speaker(self, idx: int) -> str:
        """Get speaker ID for a sentence if available (V2 feature)."""
        if idx < len(self.sentences):
            return self.sentences[idx].get('speaker_id', 'unknown')
        return 'unknown'
    
    def _emit(self, event_type: str, idx: int, evidence: List[Dict], explanation: str, action: str):
        sent = self.sentences[idx] if idx < len(self.sentences) else {}
        self.events.append({
            "event_type": event_type,
            "speaker_id": self._get_speaker(idx),
            "sentence_index": idx,
            "timestamp": {"start": sent.get('start', 0), "end": sent.get('end', 0)},
            "evidence": evidence,
            "financial_context": {"amount_band": self._amount_band(), "product_sensitivity": self._product_sensitivity()},
            "explanation": explanation,
            "suggested_action": action
        })
    
    def _rule_consent_uncertainty(self):
        """IF: customer_commitment AND no regulatory_prompt in prior 3 AND behavioral hesitation THEN: emit"""
        for idx in range(len(self.markers)):
            if not self._has_marker_type(idx, 'customer_commitment'): continue
            prior_reg = [i for i in range(max(0, idx-3), idx) if self._has_marker_type(i, 'regulatory_prompt')]
            if prior_reg: continue
            hesitation = (self._has_indicator(idx, 'pause_count_increase') or 
                         self._has_indicator(idx, 'speed_deviation') or self._has_indicator(idx, 'agreement_pattern'))
            if not hesitation: continue
            self._emit("commitment_without_consent", idx,
                [{"source": "TextEXT", "marker": "customer_commitment", "sentence": idx},
                 {"source": "Interpret", "indicator": "behavioral_hesitation", "sentence": idx}],
                f"Commitment at sentence {idx} without prior consent prompt, with behavioral hesitation",
                "compliance_review")
    
    def _rule_affordability_signal(self):
        """IF: currency_amount mentioned AND behavioral hesitation within ±1 sentence THEN: emit"""
        for idx in range(len(self.markers)):
            if not self._has_marker_category(idx, 'currency_amount'): continue
            hesitation_range = [i for i in range(max(0, idx-1), min(len(self.signals), idx+2)) 
                               if self._has_indicator(i, 'speed_deviation') or self._has_indicator(i, 'pause_count_increase')]
            if not hesitation_range: continue
            markers_in_idx = self.markers[idx].get('markers', [])
            matched = next((m.get('matched_text', '') for m in markers_in_idx if m.get('category') == 'currency_amount'), '')
            
            self._emit("affordability_signal", idx,
                [{"source": "TextEXT", "marker": "currency_amount", "matched": matched, "sentence": idx},
                 {"source": "Interpret", "indicator": "behavioral_hesitation", "sentences": hesitation_range},
                 {"source": "FinContext", "amount_band": self._amount_band()}],
                f"Affordability signal at sentence {idx}, amount_band={self._amount_band()}",
                "affordability_check")
    
    def _rule_pressure_review(self):
        """IF: urgency_language AND sales_prompt within 2 sentences AND hesitation THEN: emit"""
        for idx in range(len(self.markers)):
            if not self._has_marker_type(idx, 'urgency_language'): continue
            nearby_sales = [i for i in range(max(0, idx-2), min(len(self.markers), idx+3)) 
                           if self._has_marker_type(i, 'sales_prompt')]
            if not nearby_sales: continue
            hesitation_found = any(self._has_indicator(i, 'speed_deviation') or self._has_indicator(i, 'pause_count_increase')
                                  for i in range(max(0, idx-1), min(len(self.signals), idx+2)))
            if not hesitation_found: continue
            self._emit("pressure_review", idx,
                [{"source": "TextEXT", "marker": "urgency_language", "sentence": idx},
                 {"source": "TextEXT", "marker": "sales_prompt", "sentences": nearby_sales},
                 {"source": "Interpret", "indicator": "behavioral_hesitation"}],
                f"Pressure pattern at sentence {idx} with sales prompt at {nearby_sales}",
                "sales_conduct_review")
    
    def _rule_pii_sensitive_call(self):
        """IF: pii_disclosure detected AND product_sensitivity is high THEN: emit"""
        if self._product_sensitivity() != 'high': return
        for idx in range(len(self.markers)):
            if not self._has_marker_type(idx, 'pii_disclosure'): continue
            self._emit("pii_sensitive_call", idx,
                [{"source": "TextEXT", "marker": "pii_disclosure", "sentence": idx},
                 {"source": "FinContext", "product_sensitivity": "high"}],
                f"PII disclosed in high-sensitivity product context at sentence {idx}",
                "access_control_review")
    
    def _rule_consent_gap(self):
        """IF: financial_entity AND no regulatory_prompt in entire call AND customer_commitment THEN: emit"""
        has_reg_prompt = any(self._has_marker_type(i, 'regulatory_prompt') for i in range(len(self.markers)))
        if has_reg_prompt: return
        has_financial = any(self._has_marker_type(i, 'financial_entity') for i in range(len(self.markers)))
        if not has_financial: return
        for idx in range(len(self.markers)):
            if not self._has_marker_type(idx, 'customer_commitment'): continue
            self._emit("consent_gap", idx,
                [{"source": "TextEXT", "marker": "customer_commitment", "sentence": idx},
                 {"source": "TextEXT", "marker": "no_regulatory_prompt_in_call"}],
                f"Customer commitment at sentence {idx} with no regulatory disclosure in call",
                "compliance_escalation")


# ============================================================================
# LLM / FALLBACK INTERPRETATION
# ============================================================================

FALLBACK_ANALYSIS = {
    "commitment_without_consent": {
        "summary": "Customer commitment recorded without clear prior consent prompt",
        "risk_level": "high",
        "recommended_action": "Compliance review required - consent gap",
        "confidence": 0.7
    },
    "consent_gap": {
        "summary": "Potential compliance gap detected - consent/disclosure may be unclear",
        "risk_level": "high",
        "recommended_action": "Compliance team review required",
        "confidence": 0.6
    },
    "affordability_signal": {
        "summary": "Customer showed hesitation when discussing pricing",
        "risk_level": "medium", 
        "recommended_action": "Consider offering payment options or alternatives",
        "confidence": 0.6
    },
    "pressure_review": {
        "summary": "Sales pressure pattern detected near customer hesitation",
        "risk_level": "medium",
        "recommended_action": "Review call for sales conduct compliance",
        "confidence": 0.6
    },
    "pii_sensitive_call": {
        "summary": "Personally identifiable information was disclosed during call",
        "risk_level": "high",
        "recommended_action": "Apply restricted access controls to this call record",
        "confidence": 0.8
    }
}


def get_transcript_context(vtot_data: Dict, event: Dict, window: int = 2) -> str:
    """Extract relevant transcript context around an event with Speaker IDs."""
    sentences = vtot_data.get('sentences', [])
    event_idx = event.get('sentence_index', 0)
    
    start_idx = max(0, event_idx - window)
    end_idx = min(len(sentences), event_idx + window + 1)
    
    lines = []
    for i in range(start_idx, end_idx):
        s = sentences[i] if i < len(sentences) else {}
        marker = ">>>" if i == event_idx else "   "
        text = s.get('text', '')
        speaker = s.get('speaker_id', 'unknown')
        timestamp = f"[{s.get('start', 0):.1f}s]"
        lines.append(f"{marker} {timestamp} ({speaker}): {text}")
    
    return "\n".join(lines)


def get_llm_analysis(event: Dict, transcript_context: str, client) -> Dict:
    """Get LLM analysis for an event."""
    try:
        client.create_thread()
        analysis = client.analyze_event(event, transcript_context)
        analysis["analysis_source"] = "llm"
        return analysis
    except Exception as e:
        print(f"[WARN] LLM analysis failed: {e}", file=sys.stderr)
        return get_fallback_analysis(event)


def get_fallback_analysis(event: Dict) -> Dict:
    """Get rule-based fallback analysis."""
    event_type = event.get('event_type', '')
    base = FALLBACK_ANALYSIS.get(event_type, {
        "summary": f"Event detected: {event_type}",
        "risk_level": "medium",
        "recommended_action": "Manual review recommended",
        "confidence": 0.5
    })
    return {**base, "analysis_source": "fallback"}


def interpret_events(events: List[Dict], vtot_data: Optional[Dict], enable_llm: bool) -> List[Dict]:
    """Add interpretation to each event."""
    client = None
    if enable_llm:
        try:
            from BackboardClient import BackboardWrapper
            client = BackboardWrapper()
            client.create_assistant()
            print("[INFO] LLM client initialized", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] LLM unavailable, using fallback: {e}", file=sys.stderr)
            client = None
    
    interpreted_events = []
    for event in events:
        context = get_transcript_context(vtot_data, event) if vtot_data else ""
        if client:
            analysis = get_llm_analysis(event, context, client)
        else:
            analysis = get_fallback_analysis(event)
        
        interpreted_event = {**event, "llm_analysis": analysis}
        interpreted_events.append(interpreted_event)
        print(f"[INFO] Processed: {event.get('event_type')} for {event.get('speaker_id')} [{analysis['analysis_source']}]", file=sys.stderr)
    
    return interpreted_events


def generate_and_interpret_events(
    vtot_data: Dict,
    signals: Dict,
    text_markers: Dict,
    financial_context: Dict,
    enable_llm: bool = True
) -> Dict:
    """Unified entry point for V2."""
    detector = EventDetector(vtot_data, signals, text_markers, financial_context)
    events = detector.detect()
    
    interpreted_events = interpret_events(events, vtot_data, enable_llm)
    
    call_id = financial_context.get('context', {}).get('call_id', f"CALL-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
    
    return {
        "artifact_type": ARTIFACT_TYPE,
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "llm_enabled": enable_llm,
        "call_id": call_id,
        "events": interpreted_events,
        "summary": {
            "total_events": len(interpreted_events),
            "events_by_source": {
                "llm": len([e for e in interpreted_events if e.get('llm_analysis', {}).get('analysis_source') == 'llm']),
                "fallback": len([e for e in interpreted_events if e.get('llm_analysis', {}).get('analysis_source') == 'fallback'])
            },
            "high_risk_events": len([e for e in interpreted_events if e.get('llm_analysis', {}).get('risk_level') == 'high'])
        }
    }


def load_json(path: str) -> Dict:
    for enc in ['utf-8-sig', 'utf-8', 'utf-16']:
        try:
            with open(path, 'r', encoding=enc) as f: return json.load(f)
        except: pass
    return {}


def main():
    use_llm = '--no-llm' not in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    
    if len(args) < 4:
        print(json.dumps({"error": "usage: EventProcessor.py vtot.json signals.json markers.json context.json [--no-llm]"}, indent=2))
        sys.exit(1)
    
    vtot_data = load_json(args[0])
    signals = load_json(args[1])
    text_markers = load_json(args[2])
    financial_context = load_json(args[3])
    
    result = generate_and_interpret_events(
        vtot_data=vtot_data,
        signals=signals,
        text_markers=text_markers,
        financial_context=financial_context,
        enable_llm=use_llm
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
