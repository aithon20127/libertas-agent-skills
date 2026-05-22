---
name: libertas-daily-sync
description: "Nightly EZLynx→CRM sync pipeline: pull CSVs from Gmail, diff, stage, transform, scrape coverage. Minimal API calls."
version: 1.0.0
author: Odysseus
metadata:
  hermes:
    tags: [agency, ezlynx, crm, supabase, gmail, pipeline, automation]
  schedule: "daily at 8:30 AM CT (1 hour after EZLynx reports arrive at 7:30)"
  prerequisites:
    credentials: "~/.config/libertas/credentials.env (Gmail OAuth + Supabase keys)"
    scripts: "~/.config/libertas/scripts/libertas_daily_sync.py"
    snapshots: "~/.config/libertas/snapshots/ (yesterday's CSV for diffing)"
    chrome: "Chrome on port 9222 with EZLynx logged in (for coverage scraping)"
---

# Libertas Daily Sync Pipeline

Automated nightly pipeline: EZLynx CSV reports → CRM (Supabase) + coverage data.

## Architecture

```
  7:30 AM  EZLynx emails CSV reports to 2factorlogins@gmail.com
     |
  8:30 AM  Odysseus cron fires libertas_daily_sync.py
     |
     +-- Step 1: Pull new CSVs from Gmail (only unread/unprocessed)
     +-- Step 2: Parse CSV, diff against yesterday's snapshot
     +-- Step 3: Stage NEW+CHANGED rows into ezlynx_policy_master_staging
     +-- Step 4: Call ezlynx_transform_run() RPC (creates/updates policies, households, contacts, addresses, audit diffs)
     +-- Step 5: Coverage scrape — only policies where ezlynx_last_synced_at > coverage_last_scraped_at
     +-- Step 6: Stage Renewal Detail (no transform yet)
     |
  ~8:30 AM  CRM is up to date, coverage data refreshed
```

## Key Design Principles

1. **Minimal API calls**: Only process NEW + CHANGED rows. Unchanged rows skip staging entirely. Coverage scrape only re-visits policies that changed.
2. **Snapshot-based diffing**: Yesterday's parsed CSV is saved as JSON. Tomorrow's run diffs against it to find changes. Zero Supabase queries needed to detect diffs.
3. **Reuse the SQL transform**: The `ezlynx_transform_run()` function does all the heavy lifting (household/contact/address creation, policy upsert, audit diffs). No reason to rewrite in Python.
4. **Idempotent**: Safe to re-run. Staging uses upsert on policy_master_id. Transform processes unprocessed rows. Coverage upsert deletes+reinserts per policy.
5. **Gmail dedup**: Processed message IDs are tracked in `processed_message_ids.json`. Never re-downloads the same report.

## Credentials

All in `~/.config/libertas/credentials.env` (chmod 600):

| Key | Purpose |
|-----|---------|
| GMAIL_CLIENT_ID / SECRET | Shared OAuth client (GCP "libertas-quoting") |
| GMAIL_DEFAULT_REFRESH_TOKEN | 2factorlogins@gmail.com (EZLynx reports, Safeco/DCS 2FA) |
| GMAIL_LIBERTASLOGINS_REFRESH_TOKEN | libertaslogins@gmail.com (Foremost/NatGen 2FA) |
| SUPABASE_URL / SERVICE_ROLE_KEY | CRM database (bypasses RLS) |
| SUPABASE_DB_URL | Direct PostgreSQL for migrations |

## Gmail Inbox Routing

| Inbox | Account key | Used for |
|-------|------------|----------|
| 2factorlogins@gmail.com | default | EZLynx nightly CSVs, Safeco 2FA, DCS 2FA |
| libertaslogins@gmail.com | libertaslogins | Foremost (Okta) 2FA, National General 2FA |

## Database Tables

- `ezlynx_policy_master_staging` — raw CSV rows (upsert on policy_master_id)
- `ezlynx_renewal_detail_staging` — renewal data (staged, no transform yet)
- `ezlynx_ingestion_runs` — run history (legacy from edge function)
- `policies` — canonical policy table (transform target), has `coverage_last_scraped_at`
- `policy_coverages` — per-policy coverage lines (NEW, keyed on policy_id + coverage_code)
- `policy_terms` — policy terms (auto-created by upsert_policy_coverages)
- `policies_audit` — field-level change log (premium, status, LOB, carrier changes)

## Key RPCs

- `ezlynx_transform_run(p_run_id, p_offset, p_limit)` — processes staging rows into policies
- `upsert_policy_coverages(p_policy_id, p_coverages)` — replaces coverage lines for a policy

## Running

```bash
# Normal daily run (called by cron)
python3 ~/.config/libertas/scripts/libertas_daily_sync.py

# Dry run (parse + diff only, no CRM writes)
python3 ~/.config/libertas/scripts/libertas_daily_sync.py --dry-run

# Force full coverage re-scrape of all policies
python3 ~/.config/libertas/scripts/libertas_daily_sync.py --full-scrape
```

## Coverage Data Status (Phase 0 results)

823 active policies, full ACORD page scan completed:
- **569 FULL (69%)** — have DWELL or BI with limits, scrapable now
- **208 EMPTY (25%)** — no coverage in EZLynx, need carrier portal scripts
- **42 CODES (5%)** — has data but carrier-specific codes, no DWELL/BI

HOME: 495/629 FULL (79%). AUTO: 72/157 FULL (46%).

Top EMPTY carriers: Progressive (72), Logic-Standard (22), Mercury (19), Allstate (15), Foremost (18).

**Backfill:** Phase 0 scan recorded status only, not actual limits. Use `~/.config/libertas/scripts/phase0_backfill.py` to re-scrape and write real coverage data. See `references/phase0-backfill.md` for details.

**Backfill resume:** The backfill script caches ACORD page text to `/tmp/ezlynx_phase0/acord_pages/{pmid}.txt`. If interrupted (Kyle goes mobile, Chrome disconnect, etc.), just re-run the same script — it skips already-cached pages and resumes from where it left off. Monitor progress with `ls /tmp/ezlynx_phase0/acord_pages/ | wc -l` (total target: ~594 for FULL+CODES policies). **If Kyle says "pause"**, kill the process immediately — the cache ensures no work is lost. The script also needs `timeout=30` on all `urlopen()` calls to prevent silent hangs on network issues.

**Supabase REST patterns:** See `references/supabase-rest-patterns.md` for proven code patterns (pagination, upsert with Prefer header, RPC calls, UUID casting, transform run_id flow).

## Adding Carrier Scripts

When a carrier portal script is built (e.g., Foremost STAR via Browserbase), it feeds into the same pipeline:
1. Script pulls data from carrier site
2. Maps to the same staging format (or directly to policy_coverages)
3. Calls the same `upsert_policy_coverages` RPC

The transform and staging tables are carrier-agnostic.

## Edge Function Status

The `ezlynx-ingest` edge function is still deployed but no longer triggered by pg_cron. It serves as a manual fallback if the ROG is down. To invoke manually:

```bash
curl -X POST 'https://bfdsyqekvjdexmqycyms.supabase.co/functions/v1/ezlynx-ingest' \
     -H 'Authorization: Bearer <service_key>' \
     -H 'X-Ingest-Secret: <secret>'
```

## Pitfalls

- **CSV must be downloaded, not read on-screen** — the EZLynx report viewer truncates data
- **Gmail tokens are read-only** — cannot send/label/delete. If broader scope needed, re-auth.
- **Chrome must be running on port 9222 with an ACTIVE EZLynx session** — coverage scraper connects via CDP. If Chrome is down OR the EZLynx session has expired (redirects to login page), the sync still works for CSV staging/transform but coverage scrape silently returns 0 coverages (it scrapes the login page instead). **Always verify EZLynx login before running the coverage phase.**
- **Allstate AUTO coverage** — earlier samples appeared empty but most DO have BI coverage data. Empty ones are the exception.
- **Germania HOME** — Coverage A is NOT in coverage lines. It's in the Dwelling section as "Estimated Repl Cost Amount". Home and liability are separate policies billed together.
- **Sync Playwright only** — async Playwright gets stuck in long scrapes. Use sync for coverage scraping.
- **Supabase service key bypasses RLS** — be careful with writes. The transform function has its own validation.
- **Staging upsert requires `Prefer: resolution=merge-duplicates` header** — the `on_conflict=policy_master_id` query param alone causes HTTP 409 (duplicate key) on re-insert. The REST API upsert only works with `Prefer: resolution=merge-duplicates` in the header, NOT just the `on_conflict` query param.
- **Transform RPC requires a real UUID run_id AND staging rows must be reassigned** — the `ezlynx_transform_run(p_run_id, ...)` function filters by `WHERE ingestion_run_id = p_run_id`. When staging rows are upserted, they keep their ORIGINAL run_id from the edge function. Before calling the transform, you MUST update all staging rows to use the new run_id via direct DB (psycopg2): `UPDATE ezlynx_policy_master_staging SET ingestion_run_id = %s::uuid WHERE ingestion_run_id = ANY(%s::uuid[])`. Without this, the transform returns 0 rows.
- **UUID type casting in psycopg2** — the `ingestion_run_id` column is type `uuid`, not `text`. All psycopg2 queries referencing it must use `%s::uuid` (for single values) and `%s::uuid[]` (for arrays). Passing bare strings causes `operator does not exist: uuid = text` errors.
- **Phase 0 scan data has status only, not actual coverage lines** — the full_scrape_results.json only records FULL/EMPTY/CODES status and coverage code names, not the actual limit/deductible values. To write real coverage data to the CRM, you must RE-SCRAPE the ACORD pages and parse the full coverage details. The backfill script (`~/.config/libertas/scripts/phase0_backfill.py`) does this, saving ACORD page text to `/tmp/ezlynx_phase0/acord_pages/` for reuse.
- **`coverage_last_scraped_at` on policies table** — the column exists but `upsert_policy_coverages()` RPC may not be setting it. Check before assuming coverage timestamps are accurate. If needed, set manually via direct DB: `UPDATE policies SET coverage_last_scraped_at = NOW() WHERE id = %s`.
- **Cron fires at 8:30 AM CT** — 1 hour after EZLynx reports arrive (7:30 AM), giving reports time to land in Gmail.
- **Hermes background process output is invisible** — `terminal(background=true)` does NOT relay Python stdout/stderr to the process log, even with `PYTHONUNBUFFERED=1`, `python3 -u`, and `sys.stdout.reconfigure(line_buffering=True)`. The `process(action='log')` call returns empty. **Workaround**: monitor filesystem artifacts instead — check cached files (`ls` count in ACORD cache dir), check Supabase row counts, or write to a log file with `exec python3 -u script.py > /tmp/log.txt 2>&1` from a wrapper script. Do NOT rely on `process(action='poll')` output for long-running Python jobs.
- **Supabase REST API pagination** — default max is 1000 rows per request. To get all records, iterate with `offset=N&limit=1000` until an empty array is returned. Always add `timeout=30` to `urllib.request.urlopen()` calls to prevent hangs.
- **EZLynx session re-login** — when the Chrome EZLynx tab redirects to the login page (session expired), you can often click "Log in" without re-entering credentials if the tab hasn't been closed. The browser remembers the form data. Just click the submit button and the session resumes. No 2FA required for same-tab re-login. **Confirmed working**: `page.click('button:has-text("Log in")')` was enough to restore the session after a timeout.
- **Don't guess carrier portal URLs** — use the master login sheet or ask Kyle. Wrong URLs waste time. Search for EXACT carrier name in Column A — partial matches land on wrong rows (e.g., "Logic" matches "Logic (For CC Payments)" before "Logic-Standard Casualty").
- **EZLynx Policy Master report may arrive as .xls instead of .csv** — As of 2026-05-22, the Policy Master report started arriving as `Scheduled Report - CRM Sync - Policy Master.xls` instead of `.csv`. The sync script only downloads CSV attachments (`filename:csv` in Gmail query), so it silently skips XLS files. The Renewal Detail still comes as CSV. When the script logs "Downloaded: Renewal Detail" but no "Downloaded: Policy Master", this is likely the cause. **Result**: zero policy master rows staged/transformed into CRM that day — all active policies go unsynced. **Fix needed**: Add XLS/XLSX parsing support (openpyxl or xlrd) to the sync script, or change the EZLynx report schedule back to CSV format. Check Gmail subjects to confirm: `Scheduled Report - CRM Sync - Policy Master.xls` = XLS, `Scheduled Report - CRM Sync - Policy Master.csv` = CSV. The Gmail query itself (`subject:"CRM Sync" has:attachment filename:csv`) must be broadened to `filename:xls OR filename:csv` or just `has:attachment` with post-filtering.
- **Reading Google Sheets cells from Chrome** — Sheets renders as canvas; DOM inspection doesn't work. Use Playwright CDP to the already-logged-in Chrome tab: (1) Ctrl+F, type search term, (2) Escape to close find, (3) Shift+Space to select the row, (4) Ctrl+C to copy, (5) `page.evaluate('() => navigator.clipboard.readText()')` to read the clipboard. Tab-delimited row data is returned.
