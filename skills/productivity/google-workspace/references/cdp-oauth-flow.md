# CDP-Driven Google OAuth Flow

When the user can't open an auth URL on their own browser, drive the entire OAuth
flow through Chrome via CDP (Chrome DevTools Protocol).

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- OAuth client credentials (client_id + client_secret) saved to `~/.hermes/google_client_secret.json`
- Know the target Google account email

## Step-by-Step

### 1. Generate Auth URL

```python
from urllib.parse import urlencode
import json

with open(os.path.expanduser("~/.hermes/google_client_secret.json")) as f:
    cs = json.load(f)

auth_url = "https://accounts.google.com/o/oauth2/auth?" + urlencode({
    "client_id": cs["installed"]["client_id"],
    "redirect_uri": "http://localhost:1",
    "response_type": "code",
    "scope": "https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/gmail.readonly",
    "access_type": "offline",
    "prompt": "consent",
})
```

**Do NOT use PKCE** unless you're certain you can persist the code_verifier through
the entire flow. PKCE state mismatch is the #1 cause of `invalid_grant` errors.

### 2. Navigate Chrome

```python
import json, urllib.request, websocket

tabs = json.loads(urllib.request.urlopen('http://localhost:9222/json').read())
page = next(t for t in tabs if t['type'] == 'page')
ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=60)

def cdp_send(method, params=None):
    # ... standard CDP send pattern
    
cdp_send('Page.navigate', {'url': auth_url})
```

### 3. Click Account on Account Chooser

```javascript
document.querySelector('[data-identifier="user@gmail.com"]').click()
```

### 4. Handle "Unverified App" Warning

Click "Advanced" link, then "Go to {App Name} (unsafe)" link:

```python
# Find and click "Advanced"
evaluate("""Array.from(document.querySelectorAll('a')).find(a => a.textContent.trim() === 'Advanced')?.click()""")

# Find and click "Go to {app} (unsafe)"  
evaluate("""Array.from(document.querySelectorAll('a')).find(a => a.textContent.trim().startsWith('Go to'))?.click()""")
```

### 5. Check All Permission Checkboxes

```python
# Click "Select all" to enable all checkboxes
evaluate("""Array.from(document.querySelectorAll('a, span, div')).find(el => el.textContent.trim() === 'Select all')?.click()""")
```

### 6. Click Continue (THE RIGHT ONE)

**CRITICAL: There are TWO Continue buttons on the consent page:**
- `button[type=submit]` — inside a dialog, clicks "continue without consenting" → gives `error=access_denied`
- `button[type=button]` — at the bottom of the page, the REAL consent button

Always click `button[type=button]` with text "Continue":

```python
# Find the button and get its position
pos = evaluate("""
(function(){
    var btns = document.querySelectorAll('button[type=button]');
    for(var i=0;i<btns.length;i++){
        if(btns[i].textContent.trim() === 'Continue'){
            var r = btns[i].getBoundingClientRect();
            return JSON.stringify({x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)});
        }
    }
})()
""")

# CDP mouse events (NOT .click() — Google Material Design ignores it)
x, y = json.loads(pos)['x'], json.loads(pos)['y']
cdp_send('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': x, 'y': y})
time.sleep(0.3)
cdp_send('Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
time.sleep(0.1)
cdp_send('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
```

### 7. Extract Auth Code

The redirect to `http://localhost:1` fails with a Chrome error page. The auth code
is in the page text:

```python
txt = evaluate('document.body.innerText')
import re
code_match = re.search(r'code=([^&\s]+)', txt)
auth_code = code_match.group(1)
```

### 8. Exchange for Token

```python
import urllib.parse, urllib.request

data = urllib.parse.urlencode({
    'code': auth_code,
    'client_id': client_id,
    'client_secret': client_secret,
    'redirect_uri': 'http://localhost:1',
    'grant_type': 'authorization_code',
}).encode()

resp = urllib.request.urlopen(urllib.request.Request(
    "https://oauth2.googleapis.com/token", data=data
))
token_data = json.loads(resp.read())

# Save token
with open(os.path.expanduser("~/.hermes/google_token.json"), 'w') as f:
    json.dump({
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token", ""),
        "scope": token_data.get("scope", ""),
        "token_type": token_data.get("token_type", "Bearer"),
        "client_id": client_id,
        "client_secret": client_secret,
    }, f, indent=2)
```

## Common Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| `invalid_grant: Missing code verifier` | Auth URL used PKCE but exchange didn't | Redo without PKCE, or persist code_verifier |
| `invalid_grant: Bad Request` | Code already used or expired | Generate new auth URL, redo flow |
| `error=access_denied` in redirect | Clicked type=submit Continue (dialog) | Redo, click type=button Continue (bottom) |
| Consent page doesn't redirect | Checkboxes not checked | Click "Select all" first |
| 403 SERVICE_DISABLED on Sheets API | API not enabled in Google Cloud project | Project owner must enable at console URL |
| 403 "You need additional access" | Wrong account for project admin | Use the account that owns the GCP project |

## Agency-Specific Notes

- The Libertas Bot OAuth client (project 848419619510) is owned by 2factorlogins@gmail.com
- The aithon20127@gmail.com account can complete OAuth but CANNOT enable APIs in the project
- To enable Sheets API: the 2factorlogins owner must visit
  `https://console.developers.google.com/apis/api/sheets.googleapis.com/overview?project=848419619510`
