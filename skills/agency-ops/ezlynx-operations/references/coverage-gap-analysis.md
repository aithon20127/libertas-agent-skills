# ACORD Coverage Gap Analysis — Phase 0 COMPLETE

Generated: 2026-05-21 (full scan of ALL 823 active policies)
Method: Playwright-over-CDP scrape of PolicyDisplayAndCompare for every active policy

## Methodology

1. Downloaded full Policy Master CSV via `$find('WebReportViewer').exportReport('CSV')` (3,980 rows)
2. Filtered to `Status2 == 'Active'` → 823 active policies across 31 carriers
3. Initially sampled 1-2 policies per carrier (misleading — see lessons below)
4. Ran full scan of ALL 823 policies using sync Playwright with checkpoint/resume (~84 min)
5. Categorized each policy by ACORD page data: FULL, CODES, EMPTY

**Critical lessons:**
- The on-screen report viewer truncates — ALWAYS download the CSV
- Sampling 1-2 policies per carrier is MISLEADING. Allstate AUTO appeared empty in samples but most have rich BI data (33-96 coverage lines). Always run the full scan.
- The CSV `Source` column ("Download" vs "Manual") does NOT reliably indicate coverage data availability. Allstate AUTO NAIC 29688 shows "Download" but has zero coverage — Kyle says these "likely aren't downloading at all."
- **Kyle prefers tables with client names** so he can investigate individually. Use `Account_Name` from CSV (not First_Name/LastName).

## Full Scan Results (ALL 823 Active Policies)

| Status | Count | % | Description |
|--------|-------|---|-------------|
| FULL | 569 | 69% | Has DWELL or BI with limits — scrapable now |
| EMPTY | 208 | 25% | No coverage data in EZLynx |
| CODES | 42 | 5% | Has coverage lines but no DWELL/BI (carrier-specific codes) |
| EMPTY_PAGE | 3 | <1% | Page didn't load |
| ERROR | 1 | <1% | Scrape error |

### By LOB

| LOB | FULL | EMPTY | CODES | Other | Total |
|-----|------|-------|-------|-------|-------|
| HOME (HO, DF, MH, Wind, Hail) | 495 (79%) | 101 (16%) | 30 (5%) | 3 | 629 |
| AUTO | 72 (46%) | 80 (51%) | 4 (3%) | 1 | 157 |
| OTHER (umbrella, commercial, surety, etc.) | 2 (5%) | 27 (73%) | 8 (22%) | 0 | 37 |

## EMPTY Policies by Carrier (the gap to fill)

| Carrier | EMPTY Count | Notes |
|---------|-------------|-------|
| Progressive Insurance | 72 | Download fix in progress — re-scrape after |
| Logic-Standard Casualty | 22 | Manual-only, no IVANS |
| Mercury Insurance | 19 | Manual-only |
| Allstate | 15 | Specific empty policies mixed in with full ones |
| Foremost (both entities) | 18 | Manual-only |
| National General Ins Co | 7 | Two logins, only one downloads |
| Homeowners of America | 6 | Manual-only |
| Allied | 4 | Manual-only |
| Texas Fair Plan | 4 | Manual-only |
| Tower Hill | 4 | Manual-only |
| American Modern | 3 | Manual-only |
| AMERICAN RISK INS CO INC | 3 | Manual-only |
| Hippo Insurance | 3 | Manual-only |
| REInsurePro | 3 | Manual-only |
| Safeco Insurance | 3 | Unusual — normally full |
| Others (1-2 each) | 17 | Various small carriers |

## Carrier-Specific Findings

### Allstate (206 policies — largest carrier)

**MAJOR CORRECTION**: Earlier Phase 0 sampling showed "Allstate AUTO = ZERO coverage." This was WRONG — based on 1-2 empty policies. The full scan shows most Allstate AUTO policies have rich BI data (15-96 coverage lines per policy). Only 15 of 206 Allstate policies are EMPTY.

**NAIC code breakdown:**

| NAIC | Policies | LOBs | Actually downloading? | Coverage in EZLynx |
|------|----------|------|---------------------|-------------------|
| 37907 (main code) | 142 | 141 HOME + 1 AUTO | Yes, HOME downloads | ~80% HOME have DWELL; AUTO has BI |
| 29688 (auto code) | 38 | 38 AUTO | NO — Kyle says "likely aren't downloading at all" | Most have BI despite this |
| 19240 (secondary) | 9 | 9 HOME | Yes | DWELL present |
| (no NAIC) | 17 | Mixed | No | ZERO coverage |

**Allstate HOME Download endorsement codes** (useful for enrichment, not needed for Cov A-F):
LFREE, VANDL, BURG, RESPY, WTRDM, ESIGN, ROOF, EPPDS, FTBYR, SENMI, ILMC, PROTD, GLASS, RCD, RCC, LOYAL, ACCT

### Germania Farm Mutual (61 policies)

- Writes **home and liability on SEPARATE policies** — generally billed together
- HOME policy has NO DWELL/OS/PP in Coverage lines — only discount codes (HLFC, RENEW, ACCT) and minor coverages (MEDPM, PL, DMGPO, LAC, FP01)
- Coverage A is in the **Dwelling section** as `Estimated Repl Cost Amount` (e.g., = 222018)
- Must pair companion policies to get full coverage picture
- Parser needs Dwelling-section extractor, not just Coverage lines

### Progressive (84 policies)
- 76+ auto — currently zero coverage data
- Kyle says download fix is in progress — once active, re-scrape and data should appear

### National General (37 policies)
- Two logins, only one downloads
- Not fixable for old code; can migrate old NG book to new code eventually

## Pipeline Architecture (DECIDED 2026-05-21)

**The new flow replaces the Supabase edge function's Gmail polling with Odysseus-driven pulls:**

1. **Odysseus pulls CSV from Gmail every morning** — Gmail API for libertaslogins@gmail.com works (refresh token in ~/libertas-crm/browserbase-functions/.env). Need 2factorlogins@gmail.com token or redirect reports.
2. **Parse CSV, diff against yesterday** — detect premium changes, status changes, new/cancelled policies
3. **Write to staging via Supabase REST API** — same staging tables the edge function uses
4. **Call `ezlynx_transform_run()` RPC** — same SQL transform (households, contacts, addresses, audit diffs, policy upserts). Don't rewrite it.
5. **Coverage scrape after CSV sync** — only re-scrape policies where `ezlynx_last_synced_at > coverage_last_scraped_at`
6. **Later: carrier-specific scripts** feed same staging + transform pipeline

**Turn off the edge function's Gmail polling but keep it deployed as fallback.**

### Supabase Architecture for Coverage Data

1. **SQL migration**: `~/libertas-crm/supabase/migrations/20260521120000_policy_coverages.sql`
   - `policy_coverages` table (one row per coverage line, keyed on `policy_id + coverage_code`)
   - `coverage_last_scraped_at` column on `policies`
   - Indexes for fast lookup by policy, carrier, coverage code
   - RLS policies matching existing `policies` table pattern

2. **Scraper writes via REST API**: `POST /rest/v1/policy_coverages` from the ROG
   - Reads policy IDs from DB, scrapes ACORD pages, writes coverage rows
   - No new edge function — the scraper runs locally where Chrome is

3. **Blocked on**: Real Supabase service key on the ROG (current .env has abbreviated placeholders)

## Gmail Accounts

| Account | Purpose | API Access | Notes |
|---------|---------|-----------|-------|
| libertaslogins@gmail.com | 2FA codes for EZLynx login | **Working** — refresh token in ~/libertas-crm/browserbase-functions/.env | gmail.readonly scope |
| 2factorlogins@gmail.com | Receives nightly CSV reports | **No refresh token** — need OAuth setup | Current report target |
| Aithon20127@gmail.com | Agent Google account | Browser only (needs 2FA + App Password for himalaya) | himalaya v1.2.0 installed |

## Key Files

| File | Purpose |
|------|---------|
| `/tmp/ezlynx_phase0/policy_master_export.csv` | Full Policy Master export (3,980 rows, 823 active) |
| `/tmp/ezlynx_phase0/full_scrape/full_scrape_results.json` | Per-policy coverage status for all 823 |
| `/tmp/ezlynx_phase0/full_scrape/full_scrape_checkpoint.json` | Last checkpoint (resume point) |
| `/tmp/ezlynx_phase0/full_scrape/scan_log.txt` | Full scan log with per-policy results |
| `/tmp/ezlynx_phase0/coverage_gap_with_names.md` | Client-name table for Kyle (all 823 policies) |
| `/tmp/pw_acord_scraper_v5.py` | Production ACORD scraper with Supabase write support |
| `/tmp/pw_full_coverage_scan_v4.py` | Bulk coverage scanner (sync Playwright, checkpoint/resume) |
| `~/libertas-crm/supabase/migrations/20260521120000_policy_coverages.sql` | Policy coverages table migration |
