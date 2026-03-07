#!/usr/bin/env python3
# Copyright 2026 Seth Brian Wells
"""
Artist onboarding bot.

Asks the artist questions. Writes their hub config.
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


def validate_url_or_blank(val: str):
    if not val:
        return None
    return validate_url(val)


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


def ask_events() -> list:
    """Loop asking for show entries until the artist presses Enter with no input."""
    events = []
    print()
    print("  Enter each show one at a time. Blank line when done.")
    print("  Date format: YYYY-MM-DD (e.g. 2026-09-15)")
    while True:
        date_raw = input("\n  Date (or blank to finish)\n  > ").strip()
        if not date_raw:
            break
        title_raw = input("  Show title\n  > ").strip()
        venue_raw = input("  Venue\n  > ").strip()
        url_raw = input("  Ticket/event URL (or blank)\n  > ").strip()
        type_raw = input("  Type — show / stream / festival [show]\n  > ").strip()
        ev_type = type_raw if type_raw in ("show", "stream", "festival") else "show"
        events.append({
            "date": date_raw,
            "title": title_raw,
            "venue": venue_raw,
            "url": url_raw,
            "type": ev_type,
        })
        print(f"  Added: {title_raw} on {date_raw}")
    return events


def ask_related_artists() -> list:
    """Loop asking for related artist entries (up to 10)."""
    related = []
    print()
    print("  Enter each artist one at a time. Blank name when done. (max 10)")
    while len(related) < 10:
        name_raw = input("\n  Act name (or blank to finish)\n  > ").strip()
        if not name_raw:
            break
        url_raw = input("  Their hub or site URL (or blank)\n  > ").strip()
        music_raw = input("  Bandcamp or SoundCloud URL for in-app playback (or blank)\n  > ").strip()
        related.append({
            "act_name": name_raw,
            "url": url_raw,
            "music_url": music_raw,
        })
        print(f"  Added: {name_raw}")
    return related


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

    # 2. Bio
    print()
    print("─" * 52)
    print("  Bio")
    print("  2-3 sentences fans will see on your page.")
    print("─" * 52)
    bio_raw = ask_optional("Write a short bio")
    bio = bio_raw if bio_raw else ""

    # 3. Contact
    contact_email = ask(
        "Your email address (for platform notifications only — never shared with fans)",
        validate=validate_email,
    )

    # 4. Music
    print()
    print("─" * 52)
    print("  Where you host your music")
    print("  (Bandcamp, SoundCloud, your own site — anywhere)")
    print("─" * 52)
    music_url = ask("Paste the URL to your music", validate=validate_url)

    # 4b. Photo
    print()
    print("─" * 52)
    print("  Press or profile photo")
    print("─" * 52)
    photo_raw = ask_optional("Paste a URL to a press or profile photo")
    photo_url = photo_raw if photo_raw else ""

    # 5. Streaming
    print()
    print("─" * 52)
    print("  Live streaming")
    print("  (YouTube Live, Twitch, Vimeo, your own RTMP — your call)")
    print("  The platform validates tickets and surfaces your link.")
    print("  You control the stream. We just open the door.")
    print("─" * 52)
    stream_raw = ask_optional("Paste your stream URL (or leave blank if no shows planned yet)")
    stream_url = stream_raw if stream_raw else "TBD"

    # 5b. Shows / events
    print()
    print("─" * 52)
    print("  Shows")
    print("─" * 52)
    has_shows = input("\nDo you have any shows to list? (Y/N)\n> ").strip().lower()
    events = []
    if has_shows in ("y", "yes"):
        events = ask_events()

    # 6. Tickets
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

    # 7. Refund policy
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

    # 8. Merch
    print()
    print("─" * 52)
    print("  Merch")
    print("  (Shopify, Bandcamp, Printful, your own site — whatever you use)")
    print("─" * 52)
    merch_raw = ask_optional("Paste your merch URL")
    merch_url = merch_raw if merch_raw else ""

    # 8b. Related artists
    print()
    print("─" * 52)
    print("  Artist recommendations")
    print("  These show up on your hub so fans can discover others you like.")
    print("─" * 52)
    has_related = input("\nWant to recommend any artists to your fans? (Y/N)\n> ").strip().lower()
    related_artists = []
    if has_related in ("y", "yes"):
        related_artists = ask_related_artists()

    # 9. Stripe
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
        "bio": bio,
        "photo_url": photo_url,
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
        "events": events,
        "related_artists": related_artists,
        "active": False,
    }

    # 10. Go live
    print()
    print("─" * 52)
    go_live = ask("Ready to go live now? (yes/no)", default="no")
    if go_live.lower() in ("yes", "y"):
        config["active"] = True
    else:
        config["active"] = False

    path = save_config(config, act_name)

    # Summary
    print()
    print("=" * 52)
    print("  Done.")
    print("=" * 52)
    print()
    print(f"  Act name:    {act_name}")
    if bio:
        print(f"  Bio:         {bio[:60]}{'...' if len(bio) > 60 else ''}")
    print(f"  Music:       {music_url}")
    print(f"  Stream:      {stream_url}")
    if ticket_price == 0:
        print(f"  Tickets:     Free — {ticket_qty} available, {purchase_limit} per fan")
    else:
        print(f"  Tickets:     ${ticket_price:.2f} — {ticket_qty} available, {purchase_limit} per fan")
    print(f"  Refunds:     {refund_policy}")
    if merch_url:
        print(f"  Merch:       {merch_url}")
    if events:
        print(f"  Shows:       {len(events)} listed")
    if related_artists:
        print(f"  Recommended: {len(related_artists)} artists")
    print(f"  Platform fee: {PLATFORM_FEE_PCT}%  (you keep the rest)")
    print()
    print(f"  Config saved to:")
    print(f"  {path}")
    print()

    if config["active"]:
        print("  Status: LIVE")
    else:
        print('  Status: DRAFT — set "active": true when ready.')
    print()

    if not stripe_account:
        print("  Reminder: add your Stripe account ID before going live.")
        print("  stripe.com → Settings → Account details → Account ID")
        print()


if __name__ == "__main__":
    run()
