import { createClient } from "https://esm.sh/@supabase/supabase-js@2.80.0";

const supabase = createClient(
  "https://unjulxbkxnscwkxlmtbd.supabase.co",
  "sb_publishable_F5Ix3YoQLNA3JPhbfeAoCg_oLMGfrK3"
);
const $ = (id) => document.getElementById(id);
let currentSession = null;
const setStatus = (message, error = false) => {
  const el = $("accountStatus");
  if (el) { el.textContent = message; el.style.color = error ? "#ff9a8b" : "#a9b5c8"; }
};
async function refreshMembership() {
  if (!currentSession?.user) {
    if ($("membershipCloudStatus")) $("membershipCloudStatus").textContent = "Sign in to connect membership to your account.";
    if ($("manageBilling")) $("manageBilling").classList.add("hidden");
    if ($("premiumCheckout")) $("premiumCheckout").disabled = true;
    return;
  }
  const { data, error } = await supabase.from("memberships")
    .select("status,current_period_end,cancel_at_period_end,stripe_customer_id")
    .eq("user_id", currentSession.user.id).maybeSingle();
  if (error) {
    $("membershipCloudStatus").textContent = "Account connected; membership status could not be loaded.";
    return;
  }
  const active = data && ["active", "trialing"].includes(data.status);
  $("membershipCloudStatus").textContent = active
    ? "Stripe membership: " + data.status + (data.current_period_end ? " · period ends " + new Date(data.current_period_end).toLocaleDateString() : "") + (data.cancel_at_period_end ? " · cancellation scheduled" : "")
    : "Membership: " + (data?.status || "Free plan") + ". Paid access activates only after Stripe confirms payment.";
  if ($("manageBilling")) $("manageBilling").classList.toggle("hidden", !data?.stripe_customer_id);
  if ($("premiumCheckout")) {
    $("premiumCheckout").disabled = Boolean(active);
    $("premiumCheckout").textContent = active ? "Membership active" : "Subscribe securely with Stripe";
  }
}
async function startCheckout() {
  if (!currentSession?.user) return setStatus("Sign in before subscribing.", true);
  const button = $("premiumCheckout");
  button.disabled = true;
  button.textContent = "Opening secure Stripe checkout…";
  setStatus("Creating your secure subscription checkout…");
  try {
    const { data, error } = await supabase.functions.invoke("create-checkout-session", { body: {} });
    if (error) throw error;
    if (!data?.url || typeof data.url !== "string" || !data.url.startsWith("https://checkout.stripe.com/")) {
      throw new Error(data?.error || "Stripe did not return a valid checkout URL.");
    }
    window.location.assign(data.url);
  } catch (error) {
    setStatus(error?.message || "Checkout is unavailable. Please try again later.", true);
    await refreshMembership();
  } finally {
    if (button && !button.disabled) button.textContent = "Subscribe securely with Stripe";
  }
}
async function manageBilling() {
  if (!currentSession?.user) return setStatus("Sign in to manage your membership.", true);
  const button = $("manageBilling");
  if (button) { button.disabled = true; button.textContent = "Opening billing portal…"; }
  try {
    const { data, error } = await supabase.functions.invoke("create-portal-session", { body: {} });
    if (error) throw error;
    if (!data?.url || typeof data.url !== "string" || !data.url.startsWith("https://billing.stripe.com/")) {
      throw new Error(data?.error || "Stripe did not return a valid billing portal URL.");
    }
    window.location.assign(data.url);
  } catch (error) {
    setStatus(error?.message || "Billing management is unavailable.", true);
  } finally {
    if (button) { button.disabled = false; button.textContent = "Manage / cancel membership"; }
  }
}
async function updateAccount() {
  const user = currentSession?.user;
  const signed = Boolean(user);
  if ($("accountEmail")) $("accountEmail").textContent = signed ? user.email : "Not signed in";
  $("accountLogin")?.classList.toggle("hidden", signed);
  $("accountSignup")?.classList.toggle("hidden", signed);
  $("accountLogout")?.classList.toggle("hidden", !signed);
  if ($("accountName")) $("accountName").disabled = signed;
  if ($("premiumCheckout")) $("premiumCheckout").disabled = !signed;
  await refreshMembership();
}
async function signUp() {
  const email = $("accountEmailInput").value.trim();
  const password = $("accountPassword").value;
  const name = $("accountName").value.trim();
  if (!email || password.length < 8) return setStatus("Enter an email and password with at least 8 characters.", true);
  const { data, error } = await supabase.auth.signUp({ email, password, options: { data: { display_name: name } } });
  if (error) return setStatus(error.message, true);
  if (data.session) {
    currentSession = data.session;
    await supabase.from("profiles").upsert({ id: data.user.id, display_name: name || null });
    await updateAccount();
    setStatus("Account created and signed in.");
  } else setStatus("Account created. Check your email to confirm, then sign in.");
}
async function signIn() {
  const { data, error } = await supabase.auth.signInWithPassword({
    email: $("accountEmailInput").value.trim(), password: $("accountPassword").value
  });
  if (error) return setStatus(error.message, true);
  currentSession = data.session;
  await supabase.from("profiles").upsert({ id: data.user.id, display_name: $("accountName").value.trim() || null });
  await updateAccount();
  setStatus("Signed in.");
}
async function signOut() {
  const { error } = await supabase.auth.signOut();
  if (error) return setStatus(error.message, true);
  currentSession = null;
  await updateAccount();
  setStatus("Signed out.");
}
$("accountSignup")?.addEventListener("click", signUp);
$("accountLogin")?.addEventListener("click", signIn);
$("accountLogout")?.addEventListener("click", signOut);
$("manageBilling")?.addEventListener("click", manageBilling);
$("premiumCheckout")?.addEventListener("click", startCheckout);
supabase.auth.onAuthStateChange((_event, session) => { currentSession = session; updateAccount(); });
const { data } = await supabase.auth.getSession();
currentSession = data.session;
await updateAccount();
window.moneyHunterCloud = { supabase, refreshMembership };
