# Logic Insurance / Standard Casualty — EZ*Insure Portal Field Map

Portal: https://logicunderwriters.com/beyontecsuite/
Platform: Beyontec Suite (EZ*Insure)
Login: AGENT mode, User ID 2527
Date mapped: 2026-05-22

## Iframe Architecture (UPDATED — 3 levels of nesting)

The quoting form lives inside **three levels** of nested iframes. This is critical for Playwright automation:

```
logic_page (fullquotelist.do) — outer page
  └── frames[0] = parent frame (fullquotelist.do) — tabs, Save/Next buttons, action buttons
      └── child_frames[0] = fullquoterisk.do — intermediate risk info screen
          └── child_frames[0] = uwp2hoa_LUW.do — THE ACTUAL QUOTE FORM (112 fields)
```

**IMPORTANT:** The quote form is TWO levels deep in iframes, not one. The intermediate risk screen (`fullquoterisk.do`) wraps the actual HO-A form (`uwp2hoa_LUW.do`). Both the risk screen AND the form are children of the parent `fullquotelist.do` frame.

**Playwright access patterns:**
```python
logic_page = [find page with 'fullquotelist' in URL]
parent = logic_page.frames[0]

# Risk info screen (intermediate gate):
risk_frame = None
for f in logic_page.frames:
    if 'fullquoterisk' in f.url and 'navigate' in f.url:
        risk_frame = f
        break

# The HO-A form — deepest iframe:
hoa_form = None
for f in logic_page.frames:
    if 'uwp2hoa_LUW' in f.url:
        hoa_form = f
        break
```

**Frame URL changes after save:** When `fQDBSave()` runs, the `fullquoterisk.do` URL changes from `?method=navigate&nextPage=...` to `?method=save`. The child `uwp2hoa_LUW` frame may detach. **Always re-find frames after save/calculate operations.**

## Customer Details Tab (UTDS_LEVEL_M_ID)

### Header Fields (auto-populated)
- Customer: (auto-filled from name fields)
- Quote #: (auto-generated on save)
- Version: (auto)
- Inception Date: (set to current date by default)
- Status: (link, shows quote status)
- Product: Home Owners A / Home Owners B (set from quote type)
- Application #: (auto)
- Expiration Date: (auto, inception + 1 year)
- Agent #: 0000002527 (pre-filled)

### Insured Type
| Field | ID | Type | Notes |
|-------|----|------|-------|
| Individual | `custIndividualId` | radio | Default checked |
| Entity | `custCorporateId` | radio | |

### Name Fields
| Field | ID | Name Attr | Notes |
|-------|----|-----------|-------|
| First Name | `customerFirstNameId` | `txt_customerFirstName` | Required |
| Middle Initial | `txt_customerMiddleInitial` | `txt_customerMiddleInitial` | |
| Last Name | `txt_customerLastName` | `txt_customerLastName` | Required |

### Identity
| Field | ID | Name Attr | Notes |
|-------|----|-----------|-------|
| DOB | `customerDateOfBirthId` | `txt_customerDateOfBirth` | Date picker, format MM/DD/YYYY |
| ID Type | `idTypeId` | `opt_IdType` | Select |
| ID Number | `idNumberId` | `hdn_ssnIdNumber` | Hidden input |

### Insured
| Field | ID | Notes |
|-------|----|-------|
| Currently Insured | `currentlyInsuredId` (`chk_currentlyInsured`) | Checkbox |
| Previous Insurer Name | `currentlyInsuredName` (`txt_previousInsured`) | Text |
| Full Insured Name | `fqcmfullname` (`txt_insured`) | Auto-composite |

### Address
| Field | ID | Name Attr | Notes |
|-------|----|-----------|-------|
| Address Type | `opt_AddressType` | `opt_AddressType` | Select (auto-set to 'W' after save) |
| Address Reference | `hdn_AddressReference` | `hdn_AddressReference` | Hidden (auto-set to '1' after save) |
| Zip Code | `txt_ZipCode` | `txt_ZipCode` | Required — triggers city/state/county auto-fill on Tab-out |
| Address Line 1 | `txt_Address1` | `txt_Address1` | Required |
| Address Line 2 | `txt_Address2` | `txt_Address2` | |
| Address Line 3 | `txt_Address3` | `txt_Address3` | |
| County | `txt_County` | `txt_County` | Auto-filled by zip lookup |
| City | `txt_City` | `txt_City` | Auto-filled by zip lookup (uppercase) |
| State | `txt_State` | `txt_State` | Auto-filled by zip lookup |
| Country | `txt_Country` | `txt_Country` | Auto-filled (US) |

### Zip Code Auto-Lookup Behavior
- Enter zip, then Tab out of the field (or wait ~1 second)
- City, State, County auto-populate (e.g., 76065 → MIDLOTHIAN, TX, Ellis; 76710 → WACO, TX, McLENNAN)
- City appears UPPERCASE in the field
- There is a ">>" link/button next to the zip field that may trigger lookup
- **City field may appear filled but cause errors** — the portal requires you to press Space in the City field to trigger a city name dropdown, then click the correct city name from the list. Even if "WACO" is already in the field, you MUST do the Space-press + click to validate it. Options appear as `<div id="WACO">`, `<div id="DALLAS">`, etc. — click the matching one.
- **County field works similarly** — press Space in the County field to trigger a dropdown, then click the correct county name. The option appears as a `<div>` with the county name as its `id` attribute (e.g., `<div id="MCLENNAN">`).
- **Tab-order for county/city validation (Kyle's explicit instruction):** From Address Line 1, Tab to County, press Space, click the correct county `<div>`, then Tab to City, press Space, click the correct city `<div>`. This order (county BEFORE city) clears the "Locality Change" warning.
- **"Warning! Locality Change" behavior:** The warning clears after Space-press validation of county + city, but REAPPEARS when you click Confirm/Next or Save. It is NOT blocking — just dismiss and keep advancing. Do NOT waste time trying to permanently clear it.
- **Chrome "Save address" autofill popup** — appears constantly on address fields. **Fix: disable in Chrome** at `chrome://settings/addresses` — toggle off "Save and fill addresses." Also check `chrome://settings/payments`. In automation, dismiss with `logic_page.press('body', 'Escape')` before any click interaction. This popup blocks Playwright clicks until dismissed.
- **Popup overlays can intercept clicks** — a "Warning! Locality Change" or similar overlay div may block button clicks. Dismiss with Escape key or by clicking OK on the popup before retrying the intended action.

### Contact
| Field | ID | Name Attr | Notes |
|-------|----|-----------|-------|
| Phone # | `txt_SPQQ_PhoneNo` | `txt_SPQQ_PhoneNo` | Required — auto-formats (8175941234 → 817-594-1234) |
| E-Delivery | `chk_ulm_edel_qq_yn` | `chk_ulm_edel_qq_yn` | Checkbox |
| Work Phone | `txt_SPQQ_WorkPhoneNo` | `txt_SPQQ_WorkPhoneNo` | |
| E-Delivery Mode | `opt_edel_qq_mode` | `opt_edel_qq_mode` | Select (default 'E' = E-mail) |
| Mobile | `txt_SPQQ_CellNo` | `txt_SPQQ_CellNo` | |
| Fax | `txt_SPQQ_FaxNo` | `txt_SPQQ_FaxNo` | |
| Email | `txt_SPQQ_EmailId` | `txt_SPQQ_EmailId` | Required |

### Policy Dates
| Field | ID | Name Attr | Notes |
|-------|----|-----------|-------|
| Req Eff Date | `fullQuoteEffDateId` | `txt_ULM_FMD` | |
| Term | `FQ_CD_term_Id` | `opt_Ulm_Term` | Select (default 01|D = 12 Months) |
| Expiration Date | `fullQuoteExpDateId` | `txt_ULM_TOD` | Auto-calculated |

### Agent Info
| Field | ID | Name Attr | Notes |
|-------|----|-----------|-------|
| Agent/Broker | `txt_ULM_AGENT_ID` | `txt_ULM_AGENT_ID` | Pre-filled 0000002527 |
| Agent Address 1 | `txt_agent_address1` | `txt_agent_address1` | Auto: 600 COLUMBUS AVE STE 4 |
| Agent City | `txt_agent_city` | `txt_agent_city` | Auto: WACO |
| Agent State | `txt_agent_state` | `txt_agent_state` | Auto: TX |
| Agent Contact # | `txt_agent_contact_number` | `txt_agent_contact_number` | Auto: 512-761-6379 |
| Agent Email | `txt_agent_uw_email` | `txt_agent_uw_email` | Auto: service@libertasinsurance.com |

### Manual Renewal Section
| Field | ID | Notes |
|-------|----|-------|
| Manual Renewal | `chk_Ulm_Man_Ren_YN` | Checkbox |
| Prior Policy # | `txt_ulm_pre_pol_no` | |
| Loss Free Years | `txt_ulm_ren_lfr` | |
| Claim Surcharge | `txt_ulm_man_ren_cs` | |

### Hidden Fields (important for form submission)
- `hdn_ULM_PERIOD`, `hdn_ULM_PREM_CALC_TYP`, `hdn_ULM_VALID_DAYS`
- `hdn_AddressPrimaryKey`, `hdn_ContactPrimaryKey`, `hdn_ProcessId`
- `fqqeditContentFlag`, `hdn_UP_PROD_TYP`
- `hdn_UCD_FMD`, `hdn_UCD_TOD` (from/to dates)
- `hdn_Skip_FormValidation`
- `customerFirstNameHidden`, `txt_ULM_AGENT_REF_hidden`
- `txt_ULM_AGENT_PARENT_ID`, `txt_ULM_AGENT_RNK_ID`

## Validation Requirements for Tab Navigation

The portal BLOCKS navigation to Quote Details if Customer Details has validation errors. Known required fields:

**Explicitly required:**
- First Name (`customerFirstNameId`)
- Last Name (`txt_customerLastName`)
- DOB (`customerDateOfBirthId`)
- Phone # (`txt_SPQQ_PhoneNo`)
- Email (`txt_SPQQ_EmailId`)
- Address Line 1 + Zip Code (must be valid and pass carrier lookup)
- City (must be validated via Space-press dropdown — see Zip Lookup section above)
- County (may need Space-press validation too)

**Known blocking errors (observed 2026-05-22):**

| Error Message | Location | Cause | Resolution |
|---|---|---|---|
| "Enter address1/Zipcode to proceed!" | Near Address Line 1 | Address/zip not filled or zip lookup not triggered | Fill zip, Tab-out to trigger lookup, fill address |
| "County is required" | Near County | County not auto-populated | Wait for zip lookup to complete; county auto-fills |
| "Phone # is required" | Near Phone # | Phone not entered | Fill `txt_SPQQ_PhoneNo` |
| "Email ID is required" | Near Email | Email not entered | Fill `txt_SPQQ_EmailId` |
| "Component Mismatch Error" | Near Address Line 1 | Zip code doesn't match carrier's territory, or address format issue | Try a different zip in carrier's service area, or verify address format |
| "Disconnected Phone" | Near Phone # | Phone number fails carrier's real-time phone validation (checks if number is disconnected) | Use a known-valid phone number. Test/fake numbers WILL fail — the carrier runs a LIVE phone check. Use agency number 512-761-6379 or a real client number from the CRM. |
| "Warning! Locality Change" | Under Address Line 1 | Changed zip code on an existing quote, or property address differs from mailing address | **NOT BLOCKING** — dismiss the popup with OK or Escape, then click Confirm/Next. It may reappear after save/next; ignore it and keep advancing. Do NOT waste time trying to clear it by re-validating city/county. |
| Backdated effective date | Risk info screen | Effective date is in the past (even by one day) | Set the effective date to a future date. Carrier will not backdate. Kyle suggests 2 weeks out for test quotes. After midnight, yesterday's date becomes invalid. |
| Chrome "Save address" popup | Overlays entire page | Chrome autofill detects address fields | Press Escape to dismiss before any click interaction. Blocks Playwright clicks until dismissed. |
| Session timeout overlay | Overlays page | Inactivity timeout | Click "Continue Session" button or the session expires and you must re-login. |
| City name error (top of form) | Above form | City was auto-filled from zip lookup but not validated via Space-press dropdown | Press Space in the City field, then click the matching city name `<div>` from the dropdown |

**IMPORTANT:** "Component Mismatch Error" and "Disconnected Phone" are CARRIER-LEVEL validation errors — they come from the Beyontec rating engine, not just front-end JS. These can appear even after all fields are filled. The "Disconnected Phone" check is a LIVE validation — the carrier queries a phone database to verify the number is active. Random/fake phone numbers will fail. Test with real client data from the CRM or the agency's own number to avoid these.

## Tab Navigation

### JS function (from parent page scope)
```javascript
fQPageNavigate('UTDS_LEVEL_M_ID');      // Customer Details
fQPageNavigate('UTDS_LEVEL_R_ID');      // Quote Details
fQPageNavigate('TDS_LEVEL_BR_DTLS_ID'); // Business Rule
```

### Sub-tab navigation (from within Quote Details iframe)
```javascript
menuSelection('UTDS_LEVEL_R_EDIT'); // Quote Details edit form
menuSelection('NOTE');              // Notes
menuSelection('CONDITIONS');         // Conditions
menuSelection('QUESTIONS');          // Questions
```

### Action buttons (from parent frame)
| Button | ID | JS Function | Notes |
|--------|-----|-------------|-------|
| Save | `spansaveAction` | `fQDBSave()` | Saves current form state |
| Calculate/Rate | `spancalcAction` | `fullQuoteCalc()` | Runs premium calculation |
| Get Premium | `spanGetPremiumAction` | (click) | Replaces "Confirm/Next" on Quote Details screen — use this instead of fullQuoteCalc() |
| Freeze | `spanapproveAction` | `fullQuoteApprove()` | Locks the quote |
| Reset | `spancancelAction` | `resetQuickQuote()` | Clears the form |
| Iteration | `spaniterationAction` | `quickQuoteIteration()` | Creates a new version |
| Decline | `DeclineAction` | | |

### Behavior
- `fQPageNavigate` makes an AJAX call that updates the child iframe URL to `?method=navigate&nextPage=<TAB_ID>`
- If validation passes, the form content changes to the target tab's fields
- If validation FAILS, the Customer Details form stays visible with error messages — the iframe URL still updates but the DOM doesn't change
- The "Confirm/Next" button in the parent frame also attempts tab navigation
- Always check for validation errors after tab navigation attempts

### Playwright pattern for tab navigation
```python
# Navigate to Quote Details
logic_page.evaluate("fQPageNavigate('UTDS_LEVEL_R_ID')")
time.sleep(5)

# Verify tab actually switched — check for dwelling/coverage fields
form = None
for f in logic_page.frames:
    if 'uwp2hoa_LUW' in f.url:
        form = f
        break
if form:
    # Quote Details form is loaded
    pass
else:
    # Still on Customer Details — check for errors
    ...
```

## Quote Details Tab (UTDS_LEVEL_R_ID) — FULLY MAPPED 2026-05-22

### Intermediate Risk Info Screen (gate before Quote Details)

After Customer Details is filled and validated, navigating to Quote Details shows an intermediate screen with these fields:

| Field | Element ID | Type | Notes |
|-------|-----------|------|-------|
| Risk Type | `riskTypeId` | Select | Values: HOA, HOB, DP1, TDP1. Pre-set from the "New Quote" menu choice. |
| Insured in FC | `chkRiskInsuredInFC` | Checkbox | "Full Coverage" indicator |
| Effective From Date | `strRisk_FMD` | Input | Pre-filled from Customer Details eff date (e.g., 05-21-2026) |
| Effective To Date | `strRisk_TOD` | Input | Pre-filled from Customer Details exp date (e.g., 05-21-2027) |

**This screen is a GATE** — the Quote Details HTML (117K chars) is already loaded in the child frame but hidden. The portal won't display Quote Details until this intermediate screen is confirmed/submitted. Clicking Confirm/Next on this screen should advance, but the mechanism needs further investigation (Confirm/Next clicks didn't advance during testing — the form remained on the risk info screen).

**Sub-tabs within Quote Details (discovered in hidden HTML):**
| Sub-tab ID | Function | Access via |
|-----------|----------|------------|
| `UTDS_LEVEL_R_EDIT` | Quote Details edit form | `menuSelection('UTDS_LEVEL_R_EDIT')` |
| `NOTE` | Notes | `menuSelection('NOTE')` |
| `CONDITIONS` | Conditions | `menuSelection('CONDITIONS')` |
| `QUESTIONS` | Questions | `menuSelection('QUESTIONS')` |

These sub-tabs are NOT visible until the risk info screen is confirmed. The `UTDS_LEVEL_R_EDIT` element exists but has `display: none` — trying to click it returns "element is not visible" error.

### The HO-A Quote Form (uwp2hoa_LUW.do) — 112 Fields

This is the actual quoting form with property details, coverage limits, and deductible selections. It loads inside the risk frame as a second-level child iframe.

#### Location/Address Section
| Field | ID | Type | Options/Notes |
|-------|-----|------|------|
| Same as Customer | `chk_DEFAULT_CUSTOMER` | checkbox | Copies customer address |
| Zip Code | `txt_PIN_CODE_1` | text | Triggers city/county lookup (same as Customer Details) |
| Address Type | `opt_Other_RiskTyp_Address` | select | |
| Address 1 | `txt_ADDR1_1` | text | |
| Address 2 | `txt_ADDR2_1` | text | |
| County | `txt_ADDR4_1` | text | Auto-filled from zip; may need Space-press validation |
| City | `txt_CITY_1` | text | Auto-filled from zip; MUST press Space + click city `<div>` to validate |
| State | `txt_STATE_1` | text | Auto-filled (hidden but populated) |
| Country | `txt_COUNTRY_1` | text | Auto-filled (US) |
| Address Question | `cmb_Ulrp_Addr_Qn_1` | select | ---Select---, Yes, No |

**PITFALL: City and County fields on the Quote Details form also require Space-press + click validation**, same as Customer Details. After zip lookup populates city/county, you MUST press Space in the City field, then click the matching `<div id="WACO">` element. Same for county — press Space, then click `<div id="MCLENNAN">`. Failure to do this causes a validation error at the top of the form.

#### Dwelling/Property Info Section
| Field | ID | Type | Options/Notes |
|-------|-----|------|------|
| Occupancy Type | `cmb_ULRP_OCCUPANCY_TYP` | select | Owner, Secondary, Vacant, Tenant, Seasonal/Vacation |
| Building Type | `cmb_ULRP_BUILD_TYP` | select | Dwelling, Townhome, Condo, Log Home, Historical Home, Other, Manufactured/Modular Homes |
| Fire Hydrant ≤1000ft | `cmb_ULRP_DIST_FIRE_HYDR` | select | Yes, No |
| Fire Dept ≤5 miles | `cmb_ULRP_DIST_FIRE_STN` | select | Yes, No |
| Fire District | `txt_ULRP_FIRE_DISTRICT` | text | |
| Protection Class | `txt_ULRP_PROTECT_CLS` | select | |
| Territory | `txt_ULR_TERRITORY_ID` | text | Auto-calculated |
| Zip Tier | `txt_ULRP_ZIP_TIER_ID` | text | Auto-calculated |
| Year Built | `txt_ULRP_YEAR_BUILT` | text | |
| Square Feet | `txt_ULRP_SQ_FEET` | text | |
| Construction Type | `cmb_ULRP_CONST_TYP` | select | Asbestos, Brick, Brick Veneer, Frame, Hardi/Concrete Board, Metal, Other |
| # of Stories | `txt_ULRP_NO_OF_FLOORS` | select | 1, 1.5, 2, 2.5, 3 |
| Roof Cover Year | `txt_ULRP_ROOF_CR_YEAR` | text | |
| Roof Construction Type | `txt_ULRP_ROOF_CONS_TYP` | select | Asphalt, Composition, Concrete/Slate, Metal, Other, Tile, Wood |
| # of Families | `txt_ULRP_NO_OF_RES_HH` | select | 1, 2 |
| Roof Impact Class | `cmb_ULRP_ROOF_CR_CLASS` | select | Class I, II, III, IV, None |
| Burglar Alarm Type | `cmb_ULRP_BURG_ALM_TYP` | select | None, Fire, Burglary, Burglary & Fire |
| Loan Year | `txt_ULRP_LOAN_YR` | text | |
| Hip Roof | `cmb_ULRP_ROOF_TYP` | select | Yes, No |
| Fire Protection | `cmb_ULRP_FIRE_PROTECT_TYP` | select | None, Fire Extinguisher, Smoke Alarm, In-door Sprinkler System, Fire Ext & Smoke Alarm |
| Misrepresentation | `opt_Intenal_Misreption` | select | Yes, No — HIDDEN, may need "Addl Fields" expansion |
| Solar Panels | `opt_solar_panels` | select | Yes, No |
| Remove Roof Exclusion | `opt_remove_roofExclson` | select | No, Yes — HIDDEN, may need "Addl Fields" expansion |
| Coverage Desired | `opt_coverage_desired` | select | Yes, No — HIDDEN |
| # of Solar Panels | `txt_no_of_panels` | text | — HIDDEN |
| ITIN | `chk_ULRP_USS_ITIN` | checkbox | |
| ITIN Number | `txt_ULRP_USS_ITIN_NUM` | text | |
| Dump Surcharge | `chk_ULRP_DUMP_SUR` | checkbox | |
| Appraisal/Fair Market Value | `txt_ULRP_FAIR_MKT_VAL` | text | |
| Replacement Cost Description | `cmb_ULRP_REP_COST` | select | **REQUIRED** — Contents, None, Dwelling, Both |
| Replacement Value | `txt_ULRP_REPLACEMENT_VAL` | text | **THE KEY FIELD** — drives Coverage A. This is the ENABLED input. Coverage A (`txt_CVRA`) is DISABLED and auto-populated from this. |
| Actual Value | `txt_ULRP_ACTUAL_VAL` | text | DISABLED |
| Dwelling Style (# corners) | `cmb_ULRP_NO_OF_CORS` | select | 1-4 corner, 2-6 corner, 3-8 corner, 4-10 corner |
| Special Class | `cmb_ULRP_SPL_CLASS` | select | Manufactured homes, Best, Best/Good, Good, Good/Avg, Average, Avg/Low |
| Garage Type | `cmb_ULRP_GARAGE_TYP` | select | No Garage, Attached Garage, Detached Carport, Attached Carport, Detached Garage |
| Garage Sq Ft | `txt_ULRP_GAR_SQ_FEET` | text | |
| Central HVAC | `cmb_ULRP_CENT_HVAC_YN` | select | Yes, No |
| Wood/Fireplace | `cmb_ULRP_WB_GFIRE_PLACE_YN` | select | Yes, No |
| Companion Policy | `chk_ULRP_COMPANION_POLICY_YN` | checkbox | |
| Secondary Bldg Credit | `chk_ULRP_SEC_BLDG_CR_YN` | checkbox | |
| Prior Coverage | `cmb_ULRP_COV_CONT_YN` | select | Prior Coverage, New Purchase, Refinance — **REQUIRED** |
| Prior Ins Co | `txt_Ulrp_Prv_Ins_Comp` | text | |
| Other Ins Co | `txt_Ulrp_Oth_Ins_Comp` | text | |
| Prior Cov Date | `txt_Ulrp_Prior_Cov_Dt` | text | **REQUIRED** when Prior Coverage selected |
| Prior Underwriting Damage | `chk_Ulrp_Prior_Ur_Dmg` | checkbox | |
| # of Mortgagee | `addlEntityYnId` | select | 0, 1, 2 |
| # Addl Insured | `txt_ULRP_NO_OF_ADDL_INSD` | text | |

**PITFALL: Hidden/"Addl Fields" section** — Some fields (like `opt_remove_roofExclson`, `opt_Intenal_Misreption`, `opt_coverage_desired`, `txt_no_of_panels`) are NOT visible by default. The form has an "Addl Fields" button/link that expands additional sections. These fields will timeout with "element is not visible" if you try to interact with them before expanding. Click the "Addl Fields" button first, then interact with the expanded fields.

**PITFALL: Coverage A (Dwelling) is DISABLED** — `txt_CVRA` has `disabled=True`. You cannot type into it. The dwelling limit is set via the **Replacement Value** field (`txt_ULRP_REPLACEMENT_VAL`), which is the enabled input. Coverage A auto-populates from the replacement value after save/calculate. Do NOT try to fill `txt_CVRA` directly — always use `txt_ULRP_REPLACEMENT_VAL`.

**PITFALL: Carrier enforces dwelling coverage range** — after setting Replacement Value and clicking "Get Premium," the carrier may reject the value with a popup like "Dwelling Limit not in the valid range for Replacement Cost. Valid Range is between 186,854 and 228,377." The carrier calculates the valid range based on year built, sq ft, construction type, etc. You MUST set the replacement value within the carrier's calculated range. If you see this error, adjust `txt_ULRP_REPLACEMENT_VAL` to a value within the stated range and retry.

**PITFALL: Required fields that don't look required** — `cmb_ULRP_REP_COST` (Replacement Cost Description) and `txt_Ulrp_Prior_Cov_Dt` (Prior Coverage Date) show validation errors ("Replac Cost Des is required", "Pur Date is required") that aren't obvious from the form layout. Always set these when filling the form.

#### Coverage Limits Section
| Field | ID | Type | Options/Notes |
|-------|-----|------|------|
| Coverage A - Dwelling | `txt_CVRA` | text | **DISABLED** — set via `txt_ULRP_REPLACEMENT_VAL` instead |
| Coverage Other Structures | `rate\|OTHSTRU` | select | 10%, 15%, 20%, 25%, 30%, 35%, 40%, 45% |
| Coverage B - Personal Property | `rate\|PP` | select | 40%, 60% |
| Coverage B - PP Off Premises | `rate\|PPOP` | select | 10% |
| Coverage Loss of Use | `rate\|LOU` | select | 10% |
| Coverage C - Personal Liability | `txt_CVRC` | select | 25,000 / 50,000 / 100,000 / 300,000 |
| Coverage D - Medical Payments | `txt_CVRD` | select | 500 / 1,000 / 2,000 / 3,000 / 4,000 / 5,000 |

#### Endorsements Section
| Field | ID | Type | Options/Notes |
|-------|-----|------|------|
| Firearm & Animal Liability | `ANILIA` | checkbox | |
| HO 105 Residence Glass | `HO105` | checkbox | |
| HO 110 Jewelry/Watches/Furs | `txt_UNSJS` | text | Dollar limit |
| HO 111 Business Personal | `txt_HO111` | text | Dollar limit |
| HO 112 Money/Bank Cards | `txt_HO112` | text | Dollar limit |
| HO 113 Bullion/Valuable Papers | `txt_HO113` | text | Dollar limit |
| HO 120 TV/Radio Antenna | `txt_HO120` | text | Dollar limit |
| HO 126 Personal Computer | `txt_HO126` | select | $1,000 / $2,000 / $3,000 |
| HO 135 Constr Building Laws | `rate\|HO135` | select | 10%, 15%, 25% |
| HO 160 Scheduled Personal Prop | `txt_HO160` | text | Dollar limit |
| HO 161 Mold/Fungi/Microbes | `rate\|HO161` | select | ---Select---, 100%, 25%, 50% |
| HO 225 Addl Premises Liability | `txt_HO225L` | text | |
| HO 225 Addl Premises Med Pay | `txt_HO225MP` | text | |
| HO 301 Additional Insured | `HO301` | checkbox | |
| Addl Insured Perils & Ltd Water | `txt_SADW` | select | $5,000 / $10,000 / $15,000 / $25,000 |
| Extended Repl Cost Protection | `rate\|ERCP` | select | ---Select---, 125%, 150% |
| Ltd Loss Settlement Endorsement | `SCLRCHOA01` | checkbox | |
| Loss Settlement Endorsement | `SCRCHOA01` | checkbox | |
| Enhanced Partial Loss | `NLH011` | checkbox | |
| Excl Cosmetic Dmg Non-Hail Roof | `EXDMGNHR` | checkbox | |
| Excl Cosmetic Dmg Metal Struct | `EXDMGMET` | checkbox | |

#### Deductibles Section
| Field | ID | Type | Options/Notes |
|-------|-----|------|------|
| Wind/Hail/Hurricane Ded | `txtXS_CLAUSE1` | select | 1%, 1.5%, 2%, 2.5%, 3%, 4%, 5% |
| All Other Perils Ded | `txtXS_CLAUSE2` | select | 1%, 1.5%, 2%, 2.5%, 3%, 4%, 5% |

#### Claims History Section
| Field | ID | Type | Options/Notes |
|-------|-----|------|------|
| Losses in last 5 years | `txt_ULRP_NON_WEATHER_CLM` | select | Yes, No |
| # Weather Claims | `txt_ULRP_NUM_WEATHER_CLM` | text | Default 0 |

#### Default Values (observed on fresh form)
- Coverage Other Structures: 10%
- Coverage B - Personal Property: 40%
- Coverage B - PP Off Premises: 10%
- Coverage Loss of Use: 10%
- Coverage C - Personal Liability: 25,000
- Coverage D - Medical Payments: 500
- Wind/Hail Ded: 1%
- All Other Perils Ded: 1%
- # of Stories: 1
- Dwelling Style: 1-4 corner
- Special Class: Average
- Roof Impact Class: None
- Burglar Alarm: None
- # of Mortgagee: 0
- # of Families: 1 (when set)

## Premium & Coverage Summary Screen (after "Get Premium")

After clicking "Get Premium" on the Quote Details screen, the Premium & Coverage Summary loads (navigated via the "Premium" tab in the parent frame's navigation). This is a read-only results page.

**Sample quote (QHA-107040, Sarah Mitchell, HO-A, Waco TX 76710):**
- Total Premium & Fee: **$1,892.67**
- Dwelling (Cov A): $250,000 / $1,762.00
- Other Structures 10%: $25,000 / Included
- Personal Property 40%: $100,000 / Included
- PP Off Premises 10%: $10,000 / Included
- Loss of Use 10%: $25,000 / Included
- Personal Liability: $25,000 / Included
- Medical Payments: $500 / Included
- Wind/Hail Deductible: 2% / -$141.00
- Firearm/Animal Liab Limitation: -$7.00
- Loss Settlement Endorsement: $176.00
- Credits: Fire Safety 4%, Loss Experience 5%, Age of Risk 9% / Total -$317.00
- Surcharges: Age of Roof / $194.00
- Fees: Policy Fee $125, Inspection Fee $60, VFD Fee $1.50, TFPA 2023 $1, TFPA 2024 $3, CAT Fee $35.17

**Navigation back to Quote Details:** Use the "Quote Details" tab or `fQPageNavigate('UTDS_LEVEL_R_ID')` from the parent frame. After returning, re-find the HO-A form frame (it may have reloaded).

**Key observation:** The default coverage selections (Cov C = 25K, Med Pay = 500) produce the cheapest premium. Increasing liability and med pay adds to premium. The "Loss Settlement Endorsement" (checked by default) adds significant premium ($176). Wind/Hail deductible at 2% provides a credit.

## HO-B Quote Details — NOT YET MAPPED

HO-B (Home Owners B / Broad Form) uses the same Beyontec platform and iframe structure. The form is expected at `uwp2hob_LUW.do` (by analogy with `uwp2hoa_LUW.do`). The customer details flow is identical. The Quote Details form will have different perils, coverage options, and endorsements specific to the HO-B form. **This needs to be mapped in a future session** by starting a New Quote HO-B and capturing all field IDs, dropdown options, and endorsement checkboxes the same way HO-A was mapped.

## Business Rule Tab (TDS_LEVEL_BR_DTLS_ID)

NOT YET MAPPED.

## Playwright Automation Pattern (Tested 2026-05-22)

### CRITICAL: Do NOT launch new Chrome instances
Always connect to Kyle's existing Chrome on port 9222. Launching extra Chrome windows froze his computer. If Chrome isn't running, ask Kyle to open it — don't spawn one yourself. This applies to ALL carrier portal automation, not just Logic.

```python
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    # Connect to EXISTING Chrome — NEVER launch a new one
    browser = p.chromium.connect_over_cdp('http://localhost:9222')
    ctx = browser.contexts[0]
    
    # Find the Logic quote page
    logic_page = None
    for pg in ctx.pages:
        if 'fullquotelist' in pg.url:
            logic_page = pg
            break
    
    # DISMISS any Chrome autofill popup or session timeout overlay
    try:
        logic_page.press('body', 'Escape')  # Chrome "Save address" popup
    except:
        pass
    try:
        cont = logic_page.query_selector('text=Continue Session')
        if cont and cont.is_visible():
            cont.click()
    except:
        pass
    
    parent = logic_page.frames[0]
    
    # STEP 1: Fill Customer Details
    form = parent.child_frames[0]  # quickquotecustomer.do
    form.fill('#customerFirstNameId', 'Sarah')
    form.fill('#txt_customerLastName', 'Mitchell')
    form.fill('#customerDateOfBirthId', '06/20/1978')
    form.fill('#txt_ZipCode', '76710')
    form.press('#txt_ZipCode', 'Tab')
    time.sleep(3)  # Wait for city/state/county auto-fill
    
    # VALIDATE city via Space-press + click
    form.press('#txt_City', ' ')
    time.sleep(1)
    form.query_selector('#WACO').click()  # Click the city div
    time.sleep(0.5)
    
    form.fill('#txt_Address1', '1500 Lake Air Dr')
    form.fill('#txt_SPQQ_PhoneNo', '5127616379')  # Agency number — carrier validates live
    form.fill('#txt_SPQQ_EmailId', 'sarah@email.com')
    time.sleep(0.5)
    
    # Save
    parent.evaluate("fQDBSave()")
    time.sleep(3)
    
    # STEP 2: Navigate to Quote Details
    parent.evaluate("fQPageNavigate('UTDS_LEVEL_R_ID')")
    time.sleep(5)
    
    # STEP 3: Confirm the intermediate risk info screen
    # (risk frame has riskTypeId, eff dates — may need Confirm/Next)
    parent.query_selector('text=Confirm/Next').click()
    time.sleep(5)
    
    # STEP 4: Find and fill the HO-A form
    hoa_form = None
    for f in logic_page.frames:
        if 'uwp2hoa_LUW' in f.url:
            hoa_form = f
            break
    
    if hoa_form:
        # Validate city/county on the property form too
        hoa_form.press('#txt_CITY_1', ' ')
        time.sleep(1)
        hoa_form.query_selector('#WACO').click()
        
        hoa_form.fill('#txt_ADDR1_1', '1500 Lake Air Dr')
        
        # Property details
        hoa_form.select_option('#cmb_ULRP_OCCUPANCY_TYP', 'Owner')
        hoa_form.select_option('#cmb_ULRP_BUILD_TYP', 'Dwelling')
        hoa_form.select_option('#cmb_ULRP_CONST_TYP', 'Frame')
        hoa_form.select_option('#cmb_ULRP_DIST_FIRE_HYDR', 'Yes')
        hoa_form.select_option('#cmb_ULRP_DIST_FIRE_STN', 'Yes')
        hoa_form.fill('#txt_ULRP_YEAR_BUILT', '1995')
        hoa_form.fill('#txt_ULRP_SQ_FEET', '1800')
        hoa_form.select_option('#txt_ULRP_NO_OF_FLOORS', '1')
        hoa_form.fill('#txt_ULRP_ROOF_CR_YEAR', '2015')
        hoa_form.select_option('#txt_ULRP_ROOF_CONS_TYP', 'Composition')
        hoa_form.select_option('#cmb_ULRP_GARAGE_TYP', 'Attached Garage')
        hoa_form.select_option('#cmb_ULRP_CENT_HVAC_YN', 'Yes')
        hoa_form.select_option('#cmb_ULRP_WB_GFIRE_PLACE_YN', 'No')
        hoa_form.select_option('#cmb_ULRP_COV_CONT_YN', 'Prior Coverage')
        hoa_form.fill('#txt_Ulrp_Prior_Cov_Dt', '01/01/2025')
        hoa_form.select_option('#txt_ULRP_NON_WEATHER_CLM', 'No')
        
        # Required hidden fields
        hoa_form.select_option('#cmb_ULRP_REP_COST', 'Dwelling')
        
        # Set dwelling limit via Replacement Value (NOT Coverage A — it's disabled)
        hoa_form.fill('#txt_ULRP_REPLACEMENT_VAL', '250000')
        
        # Adjust coverages and deductibles
        hoa_form.select_option('#txtXS_CLAUSE1', '2%')   # Wind/Hail
        hoa_form.select_option('#txtXS_CLAUSE2', '2%')   # AOP
        hoa_form.select_option('#txt_CVRC', '100,000')   # Liability
        hoa_form.select_option('#txt_CVRD', '1,000')     # Med Pay
        
        # Save
        parent.evaluate("fQDBSave()")
        time.sleep(3)
        
        # RE-FIND the form frame (save may cause frame detachment)
        hoa_form = None
        for f in logic_page.frames:
            if 'uwp2hoa_LUW' in f.url:
                hoa_form = f
                break
        
        # Calculate premium — use "Get Premium" button (not Confirm/Next)
        get_premium = parent.query_selector('#spanGetPremiumAction')
        if get_premium:
            get_premium.click(force=True)
        else:
            parent.evaluate("fullQuoteCalc()")
        time.sleep(10)
        
        # RE-FIND frame again and read premium
        hoa_form = None
        for f in logic_page.frames:
            if 'uwp2hoa_LUW' in f.url:
                hoa_form = f
                break
        # Read premium from form body text
```

### Key Automation Pitfalls

1. **Frame detachment after save/calculate** — The `uwp2hoa_LUW` iframe may detach when `fQDBSave()` or `fullQuoteCalc()` runs. ALWAYS re-find the frame by iterating `logic_page.frames` and checking for `uwp2hoa_LUW` in the URL. Never cache the frame reference across save/calculate calls.

2. **City/County Space-press validation** — BOTH the Customer Details form AND the Quote Details property form have city/county fields that require Space-press + click validation. The auto-filled text is NOT sufficient — the portal requires the dropdown selection. Look for `<div id="CITYNAME">` elements after pressing Space.

3. **Coverage A is DISABLED** — Never try to fill `txt_CVRA` directly. It's `disabled=True` and resets to 0 after save. Use `txt_ULRP_REPLACEMENT_VAL` (Replacement Value) instead — that's the enabled input that drives the dwelling limit.

4. **Hidden "Addl Fields" section** — Some fields are not visible by default. Click the "Addl Fields" button first to expand them. Trying to interact with hidden fields causes Playwright timeout ("element is not visible").

5. **Required fields that aren't obvious** — `cmb_ULRP_REP_COST` (Replac Cost Des) and `txt_Ulrp_Prior_Cov_Dt` (Prior Cov Date) are required but don't have visual required markers. They cause "Replac Cost Des is required" and "Pur Date is required" errors on save/calculate.

6. **Carrier validates phone numbers LIVE** — "Disconnected Phone" error means the carrier checked a phone database and the number is flagged as disconnected. Use the agency number (512-761-6379) or real client numbers from the CRM. Random 10-digit numbers will fail.

7. **"Component Mismatch Error"** is carrier-level — the address/zip doesn't match the carrier's rating territory. Try a known-in-territory zip.

8. **Don't change zip on an existing quote** — triggers "Warning! Locality Change" popup. But this warning is NOT blocking — you can dismiss and advance past it with Confirm/Next. It may reappear; ignore it and keep going.

9. **Effective date MUST be future-dated** — the carrier will not allow backdated quotes. If the effective date is in the past (even by one day past midnight), the quote cannot proceed. Always set the effective date at least a few days out. For test quotes, Kyle suggests 2 weeks forward.

10. **Chrome "Save address" autofill popup** — dismiss with Escape before any click interaction. This popup blocks Playwright clicks on address fields.

11. **Portal session timeout** — "Continue Session" overlay appears after inactivity. Click it or the session expires and you must re-login.

9. **Never launch new Chrome for carrier portals** — use existing Chrome on port 9222. Extra Chrome windows froze Kyle's machine.

10. **Form data can be wiped** — On at least one occasion, filling the Customer Details form and then navigating caused all entered data to disappear. Always verify field values after navigation events and be prepared to re-fill.

## Renewal Quote Search

URL: Navigate via Renewals → Renewal Quote

Search filters:
- Customer Name
- FQ/Policy# 
- Product: Dwelling DP-1, TDP-1, Home Owners A, Home Owners B
- Inception Date
- Status

Results columns: Policy#, Customer, Product, From/To Date, Batch ID, Work Basket

## Key Contacts

- Underwriting: 214-739-0071 / 1-888-315-6442 (Sue Blackwell X143)
- Claims: 800-522-0146 Opt5
- Cancellations: underwriting@logicinsurance.com
