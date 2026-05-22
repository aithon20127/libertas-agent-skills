# Logic Portal Debugging Notes (2026-05-22 / updated 2026-05-23, session 2)

Session findings from building the Playwright automation scripts for HO-A/HO-B quoting.

## Login Page (`amlogin.jsp?fromId=A`)

- Form action: `https://logicunderwriters.com/beyontecsuite/loginAction.do?method=login`
- Method: POST
- Fields: `#loginname` (text), `#loginpassword` (text), `#tittleId` (hidden, value="A" for Agent)
- The "LOGIN" submit element is NOT a `<button>`, NOT an `<input type=submit>`, and NOT an `<a>`.
  - It does NOT appear in `document.querySelectorAll('button')` — returns 0.
  - It does NOT appear in HTML source as text "LOGIN" — `innerHTML.indexOf("LOGIN")` returns -1.
  - It IS visible as text "LOGIN" in `document.body.innerText`.
  - But `.click()` on that element does nothing — it's a decorative image link.
  - **Working solution**: `document.forms[0].submit()` — the only reliable way.
- After submit, the URL stays `amlogin.jsp` but content changes to portal home.
- Pre-filled credentials were observed on page[5] during debugging — the portal may cache them.

## Portal Home Structure

URL after login: `wfdemoindex.do?method=loadMyTask&sid=<float>`

### 3 Iframes
| iframe ID | URL suffix | Content |
|-----------|------------|---------|
| `NewsEventsId` | `/pages/common//index/agentNewOrEvents` | News items |
| `MyTransId` | `/pages/common/index/agentmenu1.jsp` | **Navigation menu** |
| `NewQuoteDescId` | `/pages/common//index/agentDescDtls.js` | Description panel |

### Navigation Menu (agentmenu1.jsp)
Links found (21 total):
- Quotes (expandable parent)
  - New Quote HO-A
  - New Quote HO-B
  - New Quote DP1
  - New Quote TDP1
- Existing Quotes
- Renewals → Renewal Quote
- Reports And Queries → Base Reports
- Applications → Existing Applications
- Referrals
- Policy Inquiry/Transactions
- Billing Inquiry
- Claims → Report a Loss, Reported Loss
- Documents
- Contact us
- My Account

All links are `javascript:void(0);` — they trigger JS navigation in the parent page.

## Quoting Page (fullquotelist.do)

After clicking "New Quote HO-B", a NEW BROWSER TAB opens at:
```
fullquotelist.do?method=newFq&APMP_ACCESS_TYP=N&APMP_ULM_TYP=QQ
  &APMP_STS_ID=null&APMP_STS_DESC=&APMP_PROD_ID=HOB
  &APMP_DFLT_X_DAYS=&APMP_ACTION_TYP=&APMP_RISK_TYP_ID=null
```

This is CRITICAL — the original login page tab stays open. The script must find the new tab.

### Frames on the quoting page
| Frame | URL | Content |
|-------|-----|---------|
| Frame[0] | `fullquotelist.do?method=newFq&...` | Parent with Save/Calc/Confirm JS |
| Frame[1] | `quickquotecustomer.do?method=loadCustomerInformation` | Customer form (79 inputs) |

### Customer Form Frame
- 79 input elements, including 50+ hidden fields
- Key visible fields: customerFirstNameId, txt_customerLastName, txt_ZipCode, txt_Address1, txt_County, txt_City, etc.
- Agent fields pre-filled: txt_ULM_AGENT_ID (0000002527)
- The iframe content may take 5-10 seconds to fully load — use retry loop

### Frame Content Loading Timing
The iframe URL shows immediately (`quickquotecustomer.do`), but the DOM content inside loads asynchronously. `query_selector('#customerFirstNameId')` may return None for several seconds. Use a retry loop (10 attempts × 3 sec) rather than `wait_for_selector` which can also time out.

### Confirm/Next Button
- The correct button to advance from Customer Details to Quote Details is `#idConfmNxt`
- NOT `#spanconfirmAction` (that ID doesn't exist on this form)
- After clicking Confirm/Next, wait 10+ seconds for the `uwp2hob_LUW.do` frame to appear
- "Warning! Locality Change" alert is non-blocking — proceed past it
- "Inception Date should be in between Product From Date and To" — validation error, may need date adjustment

### Quote Details Tab Navigation
- `fQPageNavigate('UTDS_LEVEL_R_ID')` — navigates to Quote Details tab
- The "Quote Details" tab may show `disabled="true"` — but the form iframe still loads
- `menuSelection('UTDS_LEVEL_R_EDIT')` — opens the edit form sub-tab
- These JS calls may fail silently (e.g., "WARN: menuSelection failed") — but the form frame may already be loaded from the Confirm/Next action

## HO-B Property Form (uwp2hob_LUW.do)

### Location Fields — READONLY
After Confirm/Next, the property form pre-fills location fields from "Same as Customer":
- `txt_PIN_CODE_1`, `txt_ADDR1_1`, `txt_ADDR4_1` (county), `txt_CITY_1`
- These are `readOnly: true` — Playwright's `fill()` fails with "not editable"
- **Skip them** — they're already correct. The `fill_text()` function should check `readOnly` and skip.

### Coverage Fields — LOCKED vs EDITABLE

The HO-B form has a two-tier coverage field system:

**Default-ON checkboxes (checked+disabled):**
CVRA, OTHSTRU, PP, PPOP, LOU, CVRC, CVRD, ANILIA, CLAUSE1_*, CLAUSE2_*

These checkboxes are both checked AND disabled — they're "mandatory coverages" that can't be toggled off.

**Editable coverage selects:**
- `rate|OTHSTRU` (Other Structures) — value-based, editable
- `rate|LOU` (Loss of Use) — value-based, editable, only 1 option (20%)
- `rate|PPOP` — value-based, editable, only 1 option (10%)
- `txt_CVRC` (Liability) — text-based matching, editable
- `txt_CVRD` (Medical) — text-based matching, editable
- `txtXS_CLAUSE1` (Wind/Hail ded) — value-based, editable
- `txtXS_CLAUSE2` (AOP ded) — value-based, editable

**Locked coverage selects (disabled: true):**
- `rate|PP` (Personal Property) — locked, value=60, need force_select to change
- `rate|HO162` (Mold/Fungi) — locked, value="", need force_select
- `rate|ERCP` (Extended Repl Cost) — locked, value="", need force_select
- `rate|HO135` (Construction Laws) — locked, value="", need force_select

**The force_select pattern:**
```python
def force_select(frame, select_id, value):
    """Force-enable a disabled select, set value via JS, trigger change."""
    frame.evaluate('''([sid, val]) => {
        let el = document.getElementById(sid);
        if (el) {
            el.disabled = false;
            el.value = val;
            el.dispatchEvent(new Event('change', {bubbles: true}));
        }
    }''', [select_id, value])
```

After `force_select`, you MUST call `fQDBSave()` to persist the values. After save, selects go back to `disabled: true` but retain their new values.

**Checkbox onclick handlers** — Each checkbox has an `onclick` that calls:
```javascript
ajaxStoreCoverageToSession(this, '<coverage_num>', '<Y|N>', 'null', '<C|F>', '1');
contAjaxStoreCoverageToSession(this);
```
Calling `el.onclick()` fires the AJAX but does NOT enable the rate select. The `force_select` approach (direct DOM manipulation) is the only working method.

### CSS Selector Issue with Pipe Characters
IDs containing `|` (like `rate|PP`) break CSS selectors:
- `#rate|PP` → INVALID selector (pipe is a CSS namespace separator)
- `[id="rate|PP"]` → WORKS
- `document.getElementById('rate|PP')` → WORKS (JS, not CSS)

The `select_option()` function must detect `|` in the ID and use attribute selector syntax.

### Value-based vs Text-based Selection
- `rate|*` fields: option values are numeric strings ("10", "40", "25", "125")
- `txtXS_CLAUSE*` fields: option values are numeric ("1", "2", "1.5")
- Regular fields: option values are codes ("01", "D", "N") but display text is human-readable
- The `select_option()` function uses `sel.select_option(value=...)` for `rate|*` and `txtXS_*`
- For other fields, it does partial text matching on display text

### Claims Field
`txt_ULRP_NON_WEATHER_CLM` — options are "1:Yes" and "0:No". The default in the script was "0" which is the VALUE, not the display text. Either:
- Use value-based selection (pass "0" and handle in select_option)
- Or change default to "No" for text-based matching

### Select Option Text (HO-B) — Verified Values
| Field | ID | Value:Text pairs |
|-------|----|-------------------|
| Occupancy | cmb_ULRP_OCCUPANCY_TYP | 01:Owner, 02:Secondary, 05:Vacant, 04:Tenant, 03:Seasonal/Vacation |
| Building Type | cmb_ULRP_BUILD_TYP | D:Dwelling, T:Townhome, C:Condo, L:Log Home, H:Historical Home, O:Other |
| Fire Hydrant | cmb_ULRP_DIST_FIRE_HYDR | 01:Yes, 02:No |
| Fire Dept | cmb_ULRP_DIST_FIRE_STN | 01:Yes, 02:No |
| Construction | cmb_ULRP_CONST_TYP | 07:Asbestos, 05:Brick, 01:Brick Veneer, 02:Frame, 03:Hardi/Concrete, 06:Metal, 08:Other, 04:Stucco |
| Stories | txt_ULRP_NO_OF_FLOORS | 1:1, 2:1.5, 3:2, 4:2.5, 5:3 |
| Roof Construction | txt_ULRP_ROOF_CONS_TYP | 07:Asphalt, 06:Composition, 03:Concrete/Slate, 01:Metal, 05:Other, 02:Tile, 04:Wood |
| Families | txt_ULRP_NO_OF_RES_HH | 1:1, 2:2 |
| Roof Impact | cmb_ULRP_ROOF_CR_CLASS | Class 1:Class I, Class 2:Class II, Class 3:Class III, Class 4:Class IV, N:None |
| Monitored Alarms | cmb_ULRP_BURG_ALM_TYP | N:None, F:Fire, BU:Burglary, BF:Burglary & Fire |
| Flat/Low Roof | cmb_ULRP_ROOF_TYP | Y:Yes, N:No |
| Local Alarms | cmb_ULRP_FIRE_PROTECT_TYP | N:None, FE:Fire Ext, SA:Smoke Alarm, IS:Indoor Sprinkler, FS:Fire Ext & Smoke |
| Solar Panels | opt_solar_panels | Y:Yes, N:No |
| RCV Contents | cmb_ULRP_REP_COST | C:Yes, N:No |
| Dwelling Style | cmb_ULRP_NO_OF_CORS | 1:1 - 4 corner, 2:2 - 6 corner, 3:3 - 8 corner, 4:4 - 10 corner |
| Struct Quality | cmb_ULRP_SPL_CLASS | B:Best, BG:Best/Good, G:Good, GA:Good/Avg, A:Average, AV:Avg/Low, L:Low |
| Garage Type | cmb_ULRP_GARAGE_TYP | 01:No Garage, 02:Attached Garage, 05:Detached Carport, 04:Attached Carport, 03:Detached Garage |
| HVAC | cmb_ULRP_CENT_HVAC_YN | Y:Yes, N:No |
| Fireplace | cmb_ULRP_WB_GFIRE_PLACE_YN | Y:Yes, N:No |
| Prior Coverage | cmb_ULRP_COV_CONT_YN | PC:Prior Coverage, NP:New Purchase, RF:Refinance |
| Liability | txt_CVRC | 25000:25,000 \| 50000:50,000 \| 100000:100,000 \| 300000:300,000 |
| Medical | txt_CVRD | 500:500 \| 1000:1,000 \| 2000:2,000 \| 3000:3,000 \| 4000:4,000 \| 5000:5,000 |

### Rate/Coverage Select Values (verified)
| Field | ID | Current Value | Options |
|-------|----|--------------|---------|
| Other Structures | rate\|OTHSTRU | 10 | 10,15,20,25,30,35,40,45,50 |
| Personal Property | rate\|PP | 60 (LOCKED) | 40,60 |
| PP Off Premises | rate\|PPOP | 10 | 10 |
| Loss of Use | rate\|LOU | 20 | 20 |
| Mold HO162 | rate\|HO162 | (LOCKED) | "",100,25,50 |
| HO135 | rate\|HO135 | (LOCKED) | "",10,15,25 |
| ERCP | rate\|ERCP | (LOCKED) | "",125,150 |
| Wind/Hail Ded | txtXS_CLAUSE1 | 1 | (blank),2,2.5,3,4,5 — NOTE: display text is "1%", "2%" etc |
| AOP Ded | txtXS_CLAUSE2 | 1 | (blank),1,1.5,2,2.5,3,4,5 |

## Premium Calculation

### isChangeCheck() Gatekeeping (discovered 2026-05-23)

`fullQuoteCalc()` is gated by `isChangeCheck()`. If it returns `"true"`, an alert "Please save the quote and calculate the premium" is shown and the calc is aborted.

**Source of `isChangeCheck()`:**
```javascript
function isChangeCheck() {
    if ($("#isChangedPSave").val() == "true") return "true";
    if ($("#fqFrame").contents().find("#isChanged").val() == "true") return "true";
    return "false";
}
```

Two hidden flags control it:
1. `#isChangedPSave` — lives in the parent (fullquotelist) frame. Checked by `isChangeDbSaveCheck()`.
2. `#isChanged` — lives in the `fqFrame` iframe (the form container).

**After `fQDBSave()` these flags are NOT automatically cleared.** The portal sets them to `"true"` whenever form fields change, but the save function doesn't reset them. You must manually clear them:
```python
parent_frame.evaluate("""() => {
    try { $("#isChangedPSave").val("false"); } catch(e) {}
    try { $("#fqFrame").contents().find("#isChanged").val("false"); } catch(e) {}
}""")
```

**After clearing, `isChangeCheck()` returns `"false"` and `fullQuoteCalc()` fires.**

### fullQuoteCalc() — 500 NullPointerException (discovered 2026-05-23)

When `fullQuoteCalc()` actually fires (after clearing flags), it submits the `fqFrame` form to `quickquotegeneral.do?method=navigate&nextPage=quickquoteCalculate`. The rating engine then returns **HTTP 500 — java.lang.NullPointerException**.

**Root cause**: Form field values set via DOM `.value` assignment (e.g. `el.value = '01'`) work client-side but are NOT included in the form POST that `fullQuoteCalc()` submits to the server. The server receives empty/null values and crashes.

**Evidence**:
- Client-side verification shows correct values (occ='01', rcv='200000', etc.)
- After `fQDBSave()`, reading back from the form shows values persist
- But the POST body sent by `fullQuoteCalc()` is effectively empty/incomplete
- The rating engine sees null fields → NullPointerException

**Possible fixes under investigation**:
1. Dispatch proper `change`+`input` events when setting values (to trigger the portal's own AJAX dirty-tracking)
2. Call `ajaxTempSave()` from the form frame (may serialize form data to server properly)
3. Call `ajaxPermanentSave()` from the form frame
4. Submit the form through its own action URL (`uwp2hoa.do?method=pagination`)

### menuSelection('UTDS_LEVEL_R_EDIT') — Causes Form Reload

Calling `menuSelection('UTDS_LEVEL_R_EDIT')` after Confirm/Next RELOADS the form frame (`uwp2hob_LUW.do`). This wipes all previously filled fields — the form comes back with all dropdowns at "---Select---" and all text inputs empty.

**After Confirm/Next (`#idConfmNxt`), the form frame loads automatically.** No `menuSelection` call is needed. The script should just find the `uwp2hob_LUW.do` / `uwp2hoa_LUW.do` frame and start filling.

### "Get Premium" vs "fullQuoteCalc()"
- The page shows a "Get Premium" button (visible in page text)
- `fullQuoteCalc()` triggers rating but may return an alert: "Please save the quote and calculate the premium"
- **Sequence must be**: Save (`fQDBSave()`) → wait 5+ sec → Calc (`fullQuoteCalc()`) → wait 15+ sec → dismiss alert if present → retrieve premium
- If calc fails, try clicking the "Get Premium" button directly instead of `fullQuoteCalc()`

### "Same as Customer" Checkbox (discovered 2026-05-23)

After Confirm/Next, the property form frame loads with location fields EMPTY — they are NOT auto-populated from customer details. You must explicitly click `#chkSameAs` to trigger the copy:

```python
form_frame.query_selector('#chkSameAs').click()
time.sleep(3)  # Wait for fields to populate and become readonly
```

After clicking, zip, address, county, city fill from customer details and become `readOnly: true`. The `fill_text()` function should then skip them.

If you skip clicking `#chkSameAs`, the form validation fails with "Zip Code required" and "Address 1 required" on Save or Confirm/Next.

### Google Sheets Clipboard Trick (for reading carrier credentials)

Google Sheets renders as canvas — you can't read cell values from the DOM. Use Playwright CDP on the already-logged-in Chrome tab:

1. Find the Sheets tab: `for pg in ctx.pages: if 'docs.google.com/spreadsheets' in pg.url: sheet_page = pg`
2. Ctrl+F, type the carrier name (e.g. "Logic-Standard"), Enter, Escape
3. Shift+Space to select the entire row
4. Ctrl+C to copy to clipboard
5. Read clipboard: `sheet_page.evaluate('() => navigator.clipboard.readText()')`

Returns tab-delimited row data. Parse with `row.split('\t')`.

### Form Value Persistence — Server-Side (under investigation, 2026-05-23)

After filling form fields via DOM manipulation (both `el.value = X` via JS evaluate AND Playwright's `el.fill(X)`), the values appear correct client-side (verification reads back correctly). However, the server never receives them:

- `ajaxTempSave()` exists in the form frame but its effect is unclear — it may only save to session, not to the DB
- `fQDBSave()` in the parent frame saves the quote record but the form POST body appears empty when `fullQuoteCalc()` submits
- `fullQuoteCalc()` calls `document.forms[0].submit()` on the `fqFrame`, which navigates to `quickquotegeneral.do?method=navigate&nextPage=quickquoteCalculate`
- The rating engine at that URL returns HTTP 500 `java.lang.NullPointerException` because all form fields are null

**Next steps to try**:
1. Fill fields using Playwright's native `.fill()` and `.select_option()` (fires proper `input`/`change` events) — then save — THEN check if `ajaxTempSave()` properly serializes
2. Try `ajaxPermanentSave()` instead of `ajaxTempSave()`
3. Try submitting the form directly: `form_frame.evaluate('() => document.forms[0].submit()')` with the form action being `uwp2hoa.do?method=pagination` — this may do a full server-side save
4. Check if there's a hidden `__ajaxSave` or similar field that needs to be set

## Common Script Bugs Found

1. **Double `#` in CSS selector**: `space_lookup(frame, '#txt_County', ...)` → the function does `f'#{field_id}'` → produces `##txt_County`. Pass bare IDs: `'txt_County'`.

2. **Stale page reference after new tab**: After HO-B click, `logic_page` still points at the login/portal-home page. Must search `ctx.pages` for the new fullquotelist tab.

3. **Frame iteration timing**: `logic_page.frames` returns frame objects even when their content hasn't loaded. Check for actual content (e.g. a known element) before proceeding.

4. **AGENT button on landing page**: The `/#` landing page has EMPLOYEE/AGENT buttons, but clicking AGENT doesn't navigate to the login form — it just stays on `/#`. The login form is at a separate URL. Skip the landing page entirely by going to `amlogin.jsp?fromId=A`.

5. **Trying to click disabled checkboxes**: Coverage checkboxes (PP, ANILIA, etc.) are both checked and disabled. `chk.check()` and `chk.click()` silently fail. Use `force_select()` on the underlying select element instead.

6. **`select_option` on disabled selects times out**: Playwright's `select_option()` waits for the element to be "visible and enabled" and times out after 30s if disabled. Must use `force_select()` pattern (JS DOM manipulation) for locked selects.

7. **Pipe characters in IDs break CSS selectors**: `query_selector('#rate|PP')` is invalid CSS. Use `query_selector('[id="rate|PP"]')` or `document.getElementById('rate|PP')` via evaluate.

8. **Confirm/Next button ID**: It's `#idConfmNxt`, NOT `#spanconfirmAction` or any other ID.

9. **Location fields readonly after Confirm/Next**: Don't try to fill them — skip or use `fill_text()` with readOnly check.

## Chrome CDP Connection Pattern

```python
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://localhost:9222')
    ctx = browser.contexts[0]

    # Clean up old Logic pages first
    for pg in list(ctx.pages):
        if 'beyontecsuite' in pg.url or 'logicunderwriters' in pg.url:
            try: pg.close()
            except: pass

    # Fresh page for login
    page = ctx.new_page()
    page.goto('https://logicunderwriters.com/beyontecsuite/eicm/pages/common/amlogin.jsp?fromId=A',
              wait_until='domcontentloaded')
    time.sleep(3)
    page.query_selector('#loginname').fill('2527')
    page.query_selector('#loginpassword').fill('<password>')
    page.evaluate("() => document.forms[0].submit()")
    time.sleep(6)
    # ... portal home loads ...
```
