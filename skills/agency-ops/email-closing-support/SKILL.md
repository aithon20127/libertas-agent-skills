---
name: email-closing-support
version: 1.0.0
category: agency-ops
description: Handle insurance coordination emails for real estate closings — timely delivery of binders, Evidence of Insurance (EOI), and Certificate of Insurance (COI). Lender requirements, mortgagee clauses, title company coordination. 0.4% of inbox (57 emails).
triggers:
  - "email about real estate closing and insurance"
  - "lender requesting EOI or evidence of insurance for closing"
  - "title company requesting binder or COI for closing"
  - "loan officer requesting insurance documentation for closing"
  - "mortgagee clause verification or update for closing"
  - "closing date coordination and insurance timing"
  - "need insurance in place for closing on date"
  - "HUD-1 or settlement statement insurance line item"
  - "proof of insurance for mortgage application"
  - "borrower closing checklist insurance item"
tags: [email, closing, binder, EOI, evidence-of-insurance, COI, certificate-of-insurance, lender, title-company, mortgagee, real-estate, agency-ops]
metadata:
  hermes:
    tags: [email, closing, EOI, binder, mortgagee, real-estate, agency-ops]
    related_skills: [agency-email, email-declarations-page, email-policy-transaction, email-underwriting, ezlynx-operations, libertas-agency-ops, libertas-crm-reference]
---

# Email Closing Support Handler

How to process real estate closing-related insurance emails — 0.4% of the Libertas service inbox (57 emails). These are time-critical requests from lenders, loan officers, title companies, and buyers who need insurance documentation (binder, EOI, COI) in place before a real estate closing. Timeliness is critical — a missing EOI can delay or kill a closing.

## When This Skill Applies

Use when an email matches any of these patterns:

### Closing-Related Requests
- "Need insurance for closing on [date]"
- "Evidence of Insurance needed for [address]"
- "Closing is [date] and we need the binder/EOI/COI"
- Lender or loan officer requesting insurance documentation with closing instructions
- Title company requesting proof of insurance for settlement
- "Mortgagee clause needs to be added" with specific lender language
- "Please add [lender] as mortgagee/loss payee"
- Borrower forwarding lender's closing checklist with insurance requirements

### EOI / Binder Requests
- "Evidence of Insurance" request with loan number and mortgagee clause
- "Need a binder for [address]" with specific coverage requirements
- Lender-specific EOI format (ACORD 27/28 or proprietary form)
- "Certificate of Insurance" for a property-closing context

### Mortgagee Clause Updates for Closing
- "Please update the mortgagee clause to: [specific language]"
- Lender name + loan number + address clause format
- "Loss payee" clause update for closing

Do NOT use for:
- Simple dec page requests (no closing, no loan number, no lender clause) → `email-declarations-page`
- General mortgagee clause updates (not closing-related) → `email-policy-transaction`
- Underwriting info requests → `email-underwriting`
- Quote requests for a new purchase (not yet at closing stage) → `email-quoting-request`
- Commercial COI (not closing-related) → general service

## Critical Distinction: This Is Time-Sensitive

Real estate closings have hard deadlines. A missing EOI can:
- **Delay the closing** — costing the buyer rate-lock fees, inspection fees, mover costs
- **Kill the deal** — if the rate lock expires or the seller walks away
- **Create legal liability** — for the agency if the delay is our fault

**Default priority for closing-support emails: HIGH until confirmed otherwise.**

## Email Sources

| Inbox | Address | Access | Notes |
|-------|---------|--------|-------|
| Service | service@libertasinsurance.com | Gmail API (GMAIL_SERVICE_REFRESH_TOKEN in ~/.config/libertas/gmail-service.env) | Main inbox for closing emails |
| Kyle direct | Kyle@libertasinsurance.com | Not API-accessible | Fwd'd closing emails, often with urgency notes |

For Gmail API access patterns, see the `agency-email` skill.

## Processing Workflow

### Step 1: Identify the Closing and Parties

1. **Determine the closing date** — this drives all deadlines
2. **Identify the parties**:
   - Buyer/borrower (named insured)
   - Lender/mortgagee (who needs the EOI)
   - Loan officer (point of contact at lender)
   - Title company (may be coordinating)
   - Real estate agent (may be CC'd)
3. **Extract key data**:
   - Property address
   - Buyer name
   - Lender name and specific mortgagee clause language (if provided)
   - Loan number (if provided)
   - Closing date
   - Coverage requirements (if specified — HO, flood, wind, etc.)
   - EOI format requirements (ACORD 27/28, lender-specific, or just a binder)
   - Who the EOI/binder should be sent to (email addresses)

### Step 2: Check for Existing Policy or Quote

```python
import psycopg2
conn = psycopg2.connect(env['SUPABASE_DB_URL'])  # from ~/.config/libertas/credentials.env
cur = conn.cursor()

# Search by buyer name and property address
cur.execute("""
    SELECT p.id, p.policy_number, p.status, p.premium_annual,
           p.effective_date, p.expiration_date, p.carrier_id,
           c.name as carrier_name, h.id as household_id,
           ct.first_name, ct.last_name, ct.email, ct.phone
    FROM policies p
    LEFT JOIN carriers c ON p.carrier_id = c.id
    LEFT JOIN households h ON p.household_id = h.id
    LEFT JOIN contacts ct ON p.primary_contact_id = ct.id
    LEFT JOIN addresses a ON p.property_address_id = a.id
    WHERE (ct.first_name ILIKE %s AND ct.last_name ILIKE %s)
       OR a.street ILIKE %s
""", (first_name, last_name, f'%{street}%'))
```

**Three scenarios:**

| Scenario | Status | Action |
|----------|--------|--------|
| **Policy already bound** | Active policy with correct effective date | Generate EOI/binder, add mortgagee clause if needed, send |
| **Quote completed but not bound** | Quote in progress or completed | Bind the policy, then generate EOI/binder |
| **No policy or quote** | New client, nothing in system | Start quoting process URGENTLY — closing deadline is approaching |

### Step 3: Bind Coverage (If Not Already Bound)

If the client has a completed quote but hasn't bound:

1. **Confirm the effective date** — typically the closing date or one day before
2. **Collect binding requirements**:
   - Signed application (or e-signature)
   - Down payment or full payment
   - Underwriting approval (if applicable)
3. **Process the bind** through the carrier portal
4. **Confirm the policy number and effective date** before proceeding to EOI

If the client has NO quote yet:
- This is URGENT — escalate to Kyle immediately
- Start the quoting process via `email-quoting-request` workflow
- Communicate the urgency to the client: "Your closing is [date] and we need to get coverage bound ASAP"

### Step 4: Add Mortgagee Clause (If Required)

Most closing-related EOI requests require a specific mortgagee clause. If not already on the policy:

1. **Get the exact mortgagee clause language** from the lender — do NOT paraphrase or abbreviate
2. **Submit the mortgagee clause update** via the carrier portal (endorsement) or at bind time
3. **Common mortgagee clause format:**
   ```
   [Lender Name]
   Its Successors and/or Assigns
   P.O. Box [number]
   [City], [State] [ZIP]
   Loan Number: [number]
   ```
4. **Verify the clause was added** before generating the EOI — an EOI with the wrong or missing mortgagee clause will be rejected by the lender

**Mortgagee clause pitfalls:**
- ISAOA (Its Successors and/or Assigns) — always include if lender requests it
- ATIMA (As Their Interests May Appear) — sometimes required alongside ISAOA
- Loan number placement varies by lender — some want it in the clause, some want it as a separate reference
- Some lenders require PMI company as additional mortgagee

### Step 5: Generate and Deliver the EOI / Binder

#### EOI (Evidence of Insurance) — ACORD 27/28
1. **Most carriers can generate an ACORD EOI** from their portal or agent system
2. **Required fields on the EOI:**
   - Named insured (buyer/borrower)
   - Property address
   - Policy number
   - Carrier name
   - Policy effective and expiration dates
   - Coverage type and limits (Dwelling, Other Structures, Personal Property, Liability, Medical Payments)
   - Deductibles
   - Mortgagee clause (exactly as provided by lender)
   - Loan number (if provided)
3. **If the carrier portal can generate the EOI** — download the ACORD form PDF
4. **If the carrier portal cannot generate the EOI** — fill out an ACORD 27 (HO) or 28 (commercial) manually:
   - ACORD forms available at `/home/kyle/libertas-crm/browserbase-functions/` or online
   - Fill all required fields accurately
   - Sign as agent (Libertas Insurance)

#### Binder (Temporary Evidence)
- Some carriers issue a binder (temporary proof of coverage) instead of or in addition to an EOI
- A binder typically shows: policy number, effective date, coverages, mortgagee clause
- Binders are time-limited (usually 30-90 days) — the actual policy replaces the binder once issued
- If a binder is requested specifically, generate it through the carrier portal

#### COI (Certificate of Insurance) — ACORD 25
- Used for commercial properties or landlord-tenant situations at closing
- Shows certificate holder (lender or property manager), additional insured status
- Generate through carrier portal or fill ACORD 25 manually

### Step 6: Send to the Requestor

1. **Email the EOI/binder/COI** to:
   - The loan officer (if they requested it)
   - The title company (if they're coordinating)
   - The buyer/borrower (for their records — CC them)
2. **Delivery format**: PDF attachment via email (preferred). Fax if lender requires it (rare).
3. **Subject line**: Clear and specific:
   ```
   Subject: Evidence of Insurance — [Borrower Name] — [Property Address] — Closing [Date]
   ```
4. **Email body**:
   ```
   Hi [Requester Name],

   Please find the attached Evidence of Insurance for the above-referenced property.

   Named Insured: [buyer name]
   Property: [address]
   Policy Number: [policy_number]
   Carrier: [carrier_name]
   Effective: [date]
   Mortgagee: [lender name] — Loan #[loan_number]

   Please confirm receipt and let me know if any additional information is needed for the closing.

   Best regards,
   Libertas Insurance
   ```
5. **Request delivery confirmation** — ask the recipient to confirm receipt, especially if the closing is within 48 hours

### Step 7: Update CRM

```python
# Log the closing support activity
cur.execute("""
    UPDATE policies
    SET notes = COALESCE(notes, '') || %s,
        updated_at = NOW()
    WHERE id = %s
""", (f"\n[{date}] Closing support: EOI sent to {lender_name} for closing on {closing_date}. Loan #{loan_number}. Mortgagee clause: {mortgagee_clause_summary}. Sent to: {recipient_emails}.", policy_id))
conn.commit()

# Also update contact record
cur.execute("""
    UPDATE contacts
    SET notes = COALESCE(notes, '') || %s
    WHERE id = %s
""", (f"\n[{date}] Closing on {closing_date} at {property_address}. EOI/binder delivered to {lender_name}.", contact_id))
conn.commit()
```

## Escalation Rules

### Always Escalate to Kyle When:
1. **Closing is within 48 hours and no policy is bound** — critical timeline; may need manual carrier intervention
2. **Closing is within 24 hours and EOI not yet delivered** — emergency — Kyle may need to call the carrier directly
3. **Carrier cannot bind before closing date** — underwriting issue, system outage, or inspection required before bind
4. **Lender rejects the EOI format** — the EOI we sent doesn't meet the lender's specific requirements
5. **Mortgagee clause is unclear or incomplete** — lender provided ambiguous clause language
6. **Multiple policies needed for closing** (HO + flood + wind) — coordination complexity
7. **Client is unresponsive** — we need info/payment to bind, but the client isn't responding with closing approaching
8. **Carrier portal is down** on closing day — Kyle may need to call the carrier to bind manually
9. **Flood insurance required** — NFIP has a 30-day wait period (with limited exceptions for closings); Kyle needs to evaluate if the closing qualifies for the exception
10. **Premium or coverage disagreement** — lender's requirements exceed what the carrier will offer

### Auto-Handle (No Escalation Needed):
- Standard EOI requests with clear lender instructions and policy already bound
- Mortgagee clause additions where the clause language is clear and provided
- Follow-up sends (same EOI resent to different parties)
- Closing extensions where we already have coverage in place

### Escalation format:
```
CLOSING SUPPORT — [URGENT/HIGH/MEDIUM]
Borrower: {client_name} | Property: {address}
Closing Date: {date}
Lender: {lender_name} | Loan #: {loan_number}
Policy Status: {bound/quoted/none}
Issue: {summary of the problem}
Deadline: {when EOI/binder must be delivered}
Action Needed: {specific action request}
Email ID: {gmail_message_id}
```

## Special Situations

### Flood Insurance 30-Day Wait Period
- NFIP flood policies have a 30-day waiting period from application to effective date
- **Exception for closings**: If the flood insurance is purchased in connection with a loan, the 30-day wait period is WAIVED — the policy can be effective immediately at closing
- This exception requires the lender to mandate flood insurance as a condition of the loan
- Document this in CRM notes and on the flood application

### Wind/Hail Deductible Requirements
- Texas coastal properties may have separate wind/hail deductibles
- Lenders often require specific maximum wind/hail deductibles (typically 2% or 5% of Coverage A)
- Verify the wind deductible meets lender requirements before delivering EOI

### Force-Placed Insurance Threat
- If the lender's email mentions force-placed insurance, the closing may be at risk
- Force-placed means the lender will buy their own (expensive, minimal coverage) policy
- This usually means the borrower hasn't provided proof of insurance
- IMMEDIATE action required — get the EOI to the lender ASAP

## Common Pitfalls

1. **Missing the closing deadline** — the #1 error. Even a one-day delay can cost the buyer their rate lock or the deal. Treat every closing email as HIGH priority until confirmed otherwise.

2. **Wrong mortgagee clause** — lenders have VERY specific mortgagee clause language requirements. A single word wrong (missing "ISAOA", wrong P.O. Box, wrong loan number format) can cause the EOI to be rejected. Copy the clause EXACTLY as provided.

3. **Sending a dec page instead of an EOI** — a dec page is NOT an EOI. Lenders require the ACORD EOI form (27 for HO, 28 for commercial) or their proprietary form. A dec page doesn't include the mortgagee clause in the required format. If the request is for a closing, send an EOI, not a dec page.

4. **Not verifying coverage meets lender requirements** — lenders may require:
   - Minimum Coverage A (replacement cost)
   - Specific deductible maximums
   - Flood coverage if in a flood zone
   - Wind coverage if in a wind zone
   - Specific liability limits
   Verify all of these before generating the EOI, or the lender will reject it.

5. **Flood zone not checked** — if the property is in a flood zone and the lender requires flood insurance, the HO EOI alone is insufficient. Check FEMA flood maps for the property address.

6. **Effective date mismatch** — the EOI effective date must match or precede the closing date. If the policy effective date is after the closing, the EOI is invalid for the closing.

7. **Not CC'ing all necessary parties** — the loan officer, title company, and buyer all may need the EOI. Send to everyone who needs it, not just the original requester.

8. **Assuming the policy is already bound** — sometimes the buyer says "I have insurance" but the policy hasn't actually been bound yet (still in quoting or underwriting). Verify the policy status in the carrier system before sending an EOI.

9. **REST API RLS blocks** — the anon key gets `permission denied` for policy writes. Use direct DB connection (psycopg2 with `SUPABASE_DB_URL` from `~/.config/libertas/credentials.env`) for all CRM writes.

10. **Not following up on EOI delivery** — send the EOI and then ASK for confirmation. If the lender says they didn't receive it (spam filter, wrong email, etc.), you need to know immediately, not at closing time.

11. **Carrier-specific EOI generation differences** — some carriers auto-generate ACORD EOIs from their portal; others require manual form completion. Know which carriers support auto-generation and which require manual work to avoid surprises on tight timelines.

## Verification Checklist

- [ ] Closing date identified and all deadlines calculated
- [ ] All parties identified (borrower, lender, title company, loan officer)
- [ ] Policy bound and active (or bind in progress with clear timeline)
- [ ] Mortgagee clause obtained and added to policy EXACTLY as lender specified
- [ ] Coverage meets lender requirements (limits, deductibles, LOBs)
- [ ] EOI/binder/COI generated with correct information
- [ ] EOI delivered to all required parties via email
- [ ] Delivery confirmation requested
- [ ] CRM updated with closing support activity log
- [ ] Flood insurance requirement checked (if applicable)
- [ ] Escalation sent if any URGENT/HIGH condition met
- [ ] Follow-up set for delivery confirmation
