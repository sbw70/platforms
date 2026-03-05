#!/usr/bin/env python3
# Copyright 2026 Seth Brian Wells. All rights reserved.

"""
Stripe webhook handler.

Listens for payment_intent.succeeded events from Stripe.
On confirmed payment, calls ticket_issue to bind and save the ticket.

Requires:
    pip install stripe flask

Usage:
    python stripe_webhook.py

Environment variables:
    STRIPE_SECRET_KEY      — your Stripe secret key (sk_live_... or sk_test_...)
    STRIPE_WEBHOOK_SECRET  — your Stripe webhook signing secret (whsec_...)
    PROVIDER_HMAC_KEY      — NUVL provider key (keep this secret)

Set up in Stripe Dashboard:
    Webhooks → Add endpoint → https://yourdomain.com/webhook
    Event: payment_intent.succeeded
    Add metadata to your PaymentIntent:
        fan_email:   fan@example.com
        config_file: configs/your-act.json
"""

import json
import os
import sys

try:
    import stripe
    from flask import Flask, request, jsonify
except ImportError:
    print("Missing dependencies. Run: pip install stripe flask")
    sys.exit(1)

from ticket_issue import load_config, validate_config, issue_ticket

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------

STRIPE_SECRET_KEY     = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

if not STRIPE_SECRET_KEY:
    print("STRIPE_SECRET_KEY not set. Export it before running.")
    sys.exit(1)

if not STRIPE_WEBHOOK_SECRET:
    print("STRIPE_WEBHOOK_SECRET not set. Export it before running.")
    sys.exit(1)

stripe.api_key = STRIPE_SECRET_KEY

# ------------------------------------------------------------------
# App
# ------------------------------------------------------------------

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    payload   = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    # Verify the event came from Stripe
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid signature"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    # Only handle confirmed payments
    if event["type"] != "payment_intent.succeeded":
        return jsonify({"status": "ignored"}), 200

    payment_intent = event["data"]["object"]
    payment_id     = payment_intent["id"]
    metadata       = payment_intent.get("metadata", {})

    fan_email   = metadata.get("fan_email", "")
    config_file = metadata.get("config_file", "")

    # Validate required metadata
    if not fan_email:
        print(f"[webhook] Missing fan_email in metadata for {payment_id}")
        return jsonify({"error": "Missing fan_email in payment metadata"}), 400

    if not config_file:
        print(f"[webhook] Missing config_file in metadata for {payment_id}")
        return jsonify({"error": "Missing config_file in payment metadata"}), 400

    # Load artist config
    try:
        config = load_config(config_file)
    except FileNotFoundError:
        print(f"[webhook] Config not found: {config_file}")
        return jsonify({"error": "Artist config not found"}), 400

    error = validate_config(config)
    if error:
        print(f"[webhook] Config error: {error}")
        return jsonify({"error": error}), 400

    # Issue ticket
    try:
        ticket = issue_ticket(config, fan_email, payment_id)
    except RuntimeError as e:
        print(f"[webhook] Issuance failed for {fan_email}: {e}")
        return jsonify({"error": str(e)}), 400

    print(f"[webhook] Ticket issued: {ticket['ticket_id']} for {fan_email}")

    return jsonify({
        "status":    "issued",
        "ticket_id": ticket["ticket_id"],
        "act":       ticket["act_name"],
        "fan":       fan_email,
    }), 200


# ------------------------------------------------------------------
# Run
# ------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4242))
    print(f"Webhook listener running on port {port}")
    print("Waiting for Stripe events...")
    app.run(port=port)
