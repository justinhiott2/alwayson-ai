# Money Hunter Stripe setup bot

This manually triggered GitHub Actions bot verifies the existing live Money Hunter
$29/month Stripe price, creates the Stripe webhook endpoint, and writes the
Stripe secrets into the Money Hunter Supabase project's Edge Function secrets.

**Safety:** it always sets `ALLOW_LIVE_CHECKOUT=false`. It does not create a
customer, charge a card, start a subscription, or turn on live checkout.

## One-time GitHub setup

In the repository's **Settings → Secrets and variables → Actions**, add:

- Secret `STRIPE_SECRET_KEY`: the live secret key from the **Watchtower sc Inc.**
  Stripe account. Never paste it into chat or commit it.
- Secret `SUPABASE_ACCESS_TOKEN`: a Supabase personal access token authorized
  to manage project secrets for project `unjulxbkxnscwkxlmtbd`.

The bot does not need a publishable key or a customer card.

## Run it

Open **Actions → Money Hunter Stripe Setup Bot → Run workflow**.
Type `SETUP` and run. It verifies the exact $29/month product/price, creates
the webhook, and syncs `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`,
`STRIPE_WEBHOOK_SECRET`, and `ALLOW_LIVE_CHECKOUT=false` to Supabase.

Save the non-secret webhook endpoint ID printed in the successful run as the
repository Actions variable `STRIPE_WEBHOOK_ENDPOINT_ID`. This prevents
accidental duplicate webhook creation on future maintenance runs.

If the run fails before provisioning, inspect the error and correct the missing
secret/permission. If it fails after endpoint creation, remove that endpoint
from Stripe before rerunning without the endpoint-ID variable, to avoid duplicates.

## Still required before accepting money

This setup bot is the credentials/webhook installer, not a substitute for
end-to-end payment tests. Use Stripe test mode with test credentials and a
test price to verify checkout, successful payment confirmation, failed renewal,
and cancellation. Only after those pass should a human explicitly enable live
checkout. The bot never flips that switch.
