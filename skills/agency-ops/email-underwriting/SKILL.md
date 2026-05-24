---
name: email-underwriting
version: 1.0.0
category: agency-ops
description: Handle underwriting request emails from carriers — info requests, rate revisions, eligibility changes, inspection requirements, conditional binders. How to provide info to the carrier, update client, and manage the underwriting process. 0.4% of inbox (57 emails).
triggers:
  - "underwriting information request from carrier"
  - "rate revision or rate change notification"
  - "eligibility change or eligibility question"
  - "inspection request or inspection scheduling"
  - "conditional binder with underwriting requirements"
  - "carrier requesting additional information for pending application"
  - "underwriting referral or review notice"
  - "mid-term underwriting review"
  - "premium audit notification"
  - "loss control or risk improvement request"
tags: [email, underwriting, carrier, rate-revision, eligibility, inspection, binder, crm, supabase, agency-ops]
metadata:
  hermes:
    tags: [email, underwriting, rate-revision, eligibility, inspection, agency-ops]
    related_skills: [agency-email, email-policy-transaction, email-quoting-request, ezlynx-operations, libertas-agency-ops, libertas-crm-reference]
---

# Email Underwriting Handler

How to process underwriting-related emails — 0.4% of the Libertas service inbox (57 emails). These are carrier-to-agent communications about underwriting decisions, information requests, rate revisions, eligibility changes, and inspection requirements for pending or active policies.

## When This Skill Applies

Use when an email matches any of these patterns:

### Underwriting Information Requests
- "Underwriting Info - [Account Name], [Policy#]" (common Travelers pattern)
- "Additional information required for your submission"
- "Please provide the following for underwriting review"
- Carrier asking for photos, inspection reports, prior carrier info, or loss history
- "Underwriting referral" or "referred to underwriting"

### Rate Revisions
- "Rate revision" or "revised premium" notice
- "Rate change effective [date]"
- "Your quote has been revised" with new premium
- "Due to underwriting review, the premium has been adjusted"
- "Rate increase/decrease notification"

### Eligibility Changes
- "Eligibility question" from carrier
- "Risk no longer meets underwriting guidelines"
- "Policy subject to cancellation based on underwriting findings"
- "Property does not meet [carrier] eligibility requirements"
- "Underwriting decline" or "risk declined"

### Inspection Requirements
- "Inspection required for policy [number]"
- "Property inspection scheduled for [date]"
- "Loss control inspection" or "risk improvement survey"
- "We have scheduled an inspection of the insured property"
- "Inspection report indicates [finding]"

### Conditional Binders
- "Conditional binder issued pending [requirement]"
- "Policy bound subject to [condition]"
- "Binder expires if [requirement] not met by [date]"
- "Temporary binder — underwriting requirements due by [date]"

Do NOT use for:
- Endorsement processing (address change, vehicle change, etc.) → `email-policy-transaction`
- New quote requests → `email-quoting-request`
- Cancellation/nonrenewal notices → `email-policy-transaction`
- Claims notifications → claims skill
- Dec page requests → `email-declarations-page`
- Closing-related EOI/binder requests → `email-closing-support`

## Classification

| Email Type | Key Signals | Priority | Typical Action |
|---|---|---|---|
| **Info request** | "additional information required", "underwriting review" | HIGH — respond within 48 hours | Gather requested info, submit to carrier |
| **Rate revision** | "revised premium", "rate change" | MEDIUM — review and communicate | Compare old vs new premium, notify client |
| **Eligibility change** | "no longer meets guidelines", "declined" | HIGH — may lose the policy | Evaluate alternatives, contact client |
| **Inspection required** | "inspection scheduled", "loss control" | MEDIUM — coordinate access | Confirm with client, ensure access |
| **Conditional binder** | "bound subject to", "requirements due by" | HIGH — deadlines matter | Fulfill conditions before deadline |
| **Premium audit** | "premium audit", "audit worksheet" | MEDIUM — financial accuracy | Provide payroll/revenue data, review results |
| **Loss control / risk improvement** | "recommendations", "risk improvement" | LOW-MEDIUM — may affect eligibility | Communicate to client, track compliance |

## Email Sources

| Inbox | Address | Access | Notes |
|-------|---------|--------|-------|
| Service | service@libertasinsurance.com | Gmail API (GMAIL_SERVICE_REFRESH_TOKEN in ~/.config/libertas/gmail-service.env) | Main inbox for underwriting emails |
| Kyle direct | Kyle@libertasinsurance.com | Not API-accessible | Fwd'd underwriting emails, often with instructions |

For Gmail API access patterns, see the `agency-email` skill.

## Processing Workflow

### Step 1: Parse and Classify

1. **Read the email body, subject, and sender** carefully — underwriting emails contain critical details
2. **Identify the type** from the classification table above
3. **Extract key data**:
   - Policy number or quote/submission number
   - Client name
   - Carrier name and underwriter contact (name, email, phone)
   - Deadline for response (if specified)
   - Specific information or action requested
   - New premium or rate (if rate revision)
   - Conditions to fulfill (if conditional binder)
   - Inspection date and time (if inspection scheduled)

### Step 2: Look Up Policy in CRM

```python
import psycopg2
conn = psycopg2.connect(env['SUPABASE_DB_URL'])  # from ~/.config/libertas/credentials.env
cur = conn.cursor()

# Search by policy number
cur.execute("""
    SELECT p.id, p.policy_number, p.status, p.premium_annual,
           p.effective_date, p.expiration_date, p.carrier_id,
           c.name as carrier_name, h.id as household_id,
           ct.first_name, ct.last_name, ct.email, ct.phone
    FROM policies p
    LEFT JOIN carriers c ON p.carrier_id = c.id
    LEFT JOIN households h ON p.household_id = h.id
    LEFT JOIN contacts ct ON p.primary_contact_id = ct.id
    WHERE p.policy_number ILIKE %s
""", (f'%{policy_number}%',))
```

If the email references a quote/submission number (not yet a bound policy), search by client name and recent quote activity.

### Step 3: Handle by Type

#### Underwriting Information Request

1. **Identify what's needed** — common requests:
   - Photos of the property (exterior, roof, etc.)
   - Prior carrier dec page or loss history
   - Proof of prior insurance (continuous coverage discount)
   - Inspection report or appraisal
   - Driver's license or MVR
   - Financial documentation (for commercial)
   - Property details clarification (roof age, construction type, etc.)
2. **Check if we already have the information**:
   - CRM may have photos, prior dec pages, or inspection reports on file
   - EZLynx submission data may contain prior carrier info
   - Check prior email threads for the same client
3. **If we have it** — submit to the carrier underwriter via email reply
4. **If we need it from the client** — contact the client promptly:
   - Email the client with a clear list of what's needed
   - Include the deadline (or set a deadline 48 hours before the carrier's deadline)
   - Explain WHY it's needed ("your carrier requires X to confirm your coverage")
   - Attach a template or instructions if the client needs to take action (e.g., schedule inspection access)

**Client email template for info request:**
```
Subject: Action Needed: Information Request from [Carrier Name]

Hi [Client Name],

[Carrier Name] is reviewing your [LOB] policy ([policy_number]) and has requested the following information to complete their underwriting review:

[Specific items requested, bulleted]

Please provide this information by [deadline date] so we can ensure your coverage remains in force.

If you have any questions or need help gathering this information, please let me know — I'm happy to assist.

Best regards,
Libertas Insurance
```

#### Rate Revision

1. **Compare old vs new premium**:
   - Pull the current premium from CRM
   - Calculate the dollar and percentage change
2. **Determine the reason** — the carrier email usually states why (claim surcharge, territory change, coverage form change, rate filing change, etc.)
3. **Assess the impact**:
   - < 10% increase: informational, update CRM and notify client
   - 10-20% increase: shop for alternatives before notifying client
   - > 20% increase: HIGH — escalate to Kyle for re-shopping decision
4. **Notify the client** with the revised premium and options:
   - If increase is small: "Your premium has been adjusted to $X. This is effective [date]."
   - If increase is significant: "Your premium has changed to $X (a Y% increase). I'm checking alternatives — would you like me to shop for better rates?"

**Client email template for rate revision:**
```
Subject: Premium Update: [Carrier Name] Policy [policy_number]

Hi [Client Name],

[Carrier Name] has revised the premium on your [LOB] policy ([policy_number]).

Previous premium: $[old]
New premium: $[new] ([+%/-X%])

Reason: [carrier-provided reason, e.g., "rate filing adjustment", "territory re-evaluation"]

Effective date: [date]

[If significant increase:] I'd be happy to shop for alternative options if you'd like to compare rates.

Best regards,
Libertas Insurance
```

5. **Update CRM** with the new premium (once confirmed/bound at the revised rate):
```python
cur.execute("""
    UPDATE policies
    SET premium_annual = %s,
        notes = COALESCE(notes, '') || %s,
        updated_at = NOW()
    WHERE id = %s
""", (new_premium, f"\n[{date}] Rate revision: ${old} → ${new} ({carrier}). Reason: {reason}.", policy_id))
conn.commit()
```

#### Eligibility Change / Decline

1. **Determine the severity** — "no longer meets guidelines" is more urgent than "eligibility question"
2. **If the policy may be cancelled or non-renewed**:
   - IMMEDIATELY check if there are replacement options
   - The carrier usually provides a grace period (30-60 days) to find alternative coverage
3. **Shop for alternatives** using the quoting workflow (see `email-quoting-request`)
4. **Notify the client** with urgency and next steps:
   - Explain the situation clearly without causing panic
   - Provide a timeline
   - Offer to find replacement coverage
5. **Update CRM policy status** appropriately

**Client email template for eligibility issue:**
```
Subject: Important: Coverage Update on [Carrier Name] Policy [policy_number]

Hi [Client Name],

I'm reaching out because [Carrier Name] has indicated that your property at [address] no longer meets their underwriting guidelines for [LOB] coverage. [Details of the specific issue].

[If policy will be non-renewed:] Your current coverage will remain in force until [expiration date]. I'm actively working on finding replacement coverage and will have options for you before then.

[If policy may be cancelled:] I need to discuss this with you as soon as possible — please call me at [phone] so we can address this promptly.

Best regards,
Libertas Insurance
```

#### Inspection Required

1. **Note the inspection details** — date, time, inspector contact, type (exterior, interior, roof, etc.)
2. **Contact the client** to confirm access and preparation:
   - Exterior inspections usually don't require the client to be home
   - Interior inspections require the client to schedule and be present
   - Provide the inspector's contact info so the client can reschedule if needed
3. **If the client objects to the inspection** — explain it's a carrier requirement, not optional
4. **After inspection** — if the carrier sends findings/recommendations, process them:
   - Minor recommendations (trim tree, fix handrail): communicate to client, set follow-up
   - Major findings (roof replacement needed, wiring upgrade required): HIGH — may affect eligibility, escalate to Kyle

#### Conditional Binder

1. **Identify ALL conditions** that must be met and their deadlines
2. **Track each condition** — these are hard deadlines; missing one can void the binder
3. **Work through conditions systematically**:
   - Conditions we can fulfill (provide info, submit forms): do immediately
   - Conditions the client must fulfill (sign app, pay deposit, provide photos): contact client with deadline
   - Conditions requiring third-party action (inspection, appraisal): coordinate promptly
4. **Confirm completion** — once all conditions are met, confirm with the carrier
5. **Set reminders** for each condition deadline (at least 48 hours before)

### Step 4: Update CRM

For ALL underwriting emails, update the policy record:

```python
cur.execute("""
    UPDATE policies
    SET notes = COALESCE(notes, '') || %s,
        updated_at = NOW()
    WHERE id = %s
""", (f"\n[{date}] Underwriting: {email_type}. {summary}. Carrier: {carrier}. UW contact: {uw_email}.", policy_id))
conn.commit()
```

### Step 5: Set Follow-Up

- **Info request**: Follow up with client in 3 business days if info not yet provided
- **Rate revision**: Follow up with client in 5 business days if no response
- **Eligibility change**: Follow up with client in 2 business days — more urgent
- **Conditional binder**: Follow up daily on outstanding conditions approaching deadline
- **Inspection**: Follow up 1 business day before scheduled inspection to confirm access

## Escalation Rules

### Always Escalate to Kyle When:
1. **Eligibility decline** — carrier is cancelling or non-renewing due to underwriting; Kyle needs to decide on replacement strategy
2. **Rate increase > 20%** — re-shopping decision and client communication strategy
3. **Conditional binder deadline < 5 business days** with outstanding conditions — risk of binder voiding
4. **Underwriting request we cannot fulfill** — e.g., carrier requests documentation we don't have and client is unresponsive
5. **Carrier requests policy rewrite** instead of endorsement — structural change that affects coverage
6. **Premium audit results in additional premium > $1,000** — client may dispute; Kyle reviews
7. **Inspection finds major issues** (roof, foundation, wiring, etc.) that may make the property uninsurable
8. **Carrier underwriter is unresponsive** after 2 follow-up attempts
9. **Multiple underwriting issues on same policy** — compounding risks need strategic handling
10. **Client disputes the underwriting finding** — requires professional judgment and negotiation

### Auto-Handle (No Escalation Needed):
- Simple info requests where we already have the data
- Rate revisions < 10% with clear explanation from carrier
- Routine inspection scheduling (exterior only)
- Minor loss control recommendations (send to client, log in CRM)

### Escalation format:
```
UNDERWRITING — [Priority Level]
Policy: {policy_number} | Client: {client_name} | Carrier: {carrier}
Type: {info-request / rate-revision / eligibility / inspection / conditional-binder}
Details: {summary of the underwriting issue}
Deadline: {carrier-stated deadline, if any}
Impact: {what happens if not addressed}
Action Needed: {specific action request}
UW Contact: {underwriter_name} at {underwriter_email}
Email ID: {gmail_message_id}
```

## Common Pitfalls

1. **Missing the response deadline** — underwriting emails often have hard deadlines (10-30 days). Missing them can result in cancellation or rate lock loss. Always note the deadline and set a reminder.

2. **Not contacting the client quickly enough** — the carrier gave US a deadline, but the client needs time to provide info. Contact the client immediately, not when it's already urgent.

3. **Confusing rate revision with endorsement premium change** — a rate revision is a carrier-level change (affects all policies in that class/territory). An endorsement premium change is specific to one policy's coverage modification. They're processed differently.

4. **Not documenting underwriting communications in CRM** — underwriting decisions affect coverage validity. If a claim is later denied for an underwriting issue, the CRM log is the audit trail that shows the agency acted diligently.

5. **Conditional binder conditions falling through the cracks** — a binder with 3 conditions (signed app, down payment, photos) is easy to lose track of. Track each condition individually with its own deadline and follow-up.

6. **Inspection happens without client knowledge** — exterior inspections may not require client presence, but the client should still be informed that an inspector will visit. Unannounced visitors cause complaints.

7. **Premium audit surprises** — commercial policies are audited at term end. The audit premium can be significantly higher if payroll/revenue was underestimated. Communicate this possibility at bind time, and review audit results carefully when received.

8. **REST API RLS blocks** — the anon key gets `permission denied` for policy writes. Use direct DB connection (psycopg2 with `SUPABASE_DB_URL` from `~/.config/libertas/credentials.env`) for all CRM writes.

9. **Underwriting decline on a new-business application** — if the carrier declines during the underwriting review (after quote but before bind), the client has NO coverage. Immediately check if the quote was bound (binder issued) or just quoted. If not bound, the client may be uninsured.

10. **Auto-reply to NO_REPLY senders** — some underwriting notices come from NO_REPLY addresses. Find the underwriter's direct contact from the email body or carrier portal.

11. **Not checking for alternative carriers** — when one carrier declines or raises rates significantly, always check if other appointed carriers would accept the risk. The comparative raters (ITC, TurboRater) can provide quick alternatives.

## Verification Checklist

- [ ] Underwriting email type classified correctly
- [ ] Policy identified and matched in CRM
- [ ] Response deadline noted and follow-up set
- [ ] Requested information gathered (from CRM, client, or third party)
- [ ] Information submitted to carrier underwriter (with confirmation)
- [ ] Client notified if action needed on their part
- [ ] CRM policy notes updated with underwriting interaction
- [ ] Rate revision: old vs new premium compared, client notified
- [ ] Eligibility issue: replacement options evaluated
- [ ] Conditional binder: all conditions tracked with deadlines
- [ ] Escalation sent if any HIGH-priority condition met
- [ ] Follow-up reminder set for outstanding items
