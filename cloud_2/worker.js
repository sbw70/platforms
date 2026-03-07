/**
 * Verification Constraints - Multi-Cloud Hub
 * Cloudflare Workers implementation of the Hub/NUVL intermediary.
 *
 * Conveyance-only. No secrets. No policy. No outcome authority.
 * Routes mechanically by X-Domain header.
 * Fans out to all configured providers in the target domain.
 *
 * Architecture: verification-constraints multi-hub module
 */

const BIND_TAG = "BIND_V1";
const MAX_REQUEST_BYTES = 64 * 1024; // 64KB

// Routing config - versioned, matches ROUTING_CONFIG in multi-hub module.
// Populated from environment variables at runtime.
function buildRoutingConfig(env) {
  return {
    v1: {
      enabled: true,
      domains: {
        DOMAIN_AWS: {
          providerUrl: env.PROVIDER_AWS_URL,
          expectedContext: env.CONTEXT_AWS,
        },
        DOMAIN_AZURE: {
          providerUrl: env.PROVIDER_AZURE_URL,
          expectedContext: env.CONTEXT_AZURE,
        },
        DOMAIN_GCP: {
          providerUrl: env.PROVIDER_GCP_URL,
          expectedContext: env.CONTEXT_GCP,
        },
      },
    },
  };
}

// Mechanical binding - no secrets, deterministic, matches provider expectation.
async function mechanicalBinding(requestReprHex, verificationContext, domain) {
  const msg = `${BIND_TAG}|${domain}|${requestReprHex}|${verificationContext}`;
  const encoded = new TextEncoder().encode(msg);
  const hashBuf = await crypto.subtle.digest("SHA-256", encoded);
  return bufToHex(hashBuf);
}

async function sha256Hex(data) {
  const buf = await crypto.subtle.digest("SHA-256", data);
  return bufToHex(buf);
}

function bufToHex(buf) {
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function correlationId(requestReprHex, domain) {
  // Lightweight correlation - not execution state, just signal tracking.
  return `CORR_${domain}_${requestReprHex.slice(0, 16)}_${Date.now()}`;
}

// Fire-and-forget forward to provider. Hub disengages immediately.
async function forwardToProvider(ctx, url, artifact) {
  const body = JSON.stringify(artifact);
  ctx.waitUntil(
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    }).catch(() => {
      // Conveyance best-effort. Hub does not retry or infer from failure.
    })
  );
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Health check
    if (url.pathname === "/health") {
      return new Response("ok", { status: 200 });
    }

    // Only handle POST /submit
    if (request.method !== "POST" || url.pathname !== "/submit") {
      return new Response(null, { status: 204 });
    }

    // Size gate
    const contentLength = parseInt(request.headers.get("content-length") || "0");
    if (contentLength > MAX_REQUEST_BYTES) {
      return new Response(null, { status: 204 });
    }

    const domain = request.headers.get("x-domain") || "";
    const verificationContext = request.headers.get("x-verification-context") || "";
    const artifactToken = request.headers.get("x-artifact-token") || "";

    const routing = buildRoutingConfig(env);
    const activeVersion = env.ROUTING_VERSION || "v1";
    const config = routing[activeVersion];

    if (!config || !config.enabled) {
      // Routing not configured - constant response, no error semantics.
      return new Response(null, { status: 204 });
    }

    const domainConfig = config.domains[domain];
    if (!domainConfig) {
      // Unknown domain - constant response, no error semantics.
      return new Response(null, { status: 204 });
    }

    // Read request body
    const rawBytes = await request.arrayBuffer();
    const requestReprHex = await sha256Hex(rawBytes);
    const binding = await mechanicalBinding(requestReprHex, verificationContext, domain);
    const corr = correlationId(requestReprHex, domain);

    const artifact = {
      hub_id: "HUB_CLOUDFLARE",
      routing_version: activeVersion,
      correlation_id: corr,
      domain: domain,
      request_repr: requestReprHex,
      verification_context: verificationContext,
      binding: binding,
      artifact_token: artifactToken,
      // return_outcome_url omitted - hub does not collect outcomes (conveyance only)
    };

    // Forward to provider - fire and forget
    await forwardToProvider(ctx, domainConfig.providerUrl, artifact);

    // Constant response. Hub never returns provider outcome.
    return new Response(null, { status: 204 });
  },
};
