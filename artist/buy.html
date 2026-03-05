<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title id="page-title">Get Tickets</title>
  <script src="https://js.stripe.com/v3/"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:ital,wght@0,300;0,400;1,300&display=swap');

    :root {
      --bg:       #0a0a0a;
      --surface:  #111111;
      --border:   #222222;
      --text:     #e8e8e8;
      --muted:    #555555;
      --accent:   #c8f04a;
      --danger:   #ff4444;
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    html, body {
      background: var(--bg);
      color: var(--text);
      font-family: 'DM Mono', monospace;
      min-height: 100vh;
      overflow-x: hidden;
    }

    body::before {
      content: '';
      position: fixed;
      inset: 0;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
      pointer-events: none;
      z-index: 999;
      opacity: 0.4;
    }

    .wrap {
      max-width: 480px;
      margin: 0 auto;
      padding: 0 24px;
    }

    header {
      border-bottom: 1px solid var(--border);
      padding: 20px 0;
    }

    header .wrap {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .back-link {
      font-size: 12px;
      color: var(--muted);
      text-decoration: none;
      letter-spacing: 0.05em;
      transition: color 0.15s;
    }

    .back-link:hover { color: var(--text); }

    .hub-label {
      font-size: 11px;
      letter-spacing: 0.2em;
      color: var(--muted);
      text-transform: uppercase;
    }

    /* ── order summary ── */
    .order-summary {
      padding: 48px 0 32px;
      border-bottom: 1px solid var(--border);
      animation: fadeUp 0.5s ease both;
    }

    .act-name {
      font-family: 'Bebas Neue', sans-serif;
      font-size: clamp(40px, 10vw, 72px);
      line-height: 0.92;
      margin-bottom: 24px;
    }

    .act-name span { color: var(--accent); }

    .order-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid var(--border);
      font-size: 13px;
    }

    .order-row:last-child { border-bottom: none; }

    .order-label { color: var(--muted); }

    .order-value { color: var(--text); }

    .order-total {
      font-family: 'Bebas Neue', sans-serif;
      font-size: 32px;
      color: var(--accent);
    }

    .fee-note {
      font-size: 10px;
      color: var(--muted);
      margin-top: 8px;
    }

    /* ── form ── */
    .checkout-form {
      padding: 40px 0;
      animation: fadeUp 0.5s 0.1s ease both;
    }

    .field-group {
      margin-bottom: 24px;
    }

    .field-label {
      display: block;
      font-size: 10px;
      letter-spacing: 0.2em;
      color: var(--muted);
      text-transform: uppercase;
      margin-bottom: 10px;
    }

    .field-input {
      width: 100%;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text);
      font-family: 'DM Mono', monospace;
      font-size: 14px;
      padding: 14px 16px;
      outline: none;
      transition: border-color 0.15s;
      -webkit-appearance: none;
    }

    .field-input:focus {
      border-color: var(--accent);
    }

    .field-input::placeholder {
      color: var(--muted);
    }

    .qty-row {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .qty-btn {
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text);
      font-family: 'DM Mono', monospace;
      font-size: 18px;
      width: 44px;
      height: 44px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: border-color 0.15s;
      flex-shrink: 0;
    }

    .qty-btn:hover { border-color: var(--accent); color: var(--accent); }
    .qty-btn:disabled { opacity: 0.3; cursor: not-allowed; }

    .qty-display {
      font-size: 20px;
      min-width: 32px;
      text-align: center;
    }

    /* ── stripe card element ── */
    .card-element-wrap {
      background: var(--surface);
      border: 1px solid var(--border);
      padding: 14px 16px;
      transition: border-color 0.15s;
    }

    .card-element-wrap.focused {
      border-color: var(--accent);
    }

    /* ── submit ── */
    .btn-submit {
      width: 100%;
      background: var(--accent);
      color: #0a0a0a;
      font-family: 'DM Mono', monospace;
      font-size: 14px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      padding: 18px;
      border: none;
      cursor: pointer;
      margin-top: 32px;
      transition: opacity 0.15s, transform 0.15s;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
    }

    .btn-submit:hover:not(:disabled) {
      opacity: 0.85;
      transform: translateY(-1px);
    }

    .btn-submit:disabled {
      opacity: 0.4;
      cursor: not-allowed;
      transform: none;
    }

    .spinner {
      width: 14px;
      height: 14px;
      border: 2px solid #0a0a0a;
      border-top-color: transparent;
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
      display: none;
    }

    .btn-submit.loading .spinner { display: block; }
    .btn-submit.loading .btn-text { opacity: 0.6; }

    /* ── error / success ── */
    .msg {
      margin-top: 16px;
      font-size: 12px;
      padding: 12px 16px;
      display: none;
    }

    .msg.error {
      background: #1a0000;
      border: 1px solid #440000;
      color: var(--danger);
      display: block;
    }

    .msg.success {
      background: #0a1a00;
      border: 1px solid #224400;
      color: var(--accent);
      display: block;
    }

    /* ── success state ── */
    .success-screen {
      padding: 80px 0;
      text-align: center;
      display: none;
      animation: fadeUp 0.5s ease both;
    }

    .success-screen.visible { display: block; }

    .success-icon {
      font-family: 'Bebas Neue', sans-serif;
      font-size: 80px;
      color: var(--accent);
      line-height: 1;
      margin-bottom: 24px;
    }

    .success-title {
      font-family: 'Bebas Neue', sans-serif;
      font-size: 36px;
      margin-bottom: 16px;
    }

    .success-detail {
      font-size: 12px;
      color: var(--muted);
      line-height: 2;
      margin-bottom: 40px;
    }

    .success-detail span { color: var(--text); }

    .btn-link {
      display: inline-block;
      background: transparent;
      color: var(--text);
      border: 1px solid var(--border);
      font-family: 'DM Mono', monospace;
      font-size: 12px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      padding: 12px 24px;
      text-decoration: none;
      transition: border-color 0.15s;
    }

    .btn-link:hover { border-color: var(--accent); color: var(--accent); }

    /* ── demo notice ── */
    .demo-notice {
      background: #0a0a1a;
      border: 1px solid #222244;
      color: #6666aa;
      font-size: 11px;
      padding: 12px 16px;
      margin-bottom: 24px;
      letter-spacing: 0.05em;
      line-height: 1.6;
    }

    /* ── loading ── */
    .loading-screen {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      font-size: 12px;
      color: var(--muted);
      letter-spacing: 0.2em;
    }

    .hidden { display: none; }

    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(16px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  </style>
</head>
<body>

  <div class="loading-screen" id="loading">loading...</div>

  <div id="app" class="hidden">

    <header>
      <div class="wrap">
        <a class="back-link" id="back-link" href="artist.html">← Back</a>
        <span class="hub-label">Checkout</span>
      </div>
    </header>

    <main>
      <div class="wrap">

        <!-- order summary -->
        <div class="order-summary" id="order-summary">
          <h1 class="act-name" id="act-name">—</h1>

          <div class="order-row">
            <span class="order-label">Price per ticket</span>
            <span class="order-value" id="price-per">—</span>
          </div>
          <div class="order-row">
            <span class="order-label">Quantity</span>
            <span class="order-value">
              <div class="qty-row">
                <button class="qty-btn" id="qty-down">−</button>
                <span class="qty-display" id="qty-display">1</span>
                <button class="qty-btn" id="qty-up">+</button>
              </div>
            </span>
          </div>
          <div class="order-row">
            <span class="order-label">Total</span>
            <span class="order-total" id="total-price">—</span>
          </div>
          <p class="fee-note">2% platform fee included. Artist keeps the rest.</p>
        </div>

        <!-- checkout form -->
        <div class="checkout-form" id="checkout-form">

          <div class="demo-notice" id="demo-notice">
            Demo mode — add your Stripe publishable key to enable real payments.
          </div>

          <div class="field-group">
            <label class="field-label" for="fan-email">Your email</label>
            <input
              class="field-input"
              type="email"
              id="fan-email"
              placeholder="fan@example.com"
              autocomplete="email"
            />
          </div>

          <div class="field-group">
            <label class="field-label" for="fan-email-confirm">Confirm email</label>
            <input
              class="field-input"
              type="email"
              id="fan-email-confirm"
              placeholder="fan@example.com"
              autocomplete="email"
            />
          </div>

          <div class="field-group" id="card-field-group">
            <label class="field-label">Card details</label>
            <div class="card-element-wrap" id="card-element-wrap">
              <div id="card-element"></div>
            </div>
          </div>

          <button class="btn-submit" id="btn-pay" disabled>
            <span class="spinner"></span>
            <span class="btn-text" id="btn-text">Pay —</span>
          </button>

          <div class="msg" id="msg"></div>

        </div>

        <!-- success screen -->
        <div class="success-screen" id="success-screen">
          <div class="success-icon">✓</div>
          <h2 class="success-title">You're in.</h2>
          <p class="success-detail">
            Ticket sent to <span id="success-email">—</span><br>
            Check your inbox for your ticket ID.<br>
            You'll need it to access the stream.
          </p>
          <a class="btn-link" id="success-stream-link" href="fan.html">Access your stream →</a>
        </div>

      </div>
    </main>

  </div>

  <script>
    // ------------------------------------------------------------------
    // Config — same demo fallback as artist.html
    // Replace STRIPE_PUBLISHABLE_KEY with your real key
    // ------------------------------------------------------------------

    const STRIPE_PUBLISHABLE_KEY = "pk_test_REPLACE_WITH_YOUR_KEY";

    const DEMO_CONFIG = {
      "act_name":               "Hollow Coast",
      "ticket_price_usd":       18.00,
      "ticket_quantity":        300,
      "purchase_limit_per_fan": 2,
      "refund_policy":          "Full refund available up to 48 hours before show.",
      "platform_fee_pct":       2.0,
      "hub_id":                 "HUB_4A9F2C81B3E7",
      "active":                 true,
      "stripe_account_id":      ""
    };

    const params     = new URLSearchParams(window.location.search);
    const configPath = params.get("config") || null;

    async function loadConfig() {
      if (configPath) {
        try {
          const res = await fetch(configPath);
          if (res.ok) return res.json();
        } catch (e) {}
      }
      return DEMO_CONFIG;
    }

    // ------------------------------------------------------------------
    // State
    // ------------------------------------------------------------------

    let config  = null;
    let qty     = 1;
    let stripe  = null;
    let card    = null;
    let demoMode = true;

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    function formatPrice(usd) {
      if (usd === 0) return "FREE";
      return "$" + usd.toFixed(2);
    }

    function setMsg(text, type) {
      const el = document.getElementById("msg");
      el.textContent = text;
      el.className   = "msg " + type;
    }

    function clearMsg() {
      const el   = document.getElementById("msg");
      el.className = "msg";
      el.textContent = "";
    }

    function setLoading(on) {
      const btn = document.getElementById("btn-pay");
      if (on) {
        btn.classList.add("loading");
        btn.disabled = true;
      } else {
        btn.classList.remove("loading");
        updatePayButton();
      }
    }

    function updateTotal() {
      const price = config.ticket_price_usd * qty;
      document.getElementById("total-price").textContent = formatPrice(price);
      document.getElementById("btn-text").textContent    =
        config.ticket_price_usd === 0
          ? "Get free ticket"
          : `Pay ${formatPrice(price)}`;
    }

    function updatePayButton() {
      const email   = document.getElementById("fan-email").value.trim();
      const confirm = document.getElementById("fan-email-confirm").value.trim();
      const valid   = email.length > 3 && email.includes("@") && email === confirm;
      document.getElementById("btn-pay").disabled = !valid;
    }

    // ------------------------------------------------------------------
    // Render
    // ------------------------------------------------------------------

    function render(c) {
      config = c;

      document.getElementById("page-title").textContent = c.act_name + " — Get Tickets";

      // Back link preserves config param
      const backLink = document.getElementById("back-link");
      backLink.href  = configPath
        ? `artist.html?config=${encodeURIComponent(configPath)}`
        : "artist.html";

      // Act name
      const words  = c.act_name.trim().split(" ");
      const last   = words.pop();
      const rest   = words.join(" ");
      const nameEl = document.getElementById("act-name");
      nameEl.innerHTML = rest
        ? `${rest} <span>${last}</span>`
        : `<span>${c.act_name}</span>`;

      // Price
      document.getElementById("price-per").textContent = formatPrice(c.ticket_price_usd);
      updateTotal();

      // Qty controls
      const maxQty = c.purchase_limit_per_fan || 2;
      document.getElementById("qty-up").addEventListener("click", () => {
        if (qty < maxQty) { qty++; updateQty(); }
      });
      document.getElementById("qty-down").addEventListener("click", () => {
        if (qty > 1) { qty--; updateQty(); }
      });

      function updateQty() {
        document.getElementById("qty-display").textContent = qty;
        document.getElementById("qty-up").disabled   = qty >= maxQty;
        document.getElementById("qty-down").disabled = qty <= 1;
        updateTotal();
      }
      updateQty();

      // Stripe setup
      const isRealKey = STRIPE_PUBLISHABLE_KEY.startsWith("pk_live") ||
                        STRIPE_PUBLISHABLE_KEY.startsWith("pk_test_") &&
                        !STRIPE_PUBLISHABLE_KEY.includes("REPLACE");

      if (isRealKey) {
        demoMode = false;
        document.getElementById("demo-notice").classList.add("hidden");
        stripe = Stripe(STRIPE_PUBLISHABLE_KEY);
        const elements = stripe.elements({
          appearance: {
            theme: "night",
            variables: {
              colorPrimary:    "#c8f04a",
              colorBackground: "#111111",
              colorText:       "#e8e8e8",
              colorDanger:     "#ff4444",
              fontFamily:      "DM Mono, monospace",
              borderRadius:    "0px",
            }
          }
        });
        card = elements.create("card");
        card.mount("#card-element");
        card.on("focus", () =>
          document.getElementById("card-element-wrap").classList.add("focused"));
        card.on("blur",  () =>
          document.getElementById("card-element-wrap").classList.remove("focused"));
      } else {
        // Demo mode — hide card field
        document.getElementById("card-field-group").classList.add("hidden");
      }

      // Email validation
      document.getElementById("fan-email").addEventListener("input", updatePayButton);
      document.getElementById("fan-email-confirm").addEventListener("input", updatePayButton);

      // Submit
      document.getElementById("btn-pay").addEventListener("click", handlePay);
    }

    // ------------------------------------------------------------------
    // Payment handler
    // ------------------------------------------------------------------

    async function handlePay() {
      clearMsg();
      const email = document.getElementById("fan-email").value.trim();

      if (demoMode) {
        // Demo — simulate success
        setLoading(true);
        await new Promise(r => setTimeout(r, 1200));
        setLoading(false);
        showSuccess(email, "TKT_DEMO_" + Math.random().toString(36).slice(2, 10).toUpperCase());
        return;
      }

      // Real Stripe payment
      setLoading(true);

      try {
        // Create PaymentIntent on your server
        // Server must set metadata: { fan_email, config_file }
        const intentRes = await fetch("/create-payment-intent", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            amount:      Math.round(config.ticket_price_usd * qty * 100),
            currency:    "usd",
            fan_email:   email,
            config_file: configPath || "configs/artist.json",
            quantity:    qty,
          })
        });

        if (!intentRes.ok) throw new Error("Could not create payment intent.");
        const { client_secret } = await intentRes.json();

        const result = await stripe.confirmCardPayment(client_secret, {
          payment_method: {
            card,
            billing_details: { email }
          }
        });

        if (result.error) {
          setMsg(result.error.message, "error");
          setLoading(false);
        } else if (result.paymentIntent.status === "succeeded") {
          showSuccess(email, result.paymentIntent.id);
        }
      } catch (err) {
        setMsg("Something went wrong. Please try again.", "error");
        setLoading(false);
      }
    }

    function showSuccess(email, paymentId) {
      document.getElementById("order-summary").classList.add("hidden");
      document.getElementById("checkout-form").classList.add("hidden");
      const screen = document.getElementById("success-screen");
      screen.classList.add("visible");
      document.getElementById("success-email").textContent = email;
      const fanLink = document.getElementById("success-stream-link");
      fanLink.href  = configPath
        ? `fan.html?config=${encodeURIComponent(configPath)}`
        : "fan.html";
    }

    // ------------------------------------------------------------------
    // Boot
    // ------------------------------------------------------------------

    loadConfig()
      .then(c => {
        render(c);
        document.getElementById("loading").classList.add("hidden");
        document.getElementById("app").classList.remove("hidden");
      })
      .catch(err => {
        document.getElementById("loading").textContent = "Could not load config.";
        console.error(err);
      });
  </script>

</body>
</html>
