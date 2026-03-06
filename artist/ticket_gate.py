#!/usr/bin/env python3
# Copyright 2026 Seth Brian Wells
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Stream gate.

Fan presents ticket ID and email.
If provider_verify() passes, they get the stream URL.
If not, they get nothing.

The stream URL never leaves the provider boundary
until the binding holds.

Usage:
    python ticket_gate.py <ticket_id_or_file> <fan_email>

Example:
    python ticket_gate.py TKT_AB12CD34EF56GH78 fan@example.com
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

# ------------------------------------------------------------------
# Gate
# ------------------------------------------------------------------

def gate(ref: str, fan_email: str) -> bool:
    path = find_ticket(ref)

    print()
    print("=" * 52)

    if not path:
        print("  GATE CLOSED — ticket not found.")
        print("=" * 52)
        print()
        return False

    try:
        ticket = load_ticket(path)
    except Exception as e:
        print("  GATE CLOSED — could not read ticket.")
        print("=" * 52)
        print(f"  Error: {e}")
        print()
        return False

    # Email must match — ticket is non-transferable
    if ticket.get("fan_email", "").lower().strip() != fan_email.lower().strip():
        print("  GATE CLOSED — email does not match ticket.")
        print("=" * 52)
        print()
        print("  This ticket was issued to a different address.")
        print("  Tickets are non-transferable.")
        print()
        return False

    # Revocation check — before touching the artifact
    if ticket.get("revoked"):
        print("  GATE CLOSED — ticket has been revoked.")
        print("=" * 52)
        print()
        print(f"  Reason: {ticket.get('revoked_reason', '—')}")
        print()
        return False

    artifact = ticket.get("artifact")
    if not artifact:
        print("  GATE CLOSED — no artifact in ticket record.")
        print("=" * 52)
        print()
        return False

    verified = provider_verify(artifact)

    if not verified:
        print("  GATE CLOSED — binding mismatch.")
        print("=" * 52)
        print()
        print("  This ticket did not pass provider verification.")
        print("  It may be forged, tampered, or from a different provider.")
        print()
        return False

    # Stream URL only released after verification
    stream_url = ticket.get("stream_url", "")

    if not stream_url or stream_url == "TBD":
        print("  GATE OPEN — binding holds.")
        print("=" * 52)
        print()
        print(f"  Welcome, {fan_email}")
        print(f"  Act: {ticket.get('act_name', '—')}")
        print()
        print("  Stream URL not set yet. Check back closer to show time.")
        print()
        return True

    print("  GATE OPEN — binding holds.")
    print("=" * 52)
    print()
    print(f"  Welcome, {fan_email}")
    print(f"  Act:     {ticket.get('act_name', '—')}")
    print()
    print(f"  Stream:  {stream_url}")
    print()
    print("  This link is yours. Don't share it.")
    print()
    return True

# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    ref       = sys.argv[1]
    fan_email = sys.argv[2]
    result    = gate(ref, fan_email)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
