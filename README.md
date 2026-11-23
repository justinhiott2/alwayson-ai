# Money Hunter AI

A free-first, mobile-friendly personal recovery research workspace hosted as a static Progressive Web App.

## What is implemented

- Responsive iPhone-friendly PWA with offline app-shell caching.
- Official-source launchpad for nationwide state unclaimed-property searches and separate federal recovery databases.
- State-by-state research checklist.
- Local-only matching profile for current/former names and prior locations (no SSN, DOB, bank credentials, or identity-document numbers).
- CSV import for records downloaded from supported official portals; matching runs in the browser.
- Manual record entry, local opportunity scoring, evidence/source links, claim-preparation summaries, print-to-PDF, status tracking, CSV export, and full JSON backup/restore.
- Local storage only; records and profile are not uploaded to a server by this static app.
- Local revenue ledger for confirmed receipts, pending fees/deposits, expenses, daily/monthly revenue, net recorded cash, and CSV export; financial entries are stored locally in the browser and are not synced to payment processors.

## Important limitations

- There is no single government-wide unclaimed-money database. State programs and federal agencies maintain separate records.
- MissingMoney covers most participating states, not all states.
- Public portal links are not the same as a live API integration. This app does not scrape private claimant data or bypass agency controls.
- A name/location score is a lead-screening hint, not identity verification or proof of ownership.
- Claim packet preparation is supported; the app does not sign legal declarations, bypass CAPTCHA, or submit claims automatically. The claimant must verify the official record, satisfy the agency's evidence requirements, personally review/sign, and submit through the agency's official process.
- No recovered money or eligibility is guaranteed.

## Official starting points

- https://www.missingmoney.com/
- https://unclaimed.org/search/
- https://www.usa.gov/unclaimed-money

## Free deployment

Static hosting can be provided through GitHub Pages. The app itself does not require a paid model/API. It does not include an autonomous cloud AI agent or scheduled background searches; adding those would require a server-side runtime, data-source permissions, and potentially paid services.

## Privacy

The profile and records are stored in the current browser's local storage. Do not enter SSNs, dates of birth, bank passwords, payment card details, private keys, or seed phrases. Export a backup before clearing browser data or changing devices.
