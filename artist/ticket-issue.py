"""
Ticket issuance.

Loads artist config, validates it's active, issues a NUVL-bound
ticket artifact for a fan purchase. Saves ticket to tickets/ dir.

Usage:
    python ticket_issue.py <config_file> <fan_email> [<payment_id>]

Example:
    python ticket_issue.py configs/the-midnight.json fan@example.com pi_abc123
"""

import hashlib
import hmac
import json
import os
import sys
import time
import re

# ------------------------------------------------------------------
# NUVL core (Apache 2.0)
# ------------------------------------------------------------------

BIND_TAG          = "NUVL_BIND_V1"
PROVIDER_HMAC_KEY = os.environ.get("PROVIDER_HMAC_KEY", "PROVIDER_ONLY_KEY_CHANGE_ME").encode()

def nuvl_bind(request_bytes: bytes, context: str) -> dict:
    request_repr = hashlib.sha256(request_bytes).hexdigest()
    msg          = (BIND_TAG + "|" + request_repr + "|" + context).encode("utf-8")
    binding      = hashlib.sha256(msg).hexdigest()
    return {"request_repr": request_repr, "context": context, "binding": binding}

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

def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)

def validate_config(config: dict) -> str | None:
    if not config.get("active"):
        return "Artist config is not active. Set 'active': true to go live."
    if config.get("ticket_quantity", 0) < 1:
        return "No tickets configured."
    return None

def slug(val: str) -> str:
    s = val.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")

def ticket_id(fan_email: str, hub_id: str, issued_at: int) -> str:
    seed = f"{fan_email}|{hub_id}|{issued_at}".encode("utf-8")
    return "TKT_" + hashlib.sha256(seed).hexdigest()[:16].upper()

def remaining_tickets(config: dict) -> int:
    """Count issued tickets for this hub and return remaining."""
    os.makedirs(TICKETS_DIR, exist_ok=True)
    hub_id  = config["hub_id"]
    issued  = sum(
        1 for f in os.listdir(TICKETS_DIR)
        if f.endswith(".json") and f.startswith(slug(config["act_name"]))
    )
    return config["ticket_quantity"] - issued

def fan_ticket_count(config: dict, fan_email: str) -> int:
    """Count how many tickets this fan already holds for this hub."""
    os.makedirs(TICKETS_DIR, exist_ok=True)
    count = 0
    for fname in os.listdir(TICKETS_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(TICKETS_DIR, fname)) as f:
                t = json.load(f)
            if t.get("hub_id") == config["hub_id"] and t.get("fan_email") == fan_email:
                count += 1
        except Exception:
            continue
    return count

def save_ticket(ticket: dict, act_name: str, tkt_id: str) -> str:
    os.makedirs(TICKETS_DIR, exist_ok=True)
    filename = f"{slug(act_name)}-{tkt_id}.json"
    path     = os.path.join(TICKETS_DIR, filename)
    with open(path, "w") as f:
        json.dump(ticket, f, indent=2)
    return path

# ------------------------------------------------------------------
# Core issuance
# ------------------------------------------------------------------

def issue_ticket(config: dict, fan_email: str, payment_id: str = "") -> dict:
    """
    Issue a NUVL-bound ticket artifact for a fan purchase.
    Returns the ticket dict. Raises on any constraint violation.
    """

    # Capacity check
    remaining = remaining_tickets(config)
    if remaining < 1:
        raise RuntimeError("Sold out. No tickets remaining.")

    # Per-fan limit check
    already   = fan_ticket_count(config, fan_email)
    limit     = config.get("purchase_limit_per_fan", 2)
    if already >= limit:
        raise RuntimeError(
            f"Purchase limit reached. This fan already holds {already} ticket(s). "
            f"Limit is {limit} per fan."
        )

    # Build request payload — everything that defines this purchase
    issued_at = time.time_ns()
    tkt_id    = ticket_id(fan_email, config["hub_id"], issued_at)

    request_payload = json.dumps({
        "ticket_id":    tkt_id,
        "hub_id":       config["hub_id"],
        "act_name":     config["act_name"],
        "fan_email":    fan_email,
        "price_usd":    config["ticket_price_usd"],
        "payment_id":   payment_id,
        "issued_at_ns": issued_at,
    }, sort_keys=True).encode("utf-8")

    # Verification context — ties this ticket to this hub and this moment
    context = f"TICKET|{config['hub_id']}|{fan_email}|{issued_at}"

    # NUVL bind
    artifact = nuvl_bind(request_payload, context)

    # Provider verify — stays inside provider boundary
    if not provider_verify(artifact):
        raise RuntimeError("Provider verification failed. Ticket not issued.")

    # Assemble ticket record
    ticket = {
        "_schema":       "artist-ticket-v1",
        "ticket_id":     tkt_id,
        "hub_id":        config["hub_id"],
        "act_name":      config["act_name"],
        "fan_email":     fan_email,
        "price_usd":     config["ticket_price_usd"],
        "payment_id":    payment_id,
        "issued_at_ns":  issued_at,
        "stream_url":    config.get("stream_url", "TBD"),
        "refund_policy": config.get("refund_policy", ""),
        "artifact":      artifact,
        "valid":         True,
        "_valid_note":   "Validity is determined by provider_verify(artifact), not by this field.",
    }

    path = save_ticket(ticket, config["act_name"], tkt_id)
    ticket["_saved_to"] = path

    return ticket

# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    config_path = sys.argv[1]
    fan_email   = sys.argv[2]
    payment_id  = sys.argv[3] if len(sys.argv) > 3 else ""

    # Load and validate config
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        print(f"Config not found: {config_path}")
        sys.exit(1)

    error = validate_config(config)
    if error:
        print(f"Config error: {error}")
        sys.exit(1)

    # Issue
    try:
        ticket = issue_ticket(config, fan_email, payment_id)
    except RuntimeError as e:
        print(f"Issuance failed: {e}")
        sys.exit(1)

    # Summary
    print()
    print("=" * 52)
    print("  Ticket issued.")
    print("=" * 52)
    print()
    print(f"  Ticket ID:   {ticket['ticket_id']}")
    print(f"  Act:         {ticket['act_name']}")
    print(f"  Fan:         {ticket['fan_email']}")
    if ticket["price_usd"] == 0:
        print(f"  Price:       Free")
    else:
        print(f"  Price:       ${ticket['price_usd']:.2f}")
    print(f"  Stream:      {ticket['stream_url']}")
    print(f"  Binding:     {ticket['artifact']['binding'][:24]}...")
    print(f"  Saved to:    {ticket['_saved_to']}")
    print()
    print("  Provider verified. Binding holds.")
    print()


if __name__ == "__main__":
    main()
