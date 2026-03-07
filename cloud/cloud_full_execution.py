#!/usr/bin/env python3
"""
Verification Constraints — Local Multi-Cloud Simulation
Runs the full topology on your laptop. No installs. Pure stdlib.

Simulates:
  Cloudflare Worker  →  hub (conveyance only)
  AWS provider       →  DOMAIN_AWS  (ECS Fargate in prod)
  Azure provider     →  DOMAIN_AZURE (Container Apps in prod)
  GCP provider       →  DOMAIN_GCP  (Cloud Run in prod)

All five initiation gates per provider:
  1. Domain match
  2. Verification context
  3. Mechanical binding
  4. Artifact token
  5. Adaptive score (PCADBE)

Usage:
  python3 main.py

  # Run the negative test cases too:
  python3 main.py --full
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import argparse
import hashlib
import hmac
import json
import sys
import threading
import time
import urllib.request

# -------------------------------------------------------------------
# Network layout
# -------------------------------------------------------------------
HUB_HOST = "127.0.0.1"
HUB_PORT = 8080

PROVIDER_AWS_PORT   = 9090
PROVIDER_AZURE_PORT = 9091
PROVIDER_GCP_PORT   = 9092

HUB_URL            = f"http://{HUB_HOST}:{HUB_PORT}/submit"
PROVIDER_AWS_URL   = f"http://127.0.0.1:{PROVIDER_AWS_PORT}/ingest"
PROVIDER_AZURE_URL = f"http://127.0.0.1:{PROVIDER_AZURE_PORT}/ingest"
PROVIDER_GCP_URL   = f"http://127.0.0.1:{PROVIDER_GCP_PORT}/ingest"

# -------------------------------------------------------------------
# Shared constants
# -------------------------------------------------------------------
BIND_TAG         = "BIND_V1"
MAX_REQUEST_BYTES = 1024 * 64  # 64KB

# -------------------------------------------------------------------
# Per-domain configuration
# Provider secrets never leave provider boundary.
# Hub has NO access to these.
# -------------------------------------------------------------------
DOMAIN_CONFIG = {
    "DOMAIN_AWS": {
        "provider_id":       "PROVIDER_AWS",
        "expected_context":  "CTX_ALPHA",
        "hmac_key":          b"AWS_PROVIDER_ONLY_KEY_CHANGE_ME",
        "artifact_token":    "token-aws-valid",
        "ingest_url":        PROVIDER_AWS_URL,
    },
    "DOMAIN_AZURE": {
        "provider_id":       "PROVIDER_AZURE",
        "expected_context":  "CTX_BRAVO",
        "hmac_key":          b"AZURE_PROVIDER_ONLY_KEY_CHANGE_ME",
        "artifact_token":    "token-azure-valid",
        "ingest_url":        PROVIDER_AZURE_URL,
    },
    "DOMAIN_GCP": {
        "provider_id":       "PROVIDER_GCP",
        "expected_context":  "CTX_CHARLIE",
        "hmac_key":          b"GCP_PROVIDER_ONLY_KEY_CHANGE_ME",
        "artifact_token":    "token-gcp-valid",
        "ingest_url":        PROVIDER_GCP_URL,
    },
}

# Hub routing table — URLs only, no secrets
HUB_ROUTING = {
    domain: cfg["ingest_url"]
    for domain, cfg in DOMAIN_CONFIG.items()
}

# -------------------------------------------------------------------
# Cryptographic helpers
# -------------------------------------------------------------------

def mechanical_binding(request_repr_hex: str, verification_context: str, domain: str) -> str:
    """Deterministic, no secrets. Hub and provider both compute this."""
    msg = (BIND_TAG + "|" + domain + "|" + request_repr_hex + "|" + verification_context).encode()
    return hashlib.sha256(msg).hexdigest()


def provider_boundary_signature(hmac_key: bytes, provider_id: str, request_repr_hex: str,
                                 verification_context: str, binding: str, stage: str) -> str:
    """Provider-only. Never returned to hub or requester."""
    msg = (provider_id + "|" + stage + "|" + request_repr_hex + "|"
           + verification_context + "|" + binding).encode()
    return hmac.new(hmac_key, msg, hashlib.sha256).hexdigest()


def adaptive_score(hmac_key: bytes, request_repr_hex: str, verification_context: str,
                   expected_context: str) -> float:
    """Provider-side adaptive evaluation (PCADBE). Score not disclosed to hub."""
    material = (request_repr_hex + "|" + verification_context).encode()
    digest = hmac.new(hmac_key, material, hashlib.sha256).digest()
    n = int.from_bytes(digest[:8], "big")
    score = (n % 10_000_000) / 10_000_000.0
    if verification_context == expected_context:
        score = min(1.0, score + 0.25)
    return score


# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
_LOG_LOCK = threading.Lock()

def log(component: str, event: str, **kwargs):
    record = {"ts": time.time_ns(), "component": component, "event": event, **kwargs}
    with _LOG_LOCK:
        print(json.dumps(record), flush=True)


# -------------------------------------------------------------------
# Shared HTTP helpers
# -------------------------------------------------------------------

def fire_and_forget(url: str, payload: dict) -> None:
    def _send():
        try:
            data = json.dumps(payload, separators=(",", ":")).encode()
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2):
                pass
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()


def read_body(handler: BaseHTTPRequestHandler, max_bytes: int) -> bytes:
    length = int(handler.headers.get("Content-Length", "0"))
    if length > max_bytes:
        return b""
    return handler.rfile.read(length) if length > 0 else b""


# -------------------------------------------------------------------
# Hub (Cloudflare Worker behaviour)
# Conveyance only. No secrets. No HMAC keys. Constant 204 response.
# -------------------------------------------------------------------
class HubHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/submit":
            self.send_response(404)
            self.end_headers()
            return

        raw = read_body(self, MAX_REQUEST_BYTES)
        if not raw and int(self.headers.get("Content-Length", "0")) > MAX_REQUEST_BYTES:
            self.send_response(204)
            self.end_headers()
            return

        domain               = self.headers.get("X-Domain", "")
        verification_context = self.headers.get("X-Verification-Context", "")
        artifact_token       = self.headers.get("X-Artifact-Token", "")

        target_url = HUB_ROUTING.get(domain)
        if not target_url:
            log("HUB", "unknown_domain", domain=domain)
            self.send_response(204)
            self.end_headers()
            return

        request_repr_hex = hashlib.sha256(raw).hexdigest()
        binding          = mechanical_binding(request_repr_hex, verification_context, domain)
        corr             = f"CORR_{domain}_{request_repr_hex[:12]}_{time.time_ns()}"

        artifact = {
            "hub_id":               "HUB_CLOUDFLARE",
            "correlation_id":       corr,
            "domain":               domain,
            "request_repr":         request_repr_hex,
            "verification_context": verification_context,
            "binding":              binding,
            "artifact_token":       artifact_token,
        }

        log("HUB", "forwarding", domain=domain, corr=corr)
        fire_and_forget(target_url, artifact)

        # Constant response — hub never returns provider outcome
        self.send_response(204)
        self.end_headers()


# -------------------------------------------------------------------
# Provider (AWS / Azure / GCP — same logic, different config)
# -------------------------------------------------------------------
def make_provider_handler(domain: str, cfg: dict):
    provider_id      = cfg["provider_id"]
    expected_context = cfg["expected_context"]
    hmac_key         = cfg["hmac_key"]
    valid_token      = cfg["artifact_token"]

    class ProviderHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            if self.path != "/ingest":
                self.send_response(404)
                self.end_headers()
                return

            raw = read_body(self, MAX_REQUEST_BYTES)
            try:
                artifact = json.loads(raw.decode())
            except Exception:
                self._emit("NOT_INITIATED", reason="parse_error")
                self.send_response(204)
                self.end_headers()
                return

            request_repr         = artifact.get("request_repr", "")
            verification_context = artifact.get("verification_context", "")
            binding              = artifact.get("binding", "")
            artifact_domain      = artifact.get("domain", "")
            artifact_token       = artifact.get("artifact_token", "")
            corr                 = artifact.get("correlation_id", "")

            # Gate 1: Domain
            if artifact_domain != domain:
                self._emit("NOT_INITIATED", reason="domain_mismatch", corr=corr)
                self.send_response(204)
                self.end_headers()
                return

            # Gate 2: Context
            if verification_context != expected_context:
                self._emit("NOT_INITIATED", reason="context_mismatch", corr=corr)
                self.send_response(204)
                self.end_headers()
                return

            # Gate 3: Mechanical binding
            expected_binding = mechanical_binding(request_repr, verification_context, domain)
            if not hmac.compare_digest(binding, expected_binding):
                self._emit("NOT_INITIATED", reason="binding_mismatch", corr=corr)
                self.send_response(204)
                self.end_headers()
                return

            # Gate 4: Artifact token
            if artifact_token != valid_token:
                self._emit("NOT_INITIATED", reason="token_mismatch", corr=corr)
                self.send_response(204)
                self.end_headers()
                return

            # Gate 5: Adaptive score (PCADBE)
            score = adaptive_score(hmac_key, request_repr, verification_context, expected_context)
            if score < 0.50:
                self._emit("NOT_INITIATED", reason="score_below_threshold",
                           score=round(score, 4), corr=corr)
                self.send_response(204)
                self.end_headers()
                return

            # All gates passed — compute provider-only boundary signatures
            # Not returned to hub or requester (disclosure constraints)
            _ = provider_boundary_signature(hmac_key, provider_id, request_repr,
                                            verification_context, binding, "START")
            _ = provider_boundary_signature(hmac_key, provider_id, request_repr,
                                            verification_context, binding, "COMPLETE")

            self._emit("INITIATED", score=round(score, 4), corr=corr)

            # YOUR WORKLOAD GOES HERE
            # Provider has verified the request. Execute cloud-specific work.

            self.send_response(204)
            self.end_headers()

        def _emit(self, status: str, **kwargs):
            log(provider_id, status, domain=domain, **kwargs)

    return ProviderHandler


# -------------------------------------------------------------------
# Requester
# -------------------------------------------------------------------
def send_request(payload: bytes, domain: str, verification_context: str,
                 artifact_token: str = "") -> int:
    req = urllib.request.Request(
        HUB_URL,
        data=payload,
        headers={
            "Content-Type":           "application/octet-stream",
            "X-Domain":               domain,
            "X-Verification-Context": verification_context,
            "X-Artifact-Token":       artifact_token,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=3) as resp:
        return resp.status


# -------------------------------------------------------------------
# Startup
# -------------------------------------------------------------------
def start_server(host: str, port: int, handler_cls) -> None:
    HTTPServer((host, port), handler_cls).serve_forever()


def wait_for_ready(port: int, retries: int = 20, delay: float = 0.1) -> bool:
    url = f"http://127.0.0.1:{port}/health"
    for _ in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except Exception:
            time.sleep(delay)
    return False


def main():
    parser = argparse.ArgumentParser(description="Verification Constraints — Local Simulation")
    parser.add_argument("--full", action="store_true", help="Also run negative test cases")
    args = parser.parse_args()

    print("\n=== Verification Constraints — Local Multi-Cloud Simulation ===\n")

    # Start hub
    threading.Thread(
        target=start_server,
        args=(HUB_HOST, HUB_PORT, HubHandler),
        daemon=True,
    ).start()

    # Start providers
    for domain, cfg in DOMAIN_CONFIG.items():
        port = {
            "DOMAIN_AWS":   PROVIDER_AWS_PORT,
            "DOMAIN_AZURE": PROVIDER_AZURE_PORT,
            "DOMAIN_GCP":   PROVIDER_GCP_PORT,
        }[domain]
        threading.Thread(
            target=start_server,
            args=("0.0.0.0", port, make_provider_handler(domain, cfg)),
            daemon=True,
        ).start()

    # Wait for all services
    for label, port in [("hub", HUB_PORT),
                         ("aws",   PROVIDER_AWS_PORT),
                         ("azure", PROVIDER_AZURE_PORT),
                         ("gcp",   PROVIDER_GCP_PORT)]:
        if not wait_for_ready(port):
            print(f"ERROR: {label} did not start on port {port}")
            sys.exit(1)

    print("All services ready.\n")
    time.sleep(0.1)

    payload = b'{"op":"transfer","amount":100,"to":"acct_123"}'

    # -------------------------------------------------------------------
    # Positive test cases — all three domains
    # -------------------------------------------------------------------
    print("--- Positive: valid requests to all three domains ---\n")

    for domain, cfg in DOMAIN_CONFIG.items():
        print(f"Sending to {domain}...")
        status = send_request(
            payload,
            domain=domain,
            verification_context=cfg["expected_context"],
            artifact_token=cfg["artifact_token"],
        )
        print(f"  Hub response: {status} (hub never returns provider outcome)\n")
        time.sleep(0.3)  # let async provider log flush

    if args.full:
        print("\n--- Negative: spoofed context ---\n")

        print("Sending DOMAIN_AWS with wrong context...")
        send_request(payload, domain="DOMAIN_AWS",
                     verification_context="CTX_SPOOFED",
                     artifact_token=DOMAIN_CONFIG["DOMAIN_AWS"]["artifact_token"])
        time.sleep(0.3)

        print("\nSending DOMAIN_AWS with wrong token...")
        send_request(payload, domain="DOMAIN_AWS",
                     verification_context=DOMAIN_CONFIG["DOMAIN_AWS"]["expected_context"],
                     artifact_token="bad-token")
        time.sleep(0.3)

        print("\nSending unknown domain...")
        send_request(payload, domain="DOMAIN_UNKNOWN",
                     verification_context="CTX_ALPHA",
                     artifact_token="anything")
        time.sleep(0.3)

        print("\nCross-domain replay: DOMAIN_AWS artifact replayed to DOMAIN_AZURE...")
        # Send valid AWS request, then manually craft replay with AZURE domain
        # (binding will mismatch because domain is baked into hash)
        send_request(payload, domain="DOMAIN_AZURE",
                     verification_context=DOMAIN_CONFIG["DOMAIN_AWS"]["expected_context"],
                     artifact_token=DOMAIN_CONFIG["DOMAIN_AZURE"]["artifact_token"])
        time.sleep(0.3)

    time.sleep(0.5)
    print("\n=== Simulation complete. Check JSON log lines above for provider outcomes. ===\n")
    print("Topology:")
    print(f"  Hub:           http://127.0.0.1:{HUB_PORT}/submit")
    print(f"  AWS provider:  http://127.0.0.1:{PROVIDER_AWS_PORT}/ingest")
    print(f"  Azure provider:http://127.0.0.1:{PROVIDER_AZURE_PORT}/ingest")
    print(f"  GCP provider:  http://127.0.0.1:{PROVIDER_GCP_PORT}/ingest")
    print("\nCtrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
