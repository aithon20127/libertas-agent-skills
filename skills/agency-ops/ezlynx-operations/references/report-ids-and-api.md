# EZLynx Report IDs & API Reference

## Saved Report Direct URLs (for Edit mode, add &IsEditMode=true)

| Saved Report | savedReportID | URL |
|---|---|---|
| Covu_Libertas policy BOB | 98960 | `reportwrapper.aspx?Report=Policy_Master&id=146&SavedReportId=98960&reportMenuUrl=https%3a%2f%2fapp.ezlynx.com%2fEZLynxReportPortal%2fReportMenu` |
| CRM Sync - Policy Master | 112844 | Same pattern, SavedReportId=112844 |
| Full Policy Master | 112078 | Same pattern, SavedReportId=112078 |
| CRM Sync - Renewal Detail | 112846 | `reportwrapper.aspx?Report=RetentionCenter_RenewalDetail&id=57&SavedReportId=112846&reportMenuUrl=...` |

All URLs are relative to `https://app.ezlynx.com/EZLynxReportPortal/`

## Reports API

### Working Endpoints
- `GET /EZLynxReportsAPI/saved-report/v1/menu` — returns saved reports + categories for the org
  - Response shape: `{ savedReportMenu: SavedReport[], categories: Category[], userHasSharePermission: bool, userHasSchedulePermission: bool, orgId: 43201 }`
  - Each SavedReport: `{ savedReportID, savedReportDescription, savedReportName, reportMenu: { reportMenuID, platform, linkText, name, category, isActive, canSchedule, iconUrl, iconColor }, category, url, canManipulateReport, createdBy, sharedWithUsersCount }`
  - Categories returned are ONLY those with saved reports, NOT the full catalog

### Confirmed 404 Endpoints (do not retry)
/report/v1/types, /report/v1/catalog, /report/v1/list, /report/v1/all, /report/v1/menu, /report/v1/categories, /saved-report/v1/list, /saved-report/v1/catalog, /saved-report/v1/types, /report-menu/v1/list, /report-menu/v1/all, /reportmenu/v1/list, /reportmenu, /v1/reports, /v1/report-types, /v1/menu-items, /v1/catalog, /report/v1/schedule, /saved-report/v1/schedules

All relative to `https://app.ezlynx.com/EZLynxReportsAPI`

## Policy Master Column Finding

- Policy_Master (reportMenuID 146) has 73 total available columns
- ALL 73 are selected in CRM Sync - Policy Master (Select All checked)
- **Zero coverage columns exist in this report type** — Coverage A-E, deductibles, liability limits are simply not available
- The full raw row IS saved in `ezlynx_raw` table in Supabase but the source CSV lacks coverage data
- Coverage data must come from other report types (Policy Management category most likely)

## Key DOM Elements in Report Viewer (inside iFrame1)

- Manage Columns button: found in the report filter/header area
- Manage Columns dialog: two-panel list (Available left, Selected right) with Select All / Deselect All
- Filter panel includes: Branch, Assigned Producer, Line Of Business, Master Company, Writing Company, Rating State, Policy Status, Policy Term, Policy Type, Producer Code, Producer Code Override, Service Team
- Additional Filters (6): Applicant Status, Billing Type, CSR, Annualized Premium, etc.
- Data summary shows: customer count, policy count, annualized premium total

## Angular Scope Structure (ReportMenu page)

- Controller element: `[ng-controller]`
- Scope access: `angular.element(document.querySelector('[ng-controller]')).scope()`
- Key properties: `vm.savedReports` (array of 4 saved reports), `vm.loadingSavedReports`, `vm.init`
- The catalog report types are NOT in the scope data — they appear to be rendered server-side in the HTML
- Attempting to serialize the full `vm` object causes timeouts — extract specific properties only

## Network Requests on ReportMenu Load

Key non-static requests:
1. `GET /EZLynxReportsAPI/saved-report/v1/menu` — saved report catalog
2. `GET /EZLynxPortalAPI/Organizations/GetOrganizationLabels?includeNonActive=false` — org labels
3. `GET /EZLynxPortalAPI/Notifications/GetUnreadNotificationCount` — notification count
4. `GET /ApplicantApi/v1/site-nav?requestUrl=...` — site navigation
5. `GET /DiscussionApi/v7/tasks/counts-by-current-user` — task counts
6. Various Datadog RUM telemetry (browser-intake-datadoghq.com) — ignore

## Next Steps for Coverage Data

1. **Open Policy Management report types** — need to access Book of Business Detail, Policy Transaction Detail, Policy Transaction Master. The Angular catalog card click mechanism is the blocker.
2. **Possible workaround**: Navigate to a NEW reportwrapper URL without a SavedReportId, just with a Report name and id. E.g., try `reportwrapper.aspx?Report=Book_of_Business_Detail&id=XXX` — but the reportMenuID for these types is unknown.
3. **Alternative**: Have Kyle manually click a catalog card in Chrome, then connect to whatever page opens.
4. **Alternative**: Search for the reportMenuIDs in the HTML source of the ReportMenu page — the catalog cards must reference them somewhere in the rendered HTML or in inline script data.
