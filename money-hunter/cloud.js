import { createClient } from "https://esm.sh/@supabase/supabase-js@2.80.0";

const SUPABASE_URL = "https://unjulxbkxnscwkxlmtbd.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_F5Ix3YoQLNA3JPhbfeAoCg_oLMGfrK3";
const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);
const $ = (id) => document.getElementById(id);
const setStatus = (message, isError = false) => {
  const el = $("accountStatus");
  if (el) { el.textContent = message; el.style.color = isError ? "#ff9a8b" : "#a9b5c8"; }
};
let currentSession = null;

async function refreshMembership() {
  const status = $("membershipCloudStatus");
  const manage = $("manageBilling");
  const checkout = $("premiumCheckout");
  if (!currentSession?.user) {
    if (status) status.textContent = "Sign in to connect your membership to your account.";
    if (manage) manage.classList.add("hidden");
    if (checkout) checkout.disabled = true;
    return;
  }
  if (checkout) checkout.disabled = false;
  const { data, error } = await supabase.from("memberships")
    .select("status,current_period_end,cancel_at_period_end")
    .eq("user_id", currentSession.user.id).maybeSingle();
  if (error) {
    if (status) status.textContent = "Account connected; membership status could not be loaded.";
    return;
  }
  const active = data && ["active", "trialing"].includes(data.status);
  if (status) {
    status.textContent = active
      ? "Premium status: " + data.status + (data.current_period_end ? " · renews/ends " + new Date(data.current_period_end).toLocaleDateString() : "") + (data.cancel_at_period_end ? " · cancellation scheduled" : "")
      : "Membership status: " + (data?.status || "Free plan") + ". Paid access is granted only after Stripe payment confirmation.";
  }
  if (manage) manage.classList.toggle("hidden", !data);
  if (checkout) {
    checkout.textContent = active ? "Manage membership" : "Start sandbox checkout — $29/month";
    checkout.disabled = false;
  }
}

async function updateAccount() {
  const user = currentSession?.user;
  const signed = Boolean(user);
  if ($("accountEmail")) $("accountEmail").textContent = signed ? user.email : "Not signed in";
  if ($("accountLogin")) $("accountLogin").classList.toggle("hidden", signed);
  if ($("accountSignup")) $("accountSignup").classList.toggle("hidden", signed);
  if ($("accountLogout")) $("accountLogout").classList.toggle("hidden", !signed);
  if ($("accountName")) $("accountName").disabled = signed;
  await refreshMembership();
}

async function signUp() {
  const email = $("accountEmailInput").value.trim();
  const password = $("accountPassword").value;
  const name = $("accountName").value.trim();
  if (!email || password.length < 8) return setStatus("Enter an email and a password with at least 8 characters.", true);
  const { data, error } = await supabase.auth.signUp({ email, password, options: { data: { display_name: name } } });
  if (error) return setStatus(error.message, true);
  if (data.session) {
    currentSession = data.session;
    await supabase.from("profiles").upsert({ id: data.user.id, display_name: name || null });
    await updateAccount();
    setStatus("Account created and signed in.");
  } else {
    setStatus("Account created. Check your email to confirm, then sign in.");
  }
}
async function signIn() {
  const email = $("accountEmailInput").value.trim();
  const password = $("accountPassword").value;
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
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
async function createPortal() {
  if (!currentSession) return setStatus("Sign in first.", true);
  setStatus("Opening secure billing portal…");
  const { data, error } = await supabase.functions.invoke("create-portal-session", { body: {} });
  if (error || !data?.url) return setStatus(data?.error || error?.message || "Billing portal is not configured yet.", true);
  location.assign(data.url);
}
async function checkout() {
  if (!currentSession) return setStatus("Create an account or sign in before checkout.", true);
  const { data: membership } = await supabase.from("memberships")
    .select("status").eq("user_id", currentSession.user.id).maybeSingle();
  if (membership && ["active", "trialing"].includes(membership.status)) return createPortal();
  setStatus("Creating a sandbox Checkout session…");
  const { data, error } = await supabase.functions.invoke("create-checkout-session", { body: {} });
  if (error || !data?.url) return setStatus(data?.error || error?.message || "Checkout is not configured. No payment was taken.", true);
  location.assign(data.url);
}

$("accountSignup")?.addEventListener("click", signUp);
$("accountLogin")?.addEventListener("click", signIn);
$("accountLogout")?.addEventListener("click", signOut);
$("manageBilling")?.addEventListener("click", createPortal);
$("premiumCheckout")?.addEventListener("click", checkout);
supabase.auth.onAuthStateChange((_event, session) => {
  currentSession = session;
  updateAccount();
});
const { data: sessionData } = await supabase.auth.getSession();
currentSession = sessionData.session;
await updateAccount();
window.moneyHunterCloud = { supabase, refreshMembership };
