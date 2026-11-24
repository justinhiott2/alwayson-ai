alter table public.memberships
  add column if not exists paypal_subscription_id text,
  add column if not exists paypal_plan_id text,
  add column if not exists paypal_payer_id text,
  add column if not exists paypal_status text,
  add column if not exists paypal_next_billing_time timestamptz;
create unique index if not exists memberships_paypal_subscription_id_key on public.memberships(paypal_subscription_id) where paypal_subscription_id is not null;
create table if not exists public.paypal_billing_config(
 config_key text primary key, product_id text not null, plan_id text not null,
 currency_code text not null default 'USD', intro_amount numeric(10,2) not null default 15.99,
 intro_cycles integer not null default 3, regular_amount numeric(10,2) not null default 19.99,
 interval_unit text not null default 'MONTH', updated_at timestamptz not null default now()
);
alter table public.paypal_billing_config enable row level security;
revoke all on public.paypal_billing_config from anon, authenticated;
create table if not exists public.paypal_payments(
 sale_id text primary key, user_id uuid not null references auth.users(id) on delete cascade,
 subscription_id text not null, event_type text not null, amount numeric(12,2), currency_code text,
 payment_state text not null check(payment_state in ('completed','refunded','reversed')),
 event_time timestamptz not null, raw_event_id text not null, created_at timestamptz not null default now()
);
create index if not exists paypal_payments_user_event_idx on public.paypal_payments(user_id,event_time desc);
alter table public.paypal_payments enable row level security;
revoke all on public.paypal_payments from anon, authenticated;
alter table public.paypal_webhook_events enable row level security;
revoke all on public.paypal_webhook_events from anon, authenticated;
