---
name: email-declarations-page
version: 1.0.0
category: agency-ops
description: Handle declarations page request emails from clients or lenders — locate the dec page in carrier portals or CRM, send to requester, and update CRM. 0.5% of inbox (86 emails). Trigger patterns, processing workflow, pitfalls, and escalation rules.
triggers:
  - "email requesting declarations page or dec page"
  - "lender or mortgagee requesting proof of coverage"
  - "need a copy of my declarations page"
  - "proof of insurance request from loan officer"
  - "evidence of insurance or EOI request that actually means dec page"
  - "certificate of insurance request for a personal lines policy"
  - "borrower or title company requesting current policy declarations"
tags: [email, declarations-page, dec-page, proof-of-insurance, lender, mortgagee, crm, supabase, carrier-portal, agency-ops]
metadata:
  hermes:
    tags: [email, declarations-page, dec-page, lender, proof-of-insurance, agency-ops]
    related_skills: [agency-email, email-policy-transaction, ezlynx-operations, libertas-agency-ops, libertas-crm-reference]
---

# Email Declarations Page Handler

How to process declarations page (dec page) request emails — 0.5% of the Libertas service inbox (86 emails). These are requests from clients, lenders, loan officers, or title companies who need a copy of the current policy declarations page as proof of insurance coverage.

## When This Skill Applies

Use when an email matches any of these patterns:

### Direct Dec Page Requests
- "I need a copy of my declarations page"
- "can you send me my dec page?"
- "need proof of insurance for my mortgage"
- "declarations page" or "dec page" in subject or body
- "policy declarations" request

### Lender/Mortgagee Requests
- Email from a lender, loan officer, or mortgage company requesting "proof of coverage"
- "evidence of insurance" from a mortgagee (if it's for a personal lines HO/dwelling policy, it's a dec page; if commercial, see closing-support)
- "We need the current declarations page for loan [number]"
- Subject: "Insurance Verification Required" from a bank or lender

### Title Company Requests
- Title company requesting dec page for closing (may overlap with closing-support)
- "Need declarations page for the file on [property address]"

### Borrower-Directed
- "My lender is asking for proof of insurance"
- "Need to send my dec page to my mortgage company"

Do NOT use for:
- Evidence of Insurance (EOI) for a real estate closing with a specific format/lender clause → `email-closing-support`
- Certificate of Insurance (COI) for a commercial general liability policy → `email-closing-support` or general service
- Claims-related document requests → claims skill
- Quote requests → `email-quoting-request`
- Endorsement to change mortgagee clause → `email-policy-transaction`

## Distinction: Dec Page vs. EOI vs. COI

| Request Type | What It Is | Typical Requester | Format | Skill |
|---|---|---|---|---|
| **Declarations Page** | Summary page of the insurance policy showing coverages, limits, deductibles, named insured, property address | Client, lender (general proof), loan officer | Carrier's standard dec page format (PDF) | This skill |
| **Evidence of Insurance (EOI)** | Formal document for a real estate closing, includes mortgagee clause, loan number, specific formatting | Lender with closing instructions, title company | ACORD 27/28 form or lender-specific template | `email-closing-support` |
| **Certificate of Insurance (COI)** | Commercial liability certificate showing additional insured, certificate holder | Contractor, property manager, client business partner | ACORD 25 form | `email-closing-support` or general |

**Rule of thumb**: If the request includes a loan number, mortgagee clause, or closing date → `email-closing-support`. If it's just "send me my dec page" → this skill.

## Email Sources

| Inbox | Address | Access | Notes |
|-------|---------|--------|-------|
| Service | service@libertasinsurance.com | Gmail API (GMAIL_SERVICE_REFRESH_TOKEN in ~/.config/libertas/gmail-service.env) | Main inbox for dec page requests |
| Kyle direct | Kyle@libertasinsurance.com | Not API-accessible | Fwd'd requests |

For Gmail API access patterns, see the `agency-email` skill.

## Processing Workflow

### Step 1: Identify the Requester and Policy

1. **Determine who is requesting** — client, lender, loan officer, title company
2. **Identify the policy** they need the dec page for:
   - Client usually provides: name, address, or policy number
   - Lender usually provides: borrower name, property address, or loan number
   - Title company usually provides: property address, buyer name, or file number
3. **Extract key data**:
   - Named insured name
   - Property address (for HO/dwelling/flood)
   - Policy number (if provided)
   - Line of business (HO, auto, flood, dwelling fire, etc.)
   - Where to send the dec page (email address, fax — rare)

### Step 2: Locate the Policy in CRM

```python
import psycopg2
conn = psycopg2.connect(env['SUPABASE_DB_URL'])  # from ~/.config/libertas/credentials.env
cur = conn.cursor()

# Search by policy number (most reliable)
cur.execute("""
    SELECT p.id, p.policy_number, p.status, p.carrier_id,
           c.name as carrier_name, ct.first_name, ct.last_name,
           ct.email, h.id as household_id
    FROM policies p
    LEFT JOIN carriers c ON p.carrier_id = c.id
    LEFT JOIN contacts ct ON p.primary_contact_id = ct.id
    LEFT JOIN households h ON p.household_id = h.id
    WHERE p.policy_number ILIKE %s
""", (f'%{policy_number}%',))

# If no match by policy number, search by name + address
cur.execute("""
    SELECT p.id, p.policy_number, p.status, p.carrier_id,
           c.name as carrier_name, ct.first_name, ct.last_name
    FROM policies p
    LEFT JOIN carriers c ON p.carrier_id = c.id
    LEFT JOIN contacts ct ON p.primary_contact_id = ct.id
    LEFT JOIN addresses a ON p.property_address_id = a.id
    WHERE (ct.first_name ILIKE %s AND ct.last_name ILIKE %s)
       OR a.street ILIKE %s
""", (first_name, last_name, f'%{street}%'))
```

**Policy lookup pitfalls:**
- Policy numbers may have different formats (with/without dashes, leading zeros)
- Always use `ILIKE` with wildcards for fuzzy matching
- If no match in CRM, check EZLynx CSV snapshots at `/tmp/ezlynx_phase0/`
- A client may have multiple policies — confirm which LOB they need

### Step 3: Locate the Dec Page

Dec pages can be obtained from three sources, in order of preference:

#### Option A: Carrier Portal (Most Current)
1. Access the carrier portal (credentials in master login sheet — see `libertas-agency-ops` skill)
2. Navigate to the policy details / documents section
3. Download the current declarations page PDF

| Carrier | Portal | Dec Page Location | Access Method |
|---------|--------|-------------------|---------------|
| Logic / Standard Casualty | EZ*Insure portal | Policy → Documents → Dec Page | Browserbase+Stagehand or Playwright |
| Foremost | STAR portal | Policy → Documents | Browserbase+Stagehand |
| Safeco / Liberty Mutual | Agent portal | Policy → View Documents | Browserbase+Stagehand |
| Travelers | Agent portal | Policy → Declarations | Browserbase+Stagehand |
| Progressive | Agent portal | Policy → Documents | Browserbase+Stagehand |
| TFPA | TWIA portal | Policy → Documents | Browserbase+Stagehand |

#### Option B: EZLynx Policy Master
1. If carrier portal is unavailable, check EZLynx for the policy's dec page image
2. EZLynx stores dec page snapshots from prior downloads/transactions
3. Access via EZLynx → Policy Master → search by policy number → Documents tab

#### Option C: Prior Email Attachments
1. Search Gmail for prior dec page sends — the same client may have requested before
2. Search by policy number in Gmail: `subject:{policy_number} has:attachment`
3. Prior attachment may be outdated — check the effective/expiration dates on the PDF
4. Only use if the policy is within the same term and no endorsements have been issued since

### Step 4: Send the Dec Page

1. **Reply to the requester** with the dec page attached as PDF
2. **Email template:**

```
Subject: Re: [Original Subject]

Hi [Requester Name],

Please find the attached declarations page for your [LOB] policy [policy_number] with [carrier_name].

Policy effective: [effective_date]
Policy expiration: [expiration_date]

Let me know if you need anything else.

Best regards,
Libertas Insurance
```

3. **If the requester is a lender** (not the client):
   - Verify we have authorization to share policy details with this third party
   - If the lender is listed as mortgagee/lienholder on the policy, it's authorized
   - If not, confirm with the client first — do NOT send a dec page to an unverified third party
4. **If dec page is not immediately available** (portal down, policy not found):
   - Respond within 4 hours acknowledging the request
   - Give an estimated delivery time (typically same business day)
   - Escalate if it will take more than 24 hours

### Step 5: Update CRM

```python
# Log the dec page send on the policy record
cur.execute("""
    UPDATE policies
    SET notes = COALESCE(notes, '') || %s,
        updated_at = NOW()
    WHERE id = %s
""", (f"\n[{send_date}] Dec page sent to {requester_email} at request of {request_source}.", policy_id))
conn.commit()

# Also log on contact record for tracking
cur.execute("""
    UPDATE contacts
    SET notes = COALESCE(notes, '') || %s
    WHERE id = %s
""", (f"\n[{send_date}] Dec page for policy {policy_number} emailed to {requester_email}.", contact_id))
conn.commit()
```

## Escalation Rules

### Always Escalate to Kyle When:
1. **Unverified third-party request** — someone claiming to be a lender requests a dec page but is NOT listed as mortgagee on the policy
2. **Policy not found in CRM** — cannot locate any record for the named insured or property address
3. **Policy status is Cancelled/Non-renewed** — the policy the requester is asking about is no longer active; Kyle decides how to respond
4. **Carrier portal access failure** — cannot access the carrier portal after 2 attempts
5. **Dec page shows unexpected data** — coverage lapsed, wrong property, wrong named insured, or information that conflicts with CRM
6. **Request is for a policy written by another agency** — we may have lost the account or there's a data issue
7. **Request includes mortgagee clause changes** — they want the dec page AND a mortgagee clause update → this becomes a policy transaction (see `email-policy-transaction`)
8. **Multiple urgent requests from same lender** — may indicate a broader issue (forced-place insurance notice, etc.)

### Auto-Handle (No Escalation Needed):
- Standard dec page requests from named insured (client themselves)
- Lender requests where the lender is the listed mortgagee on the policy
- Repeat requests from same requester within 30 days (just resend)
- Client asking for their own dec page for personal records

### Escalation format:
```
DECLARATIONS PAGE REQUEST — [Priority Level]
Policy: {policy_number} | Client: {client_name} | Carrier: {carrier}
Requester: {requester_name} at {requester_email}
Is Mortgagee on Policy: {YES/NO}
Issue: {summary of why escalated}
Action Needed: {specific action request}
Email ID: {gmail_message_id}
```

## Common Pitfalls

1. **Sending dec page to unauthorized third party** — always verify the requester is either the named insured or a listed mortgagee/lienholder. If in doubt, confirm with the client before sending.

2. **Sending an outdated dec page** — if the policy has had endorsements since the last dec page was generated, the old one may show incorrect coverages or premium. Always try to get the most current version from the carrier portal first.

3. **Confusing dec page with EOI** — a dec page is NOT an Evidence of Insurance. For real estate closings, the lender typically requires an EOI (ACORD 27/28) with specific mortgagee clause language, loan number, and formatting. If the request mentions a closing date or loan number, route to `email-closing-support`.

4. **Policy number format mismatch** — carrier portal may require the exact format (e.g., `SC1-HA-033636-02`), while the requester may provide a partial or different format (`033636`). Try multiple format variations when searching.

5. **Client has multiple policies** — if John Smith has HO, auto, and flood with the agency, confirm WHICH dec page they need. Don't assume HO just because it's the most common.

6. **Carrier portal timeouts** — carrier portals (especially Logic) can be slow or unresponsive. Don't loop on retries; after 2 failed attempts, escalate and respond to the requester with an ETA.

7. **Gmail attachment size limits** — dec pages are usually small (<1MB), but if the PDF is unusually large, Gmail may reject it. Compress if needed or share via link.

8. **Not logging the send in CRM** — always update the policy notes when a dec page is sent. This prevents duplicate work when the same request comes in again and provides an audit trail.

9. **Auto-reply to NO_REPLY senders** — some carrier notifications come from NO_REPLY addresses. The dec page request itself should come from a real person. If the reply-to is NO_REPLY, find the correct contact from the email body.

10. **REST API RLS blocks** — the anon key gets `permission denied` for policy writes. Use direct DB connection (psycopg2 with `SUPABASE_DB_URL` from `~/.config/libertas/credentials.env`) for all CRM writes.

## Verification Checklist

- [ ] Requester identity verified (named insured or listed mortgagee)
- [ ] Correct policy identified (policy number + LOB confirmed)
- [ ] Most current dec page obtained (from carrier portal, not stale attachment)
- [ ] Dec page sent to requester via email with PDF attachment
- [ ] CRM policy notes updated with send record
- [ ] Escalation sent if any HIGH-priority condition met
- [ ] Acknowledgment sent within 4 hours if dec page not immediately available
- [ ] Dec page vs EOI distinction verified (route to closing-support if EOI needed)
