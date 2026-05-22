# Phase 0 Coverage Backfill

The Phase 0 full scan (`full_scrape_results.json`) recorded status (FULL/EMPTY/CODES) but NOT actual coverage limits/deductibles. To write real coverage data to the CRM, you must re-scrape the ACORD pages.

## Backfill Script

`~/.config/libertas/scripts/phase0_backfill.py` — Re-scrapes policies with coverage data (FULL + CODES), parses actual limits/deductibles, and writes to `policy_coverages` via `upsert_policy_coverages` RPC.

Usage:
```bash
source ~/ezlynx-env/bin/activate
python3 ~/.config/libertas/scripts/phase0_backfill.py
```

Prerequisites:
- Chrome on port 9222 with active EZLynx session
- `~/.config/libertas/credentials.env` with Supabase + Gmail keys
- Phase 0 scan results at `/tmp/ezlynx_phase0/full_scrape/full_scrape_results.json`

## ACORD Page Cache

Re-scraped ACORD page text is saved to `/tmp/ezlynx_phase0/acord_pages/{policy_master_id}.txt`. If a cached file exists, the backfill script can skip re-scraping and parse from the cache instead.

## Key Data

- 611 policies have coverage data (569 FULL + 42 CODES) out of 823 active
- Full Phase 0 results: `/tmp/ezlynx_phase0/full_scrape/full_scrape_results.json`
- Per-policy key format: `"{applicant_id}|{policy_master_id}"`
- Client-name gap table: `/tmp/ezlynx_phase0/coverage_gap_with_names.md`
