# Money Hunter PayPal Subscription Manager Bot

Creates PayPal recurring checkout, cancellation/status handling, signed webhook processing and a payment ledger.

## Offer
USD $15.99 monthly for the first 3 billing cycles, then USD $19.99 monthly until cancelled. The browser redirect never grants paid access; verified PayPal webhooks are the source of truth.

## Server secrets
Set in Supabase Dashboard > Edge Functions > Secrets. Never put secrets in Git or browser code:
- PAYPAL_CLIENT_ID
- PAYPAL_CLIENT_SECRET
- PAYPAL_ENVIRONMENT=sandbox initially
- PAYPAL_SETUP_TOKEN (random high-entropy setup-only secret)
- PAYPAL_WEBHOOK_ID (after registering the webhook)
Supabase provides SUPABASE_URL and server-only SUPABASE_SECRET_KEYS.

## Deploy and test
1. Apply migration supabase/migrations/202611240001_paypal_subscription_bot.sql.
2. Deploy paypal-subscription-manager with JWT verification enabled. POST {"action":"provision-plan"} with x-setup-token to create the product and plan once.
3. Deploy paypal-subscription-webhook with JWT verification disabled; PayPal cannot send Supabase JWTs.
4. Register https://<project-ref>.supabase.co/functions/v1/paypal-subscription-webhook in the same PayPal REST app and subscribe to BILLING.SUBSCRIPTION.ACTIVATED, UPDATED, CANCELLED, SUSPENDED, EXPIRED, PAYMENT.FAILED and PAYMENT.SALE.COMPLETED, REFUNDED, REVERSED.
5. Save the webhook ID as PAYPAL_WEBHOOK_ID.
6. Test sandbox signup, approval, payment, all intro cycles, transition to $19.99, renewals, failure, refund/reversal, cancellation, duplicate/out-of-order events.
7. Only after tests pass, switch to live credentials, live webhook ID and PAYPAL_ENVIRONMENT=live.

## API
Authenticated POST actions: create-checkout (returns approval_url), status, cancel.
Admin-only POST action: provision-plan.
The app frontend still needs its sign-in and subscribe controls wired to these functions and to open approval_url. Do not enable live billing until frontend, schema, webhook, and sandbox tests pass.
