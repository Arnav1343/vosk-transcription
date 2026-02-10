"""TextEXT.py v1.3.0 - Text Marker Extraction
Extracts text markers (financial, product, commitment, regulatory, PII) using precise pattern matching.
Rule-based, deterministic - no probabilistic NLP."""

import json, re, sys
from typing import Dict, List, Set

VERSION, ARTIFACT_TYPE = "1.3.0", "text_marker_extraction"

FINANCIAL_KW = ["credit card","debit card","visa","mastercard","amex","bank account","routing number",
    "account number","card number","check","payment","balance","amount due","fee","charge","invoice",
    "bill","statement","deposit","refund","transaction","paid","owed","due date"]
PRODUCT_KW = ["subscription","plan","package","service","product","map","update","upgrade","version",
    "software","warranty","insurance","coverage","membership","account","profile","order","purchase","shipping"]
REGULATORY = ["this call may be recorded","this call is being recorded","this call is recorded",
    "for quality assurance","for training purposes","calls are monitored","do you consent","do you agree to",
    "do i have your permission","do you authorize","verify your address","verify your phone","verify your name",
    "verify your identity","confirm your address","confirm your phone","for verification purposes",
    "terms and conditions","annual percentage rate","apr","cooling off period","rate of"]

# Tighter currency regex - requires specific patterns, avoids false positives
CURRENCY = re.compile(r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD|EUR|GBP|PLN|RUB)\b', re.I)
COMMIT = [re.compile(p, re.I) for p in [r"\bi\s+will\s+pay\b",r"\bi'?ll\s+pay\b",r"\bi\s+agree\s+to\s+pay\b",
    r"\bi\s+can\s+pay\b",r"\blet\s+me\s+pay\b",r"\bi\s+authorize\b",r"\bi\s+agree\b",r"\byes,?\s+i\s+agree\b",
    r"\bi\s+accept\b",r"\bi\s+consent\b",r"\bi\s+confirm\b",r"\blet'?s\s+use\s+(?:my|a)\s+(?:visa|card)\b"]]

# Tighter PII patterns - specific formats only (reduced false positives)
PII = {
    "phone": re.compile(r'\b(?:\d{3}[-.\s]?\d{3}[-.\s]?\d{4}|\(\d{3}\)\s*\d{3}[-.\s]?\d{4})\b'),  # Strict phone format
    "account": re.compile(r'\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b|\b\d{10,16}\b'),  # Card or account number
    "ssn_partial": re.compile(r'\bxxx-xx-\d{4}\b|\b\*{3}-\*{2}-\d{4}\b', re.I)  # Masked SSN only
}

def extract(text: str, recent: Set[str]) -> tuple:
    markers, tl = [], text.lower()
    for m in CURRENCY.finditer(text):
        markers.append({"type":"financial_entity","category":"currency_amount","matched_text":m.group(),"evidence":f"'{m.group()}'"})
    for kw in FINANCIAL_KW:
        if kw in tl: markers.append({"type":"financial_entity","category":"financial_term","matched_text":kw,"evidence":f"'{kw}'"}); break
    product = None
    for kw in PRODUCT_KW:
        if kw in tl and kw not in recent: markers.append({"type":"product_reference","matched_text":kw,"evidence":f"'{kw}'"}); product=kw; break
    for p in COMMIT:
        m = p.search(text)
        if m: markers.append({"type":"customer_commitment","matched_text":m.group(),"evidence":f"'{m.group()}'"}); break
    reg_matches = [(p, len(p)) for p in REGULATORY if p in tl]
    if reg_matches:
        best = max(reg_matches, key=lambda x: x[1])[0]
        markers.append({"type":"regulatory_prompt","matched_phrase":best,"evidence":f"'{best}'"})
    flagged = set()
    for cat, pat in PII.items():
        for m in pat.finditer(text):
            if m.start() not in flagged and (cat != "sequence" or len(m.group()) >= 5):
                markers.append({"type":"potential_pii","category":cat+"_pattern" if cat!="sequence" else "numeric_sequence",
                    "position":m.start(),"length":len(m.group()),"evidence":f"at pos {m.start()}"})
                flagged.add(m.start())
    return markers, {product} if product else set()

def transform(data: Dict) -> Dict:
    sents, out, recent = data.get('sentences', []), [], set()
    for idx, s in enumerate(sents):
        text = s.get('text', '')
        markers, products = extract(text, recent)
        recent = products
        out.append({"sentence_index":idx,"timestamp":{"start":s.get('start',0),"end":s.get('end',0)},"text":text,"markers":markers})
    return {"artifact_type":ARTIFACT_TYPE,"version":VERSION,"marker_types":["financial_entity","product_reference",
        "customer_commitment","regulatory_prompt","potential_pii"],"extraction_method":"deterministic_pattern_matching","sentences":out}

def main():
    data = None
    if len(sys.argv) >= 2:
        for enc in ['utf-8-sig', 'utf-8', 'utf-16']:
            try:
                with open(sys.argv[1], 'r', encoding=enc) as f:
                    data = json.load(f)
                    break
            except:
                pass
    else: data = json.load(sys.stdin)
    print(json.dumps(transform(data) if data else {"error":"read_failed"}, indent=2))

if __name__ == "__main__": main()
