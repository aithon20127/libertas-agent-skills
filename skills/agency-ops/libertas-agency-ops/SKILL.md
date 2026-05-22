---
name: libertas-agency-ops
version: 1.0.0
category: agency-ops
description: Operate and maintain the Libertas Insurance CRM data pipeline — EZLynx sync, coverage backfill, carrier data pulls, Gmail API access, Supabase queries, and all recurring book-of-business updates.
triggers:
  - CRM update or sync
  - EZLynx data pull or ingest
  - coverage backfill
  - carrier portal automation
  - Gmail API access for agency inboxes
  - Supabase DB queries for agency data
  - nightly sync verification
  - renewal radar
  - policy lifecycle management
tags: [libertas, agency, crm, ezlynx, supabase, gmail, insurance, personal-lines]
---

# Libertas Agency Operations

End-to-end guide for operating the Libertas Insurance CRM data pipeline on the ROG. Covers the nightly EZLynx sync, coverage data backfill, Gmail inbox access, Supabase queries, and all recurring book-of-business tasks.

## Architecture Overview

```
EZLynx nightly reports ──► 2factorlogins@gmail.com
                                │
                                ▼
                    Odysseus (ROG) pulls CSV from Gmail API
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
          Policy Master CSV          Renewal Detail CSV
                    │                       │
                    ▼                       ▼
    ezlynx_policy_master_staging   ezlynx_renewal_detail_staging
          (via Supabase REST API)         (via Supabase REST API)
                    │                       │
                    ▼                       ▼
          ezlynx_transform_run()   (NO transform yet)
                    │
                    ▼
     households / contacts / addresses / policies
                    │
                    ▼
          Coverage scrape (ACORD pages) ──► policy_coverages
```

**ARCHITECTURE CHANGE (2026-05-21):** Odysseus now pulls the CSV from Gmail every morning instead of the `ezlynx-ingest` edge function. The edge function stays deployed as a fallback but its Gmail polling is disabled. Odysseus writes to staging via REST API, then calls `ezlynx_transform_run()` RPC for the heavy lifting. Coverage scrape runs after CSV sync.

Key repo: `~/libertas-crm` (GitHub: `Libertas-cloud/libertas-crm-full`, branch `main`).
Deep reference doc: `~/.hermes/AGENCY-KNOWLEDGE.md` — READ before any real agency task; verify against live code/DB.

## The Coverage Gap (CRITICAL)

The nightly Policy Master CSV contains **header-level data only**: policy number, carrier, LOB, effective/expiration dates, premium, insured name/address, phone, email. It does **NOT** contain coverage details (Coverage A–E, deductibles, liability limits, etc.).

**Confirmed 2026-05-21 (DEFINITIVE across ALL 10+ report types)**: NO EZLynx Reports 5.0 report type contains coverage columns. Policy_Master has 73 columns (all selected), PolicyTransaction_Master has 76, BOB_Expanded ~38, Renewal Detail 15 — none carry Coverage A-E, deductibles, or liability limits. This is a structural limitation of the reporting engine, not a column selection issue. Coverage data lives in the IVANS download records, which EZLynx decodes and displays on individual policy pages.

The `ezlynx_raw` JSON column on each policy stores the full Policy Master row, but those rows never had coverage columns to begin with. This is why ~30% of policies (especially Manual-source ones from non-IVANS carriers like Logic/Standard Casualty) have spotty coverage data.

**DEFINITIVE (2026-05-21): NO EZLynx Reports 5.0 report type contains coverage columns.** Checked all 10+ types (Policy Master, BOB Detail, Policy Transaction Master, Premium Change Detail, etc.) — zero coverage columns in any of them. This is a structural limitation of the reporting engine, not a column selection issue.

**Fix path (CONFIRMED — priority order):**
1. **Scrape the EZLynx PolicyDisplayAndCompare page** — every policy has a "Full Policy Details" page that dumps complete ACORD XML data (coverage codes, limits, deductibles, endorsements, vehicles, drivers, dwelling details, mortgagees). URL: `/ApplicantPortal/Applicant/{applicantId}/PolicyDisplayAndCompare?Func=0&ApplicantID={applicantId}&PolMasterID=m{policyId}`. This is THE primary source. Covers ~70% of book (IVANS-sourced). See `ezlynx-operations` skill → `references/policy-coverage-pipeline.md` for full details.
2. **Generate ACORD forms from CRM data** — once coverage is in the CRM, generate ACORD 80 (Homeowners), ACORD 25 (Auto), ACORD 28 (Evidence of Property Insurance) as PDF-fillable forms. One implementation serves all carriers. Covers 80%+ of client document needs.
3. **Carrier portal dec page scripts** — for the actual carrier dec pages/ID cards (not ACORD substitutes). Build per-carrier Browserbase+Stagehand scripts. Top target: Allstate (~32% of book). Only needed for the ~30% of policies where PolicyDisplayAndCompare has sparse data AND the client specifically needs the carrier's own dec page.

## Accessing Supabase from the ROG

### PITFALL: Supabase keys — NOW PROVISIONED (2026-05-21)

Real keys are saved at `~/.config/libertas/credentials.env` (chmod 600) and `~/libertas-crm/.env.supabase` (chmod 600). Connection verified working:
- REST API: 4,078 policies in CRM, staging tables populated, transform RPC callable
- Direct DB: psycopg2 connects, migrations applied, `policy_coverages` table live
- Service role key bypasses RLS — full read/write to all tables

**Details and code patterns:** `references/supabase-access.md`

The old abbreviated placeholder keys in `~/libertas-crm/.env` and `~/libertas-crm/browserbase-functions/.env` are still there — ignore them. Use `.env.supabase` or the values in the reference doc.

### Supabase CLI auth status

As of 2026-05-20: `supabase login` has NOT been run on the ROG. Attempting `npx supabase secrets list`, `npx supabase db query --linked`, etc. will fail with "Access token not provided." Fix: `npx supabase login` with a personal access token from the Supabase dashboard.

## Accessing Gmail API from the ROG

Working pattern (validated 2026-05-20):

1. Read credentials from `~/.config/libertas/credentials.env` (chmod 600):
   - `GMAIL_CLIENT_ID`
   - `GMAIL_CLIENT_SECRET`
   - `GMAIL_DEFAULT_REFRESH_TOKEN` (2factorlogins@gmail.com)
   - `GMAIL_LIBERTASLOGINS_REFRESH_TOKEN` (libertaslogins@gmail.com)

2. Use **Python urllib** (not curl — shell quoting of long tokens is fragile):
   ```python
   import urllib.request, urllib.parse, json
   
   data = urllib.parse.urlencode({
       "client_id": client_id,
       "client_secret": client_secret,
       "refresh_token": refresh_token,
       "grant_type": "refresh_token"
   }).encode()
   
   req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
   with urllib.request.urlopen(req) as resp:
       token_data = json.loads(resp.read())
   access_token = token_data["access_token"]
   ```

3. Make Gmail API calls with the access token.

### Inbox status

| Inbox | Purpose | Access from ROG | Notes |
|---|---|---|---|
| `2factorlogins@gmail.com` | EZLynx CSV recipient, Safeco 2FA, DCS 2FA | **WORKING** — refresh token in `~/.config/libertas/credentials.env` (GMAIL_DEFAULT_REFRESH_TOKEN), scope: gmail.readonly | Daily sync pipeline pulls CSVs from this inbox automatically |
| `libertaslogins@gmail.com` | Foremost (Okta) 2FA, NatGen 2FA | **WORKING** — refresh token in `~/.config/libertas/credentials.env` (GMAIL_LIBERTASLOGINS_REFRESH_TOKEN), scope: gmail.readonly | Also used for auto-2FA during EZLynx login |
| `Aithon20127@gmail.com` | Agent's Google account | Browser only (logged into Chrome). himalaya v1.2.0 installed at `~/.local/bin/himalaya`, config at `~/.config/himalaya/config.toml`. **Needs 2FA enabled + App Password** before IMAP/SMTP works. Password: RaidTroy2026!, DOB: 5/15/1980. |
| `service@libertasinsurance.com` | Agency service inbox | **Refresh token provisioned 2026-05-21** at `~/.config/libertas/gmail-service.env` (GMAIL_SERVICE_REFRESH_TOKEN). Purpose TBD (Kyle to discuss). |

**Both agency inboxes have working API access.** The daily sync pipeline pulls EZLynx CSVs from 2factorlogins@gmail.com every morning. Gmail credentials are consolidated in `~/.config/libertas/credentials.env` (chmod 600).

## EZLynx Ingest Pipeline Details

**ARCHITECTURE (updated 2026-05-21):** Odysseus pulls CSV from Gmail every morning, writes to staging via Supabase REST API, then calls `ezlynx_transform_run()` RPC. Kyle turned OFF the `ezlynx-ingest` edge function's report loading on 2026-05-21 — it no longer pulls from Gmail. The edge function is kept deployed as a manual fallback.

- **Edge function (fallback):** `supabase/functions/ezlynx-ingest/index.ts`
- **Gmail search query:** `from:ezlynxreporting@ezlynx.com subject:"CRM Sync" has:attachment filename:csv newer_than:7d`
- **Two report types:** Policy Master (staged + transformed) and Renewal Detail (staged only, no transform yet)
- **Transform function:** `ezlynx_transform_run(UUID)` — PL/pgSQL, SECURITY DEFINER
- **Authority rule:** EZLynx wins on field conflicts; losing CRM values go to `policies_audit`
- **Transform maps:** carrier (auto-create unknown), LOB (via `ezlynx_lob_map` table), status, effective/expiration dates, premium, household, contact, address — **NO coverage fields**
- **Coverage data:** comes from ACORD page scrape (separate pipeline), NOT from the nightly CSV. Migration: `20260521120000_policy_coverages.sql`

## Git Workflow on the ROG

- Repo: `~/libertas-crm`
- **Always `git pull` before starting work**
- Work on a branch, PR to `main`
- Commit as **Aithon** (aithon20127)
- Autonomy: freely create/iterate/merge OWN new code (carrier scripts, tooling)
- **Do NOT touch** `index_CRM/` or `supabase/functions/quote/` or `supabase/functions/quote-intake/` without Kyle's explicit sign-off

## Prerequisites Checklist (items still needed)

- [ ] `supabase login` on the ROG (optional — direct DB works already)
- [ ] Enable 2FA on Aithon20127@gmail.com + generate App Password for himalaya IMAP
- [x] Google OAuth for Aithon account (`aithon20127@gmail.com`) — token at `~/.hermes/google_token.json` with `spreadsheets`, `drive.file`, `gmail.readonly` scopes. Sheets API not enabled in Google Cloud project 848419619510 (only project owner 2factorlogins@gmail.com can enable). **Working workaround: create/populate sheets via Chrome browser** — navigate to `sheets.new`, paste CSV, Split text to columns. See `google-workspace` skill → "Browser-Based Sheets Fallback" for the workflow.
- [x] Real Supabase service key — provisioned 2026-05-21 at `~/libertas-crm/.env.supabase` (chmod 600). REST API + direct DB both verified working. Keys also in `~/.config/libertas/credentials.env`.
- [x] EZLynx login credentials — `kkriegel1`, 2FA to `libertaslogins@gmail.com`
- [x] Gmail API for 2factorlogins@gmail.com — refresh token WORKING (provisioned 2026-05-21). Daily sync pulls CSVs automatically. Token in `~/.config/libertas/credentials.env`.
- [x] Gmail API for libertaslogins@gmail.com — refresh token WORKING (verified 2026-05-21). Token in `~/.config/libertas/credentials.env`.
- [x] himalaya v1.2.0 installed at `~/.local/bin/himalaya`
- [x] Full Phase 0 coverage scan complete (823/823 active policies)
- [x] Phase 0 coverage BACKFILL complete — 600/611 policies written to `policy_coverages`, 0 failures (~8,400 coverage rows). 11 policies had no CRM UUID (not in policy table yet).
- [x] SQL migration for policy_coverages table APPLIED to cloud (`20260521120000_policy_coverages.sql`)
- [x] Daily sync pipeline live — cron at 8:30 AM CT, script at `~/.config/libertas/scripts/libertas_daily_sync.py`. See `libertas-daily-sync` skill.
- [x] Logic Insurance / Standard Casualty carrier_login entry (portal mapped, credentials in master login sheet row 137)

## Carrier Portal Research — How to Start

When Kyle asks to "learn" a carrier site, do NOT guess at URLs. Carrier portals vary wildly (some are on the carrier's main domain, some are separate agent portals, some use third-party platforms). The fastest path:

1. **Use the master login sheet** — Kyle has a Google Sheet ("Libertas PWs") shared with the Aithon Google account. It's open in a Chrome tab. Row per carrier, with URL/login/password columns.
2. **Only access what Kyle authorizes** — the sheet has many stale/broken logins. Ask Kyle which entry is current before logging in. Do NOT test random credentials or click into portals Kyle hasn't told you to use.
3. **Search for EXACT carrier name in Column A** — e.g., "Logic-Standard Casualty" not just "Logic". Partial matches land on the wrong row (there are separate entries for CC payment logins, old portals, etc.). Kyle flagged this as a real problem — searching "Logic" matched "Logic (For CC Payments)" in row 136 instead of "Logic-Standard Casualty" in row 137.
4. Once you have the URL, log in via Chrome (CDP) and map the portal: navigation structure, where policy data lives, what's available for quoting vs. servicing, and any automation-relevant endpoints.
5. Save the carrier's portal URL, login page structure, and key navigation paths in `references/carrier-portals/` under this skill.
6. **NEVER edit the master login sheet** — Kyle shared it view-only. Even if edit access is granted, do not modify any cell without explicit permission.
7. **Don't access carrier portals Kyle hasn't authorized** — the sheet has many stale entries. Only log into portals Kyle has told you to use.

### Carrier Portal: Logic Insurance / Standard Casualty (EZ*Insure / Beyontec Suite)

**Portal URL:** https://logicunderwriters.com/beyontecsuite/
**Login:** Click AGENT, User ID 2527, password from master login sheet row 137
**Platform:** Beyontec Suite (EZ*Insure) — same platform may be used by other carriers

**Navigation structure:**
- Quotes → New Quote HO-A / New Quote HO-B / New Quote DP1 / New Quote TDP1 / Existing Quotes
- Renewals → Renewal Quote (search by Customer Name, FQ/Policy#, Product, Inception Date, Status)
- Reports And Queries
- Applications
- Policy Inquiry/Transactions → Billing Inquiry
- Claims
- Documents
- My Account

**Quoting form (HO-A and HO-B):**
- 3 tabs: Customer Details → Quote Details → Business Rule
- Tab navigation via JS: `fQPageNavigate('UTDS_LEVEL_M_ID')` (Customer), `fQPageNavigate('UTDS_LEVEL_R_ID')` (Quote Details), `fQPageNavigate('TDS_LEVEL_BR_DTLS_ID')` (Business Rule)
- Quote Details tab requires Customer Details to be valid (saved) first
- **Intermediate risk info screen** between Customer Details and Quote Details — has riskTypeId, effective dates; must be confirmed before Quote Details form appears
- Quote Details has sub-tabs: `UTDS_LEVEL_R_EDIT` (edit form), `NOTE`, `CONDITIONS`, `QUESTIONS` — accessed via `menuSelection()` JS function
- Content renders inside nested iframes — Hermes browser snapshots miss iframe content; Playwright-over-CDP works
**Carrier validates phone numbers LIVE** — "Disconnected Phone" error means the number is flagged as disconnected in a real phone database. Use agency number 512-761-6379 or real client numbers, never random test numbers.
- **"Component Mismatch Error"** — address/zip not in carrier's rating territory. Use known-in-territory zips.
- **"Warning! Locality Change" is NOT blocking** — it appears when address data changes between the customer mailing address and the property location, but you can still advance past it with Confirm/Next. It may reappear after save/next; ignore it and keep going. Do NOT waste time trying to clear it.
- **Effective date MUST be future-dated** — the carrier will not allow backdated quotes. If the effective date is in the past (even by one day), the quote cannot proceed. Always set the effective date at least a few days in the future (Kyle suggests 2 weeks out for test quotes). After midnight, yesterday's date becomes invalid.
- **"Get Premium" button replaces "Confirm/Next"** — when on the Quote Details screen (after Customer Details is confirmed), the action button changes from "Confirm/Next" to "Get Premium". The Confirm/Next button ID is `#idConfmNxt`. For premium calculation, use `fullQuoteCalc()` on the fullquotelist frame AFTER saving (`fQDBSave()`). If calc returns "Please save and calculate" alert, ensure save has fully completed first.
- **HO-B coverage selects are locked** — Many coverage dropdowns (rate|PP, rate|HO162, rate|ERCP, rate|HO135) are disabled and can't be changed via normal Playwright select. Use `force_select()` pattern: JS force-enable, set value, dispatch change event, then save. See `logic-quoting` skill for full details.
- **City/County fields require Space-press + click validation** — after zip lookup auto-fills city/county, you MUST press Space in the City field to trigger a dropdown, then click the matching city `<div>` element (e.g., `<div id="WACO">`). Same for county — press Space, then click `<div id="MCLENNAN">`. This applies to BOTH the Customer Details form AND the Quote Details property form. The auto-filled text alone is NOT sufficient — the dropdown selection is required for validation.
- **Tab-order for county/city (Kyle's explicit instruction):** Tab from Address Line 1 to County, press Space, click the correct county div, then Tab to City, press Space, click the correct city div. County first, then city. This clears the "Locality Change" warning.
- **Chrome "Save address" autofill popup** — appears constantly on address fields. **Fix: disable in Chrome** at `chrome://settings/addresses` — toggle off "Save and fill addresses." Also check `chrome://settings/payments`. In automation, dismiss with `logic_page.press('body', 'Escape')`.
- **"Warning! Locality Change" REAPPEARS after Confirm/Next** — it clears on Space-press validation but comes back when you advance. It is NOT blocking. Ignore it and keep going.
- **Chrome "Save address" autofill popup blocks Playwright** — dismiss with `logic_page.press('body', 'Escape')` before any click interaction. This popup appears frequently on address fields in Chrome.
- **Portal has aggressive session timeout** — "Continue Session" overlay appears after inactivity. Dismiss by clicking the "Continue Session" button or the session will expire and you'll need to re-login.
- **Quote Details property form city/county Space-press pattern (Kyle's explicit instruction):** Tab from Address Line 1 to County, press Space in County, click the correct county `<div>`, then Tab to City, press Space, click the correct city `<div>`. This clears the validation error on the property form.

**Customer Details field map (for automation):**
| Field | Element ID | Notes |
|-------|-----------|-------|
| Individual/Entity | `custIndividualId` / `custCorporateId` | Radio, default Individual |
| First Name | `customerFirstNameId` | Required |
| Middle Initial | `txt_customerMiddleInitial` | |
| Last Name | `txt_customerLastName` | Required |
| DOB | `customerDateOfBirthId` | Format: MM/DD/YYYY, required |
| Entity Type | `cmb_EntityType` | Select, only if Entity |
| Currently Insured | `currentlyInsuredId` | Checkbox |
| Zip Code | `txt_ZipCode` | Required |
| Address Line 1 | `txt_Address1` | |
| City | `txt_City` | |
| State | `txt_State` | |
| Phone | `txt_SPQQ_PhoneNo` | |
| Email | `txt_SPQQ_EmailId` | |
| Req Eff Date | `fullQuoteEffDateId` | |
| Term | `FQ_CD_term_Id` | Select |
| Agent # | `txt_ULM_AGENT_ID` | Pre-filled: 0000002527 |

**Quote Details tab: FULLY MAPPED 2026-05-22** — 112 fields in `uwp2hoa_LUW.do` iframe. Location/address, dwelling info, coverage limits, endorsements, deductibles, claims history. Key findings: Coverage A (`txt_CVRA`) is DISABLED — set dwelling limit via Replacement Value (`txt_ULRP_REPLACEMENT_VAL`) instead. **Carrier enforces valid dwelling range** — popup "Dwelling Limit not in the valid range for Replacement Cost" means the replacement value is outside the carrier's calculated range based on year built/sq ft/construction; adjust to within the stated range. City/county fields require Space-press + click validation. "Addl Fields" button expands hidden sections. Required fields `cmb_ULRP_REP_COST` and `txt_Ulrp_Prior_Cov_Dt` cause validation errors if missing. **Premium results** — "Get Premium" button (replaces "Confirm/Next") triggers rating; the Premium tab shows the full breakdown (dwelling premium, credits, surcharges, fees). Default coverages (Liability 25K, Med Pay 500) are cheapest. See `references/logic-portal-fields.md` for complete field map, all dropdown options, all endorsement checkboxes, premium results format, and HO-B mapping status.

**Renewal Quote detail page (from earlier exploration):**
- Tabs: Customer Details, Policy Details, Questionnaire, Business Rule, Payor, Print Package, Document
- Actions: Premium, Track Email
- Search filters: Customer Name, FQ/Policy#, Product (Dwelling DP-1, TDP-1, HOA, HOB), Inception Date, Status
- Results columns: Policy#, Customer, Product, From/To Date, Batch ID, Work Basket

**Automation approach:**
- **Use visible Chrome that Kyle can see** — when automating carrier portals, launch or connect to a Chrome window Kyle can watch. If the automation gets stuck (validation errors, unexpected dialogs, CAPTCHAs), Kyle can intervene manually. Do NOT run carrier portal automation headlessly or in a background browser.
- Playwright-over-CDP to real Chrome (same pattern as EZLynx) — sessions persist within a browser session
- Hermes browser works for mapping but sessions don't persist between navigations (must re-login each time)
- Build locally first, then wrap for Browserbase/Stagehand cloud deployment alongside Foremost STAR
- Products: HO-A (Home Owners A) and HO-B (Home Owners B) are the quoting priorities

**Key contacts (from portal):**
- UW: 214-739-0071 / 1-888-315-6442 (Sue Blackwell X143)
- Claims: 800-522-0146 Opt5
- Cancellations: underwriting@logicinsurance.com

**Full field-level mapping:** `references/logic-portal-fields.md`

**Quoting automation (HO-A/HO-B):** See the **`logic-quoting`** skill for complete Playwright-over-CDP automation scripts, field maps with all option values, iframe navigation patterns, the `force_select()` pattern for locked coverage selects, and current script status. Scripts at `~/.config/libertas/scripts/logic_quote_ho{a,b}.py`.

### PITFALL: Google Sheets is unreadable programmatically in view-only mode

The master login sheet is shared **view-only** with the Aithon account. This makes it effectively impossible to read cell values with Playwright:

- Google Sheets uses **canvas rendering** — `document.body.innerText` only shows top-level UI (menu bar, tab names), not cell values
- The **formula bar** has no accessible selector in the canvas-based UI
- **Ctrl+F works for locating** — it highlights the cell reference (e.g., "1 of 1, A137 Logic-Standard Casualty") which tells you the row number and column A value
- **Clipboard is blocked** — "Copying and pasting content outside this file has been disabled"
- **Cell selection + Tab through columns** doesn't expose text via `evaluate()`
- **Double-click to edit** is blocked by view-only mode

**Working approach:** Use Ctrl+F to find the row, then **ask Kyle to read you the row's URL/username/password**. Do not waste time trying to extract cell data from a view-only Google Sheet — it's a dead end.

**Full details:** `references/master-login-sheet.md` — sheet URL, structure, reading limitations, and data quality warnings.

## EZLynx Browser Automation (Playwright on ROG)

When you need to interact with the EZLynx web UI (scheduled reports, Policy Summary scraper, etc.), use Playwright driving real Chrome on the ROG. See `references/ezlynx-browser-automation.md` for the full setup, login pattern, and 2FA auto-retrieval technique.

### Key points

- **Do NOT use the Hermes browser for EZLynx** — Cloudflare Turnstile blocks it. Use Playwright with real Chrome (`/usr/bin/google-chrome`) instead.
- **Do NOT use raw CDP WebSocket for DOM queries** — `Runtime.evaluate` returns empty results for `querySelectorAll` etc. on EZLynx's Angular app despite `innerHTML` showing the correct HTML. Cause unknown (possibly Angular view encapsulation + CDP context mismatch). **Use Playwright's `connect_over_cdp()` instead** — it works perfectly for all DOM operations.
- **2FA auto-retrieval works** — when EZLynx sends a verification code to `libertaslogins@gmail.com`, poll the Gmail API (using the refresh token in browserbase-functions/.env) to grab the 6-digit code automatically. No need to ask Kyle.
- **Auth state does NOT persist** across browser restarts — EZLynx session cookies expire quickly. Always plan for a fresh login + 2FA in each session.
- **"Trust this computer" checkbox** — check it on the 2FA page to reduce future friction, but don't rely on it skipping 2FA entirely.
- **Do NOT launch new Chrome instances for carrier portal automation** — Kyle explicitly flagged that opening extra Chrome windows froze his computer. ALWAYS connect to the existing Chrome instance on port 9222 via `p.chromium.connect_over_cdp('http://localhost:9222')`. If Chrome isn't running, ask Kyle to open it — don't spawn one yourself. This applies to ALL carrier portal automation, not just EZLynx.
- **Run carrier portal automation in VISIBLE Chrome** — Kyle wants to see the browser and intervene if the automation gets stuck. Do not run headlessly for carrier portals. When stuck (validation errors, unexpected dialogs, CAPTCHAs), Kyle can click manually.

### Connecting to a running Chrome instance (preferred pattern)

When Kyle has Chrome open and logged into EZLynx, connect to it via CDP instead of launching a new browser:

```bash
# Chrome must be launched with remote debugging + allow-origins:
DISPLAY=:1 /usr/bin/google-chrome \
  --remote-debugging-port=9222 \
  --remote-allow-origins=* \
  --user-data-dir=/tmp/chrome-shared \
  --no-first-run --no-default-browser-check
```

Then connect with Playwright:

```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.connect_over_cdp("http://localhost:9222")
    for ctx in browser.contexts:
        for page in ctx.pages:
            if 'ezlynx' in page.url.lower():
                # Interact with page using full Playwright API
                await page.query_selector('button:has-text("insert_chart")')
                # etc.
```

**Why not raw CDP?** Direct `websocket.create_connection()` + `Runtime.evaluate` fails to find Angular-rendered elements via `querySelectorAll`/`getElementsByTagName` on EZLynx pages, returning 0 results for `button` and `mat-icon` tags that clearly exist in `innerHTML`. Playwright's `connect_over_cdp` works correctly for all selectors. Use Playwright.

### EZLynx Reports Portal (discovered 2026-05-21)

The Reports section is accessible via the `insert_chart` sidebar icon. Two report systems exist:

**Reports 5.0 panel** (sidebar flyout):
- Opens when you click the `insert_chart` sidebar icon
- Shows: Favorite Reports, Scheduled Reports, Shared Reports, Categories
- Categories include: Accounting, Activity, Applicant, Book of Business, Claim, Commission, **Policy Coverage**, Policy Transaction, Quote, Retention Center, Sales Center

**Reports Portal** (full page):
- Scheduled Reports: `https://app.ezlynx.com/EZLynxReportPortal/ScheduledReport`
- All Reports: `https://app.ezlynx.com/EZLynxReportPortal/ReportMenu`

**Currently scheduled reports (UPDATED 2026-05-21 — all rescheduled to 7:30 AM daily as CSV):**

| Report | Enabled | Schedule | Format | Email |
|---|---|---|---|---|
| CRM Sync Nightly | Yes | **7:30 AM daily** | **CSV** | 2factorlogins@gmail.com |
| CRM Renewal Detail Nightly | Yes | **7:30 AM daily** | **CSV** | 2factorlogins@gmail.com |
| Libertas BOB | Yes | **7:30 AM daily** | **CSV** | 2factorlogins@gmail.com |

**Schedule edit dialog** shows: saved report name, recipient email, format (Excel/PDF/CSV/Excel 2007), frequency (Daily/Weekly/BiWeekly/Monthly/Yearly), run-on time. Column selection lives in the **saved report definition** (not the schedule).

**Saved reports inventory (4 total, all Kyle Kriegel):**

| Saved Report | ID | Base Report | reportMenuID |
|---|---|---|---|
| Covu_Libertas policy BOB | 98960 | Policy_Master | 146 |
| CRM Sync - Policy Master | 112844 | Policy_Master | 146 |
| Full Policy Master | 112078 | Policy_Master | 146 |
| CRM Sync - Renewal Detail | 112846 | RetentionCenter_RenewalDetail | 57 |

**CRITICAL FINDING**: Policy_Master has ALL 73 available columns selected but **zero coverage columns** (Coverage A-E, deductibles, liability limits don't exist in this report type). Coverage data must come from other report types — likely Policy Management category (Policy Transaction Detail, Book of Business Detail, etc.).

**Report viewer does NOT display all rows** — the on-screen viewer shows a subset. To get the full dataset, download the report CSV using: `$find('WebReportViewer').exportReport('CSV')` in the ReportHost iframe. This is how the full 3,980-row export (823 active) was obtained.

**Reports API**: `GET /EZLynxReportsAPI/saved-report/v1/menu` returns saved reports + org metadata. Full report type catalog is NOT available via API — rendered server-side in ReportMenu HTML.

**Report viewer structure**: reportwrapper.aspx loads the actual report in an iframe (`iFrame1` → ReportHost.aspx). Manage Columns dialog is inside the iframe. Direct URLs work for saved reports: `reportwrapper.aspx?Report={name}&id={reportMenuID}&SavedReportId={id}&IsEditMode=true`

**Angular navigation challenge**: Catalog report cards use `ng-click='vm.runReport(savedReport.url)'` — doesn't change page URL. Opening NEW report types (without saved report instances) requires figuring out this navigation mechanism or having Kyle click manually.

**Priority next steps for coverage + document pipeline:**
1. **Build the EZLynx Policy Detail scraper** — iterate all 823 active policies, hit PolicyDisplayAndCompare, parse ACORD XML, write coverage fields to CRM. ~5-7 hours for initial backfill, then 10-30/day ongoing. See `ezlynx-operations` skill → `references/policy-coverage-pipeline.md`.
2. **Add coverage columns to CRM** — Supabase migration for `policy_coverages` table (one row per coverage line, keyed on `policy_id + coverage_code`) plus `coverage_last_scraped_at` on `policies`. Scraper writes directly via Supabase REST API — no new edge function needed. See `ezlynx-operations` skill → `references/coverage-gap-analysis.md` for architecture.
3. **Build ACORD document generator** — generate ACORD 80/25/28 PDFs from CRM data. One implementation serves all carriers.
4. **Carrier portal dec page scripts** — Allstate first (~32% of book), then Progressive, Nationwide, State Farm. Browserbase+Stagehand pattern from Foremost STAR template.
5. **Verify 7:30 AM reports actually deliver** — check 2factorlogins@gmail.com after 7:30 AM on next business day. Need refresh token for this inbox.

### Pitfalls

- **Don't classify carrier coverage from 1-2 samples** — the full scan proved that sampling is misleading. Allstate AUTO appeared "zero coverage" from 2 empty samples but most have rich BI data. Always run the full scan before drawing conclusions about a carrier's data availability.
- **Check for running processes before starting work** — before launching any long-running scraper or automation, check `ps aux | grep -i "ezlynx\|scraper\|pw_"` and check checkpoint files (`/tmp/ezlynx_phase0/full_scrape/full_scrape_checkpoint.json`). Kyle caught me building a duplicate scraper while one was already running in the background — context compaction can make you lose track of what's already in flight.
- **Kyle wants client names in reports** — when generating policy gap analyses or coverage tables, include `Account_Name` from the CSV so he can investigate individually. Not just counts — actual client names and policy numbers.
- **CSV `Source` column is unreliable** — "Download" means EZLynx received a download at some point, NOT that coverage data is flowing now. Allstate AUTO NAIC 29688 shows 38 "Download" policies but Kyle says these "likely aren't downloading at all." Verify by checking ACORD pages.

### Phase 0 Coverage Gap Analysis — COMPLETE (2026-05-21)

Full scan of ALL 823 active policies completed. Earlier sample-based estimates were wrong — always do a full scan, not samples.

| Group | HOME | AUTO | Total | Action |
|-------|------|------|-------|--------|
| FULL (standard ACORD codes, scrapable) | 495 | 72 | **569** (69%) | Run the scraper |
| CODES (carrier codes, no DWELL/BI) | 30 | 4 | **42** (5%) | Add Dwelling-section parser (Germania) |
| EMPTY (no coverage in EZLynx) | 101 | 80 | **208** (25%) | Carrier portal scripts or manual |
| Other (empty page / error) | 3 | 1 | 4 (<1%) | |
| **Total** | **629** | **157** | **823** | |

**Backfill status (2026-05-22): COMPLETE.** 600/611 policies written to `policy_coverages` table via direct DB (psycopg2). ~8,400 coverage rows. 11 policies had no matching CRM UUID.

**Key carrier specifics:**
- **Germania**: Home/liability on SEPARATE policies (billed together). Coverage A in Dwelling section as `Estimated Repl Cost Amount`, not in Coverage lines.
- **Allstate**: Full scan PROVED most Allstate AUTO has BI coverage (15-96 coverage lines). Earlier "Allstate AUTO = zero" was wrong — based on 1-2 empty samples. NAIC 29688 (auto code) "likely aren't downloading at all" per Kyle. Only ~15 of 206 Allstate policies are truly EMPTY.
- **Progressive AUTO**: Zero coverage now — download fix in progress should resolve.
- **Mercury, Foremost, Hippo, TX Fair Plan, NatLloyds, AmModern, HOA**: All EMPTY — need portal scripts.
- **Top EMPTY by count**: Progressive (72), Logic-Standard Casualty (22), Mercury (19), Foremost (18), Allstate (15).

Full details: `ezlynx-operations` skill → `references/coverage-gap-analysis.md`
Client-name table: `/tmp/ezlynx_phase0/coverage_gap_with_names.md`

### Supabase Coverage Writeback Architecture (decided 2026-05-21) — NOW LIVE

No new edge function needed. Coverage data flows via:
1. **SQL migration APPLIED**: `policy_coverages` table + `coverage_last_scraped_at` on `policies` + `upsert_policy_coverages()` RPC — all live in production
2. Scraper (runs on ROG with Chrome) writes directly to Supabase REST API or direct DB
3. Existing `ezlynx-ingest` edge function unchanged — it handles CSV data only
4. Ongoing: cron triggers coverage scraper after nightly CSV, only rescrapes policies where `ezlynx_last_synced_at > coverage_last_scraped_at`
5. **NO LONGER BLOCKED** — real Supabase keys provisioned, DB connection verified

## Daily Morning Sync Workflow

**See `libertas-daily-sync` skill for full pipeline details, pitfalls, and operational notes.**

**Script:** `~/.config/libertas/scripts/libertas_daily_sync.py` — runs the full morning pipeline with minimal API calls. Cron fires at 8:30 AM CT.

**Two phases:**
1. **CSV Ingest** — Pull CSVs from Gmail (1 token refresh + 1 search + 2-4 attachment downloads = ~6 API calls). Parse, diff against yesterday's snapshot (local — 0 API calls), write to staging via REST with `Prefer: resolution=merge-duplicates` header (2-3 batch calls), reassign staging rows to new run_id via direct DB (1 psycopg2 call), call `ezlynx_transform_run()` RPC (1 call). Save today's snapshot for tomorrow's diff.
2. **Coverage Scrape** — Query policies needing scrape with filter (1 API call). Run ACORD page scraper on Chrome (local — 0 Supabase calls until writes). Batch-write coverage rows via `upsert_policy_coverages` RPC.

**Total Supabase API calls per morning: ~12** (vs potentially hundreds without diffing).

**Usage:**
```bash
source ~/ezlynx-env/bin/activate
python3 ~/.config/libertas/scripts/libertas_daily_sync.py              # Full run
python3 ~/.config/libertas/scripts/libertas_daily_sync.py --dry-run    # Parse + diff only, no CRM writes
python3 ~/.config/libertas/scripts/libertas_daily_sync.py --full-scrape  # Force re-scrape all policies
```

**Phase 0 Backfill:** COMPLETED 2026-05-22. 600/611 policies written to `policy_coverages`, 0 failures. The `phase0_backfill.py` script at `~/.config/libertas/scripts/phase0_backfill.py` is the working reference implementation for ACORD page parsing + direct DB writes.

**Direct DB writes for coverage data The `upsert_policy_coverages` RPC function is BROKEN — it references `term_start`/`term_end` columns that don't exist in `policy_terms`. The real columns are `effective_date`/`expiration_date`. The backfill script uses **direct psycopg2 DB writes** via `SUPABASE_DB_URL` from `~/.config/libertas/credentials.env` instead of the broken RPC. The direct DB approach also avoids RLS issues (the service role keys in `.env.supabase` are abbreviated placeholders and can't bypass RLS, but the DB URL has the real password). Pattern:

```python
import psycopg2
conn = psycopg2.connect(env['SUPABASE_DB_URL'])  # from credentials.env
cur = conn.cursor()
# Insert policy_terms
cur.execute("""INSERT INTO policy_terms (policy_id, policy_number, effective_date, expiration_date, transaction_type, is_active)
               VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING id""", (...))
# Insert policy_coverages with policy_term_id FK
cur.execute("""INSERT INTO policy_coverages (policy_id, policy_term_id, coverage_code, coverage_description, ...)
               VALUES (%s, %s, %s, %s, ...) ON CONFLICT DO NOTHING""", (...))
conn.commit()
```

The REST API with the anon key gets `permission denied for table policy_coverages` (RLS blocks it). The service role key in `.env.supabase` is abbreviated and unusable. **Direct DB is the only working write path for coverage data.**

**ACORD parser technique (2026-05-21):** EZLynx PolicyDisplayAndCompare ACORD pages use tab-separated key-value pairs for coverage data. Each expanded coverage section has lines like:
```
Coverage Code\tDWELL
Coverage Description\tDwelling (Cov. A)
Format Integer Limit\t222000
Format Percent Deductible\t2
Deductible Type Code\tPC
Format Currency Amount Deductible\t2
Current Term Amount\t3289.00
```
Parse by locating `collapse` sections, then splitting each line on `\t`. The first `Format Integer Limit` is per-occurrence, the second (if present) is aggregate. Discounts/credits have no limit/deductible/premium fields — just `Coverage Code` and `Coverage Description`. Some coverages use `Deductible Type Code FL` (flat) vs `PC` (percentage); flat deductibles appear in `Format Currency Amount Deductible`.

**Prerequisites (all resolved):**
- Gmail refresh tokens for both inboxes in `~/.config/libertas/credentials.env` ✓ (also has Supabase keys)
- Chrome on port 9222 (for coverage scrape phase — EZLynx session must be active) ✓
- Supabase keys at `~/.config/libertas/credentials.env` and `~/libertas-crm/.env.supabase` ✓
- Playwright venv at `~/ezlynx-env` ✓

## References

- `references/supabase-access.md` — **START HERE for DB access** — connection details, REST API patterns, direct DB patterns, current DB state, key tables, RLS notes
- `references/supabase-rest-patterns.md` (in `libertas-daily-sync` skill) — proven code patterns for upsert, pagination, RPC calls, UUID casting, and the transform run_id flow
- `references/ezlynx-pipeline-architecture.md` — detailed pipeline architecture, transform field mappings, staging table schemas
- `references/ezlynx-browser-automation.md` — Playwright setup on ROG, login/2FA pattern, navigation notes, Cloudflare workaround
- `references/logic-portal-fields.md` — Logic Insurance / Standard Casualty EZ*Insure portal: **FULL field map for Customer Details + HO-A Quote Details (112 fields)**, iframe architecture (3-level nesting), tab/sub-tab navigation JS, city/county Space-press validation, Coverage A vs Replacement Value pitfall, renewal search, complete Playwright automation pattern with pitfalls
- See also: **ezlynx-operations** skill → `references/report-ids-and-api.md` — full saved report URLs, Reports API endpoint details, Angular scope structure, and confirmed 404 endpoints
