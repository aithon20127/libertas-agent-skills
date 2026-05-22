# Policy Coverage Data Pipeline — Architecture & Reference

Last updated: 2026-05-21

## The Problem

EZLynx Reports 5.0 does NOT expose coverage columns (Coverage A-E, deductibles, liability limits) in ANY report type. The nightly Policy Master CSV that feeds the CRM has zero coverage data. Clients need coverages visible in the CRM and eventually need dec pages/ID cards via the website chat interface.

## The Solution: PolicyDisplayAndCompare (ACORD XML)

Every policy in EZLynx has a "Full Policy Details" page that dumps the complete decoded IVANS/ACORD XML data. This page contains every coverage code, limit, deductible, endorsement, vehicle, driver, dwelling detail, and mortgagee.

**URL pattern:**
```
https://app.ezlynx.com/ApplicantPortal/Applicant/{applicantId}/PolicyDisplayAndCompare?Func=0&ApplicantID={applicantId}&PolMasterID=m{policyId}
```

- Found via: Policy Summary page -> "Click here for additional policy information"
- Also accessible via: Policy Summary -> "Export Policy Information"
- Data format: Tab-separated key-value pairs in collapsible sections
- Size: ~8-10K characters per policy
- Parse with: line-by-line regex, looking for `Key\tValue` patterns

**How to get (applicantId, policyMasterId) pairs:**
- Nightly Policy Master CSV has columns `ApplicantID` and `Policy_Master_ID`
- CRM `policies` table stores them as `ezlynx_applicant_id` and `ezlynx_policy_master_id`
- URL construction: `PolMasterID = 'm' + Policy_Master_ID` (note the 'm' prefix)

## Proven Scraper Results (Tested 2026-05-21)

Scraper at `/tmp/pw_acord_scraper_v4.py` — tested across 8 policies, 5 carriers, 2 LOBs:

| Carrier | Writing Co | LOB | Policy# | Cov | Veh | Drv | Key Data |
|---------|-----------|-----|---------|-----|-----|-----|----------|
| Nationwide | NATIONWIDE MUT INS CO | Home | 7842HR142750 | 32 | 0 | 0 | DWELL $333K/$2500, HURR 1%, MOLD $10K |
| Travelers | TRAVELERS PERSONAL INS CO | Home | 6161964186331 | 40 | 0 | 0 | DWELL $298K/$2980, PL $300K |
| Safeco | AMERICAN ECONOMY INS CO | Home | OY9329623 | 16 | 0 | 0 | DWELL $250K/$10K, PL $300K |
| Allstate | ALLSTATE FIRE & CAS INS CO | Auto | 438259043 | 42 | 2 | 2 | BI 50/100, COMP/COLL $1K ded |
| Geico | GEICO TX CNTY MUT INS CO | Auto | 6226007216 | 12 | 1 | 1 | BI 100/300, COMP/COLL $500 ded |
| Safeco | LIBERTY COUNTY MUT INS CO | Auto | Y1042021 | 43 | 4 | 4 | BI 50/100, 4 vehicles |
| NatGen | IMPERIAL FIRE & CAS INS CO | Home | 203548211400 | 20 | 0 | 0 | DWELL $390K/1-2%, HURR, PL $300K |
| NatGen | IMPERIAL FIRE & CAS INS CO | Auto | 203556045000 | 18 | 1 | 1 | BI 100/300, COMP/COLL $500 ded |

**Note:** Carrier names in EZLynx show the WRITING company (e.g., Safeco = AMERICAN ECONOMY or LIBERTY COUNTY MUT), not the parent brand. NAIC code maps to the right carrier.

**Rate:** ~7 seconds per policy + 8-10 second rate limit = ~1 policy per 15-17 seconds. Full backfill of 823 active policies = ~3.5-4 hours. Ongoing incremental (only changed/renewed) = a few minutes daily.

## Data Samples

### Homeowners (Nationwide 7842HR142750) — Key Fields

**Policy Header:**
```
LOB Code    HOME
Current Term Amount    5437.09
Policy Number    7842HR142750
Effective Date    2025-05-19
Expiration Date    2026-05-19
NAIC Code    23787
Commercial Name    NATIONWIDE MUT INS CO
```

**Insured:**
```
Person Surname    Conner
Given Name    Bryan
Birth Date    1973-03-30
Address 1    2310 W Gentry Pkwy
City    Tyler
State Province Code    TX
Postal Code    75702-2856
Email Address    bryanconner40@yahoo.com
```

**Dwelling:**
```
Construction Code    V
Year Built    2006
Roof Material Code    COMP
Fire Protection Class Code    006
Estimated Repl Cost Amount    333200
Total Area    2036
Heating/Plumbing/Roofing/Wiring Improvement Year + Code all present
```

**Coverages (ACORD codes -> descriptions -> limits):**
```
DWELL    Dwelling    333200    Deductible: 2500 FL + 1% PC
OS       Other Structures    33320
PP       Personal Property    249900
LOU      Loss of Use    Type1/LS
PL       Personal Liability    300000
MEDPM    Medical Payments    5000
HURR     Hurricane Deductible    1% PC
MOLD     Fungi or Bacteria    10000
WTRDM    Water Damage (Full)    333200    Premium: 211.09
BOLAW    Building Ordinance/Law    33320
FVREP    Dwelling Replacement Cost    499800
LAC      Loss Assessment    1000
UNJWF    Unscheduled Jewelry     2500
FREEZ    Refrigerated Foods      500
+ ~10 more endorsements
```

**Mortgagee:**
```
Commercial Name    Guild Mortgage Company
Nature Of Interest Code    MORTG
Account Number    770-2002371
```

### Auto (Allstate 438259043) — Key Fields

**Policy Header:**
```
LOB Code    AUTOP
Current Term Amount    2320.74
Policy Number    438259043
Effective Date    2026-03-31
Expiration Date    2026-09-30
NAIC Code    29688
Commercial Name    ALLSTATE FIRE & CAS INS CO
```

**Drivers:**
```
Driver 1: Kyle W Thompson, DOB 1994-03-09, Male, Married, DL# 29184912 TX, IN
Driver 2: Allie Craven, DOB 1993-09-30, Female, Married, DL# 33755938 TX, SP
```

**Vehicles + Per-Vehicle Coverages:**
```
Vehicle 1: 2016 Chevy Truc Tahoe, VIN 1GNSKCKC7GR345180, Symbol E, Rate 180
  BI       50000/100000    Premium: 206.25
  COMP     (deductible)    Premium: per-vehicle
  COLL     (deductible)    Premium: per-vehicle
  UM/UMPD/PIP with limits
  + discount codes: RREIM, PREFR, GDPAY, PREMR, EPPDS, etc.

Vehicle 2: 2017 Chevy Truc Silverado, similar structure
```

**Accidents:**
```
Accident Violation Code    ACCNF
Accident Violation Date    2022-10-06
Description    Miscellaneous - (Multi Car) No Fault
```

**Prior Policy:**
```
Policy Number    4334111173001
Insurer Name    State Farm Mut
Expiration Date    2025-04-02
```

## Carrier Landscape

**Book size:** ~649 active customers, 823 active policies, ~$2.71M premium

**Data source split (from CSV, Status2=Active):**
- **~70% IVANS Download** (~562 policies) — rich structured data, has full ACORD XML in PolicyDisplayAndCompare. But note: some "Download" flags are misleading (e.g., Allstate AUTO NAIC 29688 says Download but zero data flows).
- **~30% Manual (CSR-keyed)** (~261 policies) — sparse/header-only, needs carrier portal pull or dec-PDF upload

**Carrier rater access (from AGENCY-KNOWLEDGE.md):**
- Auto raters: TurboRater PLQ (Foremost live in sandbox; Progressive, NatGen, Travelers, Mercury, GEICO, Lamar, Allstate, Hartford need prod carrier-auth)
- Home raters: ITC XML Rate Engine (Liberty Mutual, Foremost Agent360, Mercury, Allied Trust, Travelers, Hartford)
- Portal-only: Foremost STAR (Browserbase+Stagehand, working)

**Documents reality:**
- Dec pages are NEVER auto-imported into EZLynx, even for IVANS downloads
- Some are manually uploaded by staff to the Documents tab
- Carrier portals are the only reliable source for actual dec pages and ID cards
- ACORD form generation from CRM data can substitute for most client-facing needs

## Architecture: 4-Phase Coverage + Document Pipeline

### Phase 1: EZLynx Policy Detail Scraper (Coverage Backfill)

**Approach:** Write a Playwright script that iterates all active policies, hits the PolicyDisplayAndCompare page, parses the ACORD XML text, and writes coverage fields into the CRM.

**Current state:** v5 scraper (`/tmp/pw_acord_scraper_v5.py`) is built and tested. Parses coverages + dwelling section + vehicles + drivers, detects carrier-specific codes, outputs JSON + ready for Supabase REST API writes.

**Migration:** `~/libertas-crm/supabase/migrations/20260521120000_policy_coverages.sql` creates:
- `policy_coverages` table — one row per (policy_id, coverage_code, vehicle_unit). Columns: coverage_code, vehicle_unit, description, limit_amount (TEXT), deductible (TEXT), premium (NUMERIC), is_carrier_code (BOOLEAN), raw_line (JSONB), scraped_at, updated_at. UNIQUE constraint on (policy_id, coverage_code, vehicle_unit).
- `coverage_last_scraped_at` column on `policies` table — tracks when coverage was last scraped. NULL = never scraped.
- `policy_coverages_clear_for_policy(UUID)` helper function — nukes old rows before re-scrape.
- `policy_coverages_home_summary` view — pivots key HOME coverages (DWELL, OS, PP, LOU, PL, MEDPM, HURR, MOLD) per policy.
- `policy_coverages_auto_summary` view — pivots key AUTO coverages (BI, PD, UM, PIP, COMP/COLL deductibles by vehicle).
- RLS: service_role full access, authenticated read-only.

**Steps:**
1. Get list of all active policies (from nightly Policy Master CSV or CRM query)
2. For each policy, construct the PolicyDisplayAndCompare URL
3. Navigate to the page, extract the full text (~8-10K chars)
4. Parse ACORD data: coverage codes -> limits -> deductibles -> premiums
5. Map ACORD codes to CRM fields (DWELL->coverage_a, OS->coverage_b, etc.)
6. Write to CRM `policies` table (new coverage columns needed via migration)

**Performance:** ~1 policy per 15-17 seconds = ~3.5-4 hours for all 823

**Ongoing maintenance:**
- The 7:30 AM daily reports (Policy Master + Renewal Detail) flag changes/renewals
- Only re-scrape policies that changed (typically 10-30/day)
- Cost: essentially free (runs on local Chrome, no API calls)

**Coverage for ~70% of book:** IVANS-sourced policies have complete ACORD data on this page.
**Gap: ~30% Manual policies:** May only have header data; need carrier portal pull or dec-PDF parse.

### Phase 2: ACORD Document Generator

**Approach:** Generate ACORD forms server-side from CRM coverage data. No carrier portal needed.

**Target forms:**
- **ACORD 80** (Homeowners) — standard home dec page replacement. Fields map directly from DWELL/OS/PP/LOU/PL/MEDPM codes.
- **ACORD 25** (Certificate of Insurance / Auto) — from auto coverage data.
- **ACORD 28** (Evidence of Property Insurance) — for mortgagee requests. Can auto-generate and email.

**Implementation:**
- PDF-fillable ACORD form templates (available from acord.org or pre-made)
- Populate via pdf-lib (Node) or PyPDF2/reportlab (Python)
- Coverage data from Phase 1 is already ACORD-structured — the mapping is mechanical
- Generate on-demand when client requests via chat interface

**Why this beats carrier dec pages:**
- One implementation serves ALL carriers (not 20+ per-carrier scrapers)
- Always current (regenerates from latest CRM data)
- Consistent format clients can understand
- No reliance on carrier portal availability or UI changes

### Phase 3: Carrier Portal Dec Page Scripts

**For cases where the actual carrier dec page is needed** (not ACORD substitute):

- Build per-carrier Browserbase+Stagehand scripts using the Foremost STAR template
- **Top priority: Allstate (~32% of book)** — richest IVANS source, likely best portal access
- Then: Progressive, Nationwide, State Farm
- Script pattern: Login -> navigate to policy -> find/download dec page PDF -> upload to CRM
- Smart scheduling: initial backfill overnight, then only re-pull on renewal/change (flagged by daily reports)
- Browserbase cost: ~$0.02-0.05 per page load

### Phase 4: Customer-Facing Chat Interface

- Extend existing MCP server with tools: `get_my_coverages`, `get_my_dec_page`, `get_my_id_card`
- AI chat on libertasinsurance.com answers: "what's my Coverage A?", "send me my dec page"
- ACORD forms generated on-demand from CRM data
- Real carrier dec pages served as downloadable PDFs from document storage
- Read-only first; write/service actions later

## ACORD Code -> CRM Field Mapping (Draft)

### Home Coverages

| ACORD Code | Description | CRM Field | Example Value |
|---|---|---|---|
| DWELL | Coverage A (Dwelling) | coverage_a | 333200 |
| OS | Coverage B (Other Structures) | coverage_b | 33320 |
| PP | Coverage C (Personal Property) | coverage_c | 249900 |
| LOU | Coverage D (Loss of Use) | coverage_d | Type1/LS |
| PL | Coverage E (Personal Liability) | coverage_e | 300000 |
| MEDPM | Coverage F (Medical Payments) | coverage_f | 5000 |
| HURR | Hurricane Deductible | hurricane_deductible | 1% |
| MOLD | Fungi/Bacteria Limit | mold_limit | 10000 |
| WTRDM | Water Damage Coverage | water_damage_limit | 333200 |
| BOLAW | Ordinance/Law | ordinance_law_limit | 33320 |
| FVREP | Dwelling Replacement Cost | replacement_cost | 499800 |

### Auto Coverages

| ACORD Code | Description | CRM Field | Example Value |
|---|---|---|---|
| BI | Bodily Injury Liability | bi_limits | 50000/100000 |
| PD | Property Damage Liability | pd_limit | 50000 |
| COMP | Comprehensive | comp_deductible | 500 |
| COLL | Collision | coll_deductible | 500 |
| UM | Uninsured Motorist BI | um_bi_limits | 50000/100000 |
| UMPD | Uninsured Motorist PD | umpd_limit | 25000 |
| PIP | Personal Injury Protection | pip_limit | varies |
| ADDA | Auto Death Indemnity | adda_limit | 10000 |

Per-vehicle coverages need a separate `policy_vehicles` table (VIN, year, make, model, comp deductible, coll deductible, towing, rental, etc.).

## Technical Notes

### Parsing the PolicyDisplayAndCompare Page

The page text follows this structure:
```
Section Name
collapse

Key1    Value1
Key2    Value2

Coverage :ACORD_CODE Section
collapse

Coverage Code    ACORD_CODE
Coverage Description    Human-readable name
Format Integer Limit    333200
Format Currency Amount Deductible    2500
Deductible Type Code    FL
Current Term Amount    211.09
```

**Parser pitfalls (learned from 3 iterations):**
1. Page has a NAVIGATION TREE at top (lines 1-74) with section headers — this is NOT data, just a TOC
2. Actual data starts after the SECOND "General Section" + next "collapse" marker
3. Home policies have a space after colon in coverage headers (`Coverage : PP`), auto doesn't (`Coverage :BI`) — regex must allow optional whitespace: `r'^Coverage\s+:\s*(\w+)'`. This was a real bug: without `\s*`, home policies parsed as 0 coverages.
4. Home uses `Format Integer Limit` for limits; auto uses just `Limit` — parser must handle both
5. Home uses `Format Currency Amount Deductible` and `Format Percent Deductible`; auto uses `Deductible Limit` — parser must handle all variants
6. Per-vehicle coverages in auto: `Coverage :BI Personal Vehicle 1` — extract vehicle number from context
7. Some carriers (Germania) put Coverage A in the Dwelling section (`Estimated Repl Cost Amount`) instead of in Coverage lines — parser must also extract Dwelling-section values for these carriers. Germania also writes home and liability on SEPARATE policies (generally billed together), so the HOME policy only has discount codes and minor coverages. The actual Coverage A lives on the Dwelling node of the home policy, not in a Coverage :DWELL line.
8. The on-screen report viewer does NOT show all rows — to get the full dataset from any report, you MUST download it (CSV/Excel). Use: `$find('WebReportViewer').exportReport('CSV')` in the ReportHost iframe. This is how the full 3,980-row Policy Master export was obtained.
9. Carrier-specific coverage codes (e.g., Allstate LFREE, VANDL, WTRDM, ROOF) are detected by the v5 parser and flagged with `is_carrier_code=true`. A mapping table (`CARRIER_CODE_MAP` dict in the scraper) provides descriptions for known codes. Unknown codes still parse correctly; they just get flagged as carrier-specific.
10. The Policy Master CSV `Source` column ("Download" vs "Manual") is NOT a reliable indicator of whether coverage data is present. Allstate AUTO (NAIC 29688) shows "Download" but zero coverage in ACORD pages. Always verify by sampling.
11. Always filter CSV by `Status2 == 'Active'` — the full export includes cancelled/expired (3,980 total, only 823 active).

### Rate Limiting

- EZLynx is a shared SaaS — don't blast 800+ page loads in rapid succession
- Tested rate: 8-10 second delay between page navigations works reliably
- Initial backfill can run overnight (~3.5-4 hours)
- Ongoing daily refresh: 10-30 policies = ~2-5 minutes

### Chrome Session Stability

- The Playwright-over-CDP connection can time out on heavy Angular pages (Policy Transactions page is particularly slow)
- Lighter pages (ReportMenu, Dashboard, Policy Summary, PolicyDisplayAndCompare) work reliably
- If Chrome session dies, re-launch and re-login (auth doesn't persist across restarts)
- For long batch runs, implement retry logic with session health checks
