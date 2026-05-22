# Empty Policy Export — 207 Policies with No ACORD Coverage Data

**Generated:** 2026-05-21 from full scan of 823 active policies
**Source:** `/tmp/ezlynx_phase0/full_scrape/full_scrape_checkpoint.json` matched against Policy Master CSV
**Clean CSV:** `/tmp/EZLynx_Empty_Policies.csv`

## Summary

- **207 policies** with EMPTY or EMPTY_PAGE status in the full ACORD scrape
- **$742,376** total annual premium at stake
- These policies have no coverage data in EZLynx's PolicyDisplayAndCompare page
- Must be filled via carrier portal scripts, IVANS download fixes, or manual entry

## By Line of Business

| LOB | Count |
|-----|-------|
| Homeowners | 86 |
| Auto (Personal) | 80 |
| Dwelling fire | 10 |
| Flood | 6 |
| Mobile Homes | 6 |
| Commercial Prpty | 5 |
| Auto (Commercial) | 4 |
| Commercial Pkg | 3 |
| Umbrella - Personal | 2 |
| Genl Liability | 2 |
| Watercraft (small boat) | 2 |
| Professional Liab | 1 |

## Top Carriers (where Writing_Company_Name is known)

| Carrier | Count |
|---------|-------|
| PROGRESSIVE CNTY MUT INS CO | 34 |
| AMERICAN MERCURY LLOYDS INS CO | 7 |
| ALLSTATE VEHICLE & PROP INS CO | 4 |
| FARMERS INS CO INC | 4 |
| STANDARD CAS CO | 3 |
| National General Premier Ins Co | 3 |
| National Summit Insurance Company | 2 |
| AMERICAN RISK INS CO INC | 2 |
| TEXAS FAIR PLAN ASSN | 2 |
| JAMES RIVER INS CO | 1 |
| SAFECO INS CO OF AMER | 1 |

**138 of 207 have no Writing_Company_Name in the Policy Master CSV** — the carrier name lives in the ACORD page (which is empty for these), so these need carrier identification from another source (IVANS, carrier portal, or manual lookup).

## Google Sheets Export

**Status: DONE.**

- **OAuth complete** for `aithon20127@gmail.com` — token at `~/.hermes/google_token.json` with `spreadsheets`, `drive.file`, and `gmail.readonly` scopes
- Sheets API NOT enabled in Google Cloud project 848419619510 — used browser fallback instead
- **Sheet created via Chrome browser (CDP):** navigated to `sheets.new`, pasted CSV, Split text to columns with Comma separator
- **Sheet URL:** https://docs.google.com/spreadsheets/d/1l_LsF5pmc91Lhx6-5x7CDvm6R3604wXnPFhxURGLCy8/edit
- **Sheet name:** EZLynx Empty Coverage Policies
- **Method:** Browser-based (see `google-workspace` skill → "Browser-Based Sheets Fallback")
- **CSV also saved at:** `/tmp/EZLynx_Empty_Policies.csv`

## CSV Columns

Client Name, Policy #, LOB Code, Line of Business, Sub LOB, Writing Carrier, Annual Premium, Term Premium, Full Term Premium, Effective Date, Expiration Date, Transaction Type, Policy Status, Client Status, Address, City, State, Zip, Applicant ID, Policy Master ID
