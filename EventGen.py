"""EventGen.py v1.1.0 - Financial Event Generation Engine
Combines VtoT(3), Interpret, TextEXT, FinContext outputs to emit explainable financial events.
Multi-evidence rules, human-in-the-loop, no raw audio access."""

import json, sys
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone

VERSION, ARTIFACT_TYPE = "1.2.0", "financial_event_generation"

EVENT_TYPES = {
    "consent_uncertainty": "Potential consent/disclosure gap requiring compliance review",
    "affordability_signal": "Behavioral hesitation near explicit monetary amount",
    "pressure_review": "Sales pressure pattern detected near customer hesitation",
    "pii_sensitive_call": "PII disclosed requiring restricted access handling",
    "commitment_without_consent": "Customer commitment without clear prior consent prompt"
}

class EventGenerator:
    def __init__(self, vtot: Dict, signals: Dict, markers: Dict, context: Dict):
        self.vtot = vtot
        self.signals = signals.get('sentences', [])
        self.markers = markers.get('sentences', [])
        self.context = context.get('context', {})
        self.sentences = vtot.get('sentences', [])
        self.events: List[Dict] = []
        self.signal_by_idx = {s['sentence_index']: s for s in self.signals}
        self.marker_by_idx = {m['sentence_index']: m for m in self.markers}
    
    def _get_indicators(self, idx: int) -> List[str]:
        return [i['indicator'] for i in self.signal_by_idx.get(idx, {}).get('indicators', [])]
    
    def _get_markers(self, idx: int) -> List[Dict]:
        return self.marker_by_idx.get(idx, {}).get('markers', [])
    
    def _has_indicator(self, idx: int, name: str) -> bool:
        return name in self._get_indicators(idx)
    
    def _has_marker_type(self, idx: int, mtype: str) -> bool:
        return any(m['type'] == mtype for m in self._get_markers(idx))
    
    def _get_currency_markers(self, idx: int) -> List[Dict]:
        """Get currency_amount markers from TextEXT."""
        return [m for m in self._get_markers(idx) 
                if m['type'] == 'financial_entity' and m.get('category') == 'currency_amount']
    
    def _window_check(self, idx: int, check_fn, window: int = 2) -> List[int]:
        matches = []
        for i in range(max(0, idx - window), min(len(self.sentences), idx + window + 1)):
            if check_fn(i): matches.append(i)
        return matches
    
    def _amount_band(self) -> str:
        return self.context.get('amount', {}).get('band', 'unknown')
    
    def _product_sensitivity(self) -> str:
        return self.context.get('product', {}).get('sensitivity', 'unknown')
    
    def _emit(self, event_type: str, idx: int, evidence: List[Dict], explanation: str, action: str):
        sent = self.sentences[idx] if idx < len(self.sentences) else {}
        self.events.append({
            "event_type": event_type,
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
        """
        REQUIRES ALL THREE:
        1. Explicit currency_amount marker from TextEXT
        2. Behavioral hesitation/slowdown from Interpret in tight window
        3. Amount band is 'low' or 'normal' from FinContext
        
        MERGE LOGIC: Consolidate ALL triggers in same financial context into one event.
        Only create new event if amount_band changes.
        """
        if self._amount_band() not in ['low', 'normal']: return
        
        afford_event = None  # Single event per continuous context
        first_idx = None
        
        for idx in range(len(self.sentences)):
            currency_markers = self._get_currency_markers(idx)
            if not currency_markers: continue
            
            hesitation_idx = self._window_check(idx, 
                lambda i: self._has_indicator(i, 'speed_deviation') or 
                         self._has_indicator(i, 'pause_count_increase'), window=1)
            if not hesitation_idx: continue
            
            current_band = self._amount_band()
            
            # Context reset check: only create new event if amount_band changed
            if afford_event and current_band == afford_event.get('financial_context', {}).get('amount_band'):
                # Merge into existing event
                existing_evidence = afford_event['evidence']
                
                # Add new currency marker
                new_currency = currency_markers[0].get('matched_text')
                existing_currencies = [e.get('matched') for e in existing_evidence if e.get('marker') == 'currency_amount']
                if new_currency not in existing_currencies:
                    existing_evidence.append({"source": "TextEXT", "marker": "currency_amount", "matched": new_currency, "sentence": idx})
                
                # Merge hesitation sentences
                for e in existing_evidence:
                    if e.get('indicator') == 'behavioral_hesitation':
                        e['sentences'] = sorted(set(e['sentences'] + hesitation_idx))
                        break
                
                # Extend timestamp
                sent = self.sentences[idx] if idx < len(self.sentences) else {}
                afford_event['timestamp']['end'] = sent.get('end', afford_event['timestamp']['end'])
                afford_event['explanation'] = f"Affordability signals consolidated (sentences {first_idx}-{idx}), amount_band={current_band}"
                
            else:
                # New event (first or context reset)
                sent = self.sentences[idx] if idx < len(self.sentences) else {}
                afford_event = {
                    "event_type": "affordability_signal",
                    "sentence_index": idx,
                    "timestamp": {"start": sent.get('start', 0), "end": sent.get('end', 0)},
                    "evidence": [
                        {"source": "TextEXT", "marker": "currency_amount", "matched": currency_markers[0].get('matched_text'), "sentence": idx},
                        {"source": "Interpret", "indicator": "behavioral_hesitation", "sentences": hesitation_idx},
                        {"source": "FinContext", "amount_band": current_band}
                    ],
                    "financial_context": {"amount_band": current_band, "product_sensitivity": self._product_sensitivity()},
                    "explanation": f"Affordability signal at sentence {idx}, amount_band={current_band}",
                    "suggested_action": "affordability_check"
                }
                self.events.append(afford_event)
                first_idx = idx
    
    def _rule_pressure_review(self):
        """IF: hesitation THEN product_push THEN agreement THEN: emit"""
        for idx in range(len(self.sentences) - 2):
            if not (self._has_indicator(idx, 'speed_deviation') or self._has_indicator(idx, 'pause_count_increase')): continue
            product_push = [i for i in range(idx+1, min(len(self.sentences), idx+3)) if self._has_marker_type(i, 'product_reference')]
            if not product_push: continue
            agree_idx = [i for i in range(max(product_push)+1, min(len(self.sentences), max(product_push)+3)) 
                        if self._has_indicator(i, 'agreement_pattern')]
            if not agree_idx: continue
            self._emit("pressure_review", idx,
                [{"source": "Interpret", "indicator": "hesitation", "sentence": idx},
                 {"source": "TextEXT", "marker": "product_reference", "sentences": product_push},
                 {"source": "Interpret", "indicator": "agreement_pattern", "sentences": agree_idx}],
                f"Hesitation→product push→agreement pattern: {idx}→{product_push}→{agree_idx}",
                "manual_review")
    
    def _rule_pii_sensitive(self):
        """IF: PII marker (phone/account) exists THEN: emit (PII alone is sufficient)"""
        for idx, m in enumerate(self.markers):
            pii_markers = [mk for mk in m.get('markers', []) 
                          if mk['type'] == 'potential_pii' and mk.get('category') in ['phone_pattern', 'account_pattern']]
            if not pii_markers: continue
            self._emit("pii_sensitive_call", idx,
                [{"source": "TextEXT", "marker": "potential_pii", "category": pii_markers[0].get('category'), "sentence": idx}],
                f"PII ({pii_markers[0].get('category')}) disclosed at sentence {idx}",
                "restricted_access")
            return  # One flag per call
    
    def _rule_consent_gap(self):
        """IF: regulatory_prompt AND no commitment response AND data_quality_issue THEN: emit"""
        for idx in range(len(self.markers)):
            if not self._has_marker_type(idx, 'regulatory_prompt'): continue
            commitment = [i for i in range(idx+1, min(len(self.sentences), idx+4)) if self._has_marker_type(i, 'customer_commitment')]
            if commitment: continue
            dq_issue = [i for i in range(idx+1, min(len(self.sentences), idx+4)) if self._has_indicator(i, 'data_quality_issue')]
            if not dq_issue: continue
            self._emit("consent_uncertainty", idx,
                [{"source": "TextEXT", "marker": "regulatory_prompt", "sentence": idx},
                 {"source": "Interpret", "indicator": "data_quality_issue", "sentences": dq_issue}],
                f"Consent prompt at {idx} with unclear response (data quality issue)",
                "compliance_review")
    
    def generate(self) -> Dict:
        self._rule_consent_uncertainty()
        self._rule_affordability_signal()
        self._rule_pressure_review()
        self._rule_pii_sensitive()
        self._rule_consent_gap()
        
        seen: Set[tuple] = set()
        unique = [e for e in self.events if (key := (e['event_type'], e['sentence_index'])) not in seen and not seen.add(key)]
        
        return {
            "artifact_type": ARTIFACT_TYPE, "version": VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "call_id": self.context.get('call_id'),
            "events": unique,
            "summary": {"total_events": len(unique), 
                       "events_by_type": {t: sum(1 for e in unique if e['event_type'] == t) for t in EVENT_TYPES}}
        }

def load_json(path: str) -> Dict:
    for enc in ['utf-8-sig', 'utf-8', 'utf-16']:
        try:
            with open(path, 'r', encoding=enc) as f: return json.load(f)
        except: pass
    return {}

def main():
    if len(sys.argv) < 5:
        print(json.dumps({"error": "usage: EventGen.py vtot.json signals.json markers.json context.json"}))
        sys.exit(1)
    engine = EventGenerator(load_json(sys.argv[1]), load_json(sys.argv[2]), load_json(sys.argv[3]), load_json(sys.argv[4]))
    print(json.dumps(engine.generate(), indent=2))

if __name__ == "__main__": main()
