---
name: email-commissions
version: 1.0.0
category: agency-ops
description: Handle commission statement emails from carriers — track, reconcile, and record commission payments. How to process commission reports, identify discrepancies, update financial records in CRM. 0.3% of inbox (49 emails).
triggers:
  - "commission statement or commission report from carrier"
  - "agency commission payment notification"
  - "commission reconciliation or adjustment notice"
  - "direct bill commission report"
  - "agency bill commission report"
  - "commission rate change notification"
  - "profit sharing or contingency bonus notification"
  - "commission clawback or chargeback notice"
  - "premium audit resulting in commission adjustment"
tags: [email, commissions, financial, reconciliation, carrier, crm, supabase, agency-ops]
metadata:
  hermes:
    tags: [email, commissions, financial, reconciliation, agency-ops]
    related_skills: [agency-email, email-policy-transaction, libertas-agency-ops, libertas-crm-reference]
---

# Email Commissions Handler

How to process commission statement emails — 0.3% of the Libertas service inbox (49 emails). These are carrier-to-agency communications reporting commission payments, adjustments, clawbacks, and rate changes. Commissions are the agency's primary revenue — accurate tracking and reconciliation is critical for financial health.

## When This Skill Applies

Use when an email matches any of these patterns:

### Commission Statements
- "Commission Statement" in subject
- "Agency Commission Report" or "Commission Report"
- "Commission Payment Advice" or "Payment Advice"
- Sender is a carrier finance/accounting department
- Email includes a spreadsheet or PDF with policy-by-policy commission details

### Commission Adjustments
- "Commission Adjustment" notice
- "Commission correction" or "revised commission"
- Premium audit resulting in commission change
- Endorsement premium change affecting commission
- Policy cancellation resulting in commission clawback

### Rate Changes
- "Commission rate change" notification
- "Updated commission schedule"
- "New appointment commission terms"
- "Profit sharing agreement update"

### Special Payments
- "Profit sharing" or "contingency bonus" payment
- "Performance bonus" from carrier
- "Growth bonus" or "portfolio incentive"

Do NOT use for:
- Policy transaction emails (endorsement, cancellation, etc.) → `email-policy-transaction`
- Premium payment notices → payment skill
- Underwriting decisions → `email-underwriting`
- New business quotes → `email-quoting-request`
- General carrier correspondence → `email-policy-transaction`

## Commission Types

| Commission Type | Description | Frequency | Typical Format |
|---|---|---|---|
| **New business** | Commission on a new policy sale | Per policy bind | Included in regular statement |
| **Renewal** | Commission on policy renewal (often lower rate than new) | Per renewal | Included in regular statement |
| **Endorsement** | Commission on mid-term premium changes | Per endorsement | Included in regular statement |
| **Direct bill** | Carrier collects premium, pays commission to agency | Monthly/quarterly statement | Spreadsheet or PDF with policy-level detail |
| **Agency bill** | Agency collects premium, retains commission, remits balance to carrier | Per payment received | Carrier reports what's owed |
| **Clawback/chargeback** | Commission returned to carrier (cancellation, audit, error) | As-needed | Negative amount in statement |
| **Profit sharing** | Bonus based on book performance (loss ratio, retention, growth) | Annually or semi-annually | Separate statement |
| **Contingency** | Performance-based bonus from carrier | Annually | Separate statement |

## Commission Rates by LOB (Typical)

| LOB | New Business | Renewal | Notes |
|-----|-------------|---------|-------|
| Homeowners (HO) | 15-20% | 10-15% | Varies by carrier |
| Auto | 10-15% | 8-12% | Varies by carrier and state |
| Flood (NFIP) | 15% | 15% | Fixed by NFIP — same for new and renewal |
| Dwelling Fire | 15-20% | 10-15% | Varies by carrier |
| Commercial | 10-15% | 8-12% | Lower for large accounts |
| Umbrella | 10-15% | 8-12% | |
| Workers Comp | 5-10% | 5-10% | Often lower due to audit adjustments |

**Note**: These are typical ranges. Actual rates vary by carrier and are set in the carrier appointment agreement. Some carriers use a flat rate; others use a tiered schedule based on premium volume or loss ratio.

## Email Sources

| Inbox | Address | Access | Notes |
|-------|---------|--------|-------|
| Service | service@libertasinsurance.com | Gmail API (GMAIL_SERVICE_REFRESH_TOKEN in ~/.config/libertas/gmail-service.env) | Main inbox for commission statements |
| Kyle direct | Kyle@libertasinsurance.com | Not API-accessible | Fwd'd commission emails |

For Gmail API access patterns, see the `agency-email` skill.

## Processing Workflow

### Step 1: Identify the Carrier and Statement Type

1. **Determine the carrier** from the sender domain or email body
2. **Classify the statement type** (new business, renewal, adjustment, profit sharing, etc.)
3. **Identify the statement period** — most carriers send monthly or quarterly statements
4. **Extract the attachment** if present (usually a CSV, Excel, or PDF of policy-level commission detail)

### Step 2: Parse Commission Details

From the commission statement (attachment or email body), extract for each policy:

1. **Policy number** — to match against CRM
2. **Named insured** — for verification
3. **Premium amount** — the base premium on which commission is calculated
4. **Commission rate** — the percentage applied
5. **Commission amount** — the dollar amount paid/owed
6. **Transaction type** — new, renewal, endorsement, cancellation, etc.
7. **Transaction date** — when the transaction occurred
8. **Payment date** — when the commission was (or will be) paid

**Common carrier statement formats:**

| Carrier | Format | Delivery Method | Frequency |
|---------|--------|----------------|-----------|
| Logic / Standard Casualty | Excel/CSV attachment | Email | Monthly |
| Foremost | PDF or CSV | Email | Monthly |
| Safeco / Liberty Mutual | PDF statement | Email or portal | Monthly |
| Travelers | CSV or portal download | Email or portal | Monthly |
| Progressive | Portal download | Portal (email notification) | Monthly |
| TFPA | PDF statement | Email | Quarterly |

### Step 3: Reconcile Against CRM

For each line item on the commission statement, verify against the CRM policy record:

```python
import psycopg2
conn = psycopg2.connect(env['SUPABASE_DB_URL'])  # from ~/.config/libertas/credentials.env
cur = conn.cursor()

# For each policy on the commission statement
for entry in commission_entries:
    policy_number = entry['policy_number']
    stated_premium = entry['premium']
    stated_commission = entry['commission']
    
    # Look up the policy in CRM
    cur.execute("""
        SELECT p.id, p.policy_number, p.status, p.premium_annual,
               p.effective_date, p.carrier_id, c.name as carrier_name
        FROM policies p
        LEFT JOIN carriers c ON p.carrier_id = c.id
        WHERE p.policy_number ILIKE %s
    """, (f'%{policy_number}%',))
    result = cur.fetchone()
    
    if result:
        crm_premium = result[3]  # premium_annual
        # Compare stated_premium vs crm_premium
        # Flag discrepancies
```

**Reconciliation checks:**

| Check | What to Compare | Tolerance | Action If Discrepancy |
|-------|----------------|-----------|----------------------|
| **Premium match** | Statement premium vs CRM premium_annual | ±2% (for rounding) | Flag for review |
| **Policy exists** | Policy number found in CRM | Exact match | If not found, check EZLynx CSV or escalate |
| **Status match** | Statement shows active but CRM shows cancelled | N/A | Investigate — may be timing difference or error |
| **Commission rate** | Rate matches expected rate for carrier+LOB | Must match | If different, flag for rate verification |
| **Duplicate entry** | Same policy appearing twice in same statement | N/A | Deduplicate — likely a data error in carrier report |

### Step 4: Record Commission in CRM

```python
# Record commission payment on the policy record
cur.execute("""
    UPDATE policies
    SET notes = COALESCE(notes, '') || %s,
        updated_at = NOW()
    WHERE id = %s
""", (f"\n[{payment_date}] Commission: ${commission_amount} on ${premium} premium ({commission_rate}%) for {transaction_type}. Statement period: {statement_period}.", policy_id))
conn.commit()
```

**Future: dedicated commission table** — ideally, commissions should be tracked in a dedicated `commission_payments` table:
```sql
-- Future schema (not yet in CRM)
CREATE TABLE commission_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID REFERENCES policies(id),
    carrier_id UUID REFERENCES carriers(id),
    statement_date DATE,
    transaction_type TEXT,  -- 'new', 'renewal', 'endorsement', 'cancellation', 'clawback'
    premium_amount NUMERIC(10,2),
    commission_rate NUMERIC(5,4),
    commission_amount NUMERIC(10,2),
    payment_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Until a dedicated table exists, log commission details in the policy `notes` field.

### Step 5: Flag Discrepancies

Any discrepancy identified in Step 3 must be flagged:

| Discrepancy Type | Severity | Action |
|---|---|---|
| **Policy not found in CRM** | HIGH | Could be a missing policy record, data migration issue, or wrong policy number. Escalate. |
| **Premium mismatch > 2%** | MEDIUM | May be due to endorsement, audit, or timing. Check endorsement history. |
| **Commission rate different from expected** | MEDIUM | Verify carrier appointment agreement. Rate may have changed. |
| **Commission for cancelled policy** | LOW | May be pro-rata return commission. Verify. |
| **Negative commission (clawback)** | HIGH | Usually means policy was cancelled or audited. Verify the reason and update CRM. |
| **Duplicate entries** | LOW | Deduplicate. Likely a carrier reporting error. |
| **Missing expected commission** | MEDIUM | A policy we know is active doesn't appear on the statement. May need to contact carrier. |

### Step 6: Aggregate and Report

After processing the full statement, generate a summary:

```python
summary = {
    "carrier": carrier_name,
    "statement_period": period,
    "total_premium": sum(e['premium'] for e in entries),
    "total_commission": sum(e['commission'] for e in entries),
    "effective_rate": total_commission / total_premium * 100,
    "policy_count": len(entries),
    "discrepancies": len(flagged_items),
    "new_business_count": count_by_type('new'),
    "renewal_count": count_by_type('renewal'),
    "clawback_count": count_by_type('clawback'),
}
```

Log this summary in CRM or a financial tracking sheet.

## Special Situations

### Commission Clawbacks
- Occur when a policy is cancelled mid-term and the carrier recovers the unearned commission
- Also occur on premium audits that reduce the premium
- Clawbacks appear as negative amounts on the commission statement
- **Action**: Verify the cancellation/audit in CRM. If the clawback is unexpected (policy is still active in CRM), investigate immediately.

### Profit Sharing / Contingency Bonuses
- Paid annually based on book performance metrics (loss ratio, retention, growth, premium volume)
- Typically 1-5% of annual book premium
- Not tied to individual policies — tracked separately
- **Action**: Record as a separate financial entry. Notify Kyle of the amount.

### Commission Rate Changes
- Carriers may change commission rates (usually at renewal)
- Rate changes should be documented in the carrier appointment terms
- **Action**: If a rate change is announced, update the expected commission rate for that carrier in CRM. Note the effective date.

### Direct Bill vs Agency Bill
- **Direct bill**: Carrier collects premium from client and pays commission to agency. Commission statement shows what was paid.
- **Agency bill**: Agency collects premium from client, retains commission, and remits the balance to carrier. Commission statement shows what the agency owes the carrier.
- **Key difference**: For agency bill, the commission is "self-paid" — the carrier statement is a reconciliation tool, not a payment. For direct bill, the carrier is actually sending money.

## Escalation Rules

### Always Escalate to Kyle When:
1. **Commission for a policy not in CRM** — may indicate a missing policy record (lost revenue) or a data migration issue
2. **Negative commission (clawback) > $500** — significant clawback that may indicate a cancelled or audited policy the agency wasn't aware of
3. **Commission rate significantly different from expected** (>2% variance from carrier agreement rate) — carrier may have changed terms or made an error
4. **Total commission for the period is materially different from expectations** (>20% variance from projected) — may indicate book issues
5. **Carrier announces commission rate reduction** — affects agency revenue; Kyle needs to evaluate the relationship
6. **Missing commission for a known active policy** — carrier may not be paying what's owed
7. **Duplicate commission payments** — carrier may need to be notified to prevent future clawbacks
8. **Profit sharing payment received** — Kyle needs to know for financial planning

### Auto-Handle (No Escalation Needed):
- Routine commission statements where all entries match CRM
- Small premium mismatches (<2%) due to rounding or endorsement timing
- Standard renewal commissions at expected rates
- Monthly statement processing and logging

### Escalation format:
```
COMMISSION ISSUE — [Priority Level]
Carrier: {carrier_name} | Statement Period: {period}
Type: {discrepancy type}
Details: {summary of the issue}
Policy: {policy_number} | Client: {client_name}
Expected: ${expected_commission} at {expected_rate}%
Actual: ${actual_commission} at {actual_rate}%
Variance: ${variance} ({variance_pct}%)
Action Needed: {specific action request}
Email ID: {gmail_message_id}
```

## Common Pitfalls

1. **Not reconciling commission statements** — just filing them without checking means discrepancies go unnoticed. The agency may be underpaid on commissions without knowing it.

2. **Treating commission income as policy-level revenue** — commission is a percentage of premium. If the premium in CRM is wrong, the commission reconciliation will flag it, which is useful — but don't assume the commission statement premium is always correct. Cross-reference with carrier portal data.

3. **Ignoring clawbacks** — a negative commission entry means the carrier is recovering money. If it's unexpected, the agency may owe money it wasn't tracking. Always investigate clawbacks.

4. **Not tracking commission rates by carrier** — commission rates vary by carrier and LOB. Without a reference table of expected rates, you can't identify when a carrier underpays. Build and maintain a commission rate reference.

5. **Assuming all policies appear on every statement** — some carriers only report when commission is paid (direct bill at payment receipt), not at bind. A new policy may not appear until the client makes their first payment.

6. **Commission on cancelled policies** — when a policy is cancelled, the carrier claws back the unearned commission. But the cancellation and the clawback may appear on different month's statements. Don't assume the clawback is an error just because the cancellation was last month.

7. **Not recording profit sharing separately** — profit sharing and contingency bonuses are significant income but not tied to individual policies. They should be tracked separately from policy-level commissions for accurate financial reporting.

8. **REST API RLS blocks** — the anon key gets `permission denied` for policy writes. Use direct DB connection (psycopg2 with `SUPABASE_DB_URL` from `~/.config/libertas/credentials.env`) for all CRM writes.

9. **Excel/CSV attachment parsing errors** — carrier commission files often have inconsistent formatting (merged cells, multiple header rows, date format changes). Always validate the parsed data against expected ranges before recording.

10. **Not tracking expected vs actual commission** — without a "commission receivable" projection, you can't identify when a carrier is late paying or underpaying. Track what's expected each period and reconcile against actuals.

11. **Agency bill vs direct bill confusion** — the accounting treatment is different. For agency bill, the commission is retained (not received), so the statement is a reconciliation. For direct bill, the commission is received, so the statement is a payment record. Know which model each carrier uses.

## Verification Checklist

- [ ] Carrier and statement period identified
- [ ] Commission attachment downloaded and parsed
- [ ] All line items reconciled against CRM policy records
- [ ] Premium amounts verified (within tolerance)
- [ ] Commission rates match expected rates for carrier+LOB
- [ ] Discrepancies flagged and categorized
- [ ] Commission details logged in CRM policy notes
- [ ] Summary statistics calculated (total premium, total commission, effective rate)
- [ ] Clawbacks investigated and reason verified
- [ ] Escalation sent if any HIGH-priority discrepancy found
- [ ] Profit sharing / contingency payments recorded separately
- [ ] Statement filed for financial records
