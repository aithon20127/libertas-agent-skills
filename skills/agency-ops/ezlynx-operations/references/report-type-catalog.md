# EZLynx Report Type Catalog — Full Inventory

Last verified: 2026-05-21

## Report Types with URLs and IDs

Format: `ReportWrapper.aspx?Report={name}&id={id}`

### Book of Business

| Report Name | Report Param | ID | Total Columns | Has Coverage? |
|---|---|---|---|---|
| Book of Business Detail | BOB_Expanded | 70 | ~38 | NO |
| Book of Business Summary | BOB_Summary | 68 | — | NO (summary) |
| Cross-Sell Detail | CrossSell_Detail | 74 | — | NO |
| Cross-Sell Master | CrossSell_Master | 75 | — | NO |
| Policy Expiration | BOB_PolicyExpiration_Detail | 28 | 49 | NO |
| **Policy Master** | **Policy_Master** | **146** | **73** | **NO** |

### Policy Management

| Report Name | Report Param | ID | Total Columns | Has Coverage? |
|---|---|---|---|---|
| Change Request Detail | Policy_ChangeRequest_Detail | 40 | — | NO |
| Change Request Summary | Policy_ChangeRequest_Summary | 41 | — | NO |
| Duplicate Account Detail | Policy_DupAccount_Detail | 42 | — | NO |
| New Business Transactions | Policy_NewBusinessTransactions_Details_Expanded | 37 | 46 | NO |
| Pending Transaction Detail | Policy_PendingTransaction_Detail | 38 | 42 | NO |
| **Policy Transaction Detail** | Policy_AllPolicyTransaction_Details_Expanded | 32 | 48 | NO |
| **Policy Transaction Master** | PolicyTransaction_Master | **144** | **76** | NO |
| Policy Transaction Summary | Policy_Transaction_Summary_Expanded | 31 | — | NO |
| Premium Change Detail (Carrier Data) | Policy_PremiumChange_Detail | 39 | 45 | NO |

### Retention Center

| Report Name | Report Param | ID | Total Columns | Has Coverage? |
|---|---|---|---|---|
| Renewal Detail | RetentionCenter_RenewalDetail | 57 | 15 | NO |

### Applicant

| Report Name | Report Param | ID | Total Columns | Has Coverage? |
|---|---|---|---|---|
| Applicant Master | Applicant_Master | 145 | 65 | NO |

### Activity

| Report Name | Report Param | ID | Total Columns | Has Coverage? |
|---|---|---|---|---|
| Activity Detail | Activity_Detail | 19 | — | NO |
| Activity Master | Activity_Master | 20 | — | NO |
| Activity Summary | Activity_Summary | 21 | — | NO |

### Claims

| Report Name | Report Param | ID | Total Columns | Has Coverage? |
|---|---|---|---|---|
| Claims Detail | Claims_Detail | 62 | — | NO |
| Claims Summary | Claims_Summary | 63 | — | NO |
| Claims Transaction Detail | Claims_Transaction_Detail | 64 | — | NO |

### Commission

| Report Name | Report Param | ID | Total Columns | Has Coverage? |
|---|---|---|---|---|
| Commission Detail 2.0 | Commission_Detail_2 | 34 | — | NO |
| Commission Grouping | Commission_Grouping | 35 | — | NO |

### Quotes

| Report Name | Report Param | ID | Total Columns | Has Coverage? |
|---|---|---|---|---|
| Quote Detail | Quotes_Detail | 43 | — | NO |
| Quote Summary | Quotes_Summary | 44 | — | NO |
| Carrier Leaked Detail | Quotes_CarrierLeaked_Detail | 45 | — | NO |
| Carrier Leaked Summary | Quotes_CarrierLeaked_Summary | 46 | — | NO |

### Sales Center

| Report Name | Report Param | ID | Total Columns | Has Coverage? |
|---|---|---|---|---|
| Sales Activity Detail | SalesCenter_Activity_Detail | 47 | — | NO |
| Sales Activity Summary | SalesCenter_Activity_Summary | 48 | — | NO |
| Sales Pipeline Detail | SalesCenter_Pipeline_Detail | 49 | — | NO |
| Sales Pipeline Summary | SalesCenter_Pipeline_Summary | 50 | — | NO |

## DEFINITIVE FINDING: NO Coverage Columns in Any Report Type

Coverage A, B, C, D, E, deductibles, liability limits — NONE of these exist in any EZLynx Reports 5.0 report type. Checked 10+ report types with Manage Columns open. Coverage data lives in individual policy records, NOT in the reporting engine.

### Where coverage data actually lives (CONFIRMED 2026-05-21):
- **EZLynx "Full Policy Details" page** — `PolicyDisplayAndCompare` URL contains complete ACORD XML data with every coverage code, limit, deductible, endorsement, vehicle, driver, dwelling detail, and mortgagee. This is THE primary source. See `references/policy-coverage-pipeline.md`.
- **EZLynx Policy Summary page** — human-readable version at `/applicantportal/policy/{id}/summary/index`
- **Carrier sites** — for actual dec pages, ID cards, and policy documents (PDFs)
- IVANS download XML/EDI data (underlying source that EZLynx decodes for display)

## Column Highlights by Report

### Policy Transaction Master (76 cols) — RICHEST REPORT
Has everything Policy Master has PLUS: Address Line 1-2, City, State, Zip, Email, Phone, Cell Phone, Work Phone, Fax. Best candidate for CRM data ingestion since it includes contact info.

### Policy Master (73 cols) — CURRENT CRM SOURCE
All 73 columns already selected. No more to add. Missing contact info (no addresses, emails, phones).

### Book of Business Detail (~38 cols) — LESS USEFUL
Fewer columns than Policy Master. Adds: Agency, Agency Code, Billing Company, Billing Type, but misses many Policy Master fields.

### Renewal Detail (15 cols) — CURRENT CRM RENEWAL SOURCE
Small report focused on renewal-specific data: premium changes, effective dates, transaction types.

## How to Open a Report Type

1. Navigate to ReportMenu page: `https://app.ezlynx.com/EZLynxReportPortal/ReportMenu`
2. Use Playwright text selector: `await page.locator("text=Policy Transaction Master").first.click()`
3. A NEW PAGE opens in the same browser context — switch to it: `new_page = ctx.pages[-1]`
4. The URL will be: `reportwrapper.aspx?Report={name}&id={id}`
5. The actual report content is in iframe `iFrame1` — target it for Manage Columns

### Managing Columns
- The Manage Columns button is inside the iframe
- Dialog has: Available columns (left), Selected columns (right), Select All / Deselect All
- Use text matching to find coverage-related columns: search for "coverage", "deductible", "liability", "limit"

## Saved Report IDs (for direct navigation)

| Saved Report | SavedReportId | Edit URL |
|---|---|---|
| Covu_Libertas policy BOB | 98960 | `reportwrapper.aspx?Report=Policy_Master&id=146&SavedReportId=98960&IsEditMode=true` |
| CRM Sync - Policy Master | 112844 | `reportwrapper.aspx?Report=Policy_Master&id=146&SavedReportId=112844&IsEditMode=true` |
| Full Policy Master | 112078 | `reportwrapper.aspx?Report=Policy_Master&id=146&SavedReportId=112078&IsEditMode=true` |
| CRM Sync - Renewal Detail | 112846 | `reportwrapper.aspx?Report=RetentionCenter_RenewalDetail&id=57&SavedReportId=112846&IsEditMode=true` |

## Scheduled Report IDs

| Schedule Name | scheduledReportId | savedSSRSReportId |
|---|---|---|
| CRM Renewal Detail Nightly | 41347 | (points to CRM Sync - Renewal Detail) |
| CRM Sync Nightly | 41346 | (points to CRM Sync - Policy Master) |
| Libertas BOB | 35065 | (points to Covu_Libertas policy BOB) |
