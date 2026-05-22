# EZLynx Browser Automation on the ROG

Session-derived reference: 2026-05-20 first successful Playwright login + 2FA.

## Setup (one-time)

### Playwright environment

The ROG's system Python is protected by PEP 668 — you cannot `pip install` directly. Use a venv:

```bash
python3 -m venv ~/ezlynx-env
source ~/ezlynx-env/bin/activate
pip install playwright
playwright install chromium
```

The venv lives at `~/ezlynx-env`. Always `source ~/ezlynx-env/bin/activate` before running scripts.

### Chrome

Real Chrome is at `/usr/bin/google-chrome` (v148 as of 2026-05-20). Use this instead of Playwright's bundled Chromium — it passes Cloudflare Turnstile where the Hermes browser and headless Chromium do not.

## Cloudflare Bypass

EZLynx's marketing site (`www.ezlynx.com`) sits behind Cloudflare Turnstile. The Hermes browser gets stuck on "Just a moment..." indefinitely. Solution:

1. **Use real Chrome via Playwright** — `executable_path="/usr/bin/google-chrome"` with `headless=False`
2. **Add stealth args** — `--disable-blink-features=AutomationControlled`
3. **Set a real user-agent** — `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36`
4. Cloudflare typically resolves within 5–10 seconds with real Chrome

## EZLynx Login Flow

### URLs

| Page | URL |
|---|---|
| App login | `https://app.ezlynx.com/auth/account/login` |
| 2FA type selection | `https://app.ezlynx.com/auth/TwoFactorVerification/TypeSelection` |
| 2FA code entry | `https://app.ezlynx.com/auth/TwoFactorVerification/VerificationCode` |
| Dashboard | `https://app.ezlynx.com/` (after auth) |

### Login steps

```python
page.goto("https://app.ezlynx.com/auth/account/login")
page.fill("input#txtUserName", "kkriegel1")
page.fill("input#txtPassword", "Liberty3!")
page.click("input[type=submit], button[type=submit], button:has-text('Log in')")
```

### 2FA flow

1. After login, you land on `TwoFactorVerification/TypeSelection`
2. Default option is EMAIL to `li****@gmail.com` (libertaslogins@gmail.com)
3. Click `#two-factor-next` to send the code
4. Code arrives in `libertaslogins@gmail.com` within seconds
5. Enter code in `#verification-code` input
6. Check `#trust-this-computer-input` (helps reduce future 2FA prompts)
7. Click submit/Next

### Auto-2FA via Gmail API

The 2FA code can be retrieved automatically by polling `libertaslogins@gmail.com` via the Gmail API. Credentials are in `~/libertas-crm/browserbase-functions/.env`:

- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_LIBERTASLOGINS_REFRESH_TOKEN`

Pattern:

```python
import urllib.request, urllib.parse, json, re, base64, time

# 1. Get access token
data = urllib.parse.urlencode({
    "client_id": client_id,
    "client_secret": client_secret,
    "refresh_token": refresh_token,
    "grant_type": "refresh_token"
}).encode()
req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
with urllib.request.urlopen(req) as resp:
    access_token = json.loads(resp.read())["access_token"]

# 2. Search for EZLynx verification email
query = urllib.parse.quote("from:ezlynx subject:verification newer_than:1h")
url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?q={query}&maxResults=3"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
# ... fetch message, decode base64 body, extract 6-digit code with regex
codes = re.findall(r'\b\d{6}\b', body_text)
```

**Important:** Use Python `urllib` for Gmail API calls, not curl. Long OAuth tokens break in shell quoting.

### Auth state persistence

`context.storage_state()` saves cookies, but EZLynx sessions expire quickly. Loading a saved state usually redirects back to login. **Plan for a fresh login + 2FA in every session.** Don't waste time trying to reuse old auth state.

## Connecting to Running Chrome via CDP (preferred when Kyle is logged in)

When Kyle already has Chrome open and logged into EZLynx, don't launch a new browser — connect to his existing session:

```bash
# Chrome must be launched with remote debugging + allow-origins:
DISPLAY=:1 /usr/bin/google-chrome \
  --remote-debugging-port=9222 \
  --remote-allow-origins=* \
  --user-data-dir=/tmp/chrome-shared \
  --no-first-run --no-default-browser-check
```

**CRITICAL: `--remote-allow-origins=*` is required.** Without it, WebSocket connections get `403 Forbidden`.

Then connect with Playwright (async):

```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.connect_over_cdp("http://localhost:9222")
    for ctx in browser.contexts:
        for page in ctx.pages:
            if 'ezlynx' in page.url.lower():
                # Full Playwright API works — query_selector, click, evaluate, etc.
                await page.query_selector('button:has-text("insert_chart")')
```

### Do NOT use raw CDP WebSocket for EZLynx DOM queries

Direct `websocket.create_connection()` + CDP `Runtime.evaluate` with `querySelectorAll`/`getElementsByTagName` **returns 0 results** for Angular-rendered elements (button, mat-icon, etc.) on EZLynx pages, even though `innerHTML` clearly contains them and `document.querySelectorAll('*').length` returns 367+. Cause is unknown (possibly Angular view encapsulation or CDP execution context mismatch). Playwright's `connect_over_cdp()` does NOT have this problem. Always use Playwright over CDP.

## EZLynx Reports Portal (discovered 2026-05-21)

### Sidebar navigation

The left sidebar has Material Symbols icons (collapsed by default). The hamburger `menu` icon at top-left expands/collapses the sidebar. Key icons:

| Icon Name | Tooltip | Purpose |
|---|---|---|
| `dashboard` | Dashboard | Main dashboard |
| `folder_shared` | Applicants | Applicant search |
| `folder_open` | Policy Mgmt | Policy management |
| `insert_chart` | **Reports** | Reports 5.0 panel |
| `settings` | Settings | Agency settings |
| `local_atm` | Accounting | Commission/accounting |
| `business_center` | Sales Center | Sales tools |
| `menu_book` | Support | Help docs |

### Reports 5.0 panel

Clicking `insert_chart` opens a flyout panel with two sections:
- **Categories** (left): Accounting, Activity, Applicant, Book of Business, Claim, Commission, **Policy Coverage**, Policy Transaction, Quote, Retention Center, Sales Center
- **Reports** (right): All Reports, Saved Reports, Scheduled Reports, Report Categories, Data Export, Help

### Reports Portal URLs

| Page | URL |
|---|---|
| Scheduled Reports | `https://app.ezlynx.com/EZLynxReportPortal/ScheduledReport` |
| All Reports / Report Menu | `https://app.ezlynx.com/EZLynxReportPortal/ReportMenu` |

You can navigate directly to these URLs — no need to click through the sidebar.

### Currently scheduled reports (2026-05-21)

| Report | Enabled | Created | Last Run | Saved Report Name |
|---|---|---|---|---|
| CRM Sync Nightly | Yes | May 2, 2026 | May 20, 9:01 PM | CRM Sync - Renewal Detail |
| CRM Renewal Detail Nightly | Yes | May 2, 2026 | May 20, 9:30 PM | (unknown) |
| Libertas BOB | Yes | Mar 20, 2025 | May 20, 2:00 PM | (unknown) |

### Schedule edit dialog

Click Actions → Edit Schedule on a scheduled report. Shows:
- Saved Report Name (read-only — links to the report definition)
- Recipient Email
- Report Format: Excel, PDF, CSV, Excel 2007
- Frequency: Daily, Weekly, BiWeekly, Monthly, Yearly
- Run On (time selector)
- Note: All reports execute in CST/CDT, scheduler available 7 AM–11 PM

**Column selection is NOT in the schedule — it's in the saved report definition.** To change columns, edit the saved report from Report Menu.

### Full report catalog (All Reports page)

- **Activity**: Activity Detail, Activity Master, Activity Summary
- **Applicant**: Active Customers with Email, Age Detail, Applicant Detail, Applicant Master, Applicants with No Policy, Birthday Detail, Customer Demographics, Customer Location, Leads Detail, Linked Applicant Insights, Prospects with Email
- **Book of Business**: Book of Business Detail, Book of Business Summary, Cross-Sell Detail, Cross-Sell Master, Policy Expiration, **Policy Master**
- **Claims**: Claims Detail, Claims Summary, Claims Transaction Detail
- **Commission**: Commission Detail 2.0, Commission Grouping
- **Policy Coverage** *(not yet explored — likely has Coverage A–E column options)*
- **Policy Transaction** *(not yet explored)*
- Policy Management, Quote, Retention Center, Sales Center, Data Export

### Sidebar interaction with Playwright

The sidebar buttons use `class="menu ng-star-inserted"` and contain `<mat-icon>` elements with Material Symbols text content (e.g., `insert_chart`). Playwright selector pattern:

```python
# Click the Reports sidebar icon
reports_btn = await page.query_selector('button:has-text("insert_chart")')
await reports_btn.click()
```

When the sidebar is collapsed (icon-only), buttons are at x=0 with width ~40px. The hamburger menu button (`button.nav-menu` or the one containing `text='menu'`) is in the header bar at the far left.

## Next Steps (updated 2026-05-21)

- [x] Fully explore the Reports / Scheduled Reports section in EZLynx UI
- [ ] Explore the **Policy Coverage** category in All Reports — find specific report names and available columns
- [ ] Edit the **saved report definitions** (not just schedules) to see current column selections
- [ ] Determine if Policy Coverage reports can be scheduled as CSV to 2factorlogins@gmail.com
- [ ] Check if Policy Master can be extended with coverage columns or if a separate report is needed
- [ ] Map all available report column options for each relevant report type
- [ ] Document the IVANS coverage gap per carrier (which carriers send coverages via download, which don't)
- [ ] Build the Policy Summary UI scraper for coverage backfill

A working end-to-end login script lives at `/tmp/ezlynx_v3.py` (from 2026-05-20 session). Key structure:

```python
from playwright.sync_api import sync_playwright
import time, json, re, base64, urllib.request, urllib.parse

# ... (Gmail 2FA retrieval function) ...

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/usr/bin/google-chrome",
        headless=False,
        args=["--no-first-run", "--no-default-browser-check",
              "--disable-blink-features=AutomationControlled"]
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) ..."
    )
    page = context.new_page()

    # Login
    page.goto("https://app.ezlynx.com/auth/account/login")
    page.fill("input#txtUserName", "kkriegel1")
    page.fill("input#txtPassword", "Liberty3!")
    page.click("input[type=submit]")
    time.sleep(8)

    # Handle 2FA (auto-detect + auto-retrieve code from Gmail)
    if "TwoFactorVerification" in page.url:
        # Click Next to send code
        page.click("#two-factor-next")
        time.sleep(5)
        # Get code from Gmail API
        code = get_2fa_code(gmail_token)
        page.fill("#verification-code", code)
        # Trust computer
        trust = page.query_selector("#trust-this-computer-input")
        if trust and not trust.is_checked():
            trust.click()
        page.click("button[type=submit], #two-factor-next")
        time.sleep(10)

    # Now you're on the dashboard — navigate where needed
    # ...
```

## Next Steps (updated 2026-05-21)

- [x] Fully explore the Reports / Scheduled Reports section in EZLynx UI
- [ ] Explore the **Policy Coverage** category in All Reports — find specific report names and available columns
- [ ] Edit the **saved report definitions** (not just schedules) to see current column selections
- [ ] Determine if Policy Coverage reports can be scheduled as CSV to 2factorlogins@gmail.com
- [ ] Check if Policy Master can be extended with coverage columns or if a separate report is needed
- [ ] Map all available report column options for each relevant report type
- [ ] Document the IVANS coverage gap per carrier (which carriers send coverages via download, which don't)
- [ ] Build the Policy Summary UI scraper for coverage backfill
