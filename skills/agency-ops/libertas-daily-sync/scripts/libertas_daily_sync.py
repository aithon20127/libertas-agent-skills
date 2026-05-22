#!/usr/bin/env python3
"""
Libertas Daily Sync — Nightly EZLynx→CRM pipeline.
Pulls CSVs from Gmail, diffs against yesterday, stages changes, runs
the SQL transform, then scrapes ACORD coverage for changed policies.

Minimal API calls: only processes NEW + CHANGED rows.
Run: python3 libertas_daily_sync.py [--full-scrape] [--dry-run]
"""
import os, sys, json, csv, io, re, time, argparse, base64, uuid
from datetime import datetime, timezone
import urllib.request, urllib.parse, urllib.error

sys.stdout.reconfigure(line_buffering=True)

CREDS_PATH = os.path.expanduser("~/.config/libertas/credentials.env")
SNAPSHOT_DIR = os.path.expanduser("~/.config/libertas/snapshots")
LOG_DIR = os.path.expanduser("~/.config/libertas/logs")
CHROME_CDP = "http://localhost:9222"
for d in [SNAPSHOT_DIR, LOG_DIR]:
    os.makedirs(d, exist_ok=True)

def load_creds():
    env = {}
    with open(CREDS_PATH) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k] = v
    return env

def gmail_get_token(creds, account="default"):
    key = f"GMAIL_{'DEFAULT' if account == 'default' else account.upper()}_REFRESH_TOKEN"
    rt = creds.get(key)
    if not rt:
        for k, v in creds.items():
            if account.upper() in k and "REFRESH" in k:
                rt = v; break
    if not rt:
        raise ValueError(f"No refresh token for '{account}'")
    data = urllib.parse.urlencode({
        "client_id": creds["GMAIL_CLIENT_ID"],
        "client_secret": creds["GMAIL_CLIENT_SECRET"],
        "refresh_token": rt, "grant_type": "refresh_token"
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]

def gmail_get(path, token):
    req = urllib.request.Request(
        f"https://gmail.googleapis.com{path}",
        headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def gmail_find_reports(token):
    q = urllib.parse.quote(
        'from:ezlynxreporting@ezlynx.com subject:"CRM Sync" has:attachment filename:csv newer_than:2d')
    body = gmail_get(f"/gmail/v1/users/me/messages?q={q}&maxResults=20", token)
    return body.get("messages", [])

def gmail_download_csv(token, msg_id):
    msg = gmail_get(f"/gmail/v1/users/me/messages/{msg_id}?format=full", token)
    hdrs = msg.get("payload", {}).get("headers", [])
    subject = next((h["value"] for h in hdrs if h["name"].lower() == "subject"), "?")
    def find_csv(p):
        if p.get("filename","").lower().endswith(".csv") and p.get("body",{}).get("attachmentId"):
            return p
        for c in p.get("parts", []):
            f = find_csv(c)
            if f: return f
        return None
    part = find_csv(msg["payload"])
    if not part:
        raise ValueError(f"No CSV in {msg_id}")
    att = gmail_get(f"/gmail/v1/users/me/messages/{msg_id}/attachments/{part['body']['attachmentId']}", token)
    csv_bytes = base64.urlsafe_b64decode(att["data"] + "==")
    return subject, csv_bytes.decode("utf-8-sig"), part["filename"]

DIFF_FIELDS = ["Status2","Premium_-_Annualized","Policy_Number","Line_Of_Business",
               "Effective_Date","Expiration_Date2","Master_Company",
               "First_Name","LastName","Account_Name"]

def csv_to_dict(text):
    rows = {}
    for r in csv.DictReader(io.StringIO(text)):
        c = {k.replace("\ufeff",""): v for k, v in r.items()}
        pmid = c.get("Policy_Master_ID","")
        if pmid: rows[pmid] = c
    return rows

def diff(today, yesterday):
    new, changed, unchanged, removed = {}, {}, {}, {}
    for pmid, row in today.items():
        if pmid not in yesterday:
            new[pmid] = row
        else:
            diffs = {f: (yesterday[pmid].get(f,""), row.get(f,""))
                     for f in DIFF_FIELDS if yesterday[pmid].get(f,"") != row.get(f,"")}
            (changed if diffs else unchanged)[pmid] = {"row": row, "diffs": diffs} if diffs else row
    for pmid, row in yesterday.items():
        if pmid not in today: removed[pmid] = row
    return new, changed, unchanged, removed

def save_snap(data, rtype):
    path = os.path.join(SNAPSHOT_DIR, f"{rtype}_{datetime.now():%Y-%m-%d}.json")
    with open(path, "w") as f: json.dump(data, f)
    return path

def load_latest_snap(rtype):
    today = f"{datetime.now():%Y-%m-%d}"
    files = sorted(f for f in os.listdir(SNAPSHOT_DIR)
                   if f.startswith(rtype) and f.endswith(".json") and today not in f)
    if not files: return {}
    with open(os.path.join(SNAPSHOT_DIR, files[-1])) as f:
        return json.load(f)

def sb_req(creds, method, path, body=None, params=""):
    url = f"{creds['SUPABASE_URL']}/rest/v1/{path}"
    if params: url += f"?{params}"
    hdrs = {
        "apikey": creds["SUPABASE_SERVICE_ROLE_KEY"],
        "Authorization": f"Bearer {creds['SUPABASE_SERVICE_ROLE_KEY']}",
        "Content-Type": "application/json",
    }
    if method == "POST" and body:
        hdrs["Prefer"] = "resolution=merge-duplicates,return=representation"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:300]
        try: err = json.loads(err)
        except: pass
        return err, e.code

def sb_rpc(creds, fn, params):
    return sb_req(creds, "POST", f"rpc/{fn}", body=params)

def stage_rows(creds, rows):
    batch = 500; total = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i:i+batch]
        data, status = sb_req(creds, "POST", "ezlynx_policy_master_staging",
                              body=chunk, params="on_conflict=policy_master_id")
        if status in (200, 201):
            total += len(data) if isinstance(data, list) else len(chunk)
        else:
            print(f"  Staging FAILED at batch {i//batch}: {status} {data}", flush=True)
            break
    return total

def parse_coverages(text):
    codes, covs = [], []
    start = 0; cc = 0
    for i, line in enumerate(text.split("\n")):
        if i > 30 and "collapse" in line.strip().lower():
            cc += 1
            if cc >= 2: start = i; break
    if not start:
        for i, line in enumerate(text.split("\n")[50:], 50):
            if "General Section" in line or "Vehicle Section" in line:
                start = i; break
    dwelling = {}
    for line in text.split("\n")[start:]:
        m = re.match(r"^Coverage\s*:\s*(\w+)", line.strip())
        if m:
            code = m.group(1); codes.append(code)
            parts = line.split("\t")
            lim = ded = prem = None
            for p in parts:
                p = p.strip()
                if p.startswith("$") and not lim: lim = p.replace("$","").replace(",","")
                elif p.startswith("$") and lim and not ded: ded = p.replace("$","").replace(",","")
            covs.append({"coverage_code": code, "coverage_name": code,
                         "limit_per_occurrence": lim, "deductible": ded,
                         "deductible_type": "flat", "premium": prem})
        if "Estimated Repl Cost Amount" in line:
            parts = line.split("\t")
            if len(parts) > 1 and parts[-1].strip() and not parts[-1].strip().startswith("Estimated"):
                dwelling["estimated_repl_cost"] = parts[-1].strip()
    return {"codes": codes, "has_dwell": "DWELL" in codes, "has_bi": "BI" in codes,
            "coverages": covs, "dwelling": dwelling}

def scrape_coverages(to_scrape):
    from playwright.sync_api import sync_playwright
    results = []
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CHROME_CDP)
        page = browser.contexts[0].pages[0]
        for pmid, aid, url in to_scrape:
            try:
                r = page.goto(url, wait_until="domcontentloaded", timeout=15000)
                if r and r.status == 200:
                    time.sleep(4)
                    text = page.evaluate("() => document.body.innerText")
                    parsed = parse_coverages(text)
                    status = "FULL" if (parsed["has_dwell"] or parsed["has_bi"]) else ("CODES" if parsed["codes"] else "EMPTY")
                    results.append({"pmid": pmid, "aid": aid, "coverages": parsed["coverages"], "status": status})
                else:
                    results.append({"pmid": pmid, "aid": aid, "coverages": [], "status": "HTTP_ERR"})
            except Exception as e:
                results.append({"pmid": pmid, "aid": aid, "coverages": [], "status": f"ERR:{str(e)[:40]}"})
            time.sleep(1.5)
    return results

def run(dry_run=False, full_scrape=False):
    creds = load_creds()
    today = f"{datetime.now():%Y-%m-%d}"
    logf = os.path.join(LOG_DIR, f"sync_{today}.log")
    def log(msg):
        line = f"[{datetime.now():%H:%M:%S}] {msg}"
        print(line, flush=True)
        with open(logf, "a") as f: f.write(line + "\n")

    log(f"=== Libertas Daily Sync {today} ===")
    if dry_run: log("DRY RUN")

    log("Step 1: Pulling EZLynx reports from Gmail")
    token = gmail_get_token(creds, "default")
    msgs = gmail_find_reports(token)
    log(f"  {len(msgs)} candidate emails")

    proc_path = os.path.join(SNAPSHOT_DIR, "processed_msg_ids.json")
    proc_ids = set(json.load(open(proc_path)) if os.path.exists(proc_path) else [])
    new_msgs = [m for m in msgs if m["id"] not in proc_ids]
    log(f"  {len(new_msgs)} new, {len(msgs)-len(new_msgs)} already processed")

    pm_csv = rd_csv = None
    for m in new_msgs:
        subj, txt, fname = gmail_download_csv(token, m["id"])
        log(f"  Downloaded: {fname} ({len(txt):,} chars)")
        if "Policy Master" in subj: pm_csv = txt
        elif "Renewal Detail" in subj: rd_csv = txt
        proc_ids.add(m["id"])
    with open(proc_path, "w") as f: json.dump(list(proc_ids), f)

    if pm_csv:
        log("Step 2: Parsing + diffing Policy Master")
        today_data = csv_to_dict(pm_csv)
        yday_data = load_latest_snap("policy_master")
        new, changed, unchanged, removed = diff(today_data, yday_data)
        log(f"  {len(today_data)} rows | NEW:{len(new)} CHG:{len(changed)} UNCH:{len(unchanged)} REM:{len(removed)}")
        if changed:
            for pmid, info in list(changed.items())[:3]:
                name = info["row"].get("Account_Name", "?")
                log(f"    {name}: {info['diffs']}")
        snap = save_snap(today_data, "policy_master")
        log(f"  Snapshot: {snap}")

        if dry_run:
            log("DRY RUN — skipping CRM writes")
        else:
            log("Step 3: Staging new+changed rows")
            to_stage = [{"policy_master_id": pmid,
                         "applicant_id": r.get("ApplicantID",""),
                         "policy_number": r.get("Policy_Number",""),
                         "raw": r}
                        for pmid, r in {**new, **{k: v["row"] for k,v in changed.items()}}.items()]
            if to_stage:
                count = stage_rows(creds, to_stage)
                log(f"  Staged {count} rows")
            else:
                log("  Nothing to stage")

            log("Step 4: SQL transform")
            run_id = str(uuid.uuid4())
            sb_req(creds, "POST", "ezlynx_ingestion_runs", body={
                "id": run_id, "message_id": "odysseus-sync",
                "thread_id": "odysseus-sync", "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat()})
            # Reassign staged rows to our run_id
            import psycopg2
            db_url = creds.get("SUPABASE_DB_URL", "")
            if db_url:
                pconn = psycopg2.connect(db_url)
                pconn.autocommit = True
                pcur = pconn.cursor()
                pcur.execute("SELECT DISTINCT ingestion_run_id FROM ezlynx_policy_master_staging WHERE ingestion_run_id != %s::uuid", (run_id,))
                old_ids = [r[0] for r in pcur.fetchall()]
                if old_ids:
                    pcur.execute("UPDATE ezlynx_policy_master_staging SET ingestion_run_id = %s::uuid WHERE ingestion_run_id = ANY(%s::uuid[])", (run_id, old_ids))
                    log(f"  Reassigned {pcur.rowcount} staged rows to run {run_id[:8]}...")
                pconn.close()

            off = 0; lim = 1000; totals = {"rows_transformed":0,"rows_errored":0,"rows_skipped":0}
            while True:
                d, s = sb_rpc(creds, "ezlynx_transform_run", {"p_run_id": run_id, "p_offset": off, "p_limit": lim})
                if s != 200:
                    log(f"  Transform FAILED: {s} {d}"); break
                r = d if isinstance(d, dict) else {}
                eaten = sum(r.get(k,0) for k in totals)
                for k in totals: totals[k] += r.get(k,0)
                if eaten == 0: break
                off += lim
            log(f"  Transform: {totals}")

            log("Step 5: Coverage scrape")
            if full_scrape:
                params = "select=id,ezlynx_policy_master_id,ezlynx_applicant_id,line_of_business&ezlynx_policy_master_id=not.is.null&status=eq.active&limit=1000"
                data, status = sb_req(creds, "GET", "policies", params=params)
            else:
                data, status = sb_req(creds, "GET", "policies",
                    params="select=id,ezlynx_policy_master_id,ezlynx_applicant_id,line_of_business,coverage_last_scraped_at,ezlynx_last_synced_at&ezlynx_policy_master_id=not.is.null&coverage_last_scraped_at=is.null&limit=500")
                if status == 200 and isinstance(data, list):
                    data2, s2 = sb_req(creds, "GET", "policies",
                        params="select=id,ezlynx_policy_master_id,ezlynx_applicant_id,line_of_business,coverage_last_scraped_at,ezlynx_last_synced_at&ezlynx_policy_master_id=not.is.null&coverage_last_scraped_at=not.is.null&limit=500")
                    if s2 == 200 and isinstance(data2, list):
                        seen = {p["id"] for p in data}
                        for p in data2:
                            if p["id"] not in seen and p.get("coverage_last_scraped_at") and p.get("ezlynx_last_synced_at"):
                                if p["ezlynx_last_synced_at"] > p["coverage_last_scraped_at"]:
                                    data.append(p)

            if status == 200 and isinstance(data, list) and data:
                urls = [(p["ezlynx_policy_master_id"], p["ezlynx_applicant_id"],
                         f"https://app.ezlynx.com/ApplicantPortal/Applicant/{p['ezlynx_applicant_id']}/PolicyDisplayAndCompare?Func=0&ApplicantID={p['ezlynx_applicant_id']}&PolMasterID=m{p['ezlynx_policy_master_id']}")
                        for p in data if p.get("ezlynx_policy_master_id") and p.get("ezlynx_applicant_id")]
                log(f"  {len(urls)} policies to scrape")
                if urls:
                    scraped = scrape_coverages(urls)
                    written = 0
                    id_map = {p["ezlynx_policy_master_id"]: p["id"] for p in data}
                    for rec in scraped:
                        if rec["status"] in ("FULL","CODES") and rec["coverages"]:
                            pid = id_map.get(rec["pmid"])
                            if pid:
                                _, s = sb_rpc(creds, "upsert_policy_coverages",
                                             {"p_policy_id": pid, "p_coverages": rec["coverages"]})
                                if s == 200: written += 1
                    log(f"  Coverage written for {written} policies")
            else:
                log(f"  No policies to scrape (status={status})")

    if rd_csv:
        log("Step 6: Renewal Detail snapshot")
        save_snap(csv_to_dict(rd_csv), "renewal_detail")

    log("=== Done ===")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--full-scrape", action="store_true")
    a = ap.parse_args()
    run(dry_run=a.dry_run, full_scrape=a.full_scrape)
