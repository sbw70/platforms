#!/usr/bin/env python3
# Copyright 2026 Seth Brian Wells. All rights reserved.

"""
Platform server.

Serves the front end and handles backend endpoints.
Ties together ticket issuance, validation, and Stripe payments.

Usage:
    pip install flask stripe
    python server.py

Environment variables:
    STRIPE_SECRET_KEY      — sk_live_... or sk_test_...
    STRIPE_WEBHOOK_SECRET  — whsec_... (for webhook endpoint)
    PROVIDER_HMAC_KEY      — keep this secret, never share it
    PORT                   — default 8080 (Replit uses 8080)
"""

import json
import os
import sys

try:
    from flask import Flask, request, jsonify, send_from_directory
except ImportError:
    print("Run: pip install flask stripe")
    sys.exit(1)

try:
    import stripe
except ImportError:
    stripe = None

from ticket_issue    import load_config, validate_config, issue_ticket
from ticket_validate import find_ticket, load_ticket, provider_verify
from ticket_revoke   import revoke

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------

STRIPE_SECRET_KEY     = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

if stripe and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Static files are in the same directory as this script
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------
# App
# ------------------------------------------------------------------

app = Flask(__name__, static_folder=STATIC_DIR)

# ------------------------------------------------------------------
# Static — serve HTML pages
# ------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "artist.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)

# ------------------------------------------------------------------
# POST /verify-ticket
# Called by fan.html to validate a ticket and release the stream URL.
# ------------------------------------------------------------------

@app.route("/verify-ticket", methods=["POST"])
def verify_ticket():
    data      = request.get_json(silent=True) or {}
    ticket_id = data.get("ticket_id", "").strip().upper()
    fan_email = data.get("fan_email", "").strip().lower()

    if not ticket_id or not fan_email:
        return jsonify({"valid": False, "reason": "Missing ticket ID or email."}), 400

    path = find_ticket(ticket_id)
    if not path:
        return jsonify({"valid": False, "reason": "Ticket not found."}), 200

    try:
        ticket = load_ticket(path)
    except Exception:
        return jsonify({"valid": False, "reason": "Could not read ticket."}), 200

    # Revocation check
    if ticket.get("revoked"):
        return jsonify({
            "valid":   False,
            "reason":  f"Ticket revoked: {ticket.get('revoked_reason', 'no reason given')}."
        }), 200

    # Email match
    if ticket.get("fan_email", "").lower() != fan_email:
        return jsonify({
            "valid":  False,
            "reason": "Email does not match ticket. Tickets are non-transferable."
        }), 200

    # Binding verification
    artifact = ticket.get("artifact")
    if not artifact or not provider_verify(artifact):
        return jsonify({
            "valid":  False,
            "reason": "Binding verification failed. Ticket may be forged or tampered."
        }), 200

    return jsonify({
        "valid":      True,
        "ticket_id":  ticket.get("ticket_id"),
        "act_name":   ticket.get("act_name"),
        "stream_url": ticket.get("stream_url", "TBD"),
    }), 200

# ------------------------------------------------------------------
# POST /create-payment-intent
# Called by buy.html to create a Stripe PaymentIntent.
# Metadata carries fan_email and config_file for the webhook.
# ------------------------------------------------------------------

@app.route("/create-payment-intent", methods=["POST"])
def create_payment_intent():
    if not stripe or not STRIPE_SECRET_KEY:
        return jsonify({"error": "Stripe not configured."}), 503

    data        = request.get_json(silent=True) or {}
    amount      = data.get("amount", 0)       # cents
    currency    = data.get("currency", "usd")
    fan_email   = data.get("fan_email", "")
    config_file = data.get("config_file", "")
    quantity    = data.get("quantity", 1)

    if not fan_email or not config_file:
        return jsonify({"error": "Missing fan_email or config_file."}), 400

    if amount < 0:
        return jsonify({"error": "Invalid amount."}), 400

    # Load artist config to get Stripe account ID
    try:
        config = load_config(config_file)
    except FileNotFoundError:
        return jsonify({"error": "Artist config not found."}), 400

    error = validate_config(config)
    if error:
        return jsonify({"error": error}), 400

    try:
        intent_params = {
            "amount":   max(amount, 50),   # Stripe minimum 50 cents
            "currency": currency,
            "metadata": {
                "fan_email":   fan_email,
                "config_file": config_file,
                "quantity":    quantity,
            },
            "receipt_email": fan_email,
        }

        # If artist has a Stripe account, use Connect
        stripe_account = config.get("stripe_account_id", "")
        if stripe_account:
            platform_fee = int(amount * (config.get("platform_fee_pct", 2.0) / 100))
            intent_params["application_fee_amount"] = platform_fee
            intent = stripe.PaymentIntent.create(
                **intent_params,
                stripe_account=stripe_account
            )
        else:
            intent = stripe.PaymentIntent.create(**intent_params)

        return jsonify({"client_secret": intent.client_secret}), 200

    except stripe.error.StripeError as e:
        return jsonify({"error": str(e)}), 400

# ------------------------------------------------------------------
# POST /webhook
# Stripe fires this on payment_intent.succeeded.
# Issues the ticket automatically.
# ------------------------------------------------------------------

@app.route("/webhook", methods=["POST"])
def webhook():
    if not stripe:
        return jsonify({"error": "Stripe not configured."}), 503

    payload    = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid signature."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    if event["type"] != "payment_intent.succeeded":
        return jsonify({"status": "ignored"}), 200

    pi          = event["data"]["object"]
    payment_id  = pi["id"]
    metadata    = pi.get("metadata", {})
    fan_email   = metadata.get("fan_email", "")
    config_file = metadata.get("config_file", "")

    if not fan_email or not config_file:
        print(f"[webhook] Missing metadata on {payment_id}")
        return jsonify({"error": "Missing metadata."}), 400

    try:
        config = load_config(config_file)
    except FileNotFoundError:
        return jsonify({"error": "Config not found."}), 400

    error = validate_config(config)
    if error:
        return jsonify({"error": error}), 400

    try:
        ticket = issue_ticket(config, fan_email, payment_id)
        print(f"[webhook] Issued {ticket['ticket_id']} for {fan_email}")
    except RuntimeError as e:
        print(f"[webhook] Issuance failed: {e}")
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "status":    "issued",
        "ticket_id": ticket["ticket_id"],
    }), 200

# ------------------------------------------------------------------
# POST /revoke-ticket
# Admin endpoint — revoke a ticket by ID.
# In production, protect this with an admin key.
# ------------------------------------------------------------------

@app.route("/revoke-ticket", methods=["POST"])
def revoke_ticket():
    data      = request.get_json(silent=True) or {}
    ticket_id = data.get("ticket_id", "").strip().upper()
    reason    = data.get("reason", "revoked by admin")
    admin_key = data.get("admin_key", "")

    # Basic admin protection — set ADMIN_KEY env var
    expected_key = os.environ.get("ADMIN_KEY", "")
    if expected_key and admin_key != expected_key:
        return jsonify({"error": "Unauthorized."}), 401

    if not ticket_id:
        return jsonify({"error": "Missing ticket_id."}), 400

    success = revoke(ticket_id, reason)
    if success:
        return jsonify({"status": "revoked", "ticket_id": ticket_id}), 200
    else:
        return jsonify({"error": "Could not revoke ticket."}), 400

# ------------------------------------------------------------------
# Run
# ------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print()
    print("=" * 52)
    print("  Artist Hub Platform")
    print("=" * 52)
    print()
    print(f"  Running on port {port}")
    print(f"  Stripe:  {'configured' if STRIPE_SECRET_KEY else 'not configured (demo mode)'}")
    print(f"  Webhook: {'configured' if STRIPE_WEBHOOK_SECRET else 'not configured'}")
    print()
    print("  Open: http://0.0.0.0:" + str(port))
    print()
    app.run(host="0.0.0.0", port=port, debug=False)
