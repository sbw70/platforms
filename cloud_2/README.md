# Verification Constraints — Multi-Cloud Deployment

Terraform + Cloudflare Workers deployment of the verification-constraints
ecosystem across AWS, Azure, and GCP.

## Architecture

```
Requester
    │
    │  POST /submit
    │  X-Domain: DOMAIN_AWS | DOMAIN_AZURE | DOMAIN_GCP
    │  X-Verification-Context: <context>
    │  X-Artifact-Token: <token>        (if configured)
    ▼
Cloudflare Worker  (hub.yourdomain.com)
    │  Neutral intermediary — conveyance only
    │  Computes mechanical binding (no secrets)
    │  Routes by X-Domain header
    │  Fire-and-forget forward
    │
    ├──→  AWS ECS Fargate  /ingest   (DOMAIN_AWS)
    │         HMAC key: Secrets Manager
    │         Gates: context + binding + token + adaptive score
    │
    ├──→  Azure Container Apps  /ingest   (DOMAIN_AZURE)
    │         HMAC key: Key Vault
    │         Gates: context + binding + token + adaptive score
    │
    └──→  GCP Cloud Run  /ingest   (DOMAIN_GCP)
              HMAC key: Secret Manager
              Gates: context + binding + token + adaptive score
```

**Authority never leaves the provider boundary.**
Cloudflare has no HMAC keys, no secrets, no outcome authority.
Each cloud is an independent provider domain.

## Constraint Architecture Compliance

| Constraint Module | Deployment Realization |
|---|---|
| NUVL / conveyance-only | Cloudflare Worker — no secrets, constant response |
| Multi-domain routing | `X-Domain` header → separate Cloud endpoints |
| Cross-domain replay protection | Domain baked into binding hash |
| Adaptive scoring (PCADBE) | Provider-side, keyed by KMS secret |
| Artifact token | `X-Artifact-Token` header, validated at provider |
| Disclosure constraints | Provider logs structured JSON, no internal policy details |
| Hardware boundary | Edge devices POST to hub — no authority expansion |
| Ledger constraints | CloudWatch/Monitor/Cloud Logging = passive observation only |
| Measurement constraints | No statistical aggregation used for authorization |
| Offline / air-gap | Artifacts valid at generation time regardless of delivery delay |
| Temporal gatekeeping | No timestamps used in binding or initiation logic |

## Prerequisites

- Terraform >= 1.7.0
- AWS CLI configured
- Azure CLI configured (`az login`)
- GCP CLI configured (`gcloud auth application-default login`)
- Cloudflare account with Workers enabled
- Docker + registry access to push the provider image

## Deployment Steps

### 1. Build and push the provider container

```bash
cd docker/provider
docker build -t yourorg/verification-provider:latest .
docker push yourorg/verification-provider:latest
```

### 2. Configure variables

```bash
cp terraform/environments/prod/terraform.tfvars.example \
   terraform/environments/prod/terraform.tfvars

# Edit terraform.tfvars with your values
# Set secrets via environment variables (never in tfvars):
export TF_VAR_expected_context_aws="CTX_ALPHA"
export TF_VAR_expected_context_azure="CTX_BRAVO"
export TF_VAR_expected_context_gcp="CTX_CHARLIE"
export TF_VAR_cloudflare_api_token="your-token"
```

### 3. Deploy infrastructure

```bash
cd terraform
terraform init
terraform plan -var-file=environments/prod/terraform.tfvars
terraform apply -var-file=environments/prod/terraform.tfvars
```

### 4. Populate HMAC keys (out-of-band — never via Terraform)

```bash
# AWS
aws secretsmanager put-secret-value \
  --secret-id $(terraform output -raw aws_hmac_secret_arn) \
  --secret-string "$(openssl rand -hex 32)"

# Azure
az keyvault secret set \
  --vault-name kv-verif-domain-azure \
  --name hmac-key \
  --value "$(openssl rand -hex 32)"

# GCP
echo -n "$(openssl rand -hex 32)" | \
  gcloud secrets versions add verification-domain-gcp-hmac-key \
  --data-file=-
```

### 5. Send a test request

```bash
HUB_URL=$(terraform output -raw hub_url)

curl -X POST "$HUB_URL" \
  -H "Content-Type: application/octet-stream" \
  -H "X-Domain: DOMAIN_AWS" \
  -H "X-Verification-Context: CTX_ALPHA" \
  -d '{"op":"test","amount":1}'
```

Response is always `204 No Content` — the hub never returns provider outcomes.
Check CloudWatch / Azure Monitor / Cloud Logging for provider initiation events.

## Security Notes

- **HMAC keys**: Generated locally, loaded directly into KMS. Never appear in
  Terraform state, logs, or environment variables of the hub.
- **Verification contexts**: Treated as secrets. Set via `TF_VAR_` env vars,
  stored as Cloudflare Worker secrets (encrypted at rest).
- **Provider URLs**: Stored as Cloudflare Worker secrets — hub knows where to
  route but the URLs are not publicly enumerable.
- **Cross-domain replay**: Prevented cryptographically — domain is mixed into
  the binding hash. A valid AWS artifact is invalid if replayed to Azure.
- **Temporal properties**: No timestamps in binding or initiation logic.
  Artifacts are valid at generation time regardless of delivery timing.

## Adding a 4th Provider Domain

1. Add a new provider module call in `terraform/main.tf`
2. Add `DOMAIN_NEW` to `DOMAIN_ROUTE` in `cloudflare-worker/worker.js`
3. Add the new context and URL as Worker secrets
4. Deploy

The architecture scales horizontally — each domain is fully independent.

## License

Provider service code: Apache 2.0 (see canonical reference)
Module architecture: proprietary (see module-license-notice)
