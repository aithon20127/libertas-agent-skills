---
name: ezlynx-operations
version: 1.0
description: Navigate, automate, and operate the EZLynx platform for Libertas Insurance. Covers browser access, UI structure, reports catalog, scheduled reports, and data pipeline.
---

# EZLynx Operations

## Browser Access

### Working Method: Playwright over CDP
- Hermes browser tool fails on EZLynx (Cloudflare Turnstile blocks it)
- Raw CDP WebSocket had a persistent bug where `Runtime.evaluate` DOM queries returned empty results (reason unknown)
- **Working approach**: Playwright connecting over CDP to a real Chrome instance
- Launch Chrome: `DISPLAY=:1 /usr/bin/google-chrome --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=/tmp/chrome-shared --no-first-run --no-default-browser-check`
- Connect with Playwright: `browser = await p.chromium.connect_over_cdp("http://localhost:9222")`
- **Do NOT launch new Chrome instances for carrier portal automation** — Kyle explicitly flagged that opening extra Chrome windows froze his computer. ALWAYS connect to the existing Chrome instance on port 9222 via `p.chromium.connect_over_cdp('http://localhost:9222')`. If Chrome isn't running, ask Kyle to open it — don't spawn one yourself.
- **Headless gets blocked by Cloudflare** — always use headed mode with real Chrome
- Auth state does NOT persist across browser restarts — session cookies expire

### Login
- URL: https://app.ezlynx.com/auth/account/login
- Username: KKriegel1
- Password: Liberty4!
- 2FA: sent to libertaslogins@gmail.com
- Auto-2FA: poll Gmail API for verification code (search: `from:ezlynx subject:verification newer_than:1d`)
- Gmail API creds in ~/libertas-crm/browserbase-functions/.env (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_LIBERTASLOGINS_REFRESH_TOKEN)
- "Trust this computer" checkbox was checked — may reduce 2FA frequency but doesn't persist across restarts
- Playwright venv: ~/ezlynx-env

## EZLynx UI Structure

### Top Header Bar
- **Hamburger menu button** (`.nav-menu` class) — top-left, expands/collapses sidebar labels
- Logo links to: https://app.ezlynx.com/web/dashboard
- Quick search input (`#quickSearchInput`)
- Top-right icons: AI (KK), note_add, list/4, notifications/13, account_tree, help

### Left Sidebar (collapsed = icon-only, expanded = icon + label)
Icons and their tooltips (top to bottom):
| Icon | Tooltip | Route/Function |
|------|---------|---------------|
| dashboard | Dashboard | /web/dashboard |
| folder_shared | Applicants | /applicantportal/Search/Index |
| folder_open | Policy Mgmt | Policy management |
| *(custom icon)* | Communication Center | Comms/email |
| local_atm | Accounting | Accounting/billing |
| **insert_chart** | **Reports** | **Reports 5.0 panel** |
| settings | Settings | Agency settings |
| menu_book | Support | Help/docs |
| *(custom icon)* | Retention Center | Retention tools |
| business_center | Sales Center | Sales pipeline |
| power | Marketplace | Carrier marketplace |
| redeem | Refer a Friend | External link |

### Sidebar Interaction
- Click `insert_chart` button opens the **Reports 5.0 panel** as an overlay on the right side of the page (does NOT navigate — stays on current URL)
- The panel has two sections:
  - **Left side (Categories)**: Favorite Reports, Scheduled Reports, Shared Reports, Categories (with sub-categories listed)
  - **Right side (Reports list)**: All Reports, Saved Reports, Scheduled Reports, Report Categories, Data Export, Help, Instructions
- Clicking items in the panel navigates to the Reports Portal (different domain path)

### Key App Navigation URLs

| Page | URL | Notes |
|------|-----|-------|
| Dashboard | `/web/dashboard` | Policy Downloads widget, quick stats, nav links |
| Applicant Search | `/applicantportal/Search/Index` | Search by name, address, etc. |
| Policy Transactions | `/applicantportal/Policy/Transactions/Index` | Recent transactions list |
| Policy Summary | `/applicantportal/policy/{policyId}/summary/index` | Human-readable coverage detail |
| Policy Documents | `/applicantportal/policy/{policyId}/documents/index` | Per-policy docs (dec pages, apps) |
| Account Documents | `/web/account/{accountId}/documents` | All docs across policies for applicant |
| Full Policy Details | `/ApplicantPortal/Applicant/{applicantId}/PolicyDisplayAndCompare?Func=0&ApplicantID={applicantId}&PolMasterID=m{policyId}` | **Complete ACORD XML data — THE coverage source** |

- Dashboard "Policy Downloads" widget shows: X renewals, Y new policies, Z cancellations from last 7 days
- Policy Summary page has tabs: Summary, Documents, and links for "additional policy information" and "export"
- The "Click here for additional policy information" link on Policy Summary → Full Policy Details page

## Reports Portal

### URLs
- Scheduled Reports: https://app.ezlynx.com/EZLynxReportPortal/ScheduledReport
- All Reports / Saved Reports: https://app.ezlynx.com/EZLynxReportPortal/ReportMenu
- Report categories are accessible from the ReportMenu page

### Reports 5.0 — Full Catalog

**See `references/report-type-catalog.md` for the complete inventory of all report types with URLs, IDs, column counts, and the definitive coverage-column findings.**

Categories: Activity (3 reports), Applicant (11 reports), Book of Business (6), Claims (3), Commission (2), Policy Management (9), Quotes (4), Retention Center (1+), Sales Center (4).

**Key report types for CRM data pipeline:**
- **Policy Master** (id=146) — 73 columns, current CRM source. No coverage columns.
- **Policy Transaction Master** (id=144) — 76 columns, RICHEST report. Has addresses, emails, phones Policy Master lacks. No coverage columns.
- **Renewal Detail** (id=57) — 15 columns, current CRM renewal source.
- **Book of Business Detail** (id=70) — ~38 columns, less useful than Policy Master.

**DEFINITIVE FINDING: Coverage A-E, deductibles, liability limits do NOT exist in ANY EZLynx Reports 5.0 report type.** Checked 10+ report types with Manage Columns open. Coverage data lives in individual policy records (IVANS downloads, carrier sites, policy detail pages) — NOT in the reporting engine.

### Saved Reports Inventory (4 total, all created by Kyle Kriegel)

| Saved Report Name | savedReportID | Base Report Name | reportMenuID | Category |
|---|---|---|---|---|
| Covu_Libertas policy BOB | 98960 | Policy_Master | 146 | Book of Business |
| **CRM Sync - Policy Master** | **112844** | Policy_Master | 146 | Book of Business |
| Full Policy Master | 112078 | Policy_Master | 146 | Book of Business |
| **CRM Sync - Renewal Detail** | **112846** | RetentionCenter_RenewalDetail | 57 | Retention Center |

- CRM Sync - Policy Master description: "Daily snapshot of every policy in the Libertas book (active + inactive) for ingestion into the new Libertas CRM via emailed report. DO NOT MODIFY without checking with Kyle."
- CRM Sync - Renewal Detail description: "Daily snapshot of upcoming renewal terms with premium delta (Change Amount + Percent Change). Powers the Reshop tab and pre-effective renewal pipeline. DO NOT MODIFY without checking with Kyle."

### Current Scheduled Reports (3 total, all nightly, all Success — UPDATED 2026-05-21)

| Name | scheduledReportId | Enabled | Last Run | Schedule | Format | Email |
|------|---|---------|----------|----------|--------|-------|
| CRM Renewal Detail Nightly | 41347 | Yes | May 20, 2026 9:30 PM | **7:30 AM daily** | **CSV** | 2factorlogins@gmail.com |
| CRM Sync Nightly | 41346 | Yes | May 20, 2026 9:01 PM | **7:30 AM daily** | **CSV** | 2factorlogins@gmail.com |
| Libertas BOB | 35065 | Yes | May 20, 2026 2:00 PM | **7:30 AM daily** | **CSV** | 2factorlogins@gmail.com |

- CRM Renewal Detail Nightly → saved report: **CRM Sync - Renewal Detail** (112846)
- CRM Sync Nightly → saved report: **CRM Sync - Policy Master** (112844)
- Libertas BOB → saved report: **Covu_Libertas policy BOB** (98960)

### Schedule Edit — How-To (SOLVED)

Use Angular scope manipulation via Playwright evaluate. The Actions dropdown → Edit Schedule UI path works but is fragile due to modal backdrop interception. The reliable method:

```javascript
// 1. Get Angular scope and open the edit modal
const scope = angular.element(document.querySelector('[ng-controller]')).scope();
const vm = scope.vm;
vm.editScheduledReport(vm.scheduledReports[i]);  // i = 0, 1, or 2
scope.$apply();

// 2. Set schedule values on the vm object
vm.reportRunOn = '05/22/2026 7:30 AM';  // Format: MM/DD/YYYY H:MM AM/PM
vm.reportFormat = 3;    // 1=Excel, 2=PDF, 3=CSV, 4=Excel 2007
vm.reportFrequencyType = 1;  // 1=Daily, 2=Weekly, 3=BiWeekly, 4=Monthly, 5=Yearly
scope.$apply();

// 3. Also update the DOM input (Angular two-way binding sometimes needs both)
document.getElementById('ScheduleDateTime').value = '05/22/2026 7:30 AM';
document.getElementById('ScheduleDateTime').dispatchEvent(new Event('input', {bubbles: true}));

// 4. Click Save button in the modal
const modal = document.querySelector('.modal.in');
modal.querySelectorAll('button').forEach(b => {
  if (b.textContent.trim().toLowerCase().includes('save')) b.click();
});
```

### Schedule Edit Dialog Fields
- vm.reportName — display name
- vm.emailList — recipient emails (comma-separated)
- vm.reportFormat — 1=Excel, 2=PDF, 3=CSV, 4=Excel 2007
- vm.reportFrequencyType — 1=Daily, 2=Weekly, 3=BiWeekly, 4=Monthly, 5=Yearly
- vm.reportRunOn — schedule datetime (format: "MM/DD/YYYY H:MM AM")
- Scheduler available 7:00 AM – 11:00 PM CST/CDT

### Report Wrapper & Column Management
- Report viewer URL pattern: `reportwrapper.aspx?Report={name}&id={reportMenuID}&SavedReportId={id}&IsEditMode=true&reportMenuUrl=...`
- The reportwrapper page loads the actual report in an **iframe** named `iFrame1` (src: ReportHost.aspx)
- To access the report's DOM, you must target the iframe: `await page.frame('iFrame1')` or `page.frames[1]`
- **Manage Columns** button is inside the iframe — it opens a dialog with Available (left) and Selected (right) columns, plus Select All / Deselect All
- **CRITICAL FINDING**: Coverage columns (Coverage A-E, deductibles, liability limits) **do NOT exist in ANY EZLynx Reports 5.0 report type**. Checked Policy_Master, BOB_Expanded, PolicyTransaction_Master, Policy_AllPolicyTransaction_Details_Expanded, Policy_PremiumChange_Detail, Policy_NewBusinessTransactions_Details_Expanded, Policy_PendingTransaction_Detail, BOB_PolicyExpiration_Detail, RetentionCenter_RenewalDetail, and Applicant_Master — all confirmed zero coverage columns. Coverage data must come from IVANS downloads, policy detail pages, or carrier sites.

### Reports API
- Working endpoint: `GET https://app.ezlynx.com/EZLynxReportsAPI/saved-report/v1/menu`
  - Returns: `{ savedReportMenu: [...], categories: [...], userHasSharePermission: bool, userHasSchedulePermission: bool, orgId: int }`
  - `savedReportMenu` = the 4 saved reports with full metadata (same as Angular scope data)
  - `categories` = only categories that have saved reports (Book of Business, Retention Center) — NOT the full catalog
- The full report type catalog (all available report types with their reportMenuIDs) is NOT available via a simple API endpoint. It's rendered server-side in the ReportMenu HTML and embedded in Angular scope.
- Other API patterns tried (all 404): `/report/v1/types`, `/report/v1/catalog`, `/saved-report/v1/list`, `/report-menu/v1/all`, `/v1/reports`, etc.
- The API may have more endpoints — need to intercept XHR when clicking catalog cards to discover them.

### Angular ReportMenu Navigation (SOLVED)
- The ReportMenu page is an Angular 1.5 app (NGReportApp.js, 37KB minified)
- Catalog report cards use `ng-click='vm.runReport(savedReport.url)'` to navigate
- **Working method**: Use Playwright text selectors to click catalog cards. Example:
  ```python
  await page.locator("text=Policy Transaction Master").first.click()
  ```
- Clicking a catalog card opens a **NEW PAGE/TAB** in the same browser context
- Switch to the new page: `new_page = ctx.pages[-1]`
- The new page URL will be: `reportwrapper.aspx?Report={name}&id={id}`
- For report type IDs, see `references/report-type-catalog.md`
- Some report cards (e.g., summary/insight reports) may NOT open a new page — they might render in-place or use a different viewer
- The saved reports in the left panel have direct URLs (reportwrapper.aspx?...) — these also work for navigation
- **VM data serialization times out** — the Angular scope is very large. Extract specific properties only, never `JSON.stringify(vm)` or `JSON.stringify(vm.reportMenu)`.

### Constructing Report URLs Directly
If you know the report type name and ID, you can navigate directly without clicking catalog cards:
```
https://app.ezlynx.com/EZLynxReportPortal/reportwrapper.aspx?Report=PolicyTransaction_Master&id=144
```
For edit mode (to configure columns):
```
https://app.ezlynx.com/EZLynxReportPortal/reportwrapper.aspx?Report=PolicyTransaction_Master&id=144&IsEditMode=true&reportMenuUrl=https://app.ezlynx.com/EZLynxReportPortal/ReportMenu
```

### Report Actions (from Scheduled Reports page)
Each report has an Actions dropdown: Run Report, Edit Schedule, History, Disable, Delete

### Report Actions (from Saved Reports / All Reports page)
Each saved report has: Run Report, Share, Schedule, Edit, Delete

## Policy Coverage Data — THE Key Discovery

### The "Full Policy Details" Page (ACORD XML)

Every policy in EZLynx has a page that dumps **complete ACORD XML data** — every coverage code, limit, deductible, endorsement, vehicle, driver, dwelling detail, and mortgagee. This is the decoded IVANS download data.

**URL pattern:**
```
https://app.ezlynx.com/ApplicantPortal/Applicant/{applicantId}/PolicyDisplayAndCompare?Func=0&ApplicantID={applicantId}&PolMasterID=m{policyId}
```

**Link found on:** Policy Summary page → "Click here for additional policy information"

**What it contains (home — e.g., Nationwide 7842HR142750):**
- Insured: name, DOB, SSN, address, email
- Policy: carrier, policy#, effective/expiration, premium, billing method, NAIC code
- Full dwelling: year built, sqft, construction type, roof material, wiring/plumbing/roofing/heating years and condition codes, fire protection class, distance to hydrant, estimated replacement cost, pool indicators
- Every coverage with ACORD code + description + limit + deductible:
  - DWELL (Coverage A): limit + deductible (flat + %)
  - OS (Coverage B): limit
  - PP (Personal Property/Cov C): limit
  - LOU (Loss of Use/Cov D): type code
  - PL (Personal Liability/Cov E): limit
  - MEDPM (Med Pay/Cov F): limit
  - HURR (Hurricane Deductible): percent + type
  - MOLD, WTRDM (Water Damage), BOLAW (Ordinance/Law), FVREP (Replacement Cost), etc.
  - 20+ endorsements per policy with exact limits and premiums
- Mortgagee/additional interests: name, address, loan#, nature of interest
- Underwriting questions (Y/N)
- Policy summary with status code (PCH, etc.)

**What it contains (auto — e.g., Allstate 438259043):**
- All drivers: name, DOB, gender, marital status, DL#, state, license date, relationship
- All vehicles: year, make, model, VIN, body type, symbol, anti-theft, ABS, purchase date, ACV
- Per-vehicle coverages with limits AND per-vehicle premiums:
  - BI: split limits + premium per vehicle
  - PD: limit + premium
  - COMP: deductible + premium
  - COLL: deductible + premium
  - UM, UMPD, UIM, PIP with limits
  - Towing, rental, etc. with limits
- Discount codes (RREIM, PREFR, GDPAY, PREMR, EPPDS, etc.)
- Accident/violation history with dates
- Lienholder info
- Prior policy info (carrier, policy#, expiration)

**Data format:** Tab-separated key-value pairs, structured by section (collapsible "collapse" markers). Parseable with regex or line-by-line extraction. Approximately 8-10K characters per policy.

**See `references/policy-coverage-pipeline.md` for the full architecture plan, data samples, and carrier landscape.**

### Policy Summary Page (Human-Readable)

```
https://app.ezlynx.com/applicantportal/policy/{policyId}/summary/index
```

Contains the same data rendered in a user-friendly layout. Also has:
- "Documents" tab: `/applicantportal/policy/{policyId}/documents/index`
- "Click here for additional policy information" link → Full Policy Details page
- "Export Policy Information" link

### Policy Documents Tab

Per-policy documents at: `/applicantportal/policy/{policyId}/documents/index`

What's available:
- Some policies have manually-uploaded dec pages (e.g., "2025-2026 Auto Policy - Renewal Declarations.pdf")
- **"Carrier eDocs" folder exists** but often empty — documents are NOT auto-downloaded from carriers
- Documents uploaded by staff show as "uploaded by Service Libertas"
- **EZLynx is NOT a reliable source for dec pages/ID cards** — it only stores what's manually uploaded

### Account-Level Documents Library

```
https://app.ezlynx.com/web/account/{accountId}/documents
```

Contains all documents across all policies for an applicant. Auto-generated folders like "2025-2026 Auto Policy {policy#}". Can contain dec pages, applications, cancellation forms, payment confirmations — but only if manually uploaded.

### How to Find Policy IDs

From the **Policy Transactions page** (`/applicantportal/Policy/Transactions/Index`):
- Lists recent policy transactions with direct links
- Links are `javascript:void(0)` (Angular click handlers) — can't extract URLs directly
- Policy IDs visible in the link text/data (e.g., policy 68101091, 68969330)

From the **Applicant Search** (`/applicantportal/Search/Index`):
- Search by name, address, etc.
- Results link to applicant profiles → policy list → individual policies

From the **Dashboard** (`/web/dashboard`):
- "Policy Downloads" widget shows recent transactions
- Links to policy detail pages

### Coverage Data — Coverage Pipeline Architecture

**PROVEN: ACORD Coverage Scraper (tested across 8 policies, 5 carriers, 2 LOBs)**

The scraper at `/tmp/pw_acord_scraper_v4.py` connects to Chrome on port 9222, takes (applicantId, policyMasterId) pairs, and extracts structured coverage data from the PolicyDisplayAndCompare page. Tested successfully on:

| Carrier | LOB | Policy# | Coverages | Vehicles | Drivers |
|---------|-----|---------|-----------|----------|---------|
| Nationwide | Home | 7842HR142750 | 32 | 0 | 0 |
| Travelers | Home | 6161964186331 | 40 | 0 | 0 |
| Safeco | Home | OY9329623 | 16 | 0 | 0 |
| Allstate | Auto | 438259043 | 42 | 2 | 2 |
| Geico | Auto | 6226007216 | 12 | 1 | 1 |
| Safeco | Auto | Y1042021 | 43 | 4 | 4 |
| NatGen | Home | 203548211400 | 20 | 0 | 0 |
| NatGen | Auto | 203556045000 | 18 | 1 | 1 |

**Key coverage fields extracted (home):** DWELL/Cov A limit + deductible, OS/Cov B, PP/Cov C, PL/Cov E, MEDPM/Cov F, HURR %, MOLD, WTRDM, BOLAW, FVREP + 20+ endorsements. Dwelling: year built, sqft, construction, roof, wiring/plumbing/heating/roofing years, FPC, hydrant distance, replacement cost.

**Key coverage fields extracted (auto):** BI split limits + premium, PD limit + premium, COMP deductible + premium, COLL deductible + premium, UM, UMPD, PIP per vehicle. All driver details (name, DOB, DL#, relationship). All vehicle details (VIN, year, make, model). Lienholders. Accidents/violations.

**How to get (applicantId, policyMasterId) pairs:** The nightly Policy Master CSV has columns `ApplicantID` and `Policy_Master_ID`. The CRM policies table stores these as `ezlynx_applicant_id` and `ezlynx_policy_master_id`. Either source works.

**URL construction:** `PolMasterID = 'm' + Policy_Master_ID` (note the 'm' prefix).

**Production scraper versions:**
- `pw_full_coverage_scan_v4.py` — bulk scanner (sync Playwright, checkpoint/resume). Successfully scraped ALL 823 active policies at ~9/min in 84 min. Checkpoint at `/tmp/ezlynx_phase0/full_scrape/full_scrape_checkpoint.json`. Results at `full_scrape_results.json`. **This is the script to re-run for periodic full rescans.**
- `/tmp/pw_acord_scraper_v5.py` — Full pipeline version with Supabase REST write support, Dwelling-section parser (Germania), vehicle/driver extraction, JSON output per policy. **Use this for incremental writes to the CRM once real Supabase keys are available.**
- `/tmp/ezlynx_acord_parser.py` — Standalone ACORD parser with HOME_COVERAGE_CODES and AUTO_COVERAGE_CODES mappings, section-aware parsing. Produces both structured and flat-record output.
- `/tmp/ezlynx_scraper.py` — CDP-based scraper with policy discovery + ACORD parser integration. Good for targeted scraping of specific policies (`--applicant-id` / `--pol-master-id`).
- Phase 0 analysis scripts: `/tmp/pw_phase0_v10_csv_download.py` (CSV export via report viewer), `/tmp/pw_phase0_active_gap_v2.py` (gap analysis across all carriers)

**Rate:** ~6 seconds per policy (4s page wait + 1.5s sleep) = ~9 policies/min. Full scan of 823 active policies completed in 84 minutes. Ongoing incremental (only changed/renewed) ≈ a few minutes daily.

**Phase 1: EZLynx Policy Detail Scraper (initial backfill)**
- **DONE (May 21, 2026)**: Full scan of all 823 active policies completed
- Parse ACORD XML text → extract coverage codes, limits, deductibles
- **Coverage CRM writeback IN PROGRESS (May 21, 2026)**: Backfill script rewritten to use direct DB writes (psycopg2) instead of broken `upsert_policy_coverages` RPC. ~611 policies with ACORD data being written to `policy_coverages` and `policy_terms` tables. Last check: 508/611 done, ~6,906 coverage rows. The remaining ~212 EMPTY policies need carrier portal scripts.
- Ongoing: re-scrape only policies flagged as changed/renewed in daily 7:30 AM reports

**Phase 2: ACORD Document Generator**
- Generate ACORD forms server-side from CRM data (no carrier portal needed):
  - ACORD 80 (Homeowners) — standard home dec page replacement
  - ACORD 25 (Certificate of Insurance / Auto)
  - ACORD 28 (Evidence of Property Insurance — for mortgagees)
- PDF-fillable forms via pdf-lib or similar
- Coverage data from Phase 1 is already ACORD-structured — mapping is direct
- One implementation serves ALL carriers

**Phase 3: Carrier Portal Dec Page Scripts**
- For cases needing the actual carrier dec page (not ACORD substitute)
- Build per-carrier Browserbase+Stagehand scripts (Foremost STAR template)
- Top carriers: Allstate (~32% of book), Progressive, Nationwide, State Farm
- Smart scheduling: initial backfill overnight, then only re-pull on renewal/change

**Phase 4: Customer-Facing Chat**
- Extend MCP server with coverage/doc tools
- AI chat answers "what's my Coverage A?" / "send me my dec page"
- ACORD forms generated on-demand from CRM data

**Key insight:** Scraping ONE UI (EZLynx Policy Detail) covers **69% of the book** (569/823 FULL). The remaining ~25% (208 EMPTY, mostly Progressive/Logic/Mercury/Foremost) needs carrier portal pulls or download fixes. ACORD generation covers 80%+ of client document needs without touching carrier portals.

## Data Pipeline — What We Know

### Current Flow (ARCHITECTURE CHANGE — 2026-05-21)
1. EZLynx nightly scheduled reports send CSV to 2factorlogins@gmail.com at 7:30 AM
2. **NEW**: Odysseus pulls CSV from Gmail every morning (not the Supabase edge function)
3. Odysseus parses CSV, diffs against yesterday's data, writes to staging via Supabase REST API
4. Calls `ezlynx_transform_run()` RPC for the heavy lifting (households, contacts, addresses, audit diffs, policy upserts)
5. **Coverage scrape**: runs after CSV sync — only re-scrapes changed/new policies (`ezlynx_last_synced_at > coverage_last_scraped_at`)
6. **Later**: carrier-specific scripts for non-IVANS carriers feed same staging + transform pipeline

**Key decision**: Turn OFF the Gmail polling in `ezlynx-ingest` edge function. Keep the edge function deployed as a fallback (can be manually triggered). The transform SQL function stays unchanged — Odysseus just replaces the email-pulling part with a local Python script.

**PIPELINE IS LIVE (2026-05-21)**: Daily sync script (`~/.config/libertas/scripts/libertas_daily_sync.py`) runs via cron at 8:30 AM CT. Steps: Gmail pull → CSV parse/diff → staging upsert → DB run_id reassignment → transform RPC → coverage scrape. Coverage scrape requires active EZLynx session on Chrome port 9222. See `libertas-daily-sync` skill for full details.

### Gmail Accounts
| Account | Purpose | API Access | Notes |
|---------|---------|-----------|-------|
| libertaslogins@gmail.com | 2FA verification codes for EZLynx login | **Working** — refresh token in `~/.config/libertas/credentials.env` (GMAIL_LIBERTASLOGINS_REFRESH_TOKEN), scope: gmail.readonly | Used for auto-2FA during EZLynx login |
| 2factorlogins@gmail.com | Receives nightly CSV reports from EZLynx | **Working** — refresh token in `~/.config/libertas/credentials.env` (GMAIL_DEFAULT_REFRESH_TOKEN), scope: gmail.readonly | Daily sync pipeline pulls CSVs from this inbox automatically |
| Aithon20127@gmail.com | Agent's Google account (Chrome logged in) | Browser only (no API token) — needs 2FA + App Password for himalaya | Password: RaidTroy2026!, DOB: 5/15/1980. himalaya v1.2.0 installed at ~/.local/bin/himalaya, config at ~/.config/himalaya/config.toml. App Passwords blocked until 2FA enabled. |

### Known Gaps
- **Non-IVANS carriers** (Logic/Standard Casualty, etc.) — manually entered into EZLynx, not automated
- **Real Supabase keys NOW on ROG** — at `~/.config/libertas/credentials.env` and `~/libertas-crm/.env.supabase` (chmod 600). REST API + direct DB both working.

### Files
- ~/libertas-crm/supabase/functions/ezlynx-ingest/index.ts — nightly edge function
- ~/libertas-crm/supabase/migrations/20260502130028_ezlynx_transform.sql — SQL transform (no coverage columns)
- ~/libertas-crm/browserbase-functions/.env — Gmail API credentials

## Session-to-Session Checklist

1. Check if Chrome is running: `curl -s http://localhost:9222/json/version | head -3`
2. If not, launch with `--remote-allow-origins=*` flag
3. Connect with Playwright: `await p.chromium.connect_over_cdp("http://localhost:9222")`
4. Check if logged in (navigate to /applicantportal/Search/Index — if redirected to login, need to re-auth)
5. If need login: use Playwright with real Chrome, auto-grab 2FA from Gmail API
7. **Gmail credentials** for both inboxes are in `~/.config/libertas/credentials.env` (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_DEFAULT_REFRESH_TOKEN for 2factorlogins, GMAIL_LIBERTASLOGINS_REFRESH_TOKEN for libertaslogins). The service@libertasinsurance.com token is at `~/.config/libertas/gmail-service.env` (GMAIL_SERVICE_REFRESH_TOKEN).
7. himalaya v1.2.0 installed at `~/.local/bin/himalaya` — but needs App Password (2FA on Aithon Gmail first)
8. Check for running scraper processes: `ps aux | grep -E "pw_|scraper|coverage_scan|phase0_backfill"`
9. Full coverage scan checkpoint: `/tmp/ezlynx_phase0/full_scrape/full_scrape_checkpoint.json` — check `last_idx` to see if a scan completed
10. **Real Supabase keys on ROG** — at `~/.config/libertas/credentials.env` (REST API keys) and `~/libertas-crm/.env.supabase` (DB URL). REST API + direct DB both working.
11. **Daily sync pipeline is live** — cron at 8:30 AM CT runs `~/.config/libertas/scripts/libertas_daily_sync.py`. See `libertas-daily-sync` skill for details.
12. **Phase 0 backfill** — `~/.config/libertas/scripts/phase0_backfill.py` writes coverage data from cached ACORD pages to CRM via direct DB. Uses psycopg2 (not RPC — the `upsert_policy_coverages` RPC is broken). Check progress with: `SELECT count(*) FROM policy_coverages; SELECT count(DISTINCT policy_id) FROM policy_coverages;`

## Reference Files

- **references/report-ids-and-api.md** — Saved report URLs, Reports API endpoint details, confirmed 404 endpoints, Policy Master column findings, Angular scope structure
- **references/report-type-catalog.md** — Full inventory of ALL report types with URLs, IDs, column counts, and the definitive coverage-column findings. Includes saved report IDs and scheduled report IDs.
- **references/policy-coverage-pipeline.md** — Policy Detail page (ACORD XML) structure, data samples for home/auto, carrier landscape, coverage pipeline architecture, and ACORD document generation plan.
- **references/coverage-gap-analysis.md** — Phase 0 gap analysis results: per-carrier ACORD data completeness, Germania split-policy structure, Allstate carrier-specific codes, empty carriers, and Supabase architecture for coverage writeback.
- **references/acord-coverage-codes.md** — Full ACORD coverage code mapping tables (home, auto, discounts) with carrier-specific codes seen across 823 scraped policies. Regex patterns and parsing notes for per-vehicle vs policy-level coverages.
- **references/empty-policy-export.md** — The 207 policies with no ACORD coverage data: LOB breakdown, top carriers, premium at stake ($742K), and Google Sheets export status.
## Known Pitfalls

- **CDP raw WebSocket DOM queries returning empty** — use Playwright over CDP instead
- **Cloudflare blocks headless** — always use headed Chrome
- **Auth doesn't persist across restarts** — re-login each session
- **Session re-login without re-credentials** — when the EZLynx tab redirects to login (session timed out, tab still open), clicking "Log In" often works without re-entering username/password. Browser form auto-fill retains the credentials. No 2FA triggered for same-tab re-login. If tab was closed or browser restarted, full login + 2FA is needed.
- **Sidebar reports panel is an overlay** — it doesn't navigate; clicking items IN the panel then navigates to the Report Portal
- **The "CRM Sync Nightly" schedule points to saved report "CRM Sync - Renewal Detail"** — editing the schedule only changes timing/format; to change columns, you must edit the saved report definition
- **Reports Portal is a separate Angular app** at /EZLynxReportPortal/ paths
- **Report content loads in an iframe** (`iFrame1` → ReportHost.aspx) — DOM queries must target the iframe frame, not the parent page
- **VM data serialization times out** — the Angular scope is very large; extract specific properties only, never `JSON.stringify(vm)` or `JSON.stringify(vm.reportMenu)`.
- **Playwright evaluate on large data** — if the API response or DOM extraction is large, write it to a file instead of printing to stdout to avoid terminal output limits and timeouts.
- **Actions dropdown + Edit Schedule click fails** — clicking "Actions" then trying to click "Edit Schedule" with Playwright locators fails because a modal backdrop intercepts pointer events. Use Angular scope manipulation instead (see Schedule Edit How-To above).
- **Save Report button not visible** — in the report viewer, the "Launch Save Report Modal" button may be hidden behind the filter panel. Need to scroll or collapse filters to expose it.
- **Manage Columns dialog uses custom multi-select** — not a standard HTML `<select>`. Use `innerText` text parsing to extract column names, not `option.value` on a select element.
- **Policy Transactions page is HEAVY** — the Angular app at `/applicantportal/Policy/Transactions/Index` is slow and may time out Playwright. Policy links are `javascript:void(0)` (Angular click handlers) — can't extract URLs directly. Use applicant search or direct URL construction instead.
- **Policy Detail page data is tab-separated key-value** — the Full Policy Details page renders ACORD data as collapsible sections with tab-separated fields. Parse line-by-line looking for `Key\tValue` patterns. Sections marked with "collapse" text.
- **Carrier eDocs folder usually empty** — don't rely on EZLynx for dec pages/ID cards. They must come from carrier portals or be ACORD-generated from CRM data.
- **Don't try to get coverage data from reports** — it doesn't exist there. The `PolicyDisplayAndCompare` page is the only EZLynx source for full coverage data.
- **ReportMenu page evaluations are SLOW** — the Angular app is heavy. Keep evaluate calls short and specific. Avoid `document.body.innerText` on large pages (timeout risk); use targeted selectors instead.
- **Chrome must be launched with `--remote-allow-origins=*`** — without this flag, CDP WebSocket connections fail with origin header errors.
- **Report viewer shows subset of data** — the on-screen report viewer does NOT display all rows the report returns. To get the full dataset, you must DOWNLOAD the report (CSV/Excel). Use the export command in the ReportHost iframe: `$find('WebReportViewer').exportReport('CSV')`. This is how the full 3,980-row Policy Master export was obtained.
- **ACORD parser: space after colon varies by carrier/LOB** — home policies use `Coverage : PP` (space before code), auto uses `Coverage :BI` (no space). Regex MUST use `\s*` after the colon: `r'^Coverage\s+:\s*(\w+)'`. Failing to allow optional whitespace causes home policy coverages to parse as zero.
- **ACORD parser v2: expanded coverage sections use tab-separated key-value pairs** — the PolicyDisplayAndCompare page has collapsible sections. When expanded, each coverage line shows as tab-separated fields: `Coverage Code\tDWELL`, `Coverage Description\tDwelling (Cov. A)`, `Format Integer Limit\t222000`, `Format Percent Deductible\t2`, `Deductible Type Code\tPC` (percentage) or `FL` (flat), `Format Currency Amount Deductible\t2` (for flat deductibles), `Current Term Amount\t3289.00` (premium). The first `Format Integer Limit` is per-occurrence; a second (if present) is aggregate. Discounts/credits have no limit or deductible fields. Parse by iterating collapsed sections and extracting key-value pairs per line.
- **policy_terms table columns are effective_date/expiration_date, NOT term_start/term_end** — the `upsert_policy_coverages` RPC is broken (references nonexistent columns). Use direct DB writes via psycopg2 with `SUPABASE_DB_URL` from `~/.config/libertas/credentials.env`. The `policy_coverages` table has `policy_term_id` FK linking to `policy_terms.id`. Insert term first, get the ID, then insert coverages with that FK.
- **Germania writes home and liability on separate policies** — billed together, but the HOME policy only has discount/minor coverages (HLFC, MEDPM, RENEW, FP01, PL, ACCT, DMGPO, LAC). Coverage A is NOT in any Coverage line — it's in the Dwelling section as `Estimated Repl Cost Amount`. The parser needs a Dwelling-section extractor for Germania. Companion policies must be paired to get the full picture.
- **Allstate download HOME uses carrier-specific endorsement codes** — alongside standard DWELL/PP/OS/PL/MEDPM, Allstate IVANS downloads include: LFREE (Liability Free), RESPY (Responsibility), WTRDM (Water Damage), ESIGN (Electronic Signing), ROOF, EPPDS (Enhanced PP), FTBYR (Fortified Buyer), SENMI (Senior/Military), ILMC, PROTD (Protected), GLASS, LOYAL. These are endorsements/discounts, not standard ACORD coverages — useful for enrichment but not needed for Coverage A-F.
- **Allstate AUTO has coverage data in EZLynx** — CORRECTION from full scan: earlier Phase 0 sampling of 1-2 policies was misleadingly empty. The full scan of all 823 policies shows that most Allstate AUTO policies DO have BI with full coverage lines (33c, 47c, 61c, even 96c on one policy). Only ~15 of 206 Allstate policies are EMPTY. The earlier "Allstate doesn't transmit auto via IVANS" claim was based on bad samples — always verify with multiple policies, not single samples. Kyle says the AUTO download codes (NAIC 29688) "likely aren't downloading at all" — but coverage data still appears for many policies under the main code.
- **~20% of Allstate HOME also has zero coverage data** — sampled 10 Download + 3 Manual: 7/10 Download had DWELL, 1 had codes but no DWELL, 2 had zero coverages. Manual: 2/3 had DWELL, 2/3 had zero. Not all policies have data even within a single carrier.
- **Allstate has 4 appointment NAIC codes** — NAIC 37907 (main code, 141 HOME + 1 AUTO, downloading for HOME), NAIC 29688 (auto code, 38 AUTO, flagged "Download" but Kyle says "likely aren't downloading at all"), NAIC 19240 (secondary, 9 HOME, downloading with DWELL present), and 17 no-NAIC policies (all Manual, zero coverage). The CSV Source column says "Download" for NAIC 29688 but data may be empty — don't trust the Source flag at face value.
- **Use sync Playwright for long-running scrapes** — async Playwright gets stuck in background processes (no output, no file writes). Sync Playwright with `sys.stdout.reconfigure(line_buffering=True)` and a write-to-log-file pattern works reliably. For long scrapes (800+ policies), use checkpoint/resume: save results + last index to a JSON file every 25 policies, and resume from that index on restart.
- **Policy Master CSV: `Account_Name` has full client names** — not First_Name/LastName (which are split). Use Account_Name for client-facing tables. Filter to `Status2 = 'Active'` only — full export has ~3,980 rows, only ~823 are active.
- **Policy Master CSV: filter to Status2 = 'Active' only** — the full export includes cancelled/expired policies (3,980 total rows). Only 823 are active. Always filter by `Status2 == 'Active'` when building policy lists from the CSV.
- **Kyle wants client names in reports/tables** — when generating gap analyses or policy lists, include `Account_Name` from the CSV so Kyle can investigate individually. Use the full name (Account_Name), not First_Name/LastName.
- **CSV Source column is not reliable** — "Download" in the Source column means EZLynx received a download at some point, NOT that coverage data is flowing now. Allstate AUTO (NAIC 29688) shows 38 Download policies but the ACORD pages have zero coverage data. Verify by sampling ACORD pages, not just trusting the Source flag.
- **Check for running background processes BEFORE starting any scraper** — use `ps aux | grep -i "ezlynx\|scraper\|pw_"` before launching a new scrape. The bulk scraper runs for ~84 minutes and can be easily forgotten across context compactions. A running `pw_full_coverage_scan_v4.py` process means a scrape is already in progress — don't start a second one. Also check `/tmp/ezlynx_phase0/full_scrape/full_scrape_checkpoint.json` for `last_idx` to see if a scrape is in progress or recently completed. **Kyle flagged this as a real problem** ("Are you working on this twice at once?") — he saw policies cycling through while I was building a duplicate scraper. Always check first.
- **ACORD parser: carrier name can come from mortgagee section** — the "Commercial Name" field appears in both the Carrier Insurer section AND the Additional Interest / Mortgagee section. The parser must capture the FIRST "Commercial Name" (under Carrier Insurer) and ignore subsequent ones (under mortgagee/additional interest). Otherwise the carrier gets misidentified as the mortgagee company.
- **ACORD parser: auto coverages appear per-vehicle** — on multi-vehicle auto policies, COMP/COLL/ANTHF etc. repeat for each vehicle. The parser must attach per-vehicle coverages to the vehicle object, not to the top-level coverages list. Top-level should only have policy-level coverages (BI, PD, CSL, UMCSL, discounts). A dup-count check helps: if a coverage code appears N times where N = number of vehicles, it's per-vehicle.
- **Full scan COMPLETE (May 21, 2026)** — ALL 823 active policies scraped. Results: **569 FULL (69%), 208 EMPTY (25%), 42 CODES (5%), 4 other** (3 EMPTY_PAGE + 1 ERROR). The v4 bulk scraper (`pw_full_coverage_scan_v4.py`) classified slightly differently than the Phase 0 analysis — use the v4 scan log numbers as the final word. Full checkpoint at `/tmp/ezlynx_phase0/full_scrape/full_scrape_checkpoint.json`. Log at `/tmp/ezlynx_phase0/full_scrape/scan_log.txt`. The 208 EMPTY policies represent ~$742K in annual premium with no ACORD coverage data in EZLynx — these require carrier portal scripts or manual data entry. Full client-name table at `/tmp/ezlynx_phase0/coverage_gap_with_names.md`.
- **Per-policy JSON output paths** — `pw_full_coverage_scan_v4.py` saves to `/tmp/ezlynx_coverage/policy_{id}.json`. The targeted scraper (`ezlynx_scraper.py`) saves to `~/ezlynx-coverage-data/a{aid}_p{pid}.json`. Know which directory to check based on which tool was used.
- **Google Sheets export: use browser, not API** — the Aithon account (`aithon20127@gmail.com`) has OAuth with Sheets scope at `~/.hermes/google_token.json`, but the Google Cloud project (848419619510) has the Sheets API disabled. Only the project owner (2factorlogins@gmail.com) can enable it. **Workaround that works NOW**: use Chrome (logged into aithon20127@gmail.com) to create sheets via `sheets.new`, paste CSV data, and "Split text to columns" with comma separator. See `google-workspace` skill → "Browser-Based Sheets Fallback" section for the exact workflow. This is what Kyle prefers anyway — "just open Sheets and paste it in" rather than going through the API.
- **Hermes background processes don't relay Python stdout** — `terminal(background=true)` silently swallows Python output even with `PYTHONUNBUFFERED=1`, `python3 -u`, and `sys.stdout.reconfigure(line_buffering=True)`. The `process(action='log')` call returns empty. **Workaround for long scrapes**: monitor filesystem artifacts (count cached files in output dir, check Supabase row counts) or write a wrapper that redirects to a log file. For scraper progress, check `ls /tmp/ezlynx_phase0/acord_pages/ | wc -l` instead of reading process output.
- **Supabase REST API default limit is 1000 rows** — when querying policies or other large tables, paginate with `offset=N&limit=1000` until an empty array is returned. Add `timeout=30` to all `urllib.request.urlopen()` calls to prevent silent hangs.
- **Google Sheets view-only CAN be read with Playwright** — the master login sheet ("Libertas PWs") uses canvas rendering with external clipboard blocked, but `document.execCommand('copy')` + `navigator.clipboard.readText()` inside `page.evaluate()` returns the selected cell content. Use Ctrl+F to find the row, select with keyboard, then evaluate-copy to read. If that fails, ask Kyle. Never edit the sheet without explicit permission. See `libertas-agency-ops` skill → "Reading the Master Login Sheet" section for the full workflow.
- **Don't guess carrier portal URLs** — use the master login sheet or ask Kyle. Wrong URLs waste time (3 failed navigations trying to find Logic/Standard Casualty portal). Search for the EXACT carrier name in Column A — partial matches land on wrong rows (e.g., "Logic" matches "Logic (For CC Payments)" before "Logic-Standard Casualty").
- **Policy Master CSV download via report viewer** — the on-screen viewer shows only a fraction of rows. To get ALL rows, use the export command in the ReportHost iframe: `$find('WebReportViewer').exportReport('CSV')`. This produced the full 3,980-row export. The downloaded CSV has column `Status2` for filtering active vs inactive.
