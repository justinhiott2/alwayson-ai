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
    return;
  }
  const { data, error } = await supabase.from("memberships")
    .select("status,current_period_end,cancel_at_period_end")
    .eq("user_id", currentSession.user.id).maybeSingle();
  if (error) {
    $("membershipCloudStatus").textContent = "Account connected; membership status could not be loaded.";
    return;
  }
  const active = data && ["active", "trialing"].includes(data.status);
  $("membershipCloudStatus").textContent = active
    ? "PayPal membership: " + data.status + (data.current_period_end ? " · period ends " + new Date(data.current_period_end).toLocaleDateString() : "") + (data.cancel_at_period_end ? " · cancellation scheduled" : "")
    : "Membership: " + (data?.status || "Free plan") + ". Paid access will be granted only after PayPal confirms payment.";
  if ($("manageBilling")) $("manageBilling").classList.toggle("hidden", !data);
}
async function updateAccount() {
  const user = currentSession?.user;
  const signed = Boolean(user);
  if ($("accountEmail")) $("accountEmail").textContent = signed ? user.email : "Not signed in";
  $("accountLogin")?.classList.toggle("hidden", signed);
  $("accountSignup")?.classList.toggle("hidden", signed);
  $("accountLogout")?.classList.toggle("hidden", !signed);
  if ($("accountName")) $("accountName").disabled = signed;
  if ($("premiumCheckout")) {
    $("premiumCheckout").disabled = !signed || true;
    $("premiumCheckout").textContent = "Black Friday PayPal checkout pending";
  }
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
$("manageBilling")?.addEventListener("click", () => setStatus("PayPal cancellation management will be enabled after the PayPal subscription API and webhook are configured."));
$("premiumCheckout")?.addEventListener("click", () => setStatus("PayPal subscription checkout is not enabled yet. No payment has been requested."));
supabase.auth.onAuthStateChange((_event, session) => { currentSession = session; updateAccount(); });
const { data } = await supabase.auth.getSession();
currentSession = data.session;
await updateAccount();
window.moneyHunterCloud = { supabase, refreshMembership };
