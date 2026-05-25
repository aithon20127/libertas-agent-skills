---
name: email-policy-transaction
version: 1.0.0
category: agency-ops
description: Handle policy transaction emails — endorsements, address/vehicle changes, carrier correspondence about specific policies, batch transaction reports from carriers (Logic, Foremost, etc.). 16.5% of inbox (2625 emails). Trigger, parse, update CRM, and escalate when needed.
triggers:
  - email with policy number in subject or body
  - endorsement issued/denied notification
  - address change, vehicle change, mortgagee update
  - carrier batch transaction report (Logic SC1- prefixed, Foremost, etc.)
  - endorsement denial notification
  - expiration reminder notice
  - reinstatement notice
  - nonrenewal notice
  - policy rewrite notification
  - MyCoverageInfo notification
  - mis-matched address notice
tags: [email, policy, transaction, endorsement, crm, supabase, logic, foremost, carrier]
---

# Email Policy Transaction Handler

How Odysseus processes policy-transaction emails — the #1 email category at 16.5% of the service inbox (2625 emails). These are carrier-to-agent communications about specific policy changes: endorsements, address/vehicle changes, mortgagee updates, cancellation/nonrenewal notices, reinstatements, and batch transaction reports.

## When This Skill Applies

Use when an email matches any of these patterns:

- **Policy number in subject**: `[SC1-HA-033636-02-MOORE, AUBREY]`, `Policy# HB096534`, `Policy Number: 438259043`
- **Transaction keywords**: endorsement, reinstatement, rewrite, lapse, nonrenewal, expiration reminder
- **Change type keywords**: address change, vehicle change, mortgagee clause update, loss payee update, driver change
- **Batch report subjects**: "Policy Transactions for [date]", "Endorsement Denial Notification"
- **Carrier-specific patterns**: SC1- prefix (Logic/Standard Casualty), Logic Underwriters sender
- **MyCoverageInfo** notifications
- **Mis-matched address** or **incorrect address** notices

Do NOT use for:
- Claims notifications → `email-claims-notification` (separate skill)
- Payment/billing notices → `email-payment-notice` (separate skill)
- Quote requests → `email-quoting-request` (separate skill)
- e-signature completions → `email-e-signature` (separate skill)
- New business applications → `email-new-business` (separate skill)

## Email Sources

| Inbox | Address | Access | Primary Use |
|-------|---------|--------|-------------|
| Service | service@libertasinsurance.com | Gmail API (GMAIL_SERVICE_REFRESH_TOKEN in ~/.config/libertas/gmail-service.env) | Main agency inbox, receives carrier transaction emails |
| 2factorlogins | 2factorlogins@gmail.com | Gmail API (GMAIL_DEFAULT_REFRESH_TOKEN) | EZLynx CSV recipient |
| Kyle direct | Kyle@libertasinsurance.com | Not API-accessible | Fwd'd policy emails |

## Carrier-Specific Patterns

### Logic / Standard Casualty (highest volume batch sender)
- **From**: `NO_REPLY@logicinsurance.com` or `janice@logicinsurance.com`
- **Subject format**: `[SC1-HA-033636-02-LASTNAME, FIRSTNAME]`
- **Policy number format**: `SC1-{LOB}-{6-digit}-{version}` (e.g., `SC1-HA-033636-02`)
  - HA = Homeowners A, HB = Homeowners B, T1 = Dwelling Fire TDP1
- **Common email types**:
  - Endorsement issued (revised dec packet mailed)
  - Invoice for balance due
  - Notice of cancellation
  - Expiration reminder notice
  - Mortgagee clause update confirmation
- **Attachment**: Revised declaration page or invoice PDF
- **Batch behavior**: Logic sends multiple emails per transaction in a single thread (3 messages per endorsement — the same notification repeated). Deduplicate by threadId.

### Foremost
- **From**: `@foremost.com` or `@foremostinsurance.com`
- **Subject patterns**: Often includes policy number and transaction type
- **Attachments**: Endorsement pages, dec pages

### Travelers
- **From**: `@travelers.com`
- **Subject patterns**: "Underwriting Info - [Account Name], [Policy#]"
- **May include**: Underwriting questions requiring response

### Safeco / Liberty Mutual
- **From**: `@safeco.com`, `@libertymutual.com`
- **Subject patterns**: Policy number + transaction type

### Texas FAIR Plan (TFPA)
- **From**: `@twia.org`
- **Subject patterns**: "TFPA - Notice of Nonrenewal", "TFPA - Expiration Reminder"
- **Often forwarded by Kyle** with action notes

### Progressive
- **From**: `customerservice@e.progressive.com` or `customerservice@progressiveagent.com`
- **Claims notifications** go to service@ inbox — these are claims, not transactions
- **Transaction emails** include endorsement confirmations

## Processing Workflow

### Step 1: Classify the Transaction Type

Parse the email to identify:

| Transaction Type | Key Signals | Priority |
|---|---|---|
| Endorsement issued | "endorsement", "revised policy declaration", "requested change has been processed" | Medium — informational, update CRM |
| Endorsement denied | "endorsement denial", "denied", "unable to process" | HIGH — requires agent action |
| Address change | "address change", "new address", "address updated" | Medium — update CRM |
| Vehicle change | "vehicle change", "add vehicle", "remove vehicle", "VIN" | Medium — update CRM |
| Mortgagee clause update | "mortgagee clause", "mortgagee has been updated", "lienholder" | Medium — update CRM, verify EOI |
| Cancellation notice | "notice of cancellation", "cancellation" | HIGH — time-sensitive, notify client |
| Nonrenewal notice | "nonrenewal", "non-renewal" | HIGH — time-sensitive, find replacement |
| Reinstatement | "reinstated", "reinstatement" | Medium — update CRM status |
| Expiration reminder | "expiration reminder notice", "expiring" | Medium — renewal pipeline |
| Lapse notice | "lapsed", "lapse" | HIGH — payment needed to reinstate |
| Rewrite | "rewrite", "rewriting" | Medium — update CRM policy record |
| Batch transaction report | "Policy Transactions for [date]", multiple policies in one email | Low — batch CRM update |

### Step 2: Extract Key Data

From each email, extract:

1. **Policy number** — the primary key for CRM lookup
2. **Client name** — for verification and human-readable notes
3. **Carrier name** — from sender domain or email body
4. **Transaction type** — from Step 1 classification
5. **Effective date** — when the change takes effect (if mentioned)
6. **Change details** — what specifically changed (new address, vehicle added/removed, coverage change, premium delta)
7. **Attachment present** — whether a dec page, endorsement, or invoice is attached
8. **Action required** — is there a response needed from the agency?

### Step 3: Look Up Policy in CRM

Query the Supabase CRM to find the matching policy record:

```python
# Direct DB lookup (preferred — bypasses RLS)
import psycopg2
conn = psycopg2.connect(env['SUPABASE_DB_URL'])  # from ~/.config/libertas/credentials.env
cur = conn.cursor()

# Search by policy number
cur.execute("""
    SELECT p.id, p.policy_number, p.status, p.premium_annual, 
           p.effective_date, p.expiration_date, p.carrier_id,
           c.name as carrier_name, h.id as household_id,
           ct.first_name, ct.last_name
    FROM policies p
    LEFT JOIN carriers c ON p.carrier_id = c.id
    LEFT JOIN households h ON p.household_id = h.id
    LEFT JOIN contacts ct ON p.primary_contact_id = ct.id
    WHERE p.policy_number ILIKE %s
""", (f'%{policy_number}%',))
```

**Policy number matching pitfalls:**
- Logic SC1- numbers may have dashes in different positions: `SC1-HA-033636-02` vs `SC1HA03363602E1`
- Carrier policy numbers may have different formats in CRM vs email (with/without dashes, leading zeros)
- Always use `ILIKE` with wildcards for fuzzy matching
- If no match found, search the EZLynx Policy Master CSV snapshots at `/tmp/ezlynx_phase0/` for recent data

### Step 4: Update CRM

Based on transaction type, update the appropriate CRM tables:

#### For endorsement / address change / vehicle change / mortgagee update:
```python
# Add a note to the policy record
cur.execute("""
    UPDATE policies 
    SET notes = COALESCE(notes, '') || %s,
        updated_at = NOW()
    WHERE id = %s
""", (f"\n[{email_date}] {transaction_type}: {change_summary}. Source: {carrier_name} email.", policy_id))
conn.commit()
```

#### For cancellation / nonrenewal (status change):
```python
cur.execute("""
    UPDATE policies
    SET status = 'Cancelled',
        updated_at = NOW(),
        notes = COALESCE(notes, '') || %s
    WHERE id = %s
""", (f"\n[{email_date}] {transaction_type}: {reason}. Carrier notice received.", policy_id))
conn.commit()
```

#### For reinstatement:
```python
cur.execute("""
    UPDATE policies
    SET status = 'Active',
        updated_at = NOW(),
        notes = COALESCE(notes, '') || %s
    WHERE id = %s
""", (f"\n[{email_date}] Reinstated per carrier notice.", policy_id))
conn.commit()
```

#### For premium change (from endorsement with premium delta):
```python
cur.execute("""
    UPDATE policies
    SET premium_annual = %s,
        updated_at = NOW(),
        notes = COALESCE(notes, '') || %s
    WHERE id = %s
""", (new_premium, f"\n[{email_date}] Premium changed from ${old_premium} to ${new_premium} via endorsement.", policy_id))
conn.commit()
```

### Step 5: Handle Attachments

If the email has an attached dec page, endorsement page, or invoice:
1. Download the attachment via Gmail API
2. Store in the policy's document folder (future: Supabase Storage or S3)
3. Log the document in CRM notes: "Attachment: {filename} saved"
4. For Logic attachments: the endorsement PDF contains the revised coverage details — future: parse and update policy_coverages table

### Step 6: Determine If Action Is Needed

| Action Level | Criteria | Response |
|---|---|---|
| **Informational** | Endorsement processed, address updated, mortgagee updated | Log in CRM only. No notification needed. |
| **Client notification** | Cancellation notice, nonrenewal, lapse | Draft email to client summarizing the notice and next steps. Flag for Kyle/Shannon to review before sending. |
| **Agent action** | Endorsement denial, underwriting info request, reinstatement required | Escalate to Kyle with full context. |
| **Urgent** | Cancellation effective within 10 days, nonrenewal with no replacement lined up | Escalate to Kyle IMMEDIATELY via Slack/notification. |

## Batch Transaction Reports

Some carriers send daily/weekly batch transaction reports. These are NOT individual endorsement emails — they list multiple policy transactions in a single email.

### Logic Batch Pattern
- Subject: "Policy Transactions for [date]"
- Contains a list of policy numbers with transaction types
- Process each entry individually using Steps 2-4 above
- These may overlap with individual endorsement emails — deduplicate by policy_number + transaction_type + date

### Processing Batch Reports
1. Parse all policy numbers and transaction types from the report
2. Batch query CRM for all matching policies (single query with multiple policy numbers)
3. Batch update notes/status for all policies
4. Log a single CRM note on each policy: "[date] Batch transaction report from {carrier}: {transaction_type}"

## Escalation Rules

### Always escalate to Kyle when:
1. **Endorsement denial** — carrier refused a requested change; Kyle needs to contact the client or find an alternative
2. **Cancellation within 10 days** — time-critical; client needs immediate attention
3. **Nonrenewal with no replacement** — agency needs to shop for replacement coverage
4. **Underwriting info request from carrier** — requires professional judgment response
5. **Unrecognized policy number** — cannot find in CRM; may be a new policy or data issue
6. **Discrepancy between email and CRM** — email says X but CRM shows Y for policy status, premium, etc.
7. **Client dispute** — email from client disputing a change they did not request
8. **Premium increase > 20%** on an endorsement — Kyle reviews for re-shopping opportunity
9. **Carrier requests inspection or underwriting review** — requires agent decision

### Escalation format:
```
POLICY TRANSACTION — [Priority Level]
Policy: {policy_number} | Client: {client_name} | Carrier: {carrier}
Transaction: {type}
Effective: {date}
Details: {summary}
CRM Status Before: {old_status}
Action Needed: {specific action request}
Email ID: {gmail_message_id}
```

## CRM Tables Reference

| Table | Purpose | When to Update |
|-------|---------|----------------|
| `policies` | Main policy record — status, premium, notes | Every transaction |
| `policy_terms` | Term-level data (effective/expiration dates) | New term, reinstatement |
| `policy_coverages` | Coverage details per term | Endorsement with coverage change (if details available) |
| `carriers` | Carrier reference data | Never (read-only reference) |
| `contacts` | Client contact info | Address change (if new address provided) |
| `addresses` | Address records | Address change (if new address provided) |
| `households` | Household grouping | Rarely |

**Key column on `policies`**: `notes` (text) — append transaction notes here. Do NOT overwrite existing notes.

## Common Pitfalls

1. **Logic sends 3 duplicate emails per transaction** — the same endorsement notification arrives as 3 messages in one thread. Deduplicate by threadId before processing. Only process the first message per threadId per transaction type.

2. **SC1- policy number format varies** — email may show `SC1-HA-033636-02` but CRM may store it as `SC1HA03363602E1` or `SC1-HA-033636-02-E1`. Use fuzzy matching with `ILIKE` and strip dashes/hyphens for comparison.

3. **Cancellation vs nonrenewal** — these are different. Cancellation = mid-term termination (often for nonpayment). Nonrenewal = carrier declining to renew at term end. CRM status update differs: cancellation → "Cancelled", nonrenewal → keep "Active" until expiration but flag in notes.

4. **Don't auto-change policy status without verification** — an endorsement email doesn't mean the change is live yet. Some carriers send "endorsement pending" then "endorsement issued" separately. Only update status on confirmed issued/processed notices.

5. **Batch reports overlap with individual emails** — Logic sends both individual endorsement emails AND batch daily reports. The batch report may repeat info from individual emails already processed. Deduplicate by (policy_number, transaction_type, date).

6. **Policy not found in CRM** — new policies or recently-quoted policies may not be in the CRM yet. Check the EZLynx CSV snapshots at `/tmp/ezlynx_phase0/` or search EZLynx directly. If still not found, escalate to Kyle.

7. **Gmail API rate limits** — when processing batch reports, don't make individual API calls per email. Use batch endpoints. The Gmail API allows up to 100 messages per batch request.

8. **Attachment parsing** — don't try to parse PDF attachments for coverage data yet. The ACORD page scraper handles coverage data. Just download and log the attachment. Future: parse endorsement PDFs for coverage delta.

9. **Don't reply to NO_REPLY senders** — Logic uses `NO_REPLY@logicinsurance.com`. Never send auto-replies to these addresses. If a response is needed, reply to the underwriter (e.g., `janice@logicinsurance.com`) or escalate to Kyle.

10. **Timezone handling** — Logic emails use CDT/CST (`-0500` / `-0600`). Other carriers use various timezones. Always parse dates with timezone awareness and store in UTC in the CRM.

11. **`policy_terms` columns are effective_date/expiration_date** — NOT `term_start`/`term_end`. The `upsert_policy_coverages` RPC is broken (references nonexistent columns). Use direct DB writes via psycopg2 with `SUPABASE_DB_URL`.

12. **REST API RLS blocks** — the anon key gets `permission denied` for policy writes. Use direct DB connection (psycopg2 with `SUPABASE_DB_URL` from `~/.config/libertas/credentials.env`) for all CRM writes.

13. **Don't process forwarded emails twice** — Kyle often forwards carrier notices from his personal inbox to service@. The forwarded email may be processed once from the original carrier send and again from Kyle's forward. Check threadId and message headers for "Fwd:" to avoid double-processing.

14. **Cancellation emails from Logic include invoice attachment** — the "notice of cancellation" email often has an attached invoice for the balance due. This is a PAYMENT issue, not just a status change. The client may need to pay to prevent cancellation. Flag payment-notice overlap.

15. **Endorsement denial may require re-submission** — if a change is denied, Kyle may need to submit a corrected endorsement request through the carrier portal. Don't auto-resubmit; escalate with the denial reason.

## Verification Checklist

- [ ] Policy number extracted and matched to CRM record
- [ ] Transaction type classified correctly
- [ ] CRM `policies.notes` updated with transaction detail
- [ ] Policy status updated only if confirmed (not on pending notices)
- [ ] Deduplication check passed (threadId + transaction_type + date)
- [ ] Attachment downloaded if present and logged in notes
- [ ] Escalation sent to Kyle if any HIGH-priority condition met
- [ ] No auto-reply sent to NO_REPLY addresses
- [ ] Batch report entries processed without duplicate individual-email processing
- [ ] Cancellation vs nonrenewal distinction preserved in CRM update
