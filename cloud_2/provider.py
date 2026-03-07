#!/usr/bin/env python3
# Verification Constraints - Provider Service
# Cloud-agnostic provider implementation.
# Deploy to: AWS ECS/Fargate, Azure Container Apps, or GCP Cloud Run.
#
# Each cloud deployment is an independent provider domain.
# HMAC keys never leave this environment - fetched from cloud KMS at startup.

from http.server import BaseHTTPRequestHandler, HTTPServer
import hashlib
import hmac
import json
import os
import threading
import time
import boto3          # AWS - remove if not on AWS
# from azure.keyvault.secrets import SecretClient      # Azure
# from google.cloud import secretmanager               # GCP

PROVIDER_HOST = "0.0.0.0"
PROVIDER_PORT = int(os.environ.get("PORT", "8080"))

BIND_TAG = "BIND_V1"
MAX_REQUEST_BYTES = 1024 * 64  # 64KB

# Provider identity - set via environment variable per deployment
PROVIDER_ID = os.environ.get("PROVIDER_ID", "PROVIDER_UNKNOWN")
DOMAIN_ID = os.environ.get("DOMAIN_ID", "DOMAIN_UNKNOWN")
EXPECTED_CONTEXT = os.environ.get("EXPECTED_CONTEXT", "")


# -------------------------------------------------------------------
# KMS key loading - provider-only, never transmitted
# -------------------------------------------------------------------

def load_hmac_key() -> bytes:
    """
    Load HMAC key from cloud KMS. Never logs, never transmits.
    Swap the implementation block for your cloud.
    """

    # --- AWS Secrets Manager ---
    secret_name = os.environ.get("HMAC_SECRET_ARN", "")
    if secret_name:
        client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        response = client.get_secret_value(SecretId=secret_name)
        return response["SecretString"].encode("utf-8")

    # --- Azure Key Vault (uncomment for Azure) ---
    # vault_url = os.environ.get("KEY_VAULT_URL", "")
    # secret_name = os.environ.get("HMAC_SECRET_NAME", "")
    # if vault_url and secret_name:
    #     from azure.identity import ManagedIdentityCredential
    #     credential = ManagedIdentityCredential()
    #     client = SecretClient(vault_url=vault_url, credential=credential)
    #     return client.get_secret(secret_name).value.encode("utf-8")

    # --- GCP Secret Manager (uncomment for GCP) ---
    # project_id = os.environ.get("GCP_PROJECT_ID", "")
    # secret_id = os.environ.get("HMAC_SECRET_ID", "")
    # if project_id and secret_id:
    #     client = secretmanager.SecretManagerServiceClient()
    #     name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    #     response = client.access_secret_version(request={"name": name})
    #     return response.payload.data

    # Local dev fallback - never use in production
    fallback = os.environ.get("HMAC_KEY_DEV", "")
    if fallback:
        return fallback.encode("utf-8")

    raise RuntimeError("No HMAC key source configured.")


# Load once at startup - stays in memory, never written to disk or logs
_HMAC_KEY: bytes = b""


def get_hmac_key() -> bytes:
    global _HMAC_KEY
    if not _HMAC_KEY:
        _HMAC_KEY = load_hmac_key()
    return _HMAC_KEY


# -------------------------------------------------------------------
# Cryptographic functions - provider boundary only
# -------------------------------------------------------------------

def provider_expected_binding(request_repr_hex: str, verification_context: str, domain: str) -> str:
    msg = (BIND_TAG + "|" + domain + "|" + request_repr_hex + "|" + verification_context).encode("utf-8")
    return hashlib.sha256(msg).hexdigest()


def provider_boundary_signature(request_repr_hex: str, verification_context: str, binding: str, stage: str) -> str:
    """
    Provider-only boundary signature. Never returned to hub or requester.
    Computed inside provider boundary only.
    """
    msg = (PROVIDER_ID + "|" + stage + "|" + request_repr_hex + "|" + verification_context + "|" + binding).encode("utf-8")
    return hmac.new(get_hmac_key(), msg, hashlib.sha256).hexdigest()


def provider_adaptive_score(request_repr_hex: str, verification_context: str) -> float:
    """
    Provider-side adaptive evaluation (PCADBE module).
    Score is internal - not disclosed to hub.
    """
    material = (request_repr_hex + "|" + verification_context).encode("utf-8")
    digest = hmac.new(get_hmac_key(), material, hashlib.sha256).digest()
    n = int.from_bytes(digest[:8], "big")
    score = (n % 10_000_000) / 10_000_000.0
    if verification_context == EXPECTED_CONTEXT:
        score = min(1.0, score + 0.25)
    return score


# -------------------------------------------------------------------
# Provider HTTP handler
# -------------------------------------------------------------------

class ProviderHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Structured logging only - no raw request data
        pass

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
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

        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_REQUEST_BYTES:
            self.send_response(204)
            self.end_headers()
            return

        body = self.rfile.read(length) if length > 0 else b""

        try:
            artifact = json.loads(body.decode("utf-8"))
        except Exception:
            self._emit_structured("NOT_INITIATED", reason="parse_error")
            self.send_response(204)
            self.end_headers()
            return

        request_repr = artifact.get("request_repr", "")
        verification_context = artifact.get("verification_context", "")
        binding = artifact.get("binding", "")
        artifact_domain = artifact.get("domain", "")
        artifact_token = artifact.get("artifact_token", "")
        correlation_id = artifact.get("correlation_id", "")

        initiated = False

        # Gate 1: Domain must match this provider's domain
        if artifact_domain != DOMAIN_ID:
            self._emit_structured("NOT_INITIATED", reason="domain_mismatch", corr=correlation_id)
            self.send_response(204)
            self.end_headers()
            return

        # Gate 2: Verification context
        if verification_context != EXPECTED_CONTEXT:
            self._emit_structured("NOT_INITIATED", reason="context_mismatch", corr=correlation_id)
            self.send_response(204)
            self.end_headers()
            return

        # Gate 3: Mechanical binding
        expected = provider_expected_binding(request_repr, verification_context, DOMAIN_ID)
        if not hmac.compare_digest(binding, expected):
            self._emit_structured("NOT_INITIATED", reason="binding_mismatch", corr=correlation_id)
            self.send_response(204)
            self.end_headers()
            return

        # Gate 4: Artifact token (if configured)
        valid_token = os.environ.get("VALID_ARTIFACT_TOKEN", "")
        if valid_token and artifact_token != valid_token:
            self._emit_structured("NOT_INITIATED", reason="token_mismatch", corr=correlation_id)
            self.send_response(204)
            self.end_headers()
            return

        # Gate 5: Adaptive score (PCADBE)
        score = provider_adaptive_score(request_repr, verification_context)
        if score < 0.50:
            self._emit_structured("NOT_INITIATED", reason="score_below_threshold", corr=correlation_id)
            self.send_response(204)
            self.end_headers()
            return

        initiated = True

        # Provider-only boundary signatures - computed inside boundary, not returned
        _ = provider_boundary_signature(request_repr, verification_context, binding, "START")
        _ = provider_boundary_signature(request_repr, verification_context, binding, "COMPLETE")

        self._emit_structured("INITIATED", corr=correlation_id)

        # ---------------------------------------------------------------
        # YOUR WORKLOAD GOES HERE
        # This is where the actual cloud-specific execution happens.
        # The provider has verified the request. Now execute it.
        # ---------------------------------------------------------------

        self.send_response(204)
        self.end_headers()

    def _emit_structured(self, status: str, reason: str = "", corr: str = "") -> None:
        record = {
            "ts": time.time_ns(),
            "provider": PROVIDER_ID,
            "domain": DOMAIN_ID,
            "status": status,
        }
        if reason:
            record["reason"] = reason
        if corr:
            record["correlation_id"] = corr
        # Write to stdout as structured JSON for cloud log aggregation
        print(json.dumps(record), flush=True)


def main():
    print(json.dumps({
        "event": "startup",
        "provider": PROVIDER_ID,
        "domain": DOMAIN_ID,
        "port": PROVIDER_PORT,
    }), flush=True)

    # Load key at startup to fail fast if KMS is unreachable
    try:
        get_hmac_key()
        print(json.dumps({"event": "hmac_key_loaded", "provider": PROVIDER_ID}), flush=True)
    except Exception as e:
        print(json.dumps({"event": "hmac_key_load_failed", "error": str(e)}), flush=True)
        raise

    server = HTTPServer((PROVIDER_HOST, PROVIDER_PORT), ProviderHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
