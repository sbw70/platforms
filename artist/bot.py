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
Artist onboarding bot.

Asks the artist 8 questions. Writes their hub config.
No dependencies beyond stdlib. Runs in terminal or via Replit.

Usage:
    python bot.py
"""

import json
import os
import re
import hashlib
import time

CONFIGS_DIR = os.path.join(os.path.dirname(__file__), "configs")
SCHEMA_VERSION = "artist-hub-v1"
PLATFORM_FEE_PCT = 2.0


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def ask(prompt: str, validate=None, default=None) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        raw = input(f"\n{prompt}{suffix}\n> ").strip()
        if not raw and default is not None:
            raw = default
        if not raw:
            print("  (required — please enter a value)")
            continue
        if validate:
            error = validate(raw)
            if error:
                print(f"  {error}")
                continue
        return raw


def ask_optional(prompt: str) -> str:
    raw = input(f"\n{prompt} (press Enter to skip)\n> ").strip()
    return raw


def validate_url(val: str):
    if not val.startswith("http://") and not val.startswith("https://"):
        return "Please enter a full URL starting with http:// or https://"
    return None


def validate_price(val: str):
    try:
        price = float(val)
        if price < 0:
            return "Price can't be negative."
        return None
    except ValueError:
        return "Enter a number, e.g. 15 or 15.00"


def validate_quantity(val: str):
    try:
        qty = int(val)
        if qty < 1:
            return "Quantity must be at least 1."
        return None
    except ValueError:
        return "Enter a whole number, e.g. 500"


def validate_limit(val: str):
    try:
        lim = int(val)
        if lim < 1:
            return "Limit must be at least 1."
        if lim > 10:
            return "Limit above 10 is unusual — are you sure? Enter again to confirm or choose a lower number."
        return None
    except ValueError:
        return "Enter a whole number, e.g. 2"


def validate_email(val: str):
    if "@" not in val or "." not in val.split("@")[-1]:
        return "Doesn't look like a valid email."
    return None


def slug(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def generate_hub_id(act_name: str) -> str:
    seed = (act_name + str(time.time_ns())).encode("utf-8")
    return "HUB_" + hashlib.sha256(seed).hexdigest()[:12].upper()


def save_config(config: dict, act_name: str) -> str:
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    filename = slug(act_name) + ".json"
    path = os.path.join(CONFIGS_DIR, filename)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    return path


# ------------------------------------------------------------------
# Bot conversation
# ------------------------------------------------------------------

def run():
    print()
    print("=" * 52)
    print("  Artist Hub Setup")
    print("  Your answers. Your config. Your platform.")
    print("=" * 52)
    print()
    print("This takes about 2 minutes.")
    print("You can change anything later by editing your config file.")

    # 1. Names
    artist_name = ask("What's your name? (your real name or band name)")
    act_name = ask(
        "What name should fans see? (stage name, act name — same as above if identical)",
        default=artist_name,
    )

    # 2. Contact
    contact_email = ask(
        "Your email address (for platform notifications only — never shared with fans)",
        validate=validate_email,
    )

    # 3. Music
    print()
    print("─" * 52)
    print("  Where you host your music")
    print("  (Bandcamp, SoundCloud, your own site — anywhere)")
    print("─" * 52)
    music_url = ask("Paste the URL to your music", validate=validate_url)

    # 4. Streaming
    print()
    print("─" * 52)
    print("  Live streaming")
    print("  (YouTube Live, Twitch, Vimeo, your own RTMP — your call)")
    print("  The platform validates tickets and surfaces your link.")
    print("  You control the stream. We just open the door.")
    print("─" * 52)
    stream_raw = ask_optional("Paste your stream URL (or leave blank if no shows planned yet)")
    stream_url = stream_raw if stream_raw else "TBD"

    # 5. Tickets
    print()
    print("─" * 52)
    print("  Tickets")
    print("─" * 52)
    ticket_price_raw = ask(
        "Ticket price in USD (enter 0 for free)",
        validate=validate_price,
    )
    ticket_price = float(ticket_price_raw)

    ticket_qty_raw = ask(
        "How many tickets total? (hard cap — bots can't exceed this)",
        validate=validate_quantity,
    )
    ticket_qty = int(ticket_qty_raw)

    purchase_limit_raw = ask(
        "Max tickets per fan? (keeps bots from scalping — recommended: 2)",
        validate=validate_limit,
        default="2",
    )
    purchase_limit = int(purchase_limit_raw)

    # 6. Refund policy
    print()
    print("─" * 52)
    print("  Refund policy")
    print("  Options:")
    print("    1. No refunds")
    print("    2. Full refund up to 48 hours before show")
    print("    3. Full refund up to 7 days before show")
    print("    4. Type your own")
    print("─" * 52)
    refund_choice = ask("Choose 1, 2, 3, or 4")
    refund_map = {
        "1": "No refunds.",
        "2": "Full refund available up to 48 hours before show.",
        "3": "Full refund available up to 7 days before show.",
    }
    if refund_choice in refund_map:
        refund_policy = refund_map[refund_choice]
    else:
        refund_policy = ask("Type your refund policy")

    # 7. Merch
    print()
    print("─" * 52)
    print("  Merch")
    print("  (Shopify, Bandcamp, Printful, your own site — whatever you use)")
    print("─" * 52)
    merch_raw = ask_optional("Paste your merch URL")
    merch_url = merch_raw if merch_raw else ""

    # 8. Stripe
    print()
    print("─" * 52)
    print("  Payments")
    print("  You'll need a Stripe account. Free to set up at stripe.com.")
    print("  Your Stripe account ID starts with 'acct_'")
    print("─" * 52)
    stripe_raw = ask_optional("Paste your Stripe account ID (or leave blank to set up later)")
    stripe_account = stripe_raw if stripe_raw else ""

    # Build config
    hub_id = generate_hub_id(act_name)
    config = {
        "_schema": SCHEMA_VERSION,
        "_note": "This file is owned and controlled by the artist. The platform reads it. Nothing else.",
        "artist_name": artist_name,
        "act_name": act_name,
        "contact_email": contact_email,
        "music_url": music_url,
        "stream_url": stream_url,
        "merch_url": merch_url,
        "ticket_price_usd": ticket_price,
        "ticket_quantity": ticket_qty,
        "purchase_limit_per_fan": purchase_limit,
        "refund_policy": refund_policy,
        "stripe_account_id": stripe_account,
        "platform_fee_pct": PLATFORM_FEE_PCT,
        "_fee_note": "2% covers Stripe passthrough and infra. Artist receives the rest.",
        "hub_id": hub_id,
        "_hub_note": "Assigned at registration. Artist does not set this.",
        "active": False,
        "_active_note": "Set to true by artist when ready to go live.",
    }

    path = save_config(config, act_name)

    # Summary
    print()
    print("=" * 52)
    print("  Done.")
    print("=" * 52)
    print()
    print(f"  Act name:    {act_name}")
    print(f"  Music:       {music_url}")
    print(f"  Stream:      {stream_url}")
    if ticket_price == 0:
        print(f"  Tickets:     Free — {ticket_qty} available, {purchase_limit} per fan")
    else:
        print(f"  Tickets:     ${ticket_price:.2f} — {ticket_qty} available, {purchase_limit} per fan")
    print(f"  Refunds:     {refund_policy}")
    if merch_url:
        print(f"  Merch:       {merch_url}")
    print(f"  Platform fee: {PLATFORM_FEE_PCT}%  (you keep the rest)")
    print()
    print(f"  Config saved to:")
    print(f"  {path}")
    print()
    print("  To go live, open your config file and set")
    print('  "active": true')
    print()
    if not stripe_account:
        print("  Reminder: add your Stripe account ID before going live.")
        print("  stripe.com → Settings → Account details → Account ID")
        print()


if __name__ == "__main__":
    run()
