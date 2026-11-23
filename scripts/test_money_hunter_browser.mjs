import { chromium } from "playwright";
import fs from "node:fs";

const baseURL = process.env.APP_BASE_URL || "http://127.0.0.1:4173/money-hunter/";
const results = [];
const errors = [];
const check = (name, pass, detail = "") => results.push({ name, status: pass ? "passed" : "failed", detail });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
page.on("pageerror", error => errors.push(error.message));
page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });

try {
  const response = await page.goto(baseURL, { waitUntil: "networkidle", timeout: 45000 });
  check("App homepage loads", Boolean(response && response.ok()), response ? `HTTP ${response.status()}` : "No response");
  check("App title is present", (await page.title()).includes("Money Hunter"));

  const navButtons = page.locator("nav.nav button[data-tab]");
  const tabNames = await navButtons.evaluateAll(nodes => nodes.map(node => node.dataset.tab));
  check("Main navigation has expected tabs", ["home","search","bot","profile","matches","claims","pricing","revenue","settings"].every(name => tabNames.includes(name)), tabNames.join(", "));

  for (const tab of tabNames) {
    await page.locator(`nav.nav button[data-tab="${tab}"]`).click();
    const section = page.locator(`#${tab}`);
    check(`Navigation opens ${tab}`, await section.evaluate(node => node.classList.contains("active")));
  }

  await page.locator('nav.nav button[data-tab="profile"]').click();
  const nameField = page.locator("#pName");
  await nameField.fill("Browser Test User");
  await page.locator("#saveProfile").click();
  check("Profile save gives confirmation", (await page.locator("#profileStatus").innerText()).toLowerCase().includes("saved"));
  await page.reload({ waitUntil: "networkidle" });
  check("Profile persists after reload", (await page.locator("#pName").inputValue()) === "Browser Test User");

  await page.locator('nav.nav button[data-tab="search"]').click();
  await page.locator("#manualAgency").fill("Automated browser test");
  await page.locator("#manualState").selectOption({ label: "South Carolina" }).catch(async () => {
    await page.locator("#manualState").selectOption("SC").catch(() => {});
  });
  await page.locator("#manualName").fill("Browser Test User");
  await page.locator("#manualAddress").fill("Moncks Corner, SC");
  await page.locator("#manualRef").fill("Synthetic test record — not a real claim");
  await page.locator("#manualAmount").fill("12.34");
  await page.locator("#manualUrl").fill("https://example.com/test-record");
  await page.locator("#saveManual").click();
  await page.locator('nav.nav button[data-tab="matches"]').click();
  check("Synthetic record can be saved and displayed", await page.locator("#matchResults").getByText("Browser Test User").count() > 0);
  check("Synthetic record is clearly marked as test data", await page.locator("#matchResults").getByText(/Synthetic test record/).count() > 0);

  await page.locator('nav.nav button[data-tab="pricing"]').click();
  check("Premium checkout stays disabled in test mode", await page.locator("#premiumCheckout").isDisabled());

  const manifestResponse = await page.request.get(new URL("manifest.webmanifest", baseURL).toString());
  check("PWA manifest is reachable", manifestResponse.ok(), `HTTP ${manifestResponse.status()}`);
  const manifest = await manifestResponse.json().catch(() => ({}));
  check("PWA manifest has app identity", Boolean(manifest.name && manifest.start_url));

  const reportResponse = await page.request.get(new URL("reports/latest.json", baseURL).toString());
  check("Latest research report endpoint responds", reportResponse.ok(), `HTTP ${reportResponse.status()}`);
  if (reportResponse.ok()) {
    const report = await reportResponse.json().catch(() => null);
    check("Latest research report is valid JSON", Boolean(report && typeof report === "object"));
  }

  check("No uncaught browser JavaScript errors", errors.length === 0, errors.slice(0, 5).join(" | "));
} catch (error) {
  check("Browser test run completed without a fatal exception", false, error.stack || error.message);
} finally {
  await page.screenshot({ path: "money-hunter-browser-test.png", fullPage: true }).catch(() => {});
  await browser.close();
}

const failed = results.filter(result => result.status === "failed").length;
const report = {
  bot: "Money Hunter Browser Test Bot",
  tested_at: new Date().toISOString(),
  app_url: baseURL,
  mode: "isolated browser test; synthetic data only",
  summary: { checks_run: results.length, passed: results.length - failed, failed },
  results,
  browser_errors: errors,
  safety: "No real claims submitted, no payments initiated, no customer accounts accessed, and no production data changed."
};
fs.mkdirSync("money-hunter/reports", { recursive: true });
fs.writeFileSync("money-hunter/reports/browser-test.json", JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify(report, null, 2));
if (failed) process.exitCode = 1;

// Manual test-run trigger commit: browser suite executes on every test-bot change.
