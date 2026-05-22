---
name: libertas-crm-reference
version: 1.0
description: Detailed CRM schema, data paths, and operational reference for Libertas Insurance Supabase CRM
---

# Libertas CRM Reference

## Connection
- **Project ref:** bfdsyqekvjdexmqycyms
- **DB (psycopg2):** SUPABASE_DB_URL / SUPABASE_DB_PASSWORD in ~/.config/libertas/credentials.env
- **REST API:** Full JWTs now in ~/.config/libertas/credentials.env — READ + WRITE + DELETE confirmed working with service_role key
- **Direct DB is the working path** — bypasses RLS, no service role key needed

## Key Tables

### policies (4,078 total, 840 active)
- id, household_id, primary_contact_id, carrier_id, policy_number, line_of_business, status, effective_date, expiration_date, premium_annual, payment_plan, billing_type, commission_rate, assigned_producer_id, assigned_csr_id, source_quote_id, prior_policy_id, ivans_lob_code, carrier_login_id, auto_created, notes, created_at, updated_at, payment_frequency, address_id
- Enrichment: udd_raw, udd_drivers, udd_vehicles, udd_transaction_id, udd_ran_at, vehicle_services_raw, vehicle_services_ran_at, property_data, property_ran_at, property_source, ppc_data, ppc_ran_at, drivers, vehicles, drivers_license, year_built, square_footage, stories, bathrooms, exterior, roof_material, roof_type, foundation, pool, address_county, protection_class, fire_protection_area, miles_to_coast, enrichment_signature, enrichment_completed_at
- EZLynx: ezlynx_policy_master_id, ezlynx_applicant_id, ezlynx_last_synced_at, ezlynx_raw
- Other: address_swapped_at, coverage_last_scraped_at, replacement_cost

### policy_terms
- id, policy_id, effective_date, expiration_date, term_number, is_active, created_at, premium

### policy_coverages (8,730 rows)
- id, policy_id, policy_term_id, coverage_code, coverage_name, limit_per_occurrence, limit_aggregate, deductible, deductible_type, premium, created_at
- HOME codes: DWELL, PP, OS, LOU, MEDPM, PL (have limits from ACORD backfill)
- AUTO codes: BI, PD, COMP, COLL (rows exist but most have zero limits)

### carriers
- id, name, naic_code, lines_of_business, states_active, appointment_status, appointment_date, ivans_code, api_available, portal_url, policy_url_pattern, underwriter_name, underwriter_email, underwriter_phone, claims_phone, notes, created_at, updated_at, website, aliases, underwriter

### contacts
- Has DOB (needed for Logic quoting)

### addresses
- Standard address fields

## Coverage Gap (Active Only)
- 840 active, 594 with coverage, 246 missing (29%)
- Full analysis: ~/.config/libertas/carrier-coverage-gap-analysis.md
- Dead carriers (no active policies): Lighthouse, State Auto, Pacific Specialty, Kemper

## Data Sources
- EZLynx ACORD backfill: 600 policies done (HOME coverages)
- Daily sync: libertas_daily_sync.py (cron 8:30AM CT)
- Carrier portals: see gap analysis for portal URLs

## Key Files
- ~/.config/libertas/credentials.env — DB creds (REST keys broken)
- ~/.config/libertas/scripts/phase0_backfill.py — ACORD backfill script
- ~/.config/libertas/scripts/libertas_daily_sync.py — nightly sync
- ~/.config/libertas/carrier-coverage-gap-analysis.md — gap priority list

## Critical Rule
NEVER abbreviate API keys when saving to files. Full JWTs only. The abbreviated format (eyJhbG...mr1g) is useless for actual API calls.
