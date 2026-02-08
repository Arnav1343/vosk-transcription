"""
TextEXT.py - Text Marker Extraction Module v1.2.0

ARTIFACT TYPE: text_marker_extraction
VERSION: 1.2.0

PURPOSE:
    Deterministic extraction of explicit textual elements from sentence-level
    transcripts. Text-only, independent of behavioral analysis.

MARKER TYPES (standardized):
    1. financial_entity    - Currency amounts, payment instruments, financial IDs
    2. product_reference   - Product names, service terms (de-noised)
    3. customer_commitment - First-person payment/agreement commitments
    4. regulatory_prompt   - Compliance/verification phrases only (tightened)
    5. potential_pii       - Phone, account, numeric patterns (neutral labels)

CHANGES v1.2.0:
    - Tightened regulatory_prompt to compliance-specific phrases only
    - Renamed zipcode_pattern to numeric_identifier_pattern
    - Added deduplication for regulatory markers
    - Added product_reference tracking to reduce adjacent-sentence noise
"""

import json
import re
import sys
from typing import Dict, List, Set

VERSION = "1.2.0"
ARTIFACT_TYPE = "text_marker_extraction"


# =============================================================================
# MARKER TYPE 1: FINANCIAL_ENTITY (strictly monetary)
# =============================================================================

FINANCIAL_ENTITY_KEYWORDS = [
    "credit card", "debit card", "visa", "mastercard", "amex", "american express",
    "bank account", "routing number", "account number", "card number",
    "check", "cheque", "wire transfer", "payment",
    "balance", "amount due", "total due", "fee", "charge", "interest",
    "invoice", "bill", "statement", "deposit", "refund",
    "transaction", "paid", "owed", "owing", "due date"
]

CURRENCY_PATTERN = re.compile(
    r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?'
    r'|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|cents?|usd)\b',
    re.IGNORECASE
)


# =============================================================================
# MARKER TYPE 2: PRODUCT_REFERENCE (de-noised)
# =============================================================================

PRODUCT_KEYWORDS = [
    "subscription", "plan", "package", "service", "product",
    "map", "update", "upgrade", "version", "software",
    "warranty", "insurance", "coverage", "protection",
    "membership", "account", "profile",
    "order", "purchase", "delivery", "shipping"
]


# =============================================================================
# MARKER TYPE 3: CUSTOMER_COMMITMENT (first-person + commitment verb)
# =============================================================================

CUSTOMER_COMMITMENT_PATTERNS = [
    re.compile(r"\bi\s+will\s+pay\b", re.IGNORECASE),
    re.compile(r"\bi'?ll\s+pay\b", re.IGNORECASE),
    re.compile(r"\bi\s+agree\s+to\s+pay\b", re.IGNORECASE),
    re.compile(r"\bi\s+can\s+pay\b", re.IGNORECASE),
    re.compile(r"\blet\s+me\s+pay\b", re.IGNORECASE),
    re.compile(r"\bi\s+authorize\b", re.IGNORECASE),
    re.compile(r"\bi\s+agree\b", re.IGNORECASE),
    re.compile(r"\byes,?\s+i\s+agree\b", re.IGNORECASE),
    re.compile(r"\bi\s+accept\b", re.IGNORECASE),
    re.compile(r"\bi\s+consent\b", re.IGNORECASE),
    re.compile(r"\bi\s+confirm\b", re.IGNORECASE),
    re.compile(r"\bi\s+understand\s+and\s+agree\b", re.IGNORECASE),
    re.compile(r"\blet'?s\s+go\s+ahead\s+and\s+(?:pay|use)\b", re.IGNORECASE),
    re.compile(r"\blet'?s\s+use\s+(?:my|a)\s+(?:visa|card|credit)\b", re.IGNORECASE),
]


# =============================================================================
# MARKER TYPE 4: REGULATORY_PROMPT (compliance-specific only)
# =============================================================================

# Tightened: only clear compliance/verification phrases
REGULATORY_PROMPT_PHRASES = [
    # Recording/disclosure (high confidence)
    "this call may be recorded",
    "this call is being recorded",
    "this call is recorded",
    "for quality assurance",
    "for training purposes",
    "calls are monitored",
    "calls may be monitored",
    
    # Explicit consent prompts
    "do you consent",
    "do you agree to",
    "do i have your permission",
    "do you authorize",
    
    # Identity verification (specific)
    "verify your address",
    "verify your phone number",
    "verify your phone",
    "verify your name",
    "verify your identity",
    "confirm your address",
    "confirm your phone number",
    "confirm your identity",
    "for verification purposes"
]


# =============================================================================
# MARKER TYPE 5: POTENTIAL_PII (neutral labels)
# =============================================================================

PII_PATTERNS = {
    "phone_pattern": re.compile(
        r'\b(?:'
        r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}'
        r'|\(\d{3}\)\s*[-.]?\s*\d{3}[-.\s]?\d{4}'
        r'|\d{3}\s*[-.]?\s*\d{4}'
        r'|\d{10,11}'
        r'|[a-z]-?\d{2}-?\d{3}-?\d{4}'
        r')\b',
        re.IGNORECASE
    ),
    "account_pattern": re.compile(
        r'\b\d{4,}(?:[-\s]\d{2,})+\b'
        r'|\b\d{8,16}\b'
    ),
    # Renamed from zipcode_pattern to neutral label
    "numeric_identifier_pattern": re.compile(
        r'\b\d{5}(?:-\d{4})?\b'
    ),
    "numeric_sequence": re.compile(
        r'\b\d{5,}\b'
    )
}


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

def extract_financial_entity(text: str) -> List[Dict]:
    markers = []
    text_lower = text.lower()
    
    for match in CURRENCY_PATTERN.finditer(text):
        markers.append({
            "type": "financial_entity",
            "category": "currency_amount",
            "matched_text": match.group(),
            "evidence": f"currency '{match.group()}' at position {match.start()}"
        })
    
    for keyword in FINANCIAL_ENTITY_KEYWORDS:
        if keyword in text_lower:
            markers.append({
                "type": "financial_entity",
                "category": "financial_term",
                "matched_text": keyword,
                "evidence": f"contains '{keyword}'"
            })
            break
    
    return markers


def extract_product_reference(text: str, recent_products: Set[str]) -> List[Dict]:
    """Extract product references, avoiding recent duplicates."""
    markers = []
    text_lower = text.lower()
    
    for keyword in PRODUCT_KEYWORDS:
        if keyword in text_lower:
            # Skip if same product was tagged in previous sentence
            if keyword not in recent_products:
                markers.append({
                    "type": "product_reference",
                    "matched_text": keyword,
                    "evidence": f"contains '{keyword}'"
                })
            break
    
    return markers


def extract_customer_commitment(text: str) -> List[Dict]:
    markers = []
    
    for pattern in CUSTOMER_COMMITMENT_PATTERNS:
        match = pattern.search(text)
        if match:
            markers.append({
                "type": "customer_commitment",
                "matched_text": match.group(),
                "evidence": f"first-person commitment '{match.group()}'"
            })
            break
    
    return markers


def extract_regulatory_prompt(text: str) -> List[Dict]:
    """Extract compliance/verification prompts (deduplicated)."""
    text_lower = text.lower()
    matches = []
    
    for phrase in REGULATORY_PROMPT_PHRASES:
        if phrase in text_lower:
            matches.append({
                "phrase": phrase,
                "length": len(phrase)
            })
    
    if not matches:
        return []
    
    # Deduplicate: keep only the longest/most specific match
    best_match = max(matches, key=lambda x: x["length"])
    
    return [{
        "type": "regulatory_prompt",
        "matched_phrase": best_match["phrase"],
        "evidence": f"contains '{best_match['phrase']}'"
    }]


def extract_potential_pii(text: str) -> List[Dict]:
    markers = []
    flagged_positions = set()
    
    for match in PII_PATTERNS["phone_pattern"].finditer(text):
        pos = match.start()
        if pos not in flagged_positions:
            markers.append({
                "type": "potential_pii",
                "category": "phone_pattern",
                "position": pos,
                "length": len(match.group()),
                "evidence": f"phone-like pattern at position {pos}"
            })
            flagged_positions.add(pos)
    
    for match in PII_PATTERNS["account_pattern"].finditer(text):
        pos = match.start()
        if pos not in flagged_positions:
            markers.append({
                "type": "potential_pii",
                "category": "account_pattern",
                "position": pos,
                "length": len(match.group()),
                "evidence": f"account-like pattern at position {pos}"
            })
            flagged_positions.add(pos)
    
    for match in PII_PATTERNS["numeric_identifier_pattern"].finditer(text):
        pos = match.start()
        if pos not in flagged_positions:
            markers.append({
                "type": "potential_pii",
                "category": "numeric_identifier_pattern",
                "position": pos,
                "length": len(match.group()),
                "evidence": f"numeric identifier at position {pos}"
            })
            flagged_positions.add(pos)
    
    for match in PII_PATTERNS["numeric_sequence"].finditer(text):
        pos = match.start()
        if pos not in flagged_positions and len(match.group()) >= 5:
            markers.append({
                "type": "potential_pii",
                "category": "numeric_sequence",
                "position": pos,
                "length": len(match.group()),
                "evidence": f"numeric sequence at position {pos}"
            })
            flagged_positions.add(pos)
    
    return markers


def transform(vtot_output: Dict) -> Dict:
    sentences = vtot_output.get("sentences", [])
    
    output_sentences = []
    recent_products: Set[str] = set()  # Track recent product terms
    
    for idx, sentence in enumerate(sentences):
        text = sentence.get("text", "")
        
        all_markers = []
        all_markers.extend(extract_financial_entity(text))
        
        product_markers = extract_product_reference(text, recent_products)
        all_markers.extend(product_markers)
        
        # Update recent products (keep only last sentence's products)
        recent_products.clear()
        for m in product_markers:
            recent_products.add(m["matched_text"])
        
        all_markers.extend(extract_customer_commitment(text))
        all_markers.extend(extract_regulatory_prompt(text))
        all_markers.extend(extract_potential_pii(text))
        
        output_sentences.append({
            "sentence_index": idx,
            "timestamp": {
                "start": sentence.get("start", 0),
                "end": sentence.get("end", 0)
            },
            "text": text,
            "markers": all_markers
        })
    
    return {
        "artifact_type": ARTIFACT_TYPE,
        "version": VERSION,
        "marker_types": ["financial_entity", "product_reference", "customer_commitment", "regulatory_prompt", "potential_pii"],
        "extraction_method": "deterministic_phrase_and_pattern_matching",
        "sentences": output_sentences
    }


def main():
    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
        vtot_output = None
        for encoding in ['utf-8-sig', 'utf-8', 'utf-16']:
            try:
                with open(input_file, 'r', encoding=encoding) as f:
                    vtot_output = json.load(f)
                break
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        if vtot_output is None:
            print(json.dumps({"artifact_type": ARTIFACT_TYPE, "version": VERSION, "error": "could_not_read_file"}))
            sys.exit(1)
    else:
        vtot_output = json.load(sys.stdin)
    
    result = transform(vtot_output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
