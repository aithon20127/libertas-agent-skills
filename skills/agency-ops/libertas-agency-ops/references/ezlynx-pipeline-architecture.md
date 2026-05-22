# EZLynx Pipeline Architecture

Session-derived reference: 2026-05-20 investigation of the nightly sync pipeline.

## Pipeline Stages

### 1. Scheduled Reports (EZLynx side)
- **"CRM Sync - Policy Master"** — full book of business, header-level fields only
- **"CRM Sync - Renewal Detail"** — renewal effective dates, premium changes, percent changes
- Both emailed as CSV attachments to `2factorlogins@gmail.com`
- Subject pattern: `Scheduled Report - CRM Sync - <ReportName>.csv`
- **Key insight (2026-05-20):** The report column selection is configurable in EZLynx's scheduled report settings. Before building a scraper, check if EZLynx offers a more detailed report template (e.g., "Policy Detail" or "Coverage Detail") with coverage columns. If so, switching the report config is the cheapest fix — the nightly ingest would automatically pick up extra columns via the `raw` JSONB field, and a transform update could map them.

### 2. Gmail Ingest (`ezlynx-ingest` edge function)
- **Location:** `supabase/functions/ezlynx-ingest/index.ts`
- **Gmail query:** `from:ezlynxreporting@ezlynx.com subject:"CRM Sync" has:attachment filename:csv newer_than:7d`
- **Dedup:** via `ezlynx_ingestion_runs` table (skips message_ids with status='success')
- **Max messages per run:** 20
- **Auth:** gmail.readonly scope (does NOT mark messages as read)

### 3. Staging Tables

**`ezlynx_policy_master_staging`:**
- `policy_master_id` (UNIQUE, upsert key)
- `applicant_id`
- `policy_number`
- `raw` (JSONB — full CSV row)
- `ingestion_run_id` (FK to ingestion_runs)

**`ezlynx_renewal_detail_staging`:**
- `applicant_id`
- `policy_number`
- `effective_date`
- `premium_annualized`
- `change_amount`
- `percent_change`
- `raw` (JSONB)
- `ingestion_run_id`
- Upsert conflict key: `(applicant_id, policy_number, effective_date)`

### 4. Transform (`ezlynx_transform_run` PL/pgSQL function)
- **Called by:** the ingest function after staging Policy Master rows
- **Signature:** `ezlynx_transform_run(p_run_id UUID, p_offset INT, p_limit INT) RETURNS jsonb`
- **Authority:** EZLynx wins on conflicts; CRM losing values → `policies_audit`

**Field mappings from `raw` JSONB → canonical tables:**

| Source field (raw) | Target table | Target column |
|---|---|---|
| `Master_Company` / `Writing_Company_Name` | carriers | name (auto-create if unknown, appointment_status='pending') |
| `NAIC_Code` | carriers | naic_code |
| `Line_Of_Business` | policies | line_of_business (via `ezlynx_lob_map` table, fallback 'other') |
| `Status2` | policies | status ('active' / 'canceled' / 'expired') |
| `Policy_Number` | policies | policy_number |
| `Effective_Date2` | policies | effective_date |
| `Expiration_Date2` | policies | expiration_date |
| `Annualized_Premium2` | policies | premium_annual |
| `Account_Name` / `Business_Name` / `LastName, FirstName` | households | name |
| `Account_Type` | households | type ('family' / 'commercial') |
| `First_Name`, `LastName`, `Business_Name` | contacts | first_name, last_name, business_name |
| `Primary_Email` | contacts | email |
| `Phone_Cell` / `Phone_Home` / `Business_Phone` | contacts | phone_primary |
| `Address_Line1`, `Address_Line2`, `Address_UnitNumber`, `Address_City`, `Address_State`, `Address_ZipCode` | addresses | street_1, street_2, city, state, zip |
| Full row | policies | ezlynx_raw (JSONB) |

**NOT mapped (the coverage gap):**
- Coverage A (Dwelling), Coverage B (Other Structures), Coverage C (Personal Property)
- Coverage D (Loss of Use), Coverage E (Liability), Coverage F (Medical Payments)
- Deductibles, liability limits, medical payments limits
- Endorsement details

### 5. Renewal Detail (NO transform yet)
- Rows land in `ezlynx_renewal_detail_staging` only
- Roadmap item: build `ezlynx_renewal_radar` view / Reshop queue from this data
- Fields available: applicant_id, policy_number, effective_date, premium_annualized, change_amount, percent_change

## LOB Mapping Table (`ezlynx_lob_map`)

Maps EZLynx `Line_Of_Business` labels to CRM `line_of_business` enum values. Key entries:
- Homeowners → homeowners
- Auto (Personal) → auto
- Dwelling fire → dwelling_fire
- Umbrella - Personal → umbrella
- Renters → renters
- Flood → flood
- Mobile Homes → mobile_home
- (Full list in migration `20260502130028_ezlynx_transform.sql`)

## Key Migration Files

| File | Purpose |
|---|---|
| `20260502130024_ezlynx_policy_master_staging.sql` | Staging table DDL |
| `20260502130025_ezlynx_grants.sql` | RLS / grants |
| `20260502130028_ezlynx_transform.sql` | Main transform function |
| `20260502130029_ezlynx_transform_batched.sql` | Batched transform variant |
| `20260502130030_ezlynx_transform_fix_premium.sql` | Premium field fix |
| `20260502130031_ezlynx_transform_fix_onconflict.sql` | Conflict handling fix |
| `20260502130032_ezlynx_transform_skip_address_no_city.sql` | Skip addresses missing city |
| `20260502130033_ezlynx_renewal_detail_staging.sql` | Renewal staging DDL |

## Coverage Backfill Strategy (Roadmap)

**Priority order:**

1. **First (cheapest):** Check if EZLynx scheduled reports can be configured with more columns (coverage fields). If the report definition supports it, switching to a more detailed column set means the nightly ingest picks up extra data automatically via the `raw` JSONB field. Then update the transform to map the new columns.
2. **Second (medium effort):** Scrape the EZLynx Policy Summary UI (`/applicantportal/policy/{id}/summary/index`) — one UI has full Coverage A–E for every policy. Avoids scraping 20+ carrier portals.
3. **Third (hardest):** Build carrier-specific portal scrapers for carriers not in EZLynx or where the Policy Summary UI is insufficient.

This is the single highest-value data backfill task for the agency — it unlocks coverage accuracy for quoting, service, and the future customer portal.

## IVANS Download vs Manual Source Coverage Gap

~70% of the book arrives via IVANS Download (structured, carrier-dependent richness). ~30% is Manual-entry (sparse, header-only). Key distinction:

- **IVANS Download carriers** (e.g., Allstate ~32% of book) deliver richer structured data but the Policy Master CSV columns are fixed by the scheduled report definition, not by what IVANS sends to EZLynx.
- **Manual-entry carriers** (Logic/Standard Casualty, etc.) have data in EZLynx because CSRs key it in, but the Policy Master CSV still only exports its configured columns.
- **The bottleneck is the report definition**, not the data source. Maximizing report columns is step one. After that, the Policy Summary UI scraper fills whatever the reports can't provide.

Building a carrier-by-carrier IVANS-strength matrix (which carriers deliver coverages via download vs which don't) is good early work once we have DB access.
