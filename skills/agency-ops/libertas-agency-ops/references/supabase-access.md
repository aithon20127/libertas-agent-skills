# Supabase Access from the ROG

Provisioned 2026-05-21. All connection methods verified working.

## Connection Details

- **Project URL:** `https://bfdsyqekvjdexmqycyms.supabase.co`
- **Project Ref:** `bfdsyqekvjdexmqycyms`
- **Keys file:** `~/libertas-crm/.env.supabase` (chmod 600)
- **DB URL:** `postgresql://postgres.bfdsyqekvjdexmqycyms:mn2AINddThR7jeTs@aws-1-us-east-1.pooler.supabase.com:5432/postgres`

## Method 1: REST API (Python urllib — no dependencies)

```python
import urllib.request, urllib.parse, json

SUPABASE_URL = "https://bfdsyqekvjdexmqycyms.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJmZHN5cWVrdmpkZXhtcXljeW1zIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDQxNDI2MiwiZXhwIjoyMDg5OTkwMjYyfQ.6QiiOOtpyCLoZj0MfehscdPtWCV_R6GDRla9uWNmr1g"

# Read rows
url = f"{SUPABASE_URL}/rest/v1/policies?select=id,policy_number,premium&status=eq.Active&limit=10"
req = urllib.request.Request(url, headers={
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}"
})
with urllib.request.urlopen(req) as resp:
    rows = json.loads(resp.read())

# Write rows
data = json.dumps([{"policy_id": "...", "coverage_code": "DWELL", "limit_amount": "250000"}]).encode()
req = urllib.request.Request(
    f"{SUPABASE_URL}/rest/v1/policy_coverages",
    data=data,
    headers={
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    },
    method="POST"
)
with urllib.request.urlopen(req) as resp:
    pass  # 201 Created

# Call RPC
rpc_data = urllib.parse.urlencode({"run_id": "00000000-0000-0000-0000-000000000000"}).encode()
req = urllib.request.Request(
    f"{SUPABASE_URL}/rest/v1/rpc/ezlynx_transform_run",
    data=rpc_data,
    headers={
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json"
    }
)
with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read())
```

## Method 2: Direct DB (psycopg2)

```python
import psycopg2

DB_URL = "postgresql://postgres.bfdsyqekvjdexmqycyms:mn2AINddThR7jeTs@aws-1-us-east-1.pooler.supabase.com:5432/postgres"
conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()

# Query
cur.execute("SELECT count(*) FROM policies WHERE status = 'Active'")
print(cur.fetchone())

# Run migration
with open("migration.sql") as f:
    cur.execute(f.read())
```

## Method 3: Supabase CLI (not yet set up)

Requires `npx supabase login` with a personal access token. Not needed for daily operations — REST and direct DB cover everything.

## Database State (verified 2026-05-21)

- 4,078 total policies, ~846 active
- 3,978 with EZLynx IDs (ezlynx_applicant_id, ezlynx_policy_master_id)
- `ezlynx_policy_master_staging`: 3,978 rows, last sync 2026-05-21T03:30
- `ezlynx_renewal_detail_staging`: 3,978 rows
- `policy_coverages`: 183 rows (test writes), table live with RLS
- `policy_terms`: exists but empty
- Last ingestion runs: Policy Master 2026-05-19, Renewal Detail 2026-05-17
- `policies_audit` table: tracks field changes (premium, status, LOB)

## Key Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| policies | Main policy records | id, policy_number, carrier_id, household_id, status, premium, ezlynx_applicant_id, ezlynx_policy_master_id, ezlynx_raw, coverage_last_scraped_at |
| policy_coverages | Per-coverage detail | policy_id, coverage_code, coverage_description, limit_amount, deductible, is_carrier_specific, created_at |
| households | Grouped insureds | id, name |
| contacts | People | id, household_id, first_name, last_name, email, phone |
| carriers | Insurance carriers | id, name |
| ezlynx_policy_master_staging | Raw CSV staging | all 73 CSV columns |
| ezlynx_renewal_detail_staging | Renewal CSV staging | all 15 CSV columns |
| policies_audit | Change tracking | policy_id, field_name, old_value, new_value, changed_at |

## RLS Notes

- `policy_coverages` table has RLS enabled
- Service role key bypasses all RLS — use it for automated writes
- Anon key gets 403 on protected tables
- To allow anon reads later, add a SELECT policy: `CREATE POLICY "Read policy coverages" ON policy_coverages FOR SELECT TO anon USING (true);`
