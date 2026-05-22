---
name: logic-quoting
description: Automate Logic-Standard Casualty HO-A/HO-B quoting via their EZ*Insure (Beyontec Suite) portal. Includes complete field maps, validation rules, iframe navigation, and Playwright-over-CDP automation approach.
tags: [logic, standard-casualty, quoting, hoa, hob, beyontec, ez-insure, playwright, cdp]
---

# Logic-Standard Casualty Quoting

## Portal Info
- URL: https://logicunderwriters.com/beyontecsuite/
- Login: Agent mode, ID 2527, password `libertas2026`
- Products: HO-A, HO-B, DP1, TDP1
- Portal is Beyontec Suite / EZ*Insure — deeply nested iframes

## Login (Agent Mode)

**Direct URL** (skip the EMPLOYEE/AGENT landing page entirely):
```
https://logicunderwriters.com/beyontecsuite/eicm/pages/common/amlogin.jsp?fromId=A
```

**Login fields**: `#loginname` and `#loginpassword` — directly on the page, NOT inside an iframe.

**PITFALL: The LOGIN "button" is NOT a `<button>` tag.** It's an image/styled element that does NOT respond to Playwright click (`get_by_role('button')`, `query_selector('button')`, or `click()` all fail). The working approach:
```python
page.query_selector('#loginname').fill(AGENT_ID)
page.query_selector('#loginpassword').fill(PASSWORD)
page.evaluate("() => document.forms[0].submit()")
```
The form action is `loginAction.do?method=login`. After submit, the page becomes the portal home (URL stays `amlogin.jsp` but content changes to the task/search page with "Log Out" visible).

**"Already logged in" check**: Look for "New Quote" or "Log Out" text in `document.body.innerText`.

## Portal Home Iframe Structure

After login, the portal home (`wfdemoindex.do?method=loadMyTask`) renders content in 3 iframes:

| Iframe ID | URL | Purpose |
|-----------|-----|---------|
| `NewsEventsId` | `agentNewOrEvents` | News/events |
| `MyTransId` | `agentmenu1.jsp` | **Navigation menu** — Quotes, New Quote HO-A/HO-B, etc. |
| `NewQuoteDescId` | `agentDescDtls.js` | Description panel |

The nav menu links (e.g. "New Quote HO-B") are inside the `agentmenu1.jsp` iframe. You must click "Quotes" first to expand the submenu, then click "New Quote HO-B".

**PITFALL: Clicking "New Quote HO-B" opens a NEW browser tab** at `fullquotelist.do?method=newFq&...&APMP_PROD_ID=HOB`. The original login page stays open. Your `logic_page` reference is now stale — you MUST search `ctx.pages` for the new fullquotelist page:
```python
for pg in ctx.pages:
    if 'fullquotelist' in pg.url:
        logic_page = pg
        break
```

## CRITICAL RULES
- **NEVER spawn a new Chrome window** — it freezes Kyle's computer. Use existing Chrome on port 9222 ONLY.
- **Session timeouts** — the portal logs you out after inactivity. Always re-login at the start of a script.
- **Chrome autofill popup** — disable via chrome://settings/addresses (toggle off "Save and fill addresses"). In automation, press Escape to dismiss if it appears.
- **Frame detachment** — navigating between tabs causes iframe reloads. Always re-find frames after any navigation. Use `parent.evaluate()` with JS that walks `window.frames` recursively — it's more resilient than Playwright's frame objects which detach on reload.
- **Login button is NOT a `<button>`** — see Login section below.
- **"New Quote HO-B" click opens a NEW browser tab** — the `logic_page` reference becomes stale; must re-find the fullquotelist page and switch. See Workflow step 2.
- **Pipe characters in CSS selectors** — IDs like `rate|PP` break `#rate|PP` (CSS doesn't allow `|`). Use `[id="rate|PP"]` or `document.getElementById()` via JS instead.
- **Coverage selects are MIXED (HO-B)** — some are editable (OTHSTRU, LOU, CVRC, CVRD, deductibles), others are disabled/locked (PP, HO162, ERCP, HO135). For locked selects, use `force_select()`: force-enable via JS, set value, dispatch change event, then save. See Coverage section.
- **"Same as Customer" checkbox must be explicitly clicked** — After Confirm/Next and the property form frame loads, location fields are NOT auto-populated. Click `#chkSameAs` in the form frame to copy customer address into property location fields. They then become readonly and can be skipped.
- **Confirm/Next button** — The correct ID is `#idConfmNxt`, NOT `#spanconfirmAction`.
- **Save before Calc** — `fullQuoteCalc()` checks `isChangeCheck()` which looks at TWO hidden flags: `#isChangedPSave` (in parent/fullquotelist frame) and `#isChanged` (in the `fqFrame` iframe). Even after `fQDBSave()`, these flags may remain `"true"`, causing `fullQuoteCalc()` to show the "Please save the quote" alert and refuse to run. **Fix**: After saving, explicitly clear both flags to `"false"` via JS before calling `fullQuoteCalc()`. See "Save/Calc Gatekeeping" section below.
- **`menuSelection('UTDS_LEVEL_R_EDIT')` RELOADS the form frame** — Do NOT call this after Confirm/Next. It triggers a full form-frame reload that wipes all filled fields. After Confirm/Next, the `uwp2hob_LUW.do` / `uwp2hoa_LUW.do` frame loads automatically with the property form ready to fill — no menuSelection needed.
- **Form fills via DOM `.value` assignment don't persist server-side** — Setting `el.value = '01'` via JS works client-side (verification passes) but the server never receives the values. When `fullQuoteCalc()` submits to the rating engine, it gets a `java.lang.NullPointerException` (HTTP 500) because the form POST body is empty or incomplete. **Solution under investigation**: May need to (a) dispatch proper `change`/`input` events that trigger the portal's own dirty-tracking AJAX saves, (b) call `ajaxTempSave()` from the form frame before the parent save, or (c) submit the form through the portal's own `ajaxPermanentSave()` function with serialized data.
- **`select_option` value vs text** — For `rate|*` and `txtXS_*` fields, the option value (not display text) is the selection key. The script's `select_option` function uses `sel.select_option(value=...)` for these fields. For other selects, partial text matching is used.

## Iframe Structure
The portal is 3 iframes deep, but the structure differs between the portal home and the quoting page.

### Portal Home (after login, before clicking New Quote)
- **Parent page**: `wfdemoindex.do` — the outer wrapper with "Log Out", search bar
- **iframe MyTransId**: `agentmenu1.jsp` — nav menu (Quotes → New Quote HO-A/HO-B, etc.)
- **iframe NewsEventsId**: news/events panel
- **iframe NewQuoteDescId**: description panel

### Quoting Page (after clicking New Quote HO-A/HO-B)
- **Parent page**: `fullquotelist.do` — contains Save/Calc/Confirm JS functions (fQDBSave, fullQuoteCalc, fQPageNavigate)
- **iframe[1]** (customer form): `quickquotecustomer.do` — Customer Details tab
- **Nested iframe inside fullquoterisk** (property form): `uwp2hoa_LUW.do` for HO-A, `uwp2hob_LUW.do` for HO-B — all property/coverage fields

**Key point**: The parent frame with `fQDBSave()` and `fullQuoteCalc()` is the `fullquotelist.do` frame itself (not a child). Find it by URL:
```python
def get_fullquotelist_frame(page):
    for f in page.frames:
        if 'fullquotelist' in f.url:
            return f
    return None
```

**Customer form detection**: The `quickquotecustomer.do` iframe content may take several seconds to load after the page opens. Use a retry loop with `wait_for_selector` or `query_selector`:
```python
for attempt in range(10):
    for f in logic_page.frames:
        if 'quickquotecustomer' in f.url:
            el = f.query_selector('#customerFirstNameId')
            if el:
                cust_frame = f
                break
    if cust_frame:
        break
    time.sleep(3)
```

To find the property form frame from parent:
```javascript
function findFrame(frames) {
    for (let i = 0; i < frames.length; i++) {
        try {
            if (frames[i].location.href.indexOf('uwp2') !== -1) return frames[i];
            let nested = findFrame(frames[i].frames);
            if (nested) return nested;
        } catch(e) {}
    }
    return null;
}
```

## Save/Calc Gatekeeping (CRITICAL)

The portal gates `fullQuoteCalc()` behind `isChangeCheck()`. If this returns `"true"`, you get an alert "Please save the quote and calculate the premium" and the calc is blocked.

**What `isChangeCheck()` checks** (from portal source):
```javascript
function isChangeCheck() {
    if ($("#isChangedPSave").val() == "true") return "true";
    if ($("#fqFrame").contents().find("#isChanged").val() == "true") return "true";
    return "false";
}
```
Two flags, both must be `"false"`:
1. `#isChangedPSave` — in the parent (fullquotelist) frame. Set by `isChangeDbSaveCheck()`, which reads `$("#isChangedPSave").val()`.
2. `#isChanged` — in the `fqFrame` iframe (the form container). Set when form fields are modified.

**After `fQDBSave()` completes**, these flags are NOT automatically cleared. You must clear them manually:
```python
parent_frame = get_fullquotelist_frame(logic_page)
parent_frame.evaluate("""() => {
    try { $("#isChangedPSave").val("false"); } catch(e) {}
    try { $("#fqFrame").contents().find("#isChanged").val("false"); } catch(e) {}
}""")
# Verify
check = parent_frame.evaluate("() => isChangeCheck()")
assert check != "true", "isChangeCheck still true!"
```

**Recommended save sequence** (VERIFIED WORKING 2026-05-22):
1. Fill ALL form fields via `js_fill()` (see function in Workflow section) — this sets `isRiskPageChanged` and `isChanged` to "true" in fqFrame
2. Call `fQDBSave()` from the fullquotelist parent frame
3. Wait 15-20 seconds for save to complete (server-side DB write)
4. Verify save completed — check that the page didn't navigate to an error page
5. Clear `#isChangedPSave` to `"false"` in the parent frame
6. Clear `#isChanged` and `#isRiskPageChanged` to `"false"` in the fqFrame (customer iframe)
7. Verify `isChangeCheck()` returns `"false"`
8. Call `fullQuoteCalc()` — this submits the form to the rating engine

**CRITICAL: The order matters.** You MUST call `fQDBSave()` while the dirty flags are still "true" — that's what tells the portal there are changes to save. Clearing flags BEFORE saving means the portal thinks nothing changed and won't persist your field values.

**If calc returns HTTP 500 NullPointerException**: The form values were not persisted server-side. This means `fQDBSave()` didn't actually save the risk page data. Possible causes:
- The `riskValidation()` function in the form frame rejected the data (check for validation errors)
- Required fields are missing (address, year built, square feet, construction type, occupancy, etc.)
- The `isRiskPageChanged` flag wasn't "true" when `fQDBSave()` was called

**js_fill helper** — Use this for ALL field fills, handles disabled/readonly and sets dirty flags:
```python
def js_fill(frame, field_id, value):
    """Fill a field via JS, handle disabled/readonly, trigger events, set dirty flags."""
    return frame.evaluate("""({fieldId, val}) => {
        const el = document.getElementById(fieldId);
        if (!el) return 'NOT FOUND: ' + fieldId;
        const wasDisabled = el.disabled;
        el.disabled = false;
        el.readOnly = false;
        if (el.tagName === 'SELECT') {
            el.value = val;
            el.dispatchEvent(new Event('change', {bubbles: true}));
        } else {
            el.value = val;
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            el.dispatchEvent(new Event('blur', {bubbles: true}));
        }
        // Set dirty flags in parent fqFrame
        try {
            const fqDoc = parent.document.getElementById('fqFrame')?.contentDocument 
                        || parent.frames['fqFrame']?.document;
            if (fqDoc) {
                const irpc = fqDoc.getElementById('isRiskPageChanged');
                if (irpc) irpc.value = 'true';
                const ic = fqDoc.getElementById('isChanged');
                if (ic) ic.value = 'true';
            }
        } catch(e) {}
        try {
            const ic = parent.document.getElementById('isChanged');
            if (ic) ic.value = 'true';
            const irpc = parent.document.getElementById('isRiskPageChanged');
            if (irpc) irpc.value = 'true';
        } catch(e) {}
        return 'OK: ' + fieldId + '=' + val + (wasDisabled ? ' (was disabled)' : '');
    }""", {"fieldId": field_id, "val": str(value)})
```

## Tab Navigation
- `fQPageNavigate('UTDS_LEVEL_M_ID')` → Customer Details
- `fQPageNavigate('UTDS_LEVEL_R_ID')` → Quote Details (property/coverages)
- `fQPageNavigate('TDS_LEVEL_BR_DTLS_ID')` → Business Rule
- `fQDBSave()` → Save current form
- `fullQuoteCalc()` → Calculate/rate (Get Premium)
- `fullQuoteApprove()` → Freeze quote
- Sub-tabs within Quote Details: `menuSelection('UTDS_LEVEL_R_EDIT')` (edit form), `menuSelection('NOTE')`, `menuSelection('CONDITIONS')`, `menuSelection('QUESTIONS')`

## Customer Details Fields
| Field | ID | Notes |
|-------|----|-------|
| First Name | #customerFirstNameId | |
| Last Name | #txt_customerLastName | |
| Middle Initial | #txt_customerMiddleInitial | |
| DOB | #customerDateOfBirthId | MM/DD/YYYY |
| Zip Code | #txt_ZipCode | Triggers city/state auto-lookup |
| Address 1 | #txt_Address1 | **Use .type() not .fill()** — fill() clears on blur |
| Address 2 | #txt_Address2 | |
| City | #txt_City | **MUST press Space → click DIV by name** |
| State | #txt_State | Auto-filled from zip |
| County | #txt_County | **MUST press Space → click DIV by name** |
| Phone | #txt_SPQQ_PhoneNo | Carrier validates — must be connected/working number |
| Cell | #txt_SPQQ_CellNo | |
| Email | #txt_SPQQ_EmailId | Required |
| Effective Date | #fullQuoteEffDateId | Must be today or future |
| Term | #FQ_CD_term_Id | |
| Expiration Date | #fullQuoteExpDateId | Auto-calculated, not editable |
| Agent ID | #txt_ULM_AGENT_ID | Pre-filled 0000002527 |
| Currently Insured | #currentlyInsuredId | |
| Renewal | #chk_Ulm_Man_Ren_YN | Checkbox |

### City/County Lookup Pattern (CRITICAL)
These fields use a custom typeahead lookup. You CANNOT just type a value:
1. Click the field
2. Clear it
3. Press **Space** key
4. A lookup fires and returns a list of DIV elements (e.g. `<div id="WACO">WACO</div>`, `<div id="MCLENNAN">MCLENNAN</div>`)
5. Click the matching DIV element by its ID
6. The field is now validated

If you skip this, you get "Warning! Locality Change" and/or validation errors.

**PITFALL**: When calling `space_lookup(frame, field_id, target_text)`, pass the field ID WITHOUT a `#` prefix. The function already prepends `#` internally (`frame.query_selector(f'#{field_id}')`). Passing `'#txt_County'` produces `##txt_County` which is an invalid CSS selector.

## Validation Rules
- **Phone number**: Carrier validates against a DB — must be a real connected number. "Disconnected Phone" error if not valid.
- **Zip code**: Triggers city/state/county auto-lookup
- **"Warning! Locality Change"**: Appears when property address differs from mailing. **NOT BLOCKING** — informational only, can proceed past it. Re-doing the city/county space-lookup clears it temporarily but it returns on Confirm/Next.
- **Coverage A (dwelling)**: DISABLED — auto-populated from `txt_ULRP_REPLACEMENT_VAL` field
- **Replacement Value**: Must be within carrier's calculated range (e.g. "Valid Range is between 186,854 and 228,377"). Setting this field auto-fills Coverage A.
- **County**: Required
- **Email**: Required
- **Prior Coverage Date**: Required when Prior Coverage selected (match to effective date)
- **Replacement Cost Description**: Required
- **Effective date**: Must be today or future — no backdating! If session crosses midnight, update the date.
- **Expiration date**: Auto-calculated from effective + term

## HO-A Complete Field Map

### Property Details (Text Inputs)
| Field | ID | Notes |
|-------|----|-------|
| Zip Code | txt_PIN_CODE_1 | 5-digit |
| Address 1 | txt_ADDR1_1 | |
| Address 2 | txt_ADDR2_1 | |
| City | txt_CITY_1 | Space-lookup |
| State | txt_STATE_1 | Auto from zip |
| County | txt_COUNTY_1 | Space-lookup |
| Year Built | txt_ULRP_YR_BUILT | 4 digits |
| Square Footage | txt_ULRP_SQ_FT | |
| # Bathrooms | txt_ULRP_NO_BATHS | |
| # Kitchens | txt_ULRP_NO_KITCHENS | |
| # Rooms | txt_ULRP_NO_ROOMS | |
| # Fireplaces | txt_ULRP_NO_FIRE_PLACES | |
| Garage Sq Ft | txt_ULRP_GARAGE_SQ_FT | |
| Basement Sq Ft | txt_ULRP_BASEMENT_SQFT | |
| Replacement Value | txt_ULRP_REPLACEMENT_VAL | **DRIVES Coverage A** |
| Coverage A | txt_CVRA | DISABLED, auto from replacement val |
| Loan Year | txt_ULRP_LOAN_YR | |
| Roof Year | txt_ULRP_ROOF_YR | |
| Prior Coverage Date | txt_ULRP_PRIOR_CVG_DT | Required, match eff date |
| Effective Date | txt_EFF_DT | |
| Expiration Date | txt_EXP_DT | |
| ITIN Number | txt_ULRP_USS_ITIN_NUM | Hidden |
| Policy Premium | txt_POLICY_PREMIUM | Read-only |

### Property Details (Dropdowns) — ALL OPTIONS
| Field | ID | Options |
|-------|----|---------|
| Occupancy Type | cmb_ULRP_OCCUPANCY_TYP | Owner(01), Secondary(02), Vacant(05), Tenant(04), Seasonal/Vacation(03) |
| Building Type | cmb_ULRP_BUILD_TYP | Dwelling(D), Townhome(T), Condo(C), Log Home(L), Historical Home(H), Other(O), Manufactured/Modular(MM) |
| Fire Hydrant | cmb_ULRP_DIST_FIRE_HYDR | Yes(01), No(02) |
| Fire Dept ≤5mi | cmb_ULRP_DIST_FIRE_STN | Yes(01), No(02) |
| Protection Class | txt_ULRP_PROTECT_CLS | 1,2,3,4,5,6,7,8,8B,9,10 |
| Construction Type | cmb_ULRP_CONST_TYP | Asbestos(07), Brick(05), Brick Veneer(01), Frame(02), Hardi/Concrete Board(03), Metal(06), Other(08), Stucco(04), Mfg/Modular(09) |
| # of Stories | txt_ULRP_NO_OF_FLOORS | 1, 1.5, 2, 2.5, 3 |
| Roof Construction | txt_ULRP_ROOF_CONS_TYP | Asphalt(07), Composition(06), Concrete/Slate(03), Metal(01), Other(05), Tile(02), Wood(04) |
| # of Families | txt_ULRP_NO_OF_RES_HH | 1, 2 |
| Roof Impact Class | cmb_ULRP_ROOF_CR_CLASS | Class I-IV, None(N) |
| Burglar Alarm | cmb_ULRP_BURG_ALM_TYP | None(N), Fire(F), Burglary(BU), Burglary & Fire(BF) |
| Hip Roof | cmb_ULRP_ROOF_TYP | Yes(Y), No(N) |
| Fire Protection | cmb_ULRP_FIRE_PROTECT_TYP | None(N), Fire Ext(FE), Smoke Alarm(SA), Indoor Sprinkler(IS), Fire Ext & Smoke(FS) |
| Solar Panels | opt_solar_panels | Yes(Y), No(N) |
| Repl Cost Desc | cmb_ULRP_REP_COST | Contents(C), None(N), Dwelling(D), Both(B) |
| Dwelling Style | cmb_ULRP_NO_OF_CORS | 1-4 corner(1), 2-6(2), 3-8(3), 4-10(4) |
| Special Class | cmb_ULRP_SPL_CLASS | Mfg homes(MH), Best(B), Best/Good(BG), Good(G), Good/Avg(GA), Average(A), Avg/Low(AV), Low(L) |
| Garage Type | cmb_ULRP_GARAGE_TYP | No Garage(01), Attached(02), Detached Carport(05), Attached Carport(04), Detached Garage(03) |
| Central HVAC | cmb_ULRP_CENT_HVAC_YN | Yes(Y), No(N) |
| Wood/Fireplace | cmb_ULRP_WB_GFIRE_PLACE_YN | Yes(Y), No(N) |
| Prior Coverage | cmb_ULRP_COV_CONT_YN | Prior Coverage(PC), New Purchase(NP), Refinance(RF) |
| # of Mortgagee | addlEntityYnId | 0, 1, 2 |

### Coverage Dropdowns — ALL OPTIONS
| Coverage | ID | Options |
|----------|----|---------|
| Other Structures | rate\|OTHSTRU | 10%,15%,20%,25%,30%,35%,40%,45%,50% |
| Personal Property | rate\|PP | 40%, 60% |
| PP Off Premises | rate\|PPOP | 10% |
| Loss of Use | rate\|LOU | 10% |
| Personal Liability | txt_CVRC | 25K,50K,100K,300K |
| Medical Payments | txt_CVRD | 500,1K,2K,3K,4K,5K |
| Mold/Fungi HO161 | rate\|HO161 | 25%,50%,100% |
| Personal Computer HO126 | txt_HO126 | $1K,$2K,$3K |
| Incr Costs Construction HO135 | rate\|HO135 | 10%,15%,25% |
| Addl Insured/Water SADW | txt_SADW | $5K,$10K,$15K,$25K |
| Extended Repl Cost ERCP | rate\|ERCP | 125%,150% |
| Wind/Hail Deductible | txtXS_CLAUSE1 | 2%,2.5%,3%,4%,5% |
| AOP Deductible | txtXS_CLAUSE2 | 1%,1.5%,2%,2.5%,3%,4%,5% |
| Losses in 5yr | txt_ULRP_NON_WEATHER_CLM | Yes(1), No(0) |

### Checkbox Endorsements (HO-A)
**Default ON:** CVRA (Dwelling), OTHSTRU (Other Structures), PP (Personal Property), PPOP (PP Off Premises), LOU (Loss of Use), CVRC (Liability), CVRD (Med Pay), ANILIA (Firearm/Animal Liab Limitation), CLAUSE1_* (Wind/Hail ded), CLAUSE2_* (AOP ded), SCRCHOA01 (Loss Settlement Endorsement)

**Optional (default OFF):**
- HO105: Residence Glass Coverage
- UNSJS: HO 110 Jewelry/Watches/Furs (text input for limit)
- HO111: HO 111 Business Personal Property (text input)
- HO112: HO 112 Money/Bank Cards (text input)
- HO161: Mold/Fungi (dropdown 25%/50%/100%)
- HO113: HO 113 Bullion/Valuable Papers (text input)
- HO120: HO 120 TV/Radio Antenna (text input)
- HO126: Personal Computer (dropdown $1K/$2K/$3K)
- HO135: Incr Costs Construction (dropdown 10%/15%/25%)
- HO160: Scheduled Personal Property (text input)
- HO225L: Additional Premises Liability (text input)
- HO225MP: Additional Premises Med Pay (text input)
- HO301: Additional Insured
- SADW: Addl Insured/Water Damage (dropdown $5K-$25K)
- ERCP: Extended Repl Cost (dropdown 125%/150%)
- SCLRCHOA01: Limited Loss Settlement Endorsement
- NLH011: Enhanced Partial Loss
- EXDMGNHR: Excl Cosmetic Damage Non-Hail Metal Roof
- EXDMGMET: Excl Cosmetic Damage Metal from Hail

**Other Checkboxes:**
- chk_DEFAULT_CUSTOMER: Same as Customer address
- chk_ULRP_DUMP_SUR: Delinquent/Unverifiable surcharge
- chk_ULRP_COMPANION_POLICY_YN: Companion Policy
- chk_ULRP_SEC_BLDG_CR_YN: Secondary Building Credit
- chk_Ulrp_Prior_Ur_Dmg: Prior Underwriting Damage

**Hidden Fields:**
- opt_Other_RiskTyp_Address, cmb_Ulrp_Addr_Qn_1, opt_Intenal_Misreption, opt_remove_roofExclson, opt_coverage_desired, chk_ULRP_USS_ITIN

## HO-A Sample Premium Breakdown (Quote QHA-107040)
- Dwelling $250K, Oth Struct 10%, PP 40%, Liab 25K, MedPay 500
- Wind/Hail 2%, AOP 1%
- Premium: $1,762.00 (dwelling) + $176.00 (Loss Settlement Endorsement) + $194.00 (Roof surcharge) + $125 (policy fee) + $60 (inspection) + fees = **$1,892.67 total**
- Credits: Fire Safety 4%, Loss Experience 5%, Age of Risk 9% (max 50% total)

## HO-B Live Field Map (Verified 2026-05-22)

**Source**: Direct extraction from `uwp2hob_LUW.do` iframe with 105 fields.
**Storage**: Full field dump at `/tmp/hob_form_fields_current.json`

### Risk Location Fields
| Field | ID | Notes |
|-------|----|-------|
| Same as Customer | chk_DEFAULT_CUSTOMER | Checkbox, checked by default |
| Address 1 | txt_ADDR1_1 | |
| Address 2 | txt_ADDR2_1 | |
| City | txt_CITY_1 | |
| State | txt_STATE_1 | Auto from zip |
| Country | txt_COUNTRY_1 | Auto US |
| Zip | txt_PIN_CODE_1 | 5-digit |
| Address Question | cmb_Ulrp_Addr_Qn_1 | Yes/No |
| Risk Address Type | opt_Other_RiskTyp_Address | |

### Dwelling/Property Fields (HO-B)
| Field | ID | Options |
|-------|----|---------|
| Protection Class | txt_ULRP_PROTECT_CLS | Numeric input |
| Year Built | txt_ULRP_YEAR_BUILT | 4 digits |
| Square Feet | txt_ULRP_SQ_FEET | |
| Construction Type | cmb_ULRP_CONST_TYP | Asbestos(07), Brick(05), Brick Veneer(01), Frame(02), Hardi/Concrete Board(03), Metal(06), Other(08), Stucco(04) |
| Stories | txt_ULRP_NO_OF_FLOORS | 1=>1, 1.5=>2, 2=>3, 2.5=>4, 3=>5 |
| Roof Cover Year | txt_ULRP_ROOF_CR_YEAR | |
| Roof Construction | txt_ULRP_ROOF_CONS_TYP | Asphalt(07), Composition(06), Concrete/Slate(03), Metal(01), Other(05), Tile(02), Wood(04) |
| # of Families | txt_ULRP_NO_OF_RES_HH | 1=>1, 2=>2 |
| Roof Impact Class | cmb_ULRP_ROOF_CR_CLASS | Class I-IV, None(N) |
| Occupancy | cmb_ULRP_OCCUPANCY_TYP | Owner(01), Secondary(02), Vacant(05), Tenant(04), Seasonal(03) |
| Building Type | cmb_ULRP_BUILD_TYP | Dwelling(D), Townhome(T), Condo(C), Log Home(L), Historical(H), Other(O) |
| Fire Hydrant | cmb_ULRP_DIST_FIRE_HYDR | Yes(01), No(02) |
| Fire Station | cmb_ULRP_DIST_FIRE_STN | Yes(01), No(02) |
| Fire District | txt_ULRP_FIRE_DISTRICT | |
| Monitored Alarms | cmb_ULRP_BURG_ALM_TYP | None(N), Fire(F), Burglary(BU), Burglary & Fire(BF) |
| Flat/Low Roof | cmb_ULRP_ROOF_TYP | Yes(Y), No(N) |
| Local Alarms | cmb_ULRP_FIRE_PROTECT_TYP | None(N), Fire Ext(FE), Smoke Alarm(SA), Indoor Sprinkler(IS), Fire Ext & Smoke(FS) |
| Garage Type | cmb_ULRP_GARAGE_TYP | No Garage(01), Attached(02), Detached Carport(05), Attached Carport(04), Detached Garage(03) |
| Garage Sq Ft | txt_ULRP_GAR_SQ_FEET | |
| Central HVAC | cmb_ULRP_CENT_HVAC_YN | Yes(Y), No(N) |
| Fireplace | cmb_ULRP_WB_GFIRE_PLACE_YN | Yes(Y), No(N) |
| RCV Contents? | cmb_ULRP_REP_COST | Yes(C), No(N) |
| Dwelling Style | cmb_ULRP_NO_OF_CORS | 1=>1-4 corner, 2=>2-6, 3=>3-8, 4=>4-10 |
| Quality Class | cmb_ULRP_SPL_CLASS | Best(B), Best/Good(BG), Good(G), Good/Avg(GA), Average(A), Avg/Low(AV), Low(L) |
| Prior Coverage | cmb_ULRP_COV_CONT_YN | Prior(PC), New Purchase(NP), Refinance(RF) |
| Prior Ins Co | txt_Ulrp_Prv_Ins_Comp | |
| Other Ins Co | txt_Ulrp_Oth_Ins_Comp | |
| Prior Cov Date | txt_Ulrp_Prior_Cov_Dt | Required when Prior Coverage selected |
| Loan Year | txt_ULRP_LOAN_YR | |
| Solar Panels | opt_solar_panels | Yes(Y), No(N) |
| # Solar Panels | txt_no_of_panels | |
| Roof Exclusion | opt_remove_roofExclson | No(N), Yes(Y) |
| Internal Misrep | opt_Intenal_Misreption | Yes(Y), No(N) |
| Coverage Desired | opt_coverage_desired | Yes(Y), No(N) |
| # Mortgagee | addlEntityYnId | 0, 1, 2 |
| # Addl Insured | txt_ULRP_NO_OF_ADDL_INSD | |
| ITIN | chk_ULRP_USS_ITIN / txt_ULRP_USS_ITIN_NUM | |
| Fair Mkt Value | txt_ULRP_FAIR_MKT_VAL | |
| Companion Policy | chk_ULRP_COMPANION_POLICY_YN | Checkbox, default on |
| Secondary Bldg Credit | chk_ULRP_SEC_BLDG_CR_YN | Checkbox, default on |
| Delinquent Surcharge | chk_ULRP_DUMP_SUR | Checkbox, default on (disabled) |
| Prior UW Damage | chk_Ulrp_Prior_Ur_Dmg | Checkbox, default on (disabled) |

### Coverage Fields (HO-B)
| Coverage | ID | Options | Editable? |
|----------|----|---------|-----------|
| RCV Dwelling Limit | txt_ULRP_REPLACEMENT_VAL | DISABLED, set via JS | Force enable |
| Coverage C (PP) | txt_CVRC | 25000, 50000, 100000, 300000 | YES |
| Coverage D (Med Pay) | txt_CVRD | 500, 1000, 2000, 3000, 4000, 5000 | YES |
| Coverage A (Dwelling) | txt_CVRA | 0, DISABLED | No (auto from RCV) |
| Other Structures | rate\|OTHSTRU | 10,15,20,25,30,35,40,45,50 (%) | YES |
| Personal Property | rate\|PP | 40, 60 | LOCKED (force_select) |
| PP Off Premises | rate\|PPOP | 10 | YES (1 option) |
| Loss of Use | rate\|LOU | 20 | YES (1 option) |
| Mold HO162 | rate\|HO162 | 25,50,100 (%) | LOCKED (force_select) |
| Incr Costs Const HO135 | rate\|HO135 | 10,15,25 (%) | LOCKED (force_select) |
| Extended Repl Cost ERCP | rate\|ERCP | 125,150 (%) | LOCKED (force_select) |
| Wind/Hail Ded | txtXS_CLAUSE1 | 1,1.5,2,2.5,3,4,5 (%) | YES |
| AOP Ded | txtXS_CLAUSE2 | 1,1.5,2,2.5,3,4,5 (%) | YES |
| Non-Weather Claims | txt_ULRP_NON_WEATHER_CLM | Yes(1), No(0) | YES |
| Weather Claims | txt_ULRP_NUM_WEATHER_CLM | Numeric | YES |

### Endorsement Checkboxes (HO-B)
**Default ON:** CVRA, OTHSTRU, PP, PPOP, LOU, CVRC, CVRD, ANILIA, CLAUSE1_*, CLAUSE2_*
**Optional OFF:** HO111, HO105, HO162, UNSJS, HO112, HO160, HO113, HO120, HO225L, HO225MP, HO126, HO301, HO135, ERCP, EXDMGNHR, EXDMGMET

### HO-B vs HO-A Key Differences
- **Form URL**: `uwp2hob_LUW.do` (HO-A: `uwp2hoa_LUW.do`)
- **No Manufactured/Modular** in Building/Construction/Special Class
- **Flat/Low Roof** instead of Hip Roof (same ID `cmb_ULRP_ROOF_TYP`)
- **Monitored Alarms** instead of Burglar Alarm (same ID `cmb_ULRP_BURG_ALM_TYP`)
- **RCV Contents?** only Yes(C)/No(N) (HO-A has 4 options)
- **Loss of Use** default 20% (HO-A is 10%)
- **Wind/Hail ded** starts at 1% (HO-A starts at 2%)
- **PP adds 0%** option
- **HO162** replaces HO161 for Mold
- **Missing from HO-B**: SCRCHOA01, SCLRCHOA01, NLH011, SADW

## Full Reference Documents
- HO-A complete field map: `~/.config/libertas/logic-hoa-field-map.md`
- HO-B complete field map: `~/.config/libertas/logic-hob-field-map.md`
- Raw HO-B extraction: `/tmp/hob_field_map_raw.json`
- **Portal debugging notes**: `references/portal-debugging-notes.md` — login pitfalls, iframe structure, timing issues, common script bugs

## Workflow for Automated Quoting
1. **Login**: Navigate directly to `amlogin.jsp?fromId=A`, fill `#loginname` / `#loginpassword`, submit via `document.forms[0].submit()`. Do NOT try to click the LOGIN "button" — it's an image.
2. **Navigate to New Quote HO-A/HO-B**: Find the `agentmenu1.jsp` iframe inside the portal home. Click "Quotes" to expand, then "New Quote HO-B" (or HO-A). This opens a NEW BROWSER TAB at `fullquotelist.do` — must switch `logic_page` to it.
3. **Fill Customer Details**: Find `quickquotecustomer.do` iframe (retry loop — content loads async). Fill name, DOB, address, zip, phone, email, effective date.
4. **City/County space-lookup**: Press Space in each field, click the matching DIV. Pass field IDs WITHOUT `#` prefix to `space_lookup()`.
5. **Save** → `fQDBSave()` on the fullquotelist frame. Wait for page reload.
6. **Confirm/Next** — Click `#idConfmNxt` button. Ignores locality warning (non-blocking). After click, wait for `uwp2hob_LUW.do` (or `uwp2hoa_LUW.do`) frame to appear — it may take 10+ seconds.
7. **Click "Same as Customer" checkbox** — After the `uwp2hob_LUW.do` / `uwp2hoa_LUW.do` frame loads, the location fields (zip, address, county, city) are NOT pre-filled by default. You must explicitly click `#chkSameAs` in the form frame to trigger the address copy from customer details. Wait 2-3 seconds for the fields to populate and become readonly. Then skip them in the fill loop.
8. **Fill property fields** in the `uwp2hob_LUW.do` (or `uwp2hoa_LUW.do`) iframe. Use `select_option()` for dropdowns (value-based for `rate|*` and `txtXS_*`, text-based for others).
9. **Set Replacement Value** → Coverage A auto-fills (must be in carrier's valid range). Use `txt_ULRP_REPLACEMENT_VAL`.
10. **Fill coverage limits** — For HO-B, use `force_select()` for locked selects (PP, HO162, ERCP, HO135). Regular `select_option()` for editable ones (OTHSTRU, LOU, CVRC, CVRD, deductibles).
11. **Save** → `fQDBSave()` on fullquotelist frame. **CRITICAL**: Must save before calc. Wait 5+ seconds.
12. **Calculate/Get Premium** → `fullQuoteCalc()` on fullquotelist frame. Wait 15+ seconds for rating engine.
13. **Dismiss alerts** — Check for "Alert" popup with "OK" button after calc.
14. **Retrieve premium** from the page — try parent frame text, then Conditions sub-tab.
15. **Save results** to JSON.

## Playwright-over-CDP Connection
```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://localhost:9222')
    ctx = browser.contexts[0]
    logic_page = None
    for pg in ctx.pages:
        if 'logicunderwriters' in pg.url:
            logic_page = pg
            break
```

### Frame-Finding Pattern (Resilient)
After any navigation, re-find frames. Best approach: use `parent.evaluate()` with recursive JS frame walking rather than Playwright's frame objects (which detach on reload):
```javascript
let formFrame = null;
function findFrame(frames) {
    for (let i = 0; i < frames.length; i++) {
        try {
            if (frames[i].location.href.indexOf('uwp2') !== -1) return frames[i];
            let nested = findFrame(frames[i].frames);
            if (nested) return nested;
        } catch(e) {}
    }
    return null;
}
formFrame = findFrame(window.frames);
// Then: formFrame.document.querySelectorAll('select') etc.
```

## Automation Script Status
- **HO-B script**: `/home/kyle/.config/libertas/scripts/logic_quote_hob.py` (~830 lines)
- **HO-A script**: `/home/kyle/.config/libertas/scripts/logic_quote_hoa.py` (32K+ bytes)
- **Login**: Working — uses `document.forms[0].submit()` directly
- **Portal navigation**: Working — finds agentmenu1.jsp iframe, clicks HO-B, switches to new tab
- **Customer form filling**: Working — finds quickquotecustomer iframe via retry loop
- **Confirm/Next**: Working — clicks `#idConfmNxt`, waits for uwp2hob frame to load
- **Property form filling**: Working — fills all dwelling/property fields
- **Coverage limits**: Working — `force_select()` for locked selects, regular `select_option()` for editable
- **Deductibles**: Working — txtXS_CLAUSE1/2 already editable, value-based selection
- **Save**: Working — `fQDBSave()` on fullquotelist frame
- **Calc/Premium**: PARTIALLY WORKING — `isChangeCheck()` gatekeeping bypassed (clear `#isChangedPSave` + `#isChanged`). `fullQuoteCalc()` fires and navigates to `quickquotegeneral.do?method=navigate&nextPage=quickquoteCalculate`. BUT rating engine returns HTTP 500 `NullPointerException` — form values set via DOM `.value` don't persist server-side. Need to trigger portal's own change handlers or use `ajaxTempSave`/`ajaxPermanentSave` properly. See "Save/Calc Gatekeeping" section.
- **Known bug**: `txt_ULRP_NON_WEATHER_CLM` claims field default "0" doesn't match option text "No" — use value-based selection or change default to "No".
- **Known bug in HO-A script**: Same login/nav/iframe bugs as HO-B had — needs same fixes applied (form submit login, new tab detection, force_select, readonly skip, Confirm/Next ID)
- **HO-A login field-map doc**: `~/.config/libertas/logic-hoa-field-map.md`
- **HO-B login field-map doc**: `~/.config/libertas/logic-hob-field-map.md`
- **Field extraction script**: `/home/kyle/.config/libertas/scripts/map_hob_fields.py`

### Deploy path: Browserbase/Stagehand alongside Foremost Star script (`~/libertas-crm/browserbase-functions/src/carriers/`)

## Full Reference Document
Complete field map with every ID and option saved at: `~/.config/libertas/logic-hoa-field-map.md`
