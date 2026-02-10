"""FinContext.py v1.1.0 - Financial Context Injection Layer
Converts external call metadata into normalized financial context.
IMPORTANT: Context is built ONLY from confirmed markers and known metadata.
Never derives context from behavioral signals. Does not imply risk or outcome."""

import json, sys
from typing import Dict, Optional
from datetime import datetime, timezone

VERSION, ARTIFACT_TYPE = "1.1.0", "financial_context"

# === EXPLICIT RULE TABLES (no ML, no hidden logic) ===

AMOUNT_BANDS = [  # (min, max, band_name)
    (0, 50, "low"), (50, 200, "normal"), (200, 500, "moderate"), 
    (500, 1000, "elevated"), (1000, float('inf'), "high")
]

PRODUCT_SENSITIVITY = {  # product_type -> sensitivity_level
    "subscription": "standard", "map_update": "standard", "software": "standard",
    "warranty": "elevated", "insurance": "elevated", "protection_plan": "elevated",
    "loan": "high", "credit": "high", "debt_collection": "high", "payment_plan": "high"
}

CUSTOMER_PRIORITY = {  # customer_type -> priority_level
    "new": "standard", "returning": "standard", "regular": "standard",
    "premium": "elevated", "vip": "elevated", "enterprise": "elevated",
    "delinquent": "flagged", "disputed": "flagged"
}

def classify_amount(amount: Optional[float]) -> Dict:
    """Map numeric amount to band using explicit rules."""
    if amount is None: return {"band": "unknown", "value": None}
    for min_v, max_v, band in AMOUNT_BANDS:
        if min_v <= amount < max_v:
            return {"band": band, "value": amount}
    return {"band": "unknown", "value": amount}

def classify_product(product_type: Optional[str]) -> Dict:
    """Map product type to sensitivity using lookup table."""
    if not product_type: return {"type": None, "sensitivity": "unknown"}
    pt = product_type.lower().replace(" ", "_").replace("-", "_")
    sensitivity = PRODUCT_SENSITIVITY.get(pt, "standard")
    return {"type": pt, "sensitivity": sensitivity}

def classify_customer(customer_type: Optional[str]) -> Dict:
    """Map customer type to priority using lookup table."""
    if not customer_type: return {"type": None, "priority": "unknown"}
    ct = customer_type.lower().replace(" ", "_")
    priority = CUSTOMER_PRIORITY.get(ct, "standard")
    return {"type": ct, "priority": priority}

def inject_context(metadata: Dict) -> Dict:
    """
    Convert external metadata into normalized financial context.
    
    Input fields (all optional):
        - call_id: str
        - product_type: str (e.g., "subscription", "loan", "warranty")
        - amount: float (transaction amount in dollars)
        - customer_type: str (e.g., "new", "premium", "delinquent")
        - agent_id: str
        - timestamp: str (ISO format) or auto-generated
    
    Output: Versioned financial context JSON
    """
    return {
        "artifact_type": ARTIFACT_TYPE,
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat().replace('+00:00', '') + "Z",
        "context": {
            "call_id": metadata.get("call_id"),
            "agent_id": metadata.get("agent_id"),
            "timestamp": metadata.get("timestamp", datetime.now(timezone.utc).isoformat().replace('+00:00', '') + "Z"),
            "amount": classify_amount(metadata.get("amount")),
            "product": classify_product(metadata.get("product_type")),
            "customer": classify_customer(metadata.get("customer_type"))
        },
        "rules_applied": ["amount_band_classification", "product_sensitivity_lookup", "customer_priority_lookup"]
    }

def main():
    """Accept JSON metadata from file, stdin, or CLI args."""
    metadata = {}
    
    if len(sys.argv) >= 2:
        # Try file first
        try:
            with open(sys.argv[1], 'r') as f: metadata = json.load(f)
        except:
            # Parse CLI args: key=value pairs
            for arg in sys.argv[1:]:
                if '=' in arg:
                    k, v = arg.split('=', 1)
                    metadata[k] = float(v) if k == 'amount' else v
    elif not sys.stdin.isatty():
        metadata = json.load(sys.stdin)
    
    print(json.dumps(inject_context(metadata), indent=2))

if __name__ == "__main__": main()
