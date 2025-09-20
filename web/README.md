# Finance Autopilot Web (MVP)
- Local-only CSV parsing with PapaParse + Zod.
- Normalizes to internal Tx schema; simple rule-based categorization.
- HMRC Self-Assessment CSV export (v0).
## Dev
pnpm i (or npm i)
pnpm dev
Open http://localhost:3000
## Notes
- No external calls; data stays in browser.
- CSV headers expected: Date, Description, Amount, (optional) Account.
