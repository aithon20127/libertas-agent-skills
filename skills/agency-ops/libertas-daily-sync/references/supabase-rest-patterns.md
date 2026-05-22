# Supabase REST API Patterns (from the ROG)

Proven patterns for talking to the Libertas Supabase instance from the ROG.

## Connection

Credentials at `~/.config/libertas/credentials.env` (chmod 600):
- `SUPABASE_URL` = `https://bfdsyqekvjdexmqycyms.supabase.co`
- `SUPABASE_SERVICE_ROLE_KEY` — bypasses RLS, full read/write
- `SUPABASE_ANON_KEY` — public, read-mostly
- `SUPABASE_DB_URL` — direct PostgreSQL for bulk ops and migrations

## REST API Patterns

### Basic GET
```python
url = f"{SUPABASE_URL}/rest/v1/{table}?select=id,name&limit=1000"
headers = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read())
```

### Pagination (REQUIRED for >1000 rows)
Default limit is 1000. Iterate with offset:
```python
all_records = []
offset = 0
while True:
    url = f"{SUPABASE_URL}/rest/v1/{table}?select=id&offset={offset}&limit=1000"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        batch = json.loads(resp.read())
        if not isinstance(batch, list) or len(batch) == 0:
            break
        all_records.extend(batch)
        offset += 1000
```

### Upsert (insert or update on conflict)
CRITICAL: `on_conflict` query param alone causes HTTP 409 (duplicate key). You MUST include the `Prefer: resolution=merge-duplicates` header:
```python
url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict=policy_master_id"
headers = {
    **base_headers,
    "Prefer": "resolution=merge-duplicates",
    "Content-Type": "application/json",
}
data = json.dumps(rows).encode()
req = urllib.request.Request(url, data=data, headers=headers, method="POST")
```

### RPC (call stored functions)
```python
url = f"{SUPABASE_URL}/rest/v1/rpc/{function_name}"
headers = {
    **base_headers,
    "Content-Type": "application/json",
}
data = json.dumps({"p_policy_id": uuid_str, "p_coverages": cov_list}).encode()
req = urllib.request.Request(url, data=data, headers=headers, method="POST")
```

## Direct DB Patterns (psycopg2)

Use for: bulk UPDATE, DDL, migrations, anything REST can't do.

### Connection
```python
import psycopg2
conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()
```

### UUID type casting
The `ingestion_run_id` column is type `uuid`, NOT `text`. All psycopg2 queries must cast:
```python
# Single value
cur.execute("UPDATE t SET ingestion_run_id = %s::uuid WHERE id = %s", (run_id, row_id))

# Array of UUIDs
cur.execute("UPDATE t SET ingestion_run_id = %s::uuid WHERE ingestion_run_id = ANY(%s::uuid[])", 
            (new_run_id, old_run_ids))
```
Passing bare strings causes `operator does not exist: uuid = text` errors.

### Applying migrations
```python
with open(migration_path) as f:
    sql = f.read()
# For PL/pgSQL functions, execute as a single block:
cur.execute(sql)
```
Don't split on semicolons — PL/pgSQL function bodies contain semicolons.

## Key RPCs

| RPC | Purpose | Parameters |
|-----|---------|-----------|
| `ezlynx_transform_run(p_run_id, p_offset, p_limit)` | Process staging rows into policies | `p_run_id`: UUID, `p_offset`: int (0), `p_limit`: int (1000) |
| `upsert_policy_coverages(p_policy_id, p_coverages)` | Replace coverage lines for a policy | `p_policy_id`: UUID, `p_coverages`: JSON array of coverage objects |

## Key Tables

| Table | Row count | Purpose |
|-------|-----------|---------|
| `policies` | ~4,078 | Canonical policy table |
| `ezlynx_policy_master_staging` | ~3,978 | Raw CSV rows (upsert target) |
| `policy_coverages` | ~183 (growing) | Per-policy coverage lines |
| `ezlynx_ingestion_runs` | ~10 | Run history |

## Transform run_id Flow (CRITICAL)

The `ezlynx_transform_run(p_run_id)` function only processes rows WHERE `ingestion_run_id = p_run_id`. The flow:
1. Create a new run: `INSERT INTO ezlynx_ingestion_runs (id, ...) VALUES (uuid, ...)`
2. Upsert staging rows (they keep their OLD run_id from prior ingestion)
3. **Reassign**: `UPDATE ezlynx_policy_master_staging SET ingestion_run_id = new_run_id::uuid WHERE ingestion_run_id = ANY(old_ids::uuid[])`
4. Call `ezlynx_transform_run(new_run_id)` — now it finds the rows

Without step 3, the transform returns 0 rows processed.
