#!/usr/bin/env node
/**
 * Money Hunter Stripe/Supabase setup bot.
 * Provisions the live webhook and syncs required Supabase Edge Function secrets.
 * It deliberately keeps live checkout disabled.
 */
const STRIPE_API = "https://api.stripe.com/v1";
const SUPABASE_API = "https://api.supabase.com/v1";
const PRICE_ID = "price_1UfOVhEcftO14r1HW1pRc8sZ";
const WEBHOOK_URL = "https://unjulxbkxnscwkxlmtbd.supabase.co/functions/v1/stripe-webhook";
const EVENTS = [
  "checkout.session.completed",
  "customer.subscription.created",
  "customer.subscription.updated",
  "customer.subscription.deleted",
  "invoice.paid",
  "invoice.payment_failed",
  "invoice.payment_action_required"
];

function required(name) {
  const value = process.env[name];
  if (!value) throw new Error("Missing required GitHub Actions secret/variable: " + name);
  return value;
}
async function request(url, token, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { Authorization: "Bearer " + token, ...(options.headers || {}) }
  });
  const raw = await response.text();
  let data;
  try { data = raw ? JSON.parse(raw) : {}; } catch { data = { message: raw }; }
  if (!response.ok) throw new Error((data.error?.message || data.message || response.statusText) + " (" + response.status + ")");
  return data;
}
async function stripe(path, key, method = "GET", form) {
  return request(STRIPE_API + path, key, {
    method,
    headers: form ? { "Content-Type": "application/x-www-form-urlencoded" } : {},
    body: form ? new URLSearchParams(form) : undefined
  });
}
async function main() {
  const stripeKey = required("STRIPE_SECRET_KEY");
  const supabaseToken = required("SUPABASE_ACCESS_TOKEN");
  const projectRef = process.env.SUPABASE_PROJECT_REF || "unjulxbkxnscwkxlmtbd";
  const configuredEndpointId = process.env.STRIPE_WEBHOOK_ENDPOINT_ID || "";

  if (!stripeKey.startsWith("sk_live_")) {
    throw new Error("This setup workflow is intended for the Watchtower SC live Stripe account. Supply its live secret key.");
  }

  const price = await stripe("/prices/" + PRICE_ID, stripeKey);
  if (!price.active || price.type !== "recurring" || price.recurring?.interval !== "month" || price.unit_amount !== 2900 || price.currency !== "usd") {
    throw new Error("Configured Stripe price does not match the expected active $29.00 USD monthly subscription.");
  }
  const product = await stripe("/products/" + price.product, stripeKey);
  if (!product.active || product.name !== "Money Hunter Membership") {
    throw new Error("Stripe price is not attached to the expected Money Hunter Membership product.");
  }

  let endpoint;
  if (configuredEndpointId) {
    endpoint = await stripe("/webhook_endpoints/" + encodeURIComponent(configuredEndpointId), stripeKey);
    if (endpoint.url !== WEBHOOK_URL) throw new Error("STRIPE_WEBHOOK_ENDPOINT_ID points to a different endpoint URL.");
    if (endpoint.status !== "enabled") throw new Error("Configured Stripe webhook endpoint is not enabled.");
    // Stripe does not reveal an existing endpoint's signing secret again.
    throw new Error("Existing webhook endpoint found. To securely refresh its signing secret, remove STRIPE_WEBHOOK_ENDPOINT_ID from the GitHub Actions variable and rerun; the bot will create a replacement and store its new secret.");
  } else {
    endpoint = await stripe("/webhook_endpoints", stripeKey, "POST", {
      url: WEBHOOK_URL,
      description: "Money Hunter membership subscriptions (managed by setup bot)",
      "enabled_events[]": EVENTS
    });
  }

  if (!endpoint.secret) throw new Error("Stripe did not return a webhook signing secret. No Supabase secrets were changed.");
  const secrets = [
    { name: "STRIPE_SECRET_KEY", value: stripeKey },
    { name: "STRIPE_PRICE_ID", value: PRICE_ID },
    { name: "STRIPE_WEBHOOK_SECRET", value: endpoint.secret },
    { name: "ALLOW_LIVE_CHECKOUT", value: "false" }
  ];
  await request(SUPABASE_API + "/projects/" + encodeURIComponent(projectRef) + "/secrets", supabaseToken, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(secrets)
  });

  // Mask credentials in the Actions log and expose only the non-secret endpoint ID.
  for (const item of secrets) console.log("::add-mask::" + item.value);
  console.log("::notice::Money Hunter Stripe product and $29 monthly price verified.");
  console.log("::notice::Stripe webhook created and Supabase Edge Function secrets synchronized.");
  console.log("::notice::Live checkout remains disabled (ALLOW_LIVE_CHECKOUT=false).");
  console.log("Webhook endpoint ID (save as GitHub Actions variable STRIPE_WEBHOOK_ENDPOINT_ID to prevent duplicates): " + endpoint.id);
  console.log("Next: run the separate test-mode checkout/cancellation verification before enabling live checkout.");
}
main().catch(error => {
  console.error("Stripe setup bot stopped safely: " + error.message);
  process.exitCode = 1;
});
