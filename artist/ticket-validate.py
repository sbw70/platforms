"""
Ticket validation.

Loads a ticket artifact and runs provider_verify().
Pass or reject. No middle ground.

Usage:
    python ticket_validate.py <ticket_id_or_file>

Examples:
    python ticket_validate.py TKT_AB12CD34EF56GH78
    python ticket_validate.py tickets/the-midnight-TKT_AB12CD34EF56GH78.json
"""

import hashlib
import hmac
import json
import os
import sys

# ------------------------------------------------------------------
# NUVL core (Apache 2.0)
# ------------------------------------------------------------------

BIND_TAG          = "NUVL_BIND_V1"
PROVIDER_HMAC_KEY = os.environ.get("PROVIDER_HMAC_KEY", "PROVIDER_ONLY_KEY_CHANGE_ME").encode()

def provider_verify(artifact: dict) -> bool:
    request_repr = artifact["request_repr"]
    context      = artifact["context"]
    binding      = artifact["binding"]
    msg          = (BIND_TAG + "|" + request_repr + "|" + context).encode("utf-8")
    expected     = hashlib.sha256(msg).hexdigest()
    return hmac.compare_digest(binding, expected)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

TICKETS_DIR = os.path.join(os.path.dirname(__file__), "tickets")

def find_ticket(ref: str) -> str | None:
    """
    Accept either a full file path or a ticket ID.
    Returns path to ticket file or None.
    """
    # Direct path
    if os.path.isfile(ref):
        return ref

    # Ticket ID — scan tickets dir
    if os.path.isdir(TICKETS_DIR):
        for fname in os.listdir(TICKETS_DIR):
            if ref in fname and fname.endswith(".json"):
                return os.path.join(TICKETS_DIR, fname)

    return None

def load_ticket(path: str) -> dict:
    with open(path) as f:
        return json.load(f)

# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------

def validate(ref: str) -> bool:
    path = find_ticket(ref)

    if not path:
        print()
        print("  REJECT — ticket not found.")
        print(f"  Reference: {ref}")
        print()
        return False

    try:
        ticket = load_ticket(path)
    except Exception as e:
        print()
        print("  REJECT — could not read ticket file.")
        print(f"  Error: {e}")
        print()
        return False

    artifact = ticket.get("artifact")
    if not artifact:
        print()
        print("  REJECT — no artifact in ticket record.")
        print()
        return False

    verified = provider_verify(artifact)

    print()
    print("=" * 52)

    if verified:
        print("  PASS — binding holds.")
        print("=" * 52)
        print()
        print(f"  Ticket ID:  {ticket.get('ticket_id', '—')}")
        print(f"  Act:        {ticket.get('act_name', '—')}")
        print(f"  Fan:        {ticket.get('fan_email', '—')}")
        if ticket.get("price_usd", 0) == 0:
            print(f"  Price:      Free")
        else:
            print(f"  Price:      ${ticket.get('price_usd', 0):.2f}")
        print(f"  Stream:     {ticket.get('stream_url', '—')}")
        print(f"  Binding:    {artifact['binding'][:24]}...")
        print()
    else:
        print("  REJECT — binding mismatch.")
        print("=" * 52)
        print()
        print(f"  Ticket ID:  {ticket.get('ticket_id', '—')}")
        print(f"  Act:        {ticket.get('act_name', '—')}")
        print(f"  Fan:        {ticket.get('fan_email', '—')}")
        print()
        print("  This ticket did not pass provider verification.")
        print("  It may be forged, tampered, or from a different provider.")
        print()

    return verified

# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    ref    = sys.argv[1]
    result = validate(ref)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
