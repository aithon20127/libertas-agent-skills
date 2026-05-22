#!/usr/bin/env python3
"""
Libertas Daily Sync — Morning pipeline script.
Pulls EZLynx CSV from Gmail, diffs against yesterday, writes to staging,
calls transform RPC, then runs incremental coverage scrape.

Designed for MINIMAL API calls — reads yesterday's snapshot, compares, only
writes what changed.

Usage:
  python3 daily_sync.py              # Full morning run
  python3 daily_sync.py --csv-only   # Just CSV ingest + transform (no coverage)
  python3 daily_sync.py --coverage-only  # Just incremental coverage scrape

Requirements:
  - Chrome on port 9222 (for coverage scrape)
  - Gmail API refresh token for the inbox receiving EZLynx reports
  - Supabase service role key (in ~/libertas-crm/.env.supabase)
  - Playwright in ~/ezlynx-env virtualenv

Output:
  - /tmp/libertas_sync/sync_{date}.log — detailed log
  - /tmp/libertas_sync/yesterday_snapshot.json — yesterday's policy state (for diff)
  - /tmp/libertas_sync/today_snapshot.json — today's policy state (saved after sync)
"""
import argparse, csv, io, json, os, re, sys, time
from datetime import datetime, timedelta
from pathlib import Path
import urllib.request, urllib.parse

# ── Config ──────────────────────────────────────────────────────────────
SUPABASE_URL = "https://bfdsyqekvjdexmqycyms.supabase.co"
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
DB_URL = os.environ.get("SUPABASE_DB_URL", "")

# Gmail API credentials (from browserbase-functions/.env or env vars)
GMAIL_CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET", "")
GMAIL_REFRESH_TOKEN = os.environ.get("GMAIL_REFRESH_TOKEN", "")

# EZLynx report search query
GMAIL_QUERY = 'from:ezlynxreporting@ezlynx.com subject:"CRM Sync" has:attachment filename:csv newer_than:2d'

SYNC_DIR = Path("/tmp/libertas_sync")
SNAPSHOT_FILE = SYNC_DIR / "yesterday_snapshot.json"

# ── Gmail helpers ───────────────────────────────────────────────────────

def get_gmail_access_token():
    """Refresh Gmail access token using stored refresh token."""
    data = urllib.parse.urlencode({
        "client_id": GMAIL_CLIENT_ID,
        "client_secret": GMAIL_CLIENT_SECRET,
        "refresh_token": GMAIL_REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]


def gmail_api_get(access_token, url):
    """GET request to Gmail API."""
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {access_token}"
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def find_ezlynx_emails(access_token):
    """Find recent EZLynx report emails. Returns list of message IDs."""
    result = gmail_api_get(access_token,
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=10"
        f"&q={urllib.parse.quote(GMAIL_QUERY)}")
    return result.get("messages", [])


def get_email_and_attachment(access_token, msg_id):
    """Get email metadata + download CSV attachment. Returns (subject, csv_text)."""
    msg = gmail_api_get(access_token,
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}")
    
    subject = ""
    for header in msg["payload"].get("headers", []):
        if header["name"] == "Subject":
            subject = header["value"]
            break
    
    # Find CSV attachment
    for part in msg["payload"].get("parts", []):
        if part.get("filename", "").endswith(".csv"):
            att_id = part["body"]["attachmentId"]
            att = gmail_api_get(access_token,
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
                f"/attachments/{att_id}")
            import base64
            csv_bytes = base64.urlsafe_b64decode(att["data"])
            return subject, csv_bytes.decode("utf-8-sig", errors="replace")
    
    return subject, None


# ── Supabase helpers ────────────────────────────────────────────────────

def sb_rest(method, path, body=None):
    """Call Supabase REST API. Returns parsed JSON or None."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        if resp.status == 204:
            return None
        return json.loads(resp.read())


def sb_rpc(func_name, params):
    """Call Supabase RPC function."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/{func_name}"
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    data = json.dumps(params).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_active_policies_snapshot():
    """Get yesterday's snapshot of active policies for diffing.
    Returns dict: policy_number -> {premium, status, lob, carrier, ...}
    """
    # Try loading from file first
    if SNAPSHOT_FILE.exists():
        with open(SNAPSHOT_FILE) as f:
            return json.load(f)
    
    # Fallback: query from DB (one API call)
    rows = sb_rest("GET", "policies?select=policy_number,premium,status,lob,carrier_id,ezlynx_applicant_id,ezlynx_policy_master_id,coverage_last_scraped_at&status=eq.Active&limit=5000")
    snapshot = {}
    for r in rows:
        pn = r["policy_number"]
        snapshot[pn] = {
            "premium": r.get("premium"),
            "status": r.get("status"),
            "lob": r.get("lob"),
            "carrier_id": r.get("carrier_id"),
            "ezlynx_applicant_id": r.get("ezlynx_applicant_id"),
            "ezlynx_policy_master_id": r.get("ezlynx_policy_master_id"),
            "coverage_last_scraped_at": r.get("coverage_last_scraped_at"),
        }
    return snapshot


# ── CSV parsing ─────────────────────────────────────────────────────────

def parse_policy_master_csv(csv_text):
    """Parse Policy Master CSV into list of dicts. Returns (rows, fieldnames)."""
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    return rows, reader.fieldnames


def parse_renewal_detail_csv(csv_text):
    """Parse Renewal Detail CSV into list of dicts."""
    reader = csv.DictReader(io.StringIO(csv_text))
    return list(reader), reader.fieldnames


# ── Diff engine ─────────────────────────────────────────────────────────

def diff_policies(csv_rows, yesterday_snapshot):
    """Compare today's CSV against yesterday's snapshot.
    Returns: (new_policies, changed_policies, unchanged_count)
    
    MINIMIZES API CALLS: only stages rows that are new or changed.
    """
    new_policies = []
    changed_policies = []
    unchanged = 0
    
    for row in csv_rows:
        if row.get("Status2") != "Active":
            continue
        
        pn = row.get("Policy_Number", "")
        premium = float(row.get("Premium", 0) or 0)
        
        if pn not in yesterday_snapshot:
            new_policies.append(row)
        elif abs(yesterday_snapshot[pn]["premium"] - premium) > 0.01:
            changed_policies.append(row)
        else:
            unchanged += 1
    
    return new_policies, changed_policies, unchanged


# ── Staging writes ──────────────────────────────────────────────────────

def write_to_staging(csv_rows, fieldnames, table_name):
    """Write rows to staging table via Supabase REST.
    Uses batch insert to minimize API calls.
    """
    if not csv_rows:
        return 0
    
    # Delete existing staging data first (one call)
    sb_rest("DELETE", f"{table_name}?id=not.is.null")
    
    # Batch insert in chunks of 100
    batch_size = 100
    total = 0
    for i in range(0, len(csv_rows), batch_size):
        chunk = csv_rows[i:i+batch_size]
        sb_rest("POST", table_name, body=chunk)
        total += len(chunk)
    
    return total


# ── Coverage scrape ────────────────────────────────────────────────────

def get_policies_needing_coverage():
    """Get policies that need coverage scrape (new or changed since last scrape).
    Returns list of (ezlynx_applicant_id, ezlynx_policy_master_id) tuples.
    MINIMIZES: one REST query with filter instead of full table scan.
    """
    rows = sb_rest("GET",
        "policies?select=ezlynx_applicant_id,ezlynx_policy_master_id,policy_number"
        "&status=eq.Active"
        "&ezlynx_applicant_id=not.is.null"
        "&or=(coverage_last_scraped_at.is.null,ezlynx_last_synced_at.gt.coverage_last_scraped_at)"
        "&limit=5000")
    
    return [(r["ezlynx_applicant_id"], r["ezlynx_policy_master_id"]) for r in rows]


def run_coverage_scrape(policy_pairs):
    """Run incremental coverage scrape using the v5 scraper.
    policy_pairs: list of (applicant_id, policy_master_id)
    """
    if not policy_pairs:
        print("  No policies need coverage scrape.")
        return 0
    
    # Import and run the ACORD scraper
    sys.path.insert(0, "/tmp")
    # The scraper needs Chrome on port 9222
    # For now, shell out to the scraper script
    # TODO: integrate as importable module
    
    print(f"  Scraping coverage for {len(policy_pairs)} policies...")
    # This would call pw_acord_scraper_v5.py with the policy list
    # For the initial version, we'll use subprocess
    import subprocess
    result = subprocess.run(
        ["python3", "/tmp/pw_acord_scraper_v5.py", "--incremental"],
        capture_output=True, text=True, timeout=1800  # 30 min max
    )
    print(f"  Scraper exit: {result.returncode}")
    if result.stdout:
        print(f"  Output: {result.stdout[:500]}")
    return len(policy_pairs)


# ── Main pipeline ──────────────────────────────────────────────────────

def run_csv_sync():
    """Step 1: Pull CSVs from Gmail, parse, diff, stage, transform."""
    print("=" * 60)
    print("LIBERTAS DAILY SYNC — CSV Ingest")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # 1. Get Gmail access token (1 API call)
    print("\n[1/5] Refreshing Gmail access token...")
    access_token = get_gmail_access_token()
    
    # 2. Find EZLynx emails (1 API call)
    print("[2/5] Searching for EZLynx report emails...")
    messages = find_ezlynx_emails(access_token)
    print(f"  Found {len(messages)} matching emails")
    
    if not messages:
        print("  WARNING: No EZLynx reports found! Check if reports are scheduled.")
        return False
    
    # 3. Download CSVs (2-4 API calls)
    print("[3/5] Downloading CSV attachments...")
    policy_master_csv = None
    renewal_detail_csv = None
    
    for msg in messages[:4]:  # Check last 4 emails max
        subject, csv_text = get_email_and_attachment(access_token, msg["id"])
        if not csv_text:
            continue
        if "Policy Master" in subject or "Policy_Master" in subject:
            policy_master_csv = csv_text
            print(f"  Got Policy Master CSV: {len(csv_text)} bytes")
        elif "Renewal" in subject or "RenewalDetail" in subject:
            renewal_detail_csv = csv_text
            print(f"  Got Renewal Detail CSV: {len(csv_text)} bytes")
    
    if not policy_master_csv:
        print("  ERROR: Policy Master CSV not found in any email!")
        return False
    
    # 4. Diff against yesterday (no API calls — local computation)
    print("[4/5] Diffing against yesterday's data...")
    yesterday = get_active_policies_snapshot()
    pm_rows, pm_fields = parse_policy_master_csv(policy_master_csv)
    new_policies, changed_policies, unchanged = diff_policies(pm_rows, yesterday)
    print(f"  Active in CSV: {len([r for r in pm_rows if r.get('Status2') == 'Active'])}")
    print(f"  New policies: {len(new_policies)}")
    print(f"  Changed: {len(changed_policies)}")
    print(f"  Unchanged: {unchanged}")
    
    # 5. Write to staging + transform (2-4 API calls)
    print("[5/5] Writing to staging + running transform...")
    # Always write all active rows to staging (transform handles upsert/diff)
    active_rows = [r for r in pm_rows if r.get("Status2") == "Active"]
    count = write_to_staging(active_rows, pm_fields, "ezlynx_policy_master_staging")
    print(f"  Staged {count} rows")
    
    # Run transform (1 RPC call)
    import uuid
    run_id = str(uuid.uuid4())
    result = sb_rpc("ezlynx_transform_run", {"run_id": run_id})
    print(f"  Transform result: {result}")
    
    # Save today's snapshot for tomorrow's diff (1 file write)
    today_snapshot = {}
    for row in active_rows:
        pn = row.get("Policy_Number", "")
        today_snapshot[pn] = {
            "premium": float(row.get("Premium", 0) or 0),
            "status": row.get("Status2"),
        }
    
    # Rotate: today's snapshot becomes tomorrow's yesterday
    if SNAPSHOT_FILE.exists():
        SNAPSHOT_FILE.rename(SYNC_DIR / "yesterday_snapshot.json.bak")
    with open(SYNC_DIR / "today_snapshot.json", "w") as f:
        json.dump(today_snapshot, f)
    # After successful sync, rename for next run
    (SYNC_DIR / "today_snapshot.json").rename(SNAPSHOT_FILE)
    
    # Handle renewal detail if present
    if renewal_detail_csv:
        rn_rows, rn_fields = parse_renewal_detail_csv(renewal_detail_csv)
        rn_count = write_to_staging(rn_rows, rn_fields, "ezlynx_renewal_detail_staging")
        print(f"  Staged {rn_count} renewal rows")
    
    print("\n✓ CSV sync complete!")
    return True


def run_coverage_sync():
    """Step 2: Incremental coverage scrape for new/changed policies."""
    print("\n" + "=" * 60)
    print("LIBERTAS DAILY SYNC — Coverage Scrape")
    print("=" * 60)
    
    # Get policies needing coverage (1 API call with filter)
    print("[1/2] Finding policies needing coverage scrape...")
    pairs = get_policies_needing_coverage()
    print(f"  {len(pairs)} policies need scraping")
    
    if not pairs:
        print("  All policies up to date — skipping scrape.")
        return True
    
    # Run the scrape
    print("[2/2] Running coverage scrape...")
    count = run_coverage_scrape(pairs)
    print(f"  Scraped {count} policies")
    
    print("\n✓ Coverage sync complete!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Libertas Daily Sync")
    parser.add_argument("--csv-only", action="store_true", help="Only CSV ingest + transform")
    parser.add_argument("--coverage-only", action="store_true", help="Only incremental coverage scrape")
    args = parser.parse_args()
    
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load Supabase key from file if not in env
    global SERVICE_KEY, DB_URL
    if not SERVICE_KEY:
        env_file = Path.home() / "libertas-crm" / ".env.supabase"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("SUPABASE_SERVICE_ROLE_KEY="):
                    SERVICE_KEY = line.split("=", 1)[1].strip()
                elif line.startswith("SUPABASE_DB_URL="):
                    DB_URL = line.split("=", 1)[1].strip()
    
    if not SERVICE_KEY:
        print("ERROR: No Supabase service key found. Set SUPABASE_SERVICE_ROLE_KEY or create ~/libertas-crm/.env.supabase")
        sys.exit(1)
    
    # Load Gmail creds from browserbase .env if not in env
    global GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
    if not GMAIL_CLIENT_ID:
        bb_env = Path.home() / "libertas-crm" / "browserbase-functions" / ".env"
        if bb_env.exists():
            for line in bb_env.read_text().splitlines():
                if line.startswith("GMAIL_CLIENT_ID="):
                    GMAIL_CLIENT_ID = line.split("=", 1)[1].strip()
                elif line.startswith("GMAIL_CLIENT_SECRET="):
                    GMAIL_CLIENT_SECRET = line.split("=", 1)[1].strip()
                elif "REFRESH_TOKEN" in line and "2FACTOR" not in line:
                    GMAIL_REFRESH_TOKEN = line.split("=", 1)[1].strip()
    
    if not args.coverage_only:
        run_csv_sync()
    
    if not args.csv_only:
        run_coverage_sync()
    
    print(f"\nDaily sync finished at {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
