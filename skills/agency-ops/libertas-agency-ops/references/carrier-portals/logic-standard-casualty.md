# Logic Insurance / Standard Casualty — Carrier Portal

**Platform:** Beyontec Suite (EZ*Insure) — iframe-heavy legacy web app
**Portal URL:** https://logicunderwriters.com/beyontecsuite/
**Login mode:** AGENT (two buttons on landing: EMPLOYEE / AGENT)
**Credentials:** User ID 2527, password in master login sheet row 137
**Underwriting:** 214-739-0071 / 1-888-315-6442 (Sue Blackwell X 143)
**Claims:** 800-522-0146 (Option #5) or 1-888-315-6442 Option 4
**Claims filing:** Must file by phone (portal claims online agent filing but phone is primary)
**Cancellations:** Email underwriting@logicinsurance.com
**Key emails:** underwriting@, accounting@, mickie@, mary.alvarado@, donna@ (UW Manager), janet@ (payments), claims@stdins.com

## Portal Navigation

After agent login, left sidebar menu:
- **Quotes** — new quote search/entry
- **Renewals** → **Renewal Quote** — search renewal batch, view/modify renewal details
- **Reports And Queries**
- **Applications**
- **Policy Inquiry/Transactions** → **Billing Inquiry** (sub-menu)
- **Claims**
- **Documents**
- **Contact us**
- **My Account**

## Search

Global search bar on home page: Insured Name, Quote/App/Policy #, Zip Code, Location Address.

Renewal Quote search page has additional filters:
- Customer Name
- FQ/Policy #
- Policy Form/Product (dropdown): Dwelling DP-1, Dwelling TDP-1, Home Owners A, Home Owners B
- Last X Days
- Inception Date range (date pickers)
- Status (dropdown): Active, Renewed, Expired, Cancelled, Non-Renewal, Quote, Referred, Declined, Cancel Pending, Ineligible, etc.

## Search Results Table

Columns: Policy #, Customer, Product, From Date, To Date, Batch ID, Work Basket

Results are paginated (1, 2, ... links). Policy # is a clickable link to the detail page.

## Products

- Dwelling DP-1
- Dwelling TDP-1
- Home Owners A
- Home Owners B

All TX dwelling/fire and homeowners. No auto product.

## Renewal Quote Detail Page

Clicking a policy # from search results opens the Renewal Quote detail page.

**Header info:** Customer name, Policy #, Product, Agent #, Quote #, Version, Inception Date, Expiration Date, Renewal Quote #, Status (Quote, Active, etc.), Transaction Date

**Tabs:**
1. Customer Details — name, address, entity type (Individual/Entity)
2. Policy Details — coverage/limits (iframe content — hard to read via Hermes snapshot)
3. Questionnaire — underwriting questions
4. Business Rule — underwriting rules/engine
5. Payor — billing/payor info
6. Print Package — printable documents
7. Document — uploaded documents

**Actions:**
- Premium (calculate/recalculate premium)
- Track Email

**Breadcrumb:** Renewal Quote > Search Renewal Quote

## Automation Notes

- **Heavy iframe use** — the portal loads content in nested iframes. Hermes browser snapshots show the iframe containers but NOT the content inside them. Playwright-over-CDP to real Chrome is required for automation (same pattern as EZLynx).
- **Login is simple** — no 2FA. Username + password only.
- **Policy # format** — e.g., `SC1-HA-027408-04-00` (carrier code + product code + number + version)
- **Status workflow** — Quote → Converted to App → Active → Renewed/Expired/Cancelled
- **FULL VIEW link** on search page toggles between compact and full display
- The portal appears to be a white-label Beyontec product — other carriers may use the same platform with different branding

## What We Need From This Portal (Automation Targets)

1. **Renewal data pull** — scrape upcoming renewals (next 30-60 days) with coverage details and premium
2. **Policy inquiry** — pull current coverage data for the 22 EMPTY Logic policies that have no ACORD data in EZLynx
3. **Quoting** — eventually, auto-quote renewals with coverage changes (future phase)
