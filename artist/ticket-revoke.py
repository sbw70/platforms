#!/usr/bin/env python3
# Copyright 2026 Seth Brian Wells. All rights reserved.

"""
Ticket revocation.

Marks a ticket as revoked. A revoked ticket will not pass
the gate regardless of whether the binding is valid.

Used for:
    - Refunds
    - Chargebacks
    - Artist cancellations

Revocation is recorded in the ticket file.
The original artifact is preserved for audit.

Usage:
    python ticket_revoke.py <ticket_id_or_file> <reason>

Examples:
    python ticket_revoke.py TKT_AB12CD34EF56GH78 "fan requested refund"
    python ticket_revoke.py TKT_AB12CD34EF56GH78 "chargeback"
    python ticket_revoke.py TKT_AB12CD34EF56GH78 "show cancelled"
"""

import json
import os
import sys
import time

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

TICKETS_DIR = os.path.join(os.path.dirname(__file__), "tickets")

def find_ticket(ref: str) -> str | None:
    if os.path.isfile(ref):
        return ref
    if os.path.isdir(TICKETS_DIR):
        for fname in os.listdir(TICKETS_DIR):
            if ref in fname and fname.endswith(".json"):
                return os.path.join(TICKETS_DIR, fname)
    return None

def load_ticket(path: str) -> dict:
    with open(path) as f:
        return json.load(f)

def save_ticket(ticket: dict, path: str):
    with open(path, "w") as f:
        json.dump(ticket, f, indent=2)

# ------------------------------------------------------------------
# Revocation
# ------------------------------------------------------------------

def revoke(ref: str, reason: str) -> bool:
    path = find_ticket(ref)

    print()
    print("=" * 52)

    if not path:
        print("  ERROR — ticket not found.")
        print("=" * 52)
        print(f"  Reference: {ref}")
        print()
        return False

    try:
        ticket = load_ticket(path)
    except Exception as e:
        print("  ERROR — could not read ticket file.")
        print("=" * 52)
        print(f"  Error: {e}")
        print()
        return False

    # Already revoked
    if ticket.get("revoked"):
        print("  ALREADY REVOKED.")
        print("=" * 52)
        print()
        print(f"  Ticket ID:  {ticket.get('ticket_id', '—')}")
        print(f"  Revoked at: {ticket.get('revoked_at_ns', '—')}")
        print(f"  Reason:     {ticket.get('revoked_reason', '—')}")
        print()
        return False

    # Mark revoked — preserve artifact for audit
    ticket["revoked"]         = True
    ticket["revoked_at_ns"]   = time.time_ns()
    ticket["revoked_reason"]  = reason
    ticket["valid"]           = False
    ticket["_revoke_note"]    = "Artifact preserved. Binding record intact for audit."

    save_ticket(ticket, path)

    print("  REVOKED.")
    print("=" * 52)
    print()
    print(f"  Ticket ID:  {ticket.get('ticket_id', '—')}")
    print(f"  Act:        {ticket.get('act_name', '—')}")
    print(f"  Fan:        {ticket.get('fan_email', '—')}")
    print(f"  Reason:     {reason}")
    print()
    print("  Ticket will not pass the gate.")
    print("  Artifact preserved for audit.")
    print()
    return True

# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    ref    = sys.argv[1]
    reason = sys.argv[2]
    result = revoke(ref, reason)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
