---
name: email-quoting-request
version: 1.0
description: Handle inbound quote request emails for Libertas Insurance — client requests for HO/auto/flood/commercial quotes, website form submissions, follow-ups on quotes sent, and quote please emails. Covers trigger patterns, required actions, quoting workflow per LOB, rater selection, pitfalls, and escalation rules.
category: agency-ops
triggers:
  - email requesting a quote for any line of business
  - inbound form from quote.libertasinsurance.com
  - quote please or similar phrasing in email
  - follow-up on a previously sent quote
  - client asking for coverage comparison or competitive rate
tags: [email, quoting, turboRater, ITC, logic, foremost, homeowners, auto, flood, commercial, browserbase, stagehand, agency-ops]
---

# Email Quoting Request Handler

Skill for processing the #2 email type in the Libertas inbox at 14.0% of volume (2,224 emails). These emails come from clients requesting new quotes, website form submissions, follow-ups on previously-sent quotes, and informal "quote please" requests.

## Trigger Patterns

An email should be classified as a quoting request if it matches ANY of these patterns:

### Direct Quote Requests
- "I'd like a quote" / "can I get a quote" / "quote please" / "need insurance"
- "looking for home/auto/flood/commercial insurance"
- "how much would it cost to insure my..."
- "shopping around for better rates"
- "current policy is renewing / expiring soon, want to compare"

### Website Form Submissions
- Sender domain or headers indicate origin from `quote.libertasinsurance.com`
- Structured form data in email body (name, address, DOB, coverage type, etc.)
- Subject lines like "New Quote Request from Website" or "Online Quote Form Submission"

### Follow-Ups on Previously Sent Quotes
- "did you get a chance to run that quote?"
- "following up on the quote you were working on"
- "any updates on my quote?"
- "still interested in that rate you mentioned"
- Reply chain referencing a prior quote email

### Cross-Sell / Add-On Requests
- "I also need flood insurance" (from existing HO client)
- "can you add my new car" (from existing auto client)
- "what about umbrella coverage?"

## Classification Decision Tree

```
Is the email asking for a NEW insurance quote?
├── YES → quoting-request (this skill)
│   ├── Is it a website form? → parse structured data, proceed to workflow
│   ├── Is it a follow-up? → check prior quote status, update client
│   └── Is it a new request? → gather missing info, proceed to workflow
├── NO → re-classify
│   ├── Existing policy service (endorsement, billing, claim) → service skill
│   ├── Cancellation request → cancellation skill
│   └── General inquiry → info skill
```

## Required Information Checklist

Before running any quote, these fields must be collected (either from the email or via follow-up). Not all are required for every LOB — see per-LOB sections below.

### Always Required (All LOBs)
- [ ] Full name of insured
- [ ] Date of birth (DOB)
- [ ] Property / vehicle address (at minimum, zip code for rating territory)
- [ ] Contact method (email or phone)
- [ ] Desired effective date
- [ ] Line of business (HO, auto, flood, commercial)

### Homeowners (HO) Additional
- [ ] Year built
- [ ] Square footage
- [ ] Construction type (frame, brick, brick veneer, etc.)
- [ ] Roof type and year
- [ ] Number of stories
- [ ] Garage type and size
- [ ] Current carrier and premium (if shopping)
- [ ] Prior coverage date (required by some carriers)
- [ ] Mortgagee info (if applicable)
- [ ] Protection class / fire district
- [ ] Construction quality class (for Logic HO-B)

### Auto Additional
- [ ] Vehicle year, make, model, VIN
- [ ] Driver(s) name, DOB, license state, DL#
- [ ] Current carrier and premium (if shopping)
- [ ] Desired coverages (liability limits, comp/coll deductibles)
- [ ] Prior insurance (carrier, policy#, expiration)
- [ ] Accident/violation history (last 5 years)
- [ ] Vehicle use (pleasure, commute, business)

### Flood Additional
- [ ] Property address (must be precise for FEMA flood zone determination)
- [ ] Building type (primary residence, secondary, non-residential)
- [ ] Number of floors / units
- [ ] Basement / enclosure details
- [ ] Current flood zone (if known)
- [ ] Prior flood losses
- [ ] Elevation certificate (if available — significantly reduces premium)
- [ ] Contents coverage desired

### Commercial Additional
- [ ] Business type / industry code (NAICS or SIC)
- [ ] Business name and DBA
- [ ] Annual revenue / payroll
- [ ] Number of employees
- [ ] Building details (if commercial property needed)
- [ ] Liability limits desired
- [ ] Workers comp needs (if applicable)
- [ ] Current carrier and premium (if shopping)
- [ ] Loss history (last 5 years)

## Quoting Workflow

### Step 1: Parse and Classify the Email

1. Read the email body, subject, and sender
2. Identify the LOB(s) being requested
3. If it's a website form submission (`quote.libertasinsurance.com`), parse the structured fields directly
4. If it's a follow-up, search CRM for prior quote activity on this contact
5. Classify the request urgency:
   - **URGENT**: Client's policy expires within 7 days, or client explicitly says "need coverage by [date soon]"
   - **NORMAL**: Standard shopping timeline
   - **LOW**: Tire-kicker, no timeline pressure

### Step 2: Check for Existing Client Record

1. Search CRM by name, email, phone, address
2. If client exists:
   - Pull current policy details, coverage limits, premium
   - Note the current carrier — do NOT re-quote the same carrier unless client requests
   - Check for prior quote attempts in the last 90 days (avoid duplicate work)
3. If new client:
   - Create a new contact record in CRM
   - Associate with a new or existing household

### Step 3: Identify Missing Information

1. Compare the email contents against the Required Information Checklist above
2. If critical fields are missing, draft a follow-up email requesting them
3. **Do NOT run a quote with placeholder/invented data** — bad quotes waste everyone's time and erode trust
4. Exceptions where partial quoting is acceptable:
   - Auto: can run with just name, DOB, zip, and vehicle info (coverages default to state minimums)
   - HO: can run a ballpark with name, DOB, address, year built, sqft, and construction type
   - Flood: must have precise address; elevation certificate can come later

### Step 4: Select the Rater by LOB

| LOB | Primary Rater | When to Use | Access Method |
|-----|--------------|-------------|---------------|
| **Auto** | TurboRater | All auto quotes — fastest, multi-carrier comparative | EZLynx TurboRater (web UI via Playwright-over-CDP) |
| **Homeowners** | ITC (Insurance Technologies Corp) | All HO quotes — comparative rater for standard carriers | ITC web portal (via Playwright or Browserbase+Stagehand) |
| **Logic / Standard Casualty (HO-A/HO-B)** | Logic EZ*Insure portal | When client needs Logic specifically, or ITC returns non-competitive rates for TX dwelling risks | Browserbase+Stagehand or Playwright-over-CDP (see `logic-quoting` skill) |
| **Foremost** | Foremost STAR portal | When client needs Foremost (manufactured homes, dwelling fire, flood) | Browserbase+Stagehand |
| **Flood** | ITC (for NFIP WYO carriers) + Foremost (private flood) | ITC for standard NFIP; Foremost for private flood alternatives | ITC web portal + Browserbase+Stagehand |
| **Commercial** | Manual / carrier portal | No single comparative rater — quote per carrier | Carrier portal access (varies) |

**Key rater selection rules:**
- Always run the comparative rater FIRST (TurboRater for auto, ITC for HO) — this returns multiple carrier options in one pass
- Only go to carrier-specific portals (Logic, Foremost) when: (a) the comparative rater didn't return that carrier, (b) the client specifically requested it, or (c) the risk profile fits a specialty carrier not in the comparative rater
- Logic is especially relevant for TX dwelling risks where standard carriers are non-competitive — Kyle often sends Logic quotes alongside ITC results
- Foremost is the go-to for manufactured homes and non-standard dwellings

### Step 5: Run the Quote

#### TurboRater (Auto)
1. Log into EZLynx → navigate to TurboRater
2. Enter driver details, vehicle info, coverages
3. Run comparative quote across all appointed auto carriers
4. Capture results: top 3-5 options with carrier name, premium, and coverage highlights
5. **Pitfall**: TurboRater uses approximated rates — actual carrier bind may differ by 5-15%

#### ITC (Homeowners)
1. Log into ITC portal
2. Enter property details, coverages, prior insurance info
3. Run comparative quote across appointed HO carriers
4. Capture results: top 3-5 options
5. **Pitfall**: ITC may not include all carriers — check Logic and Foremost for gaps

#### Logic EZ*Insure (HO-A / HO-B)
1. See `logic-quoting` skill for full Playwright-over-CDP automation
2. Login: `https://logicunderwriters.com/beyontecsuite/eicm/pages/common/amlogin.jsp?fromId=A`
3. Agent ID 2527, password from master login sheet
4. Navigate: Quotes → New Quote HO-A or HO-B
5. Fill Customer Details → Confirm/Next → Fill Quote Details → Save → Get Premium
6. **Critical pitfalls** (see `logic-quoting` skill for full list):
   - Login "button" is NOT a `<button>` — use `document.forms[0].submit()`
   - "New Quote" opens a NEW browser tab — must switch page reference
   - Save before Calc (`fQDBSave()` then `fullQuoteCalc()`)
   - Must clear `isChangedPSave` and `isChanged` flags after save
   - City/County require Space-press + DIV click validation
   - Coverage A is disabled — set via Replacement Value field
   - Coverage A must be within carrier's valid range (enforced by popup)
   - Effective date MUST be today or future — no backdating
   - Carrier validates phone numbers live — must be real connected numbers

#### Browserbase+Stagehand (Foremost and other carriers)
1. Use Browserbase cloud browser + Stagehand AI agent for portal navigation
2. Template: Foremost STAR portal (established pattern)
3. Login credentials from master login sheet
4. Stagehand handles form-filling and page navigation via AI prompts
5. **Pitfall**: Browserbase sessions timeout — complete the quote in one session

### Step 6: Compile and Send Quote Results

1. Format results clearly — top 3 options minimum, with:
   - Carrier name and financial rating (AM Best)
   - Annual premium and monthly payment option
   - Coverage highlights (limits, deductibles)
   - Key differences between options
2. Always include the **current carrier comparison** (if client has existing coverage) — show savings or coverage differences
3. Recommend the best option with a brief rationale
4. Include next steps: "to bind, we'll need [X, Y, Z]"
5. Set a follow-up reminder for 3 business days if no response
6. Save the quote results to the CRM contact record

### Step 7: Follow-Up

1. If no response in 3 business days, send a follow-up email
2. If no response after 2 follow-ups (7+ days), mark as "quoted — no response" in CRM
3. If client responds with questions, answer and adjust quote if needed
4. If client wants to bind, hand off to the service team / start the binding workflow

## Website Form Submissions (quote.libertasinsurance.com)

These arrive as structured emails with pre-filled form data. Handling:

1. **Parse the form data** — fields typically include: name, email, phone, address, LOB, current carrier, current premium, desired effective date
2. **Create/update CRM contact** — if new, create; if existing, update
3. **Identify the LOB** — the form usually specifies (HO, auto, flood, commercial)
4. **Check for missing fields** — website forms are typically incomplete; draft follow-up email for anything missing from the Required Information Checklist
5. **Auto-respond** — send a brief acknowledgment: "Thank you for your quote request. We're working on it and will have results within [timeframe]."
6. **Proceed to quoting workflow** — Step 4 onward

**Typical website form gaps** (almost always missing):
- DOB (required for all quotes)
- Vehicle details (year/make/model/VIN for auto)
- Year built / sqft / construction type (for HO)
- Prior insurance details
- Desired coverage limits

## Follow-Up on Previously Sent Quotes

1. **Search CRM** for the contact's quote history
2. **Check quote status** — was it sent? Which carriers? What premiums?
3. **Determine the follow-up action**:
   - If quote was never completed: apologize for the delay, complete it now
   - If quote was sent but no response: resend with a fresh offer (rates may have changed)
   - If quote was sent and carrier rates changed: re-run the quote with updated rates
   - If client says "went with another carrier": ask which one and why — record in CRM for retention intelligence
4. **Never re-run the same quote unnecessarily** — check the prior results first

## Escalation Rules

### ALWAYS Escalate to Kyle (or assigned producer)
- **Commercial quotes** — no automated rater available; requires manual carrier-by-carrier work
- **High-value homes** (replacement cost > $750K or Coverage A > $500K) — may need specialty carriers not in comparative rater
- **Non-standard risks** — prior cancellations, multiple claims, non-standard construction, vacant properties, etc.
- **Client is a current E&O claim or complaint risk** — handle with extra care
- **Flood with elevation certificate** — EC interpretation affects pricing significantly
- **Quote results are wildly different from current premium** (>50% variance) — may indicate data error or a major coverage gap
- **Client explicitly requests a specific producer** — route to that person
- **Multiple LOBs in one request** — needs coordination across raters and possibly producers

### Auto-Handle (No Escalation Needed)
- Standard auto quotes with complete information
- Standard HO quotes with complete information for carriers in the comparative rater
- Simple follow-ups on quotes you previously sent
- Website form acknowledgments and initial data-gathering emails

### Escalate After Initial Attempt
- Quote returns zero competitive options (all declined or non-competitive)
- Client has a risk profile that doesn't fit standard markets (e.g., 5+ claims, prior cancellation)
- Client requests coverage you're not appointed for
- Technical issues with rater (login failures, portal errors, timeout)

## Pitfalls and Common Mistakes

### Data Accuracy
- **NEVER fabricate data to complete a quote** — if DOB is missing, ask; don't guess. Wrong DOB = wrong rate = E&O exposure
- **NEVER assume current coverages match requested coverages** — always confirm what the client wants, not just what they have
- **Verify the property address** — wrong address = wrong territory = wrong rate. Especially critical for flood zone determination
- **Current premium from client is often inaccurate** — they may quote monthly instead of annual, or include fees, or reference an old renewal. Get the dec page if possible

### Rater-Specific
- **TurboRater rates are approximated** — they're close but not binding. Tell clients "final premium may vary slightly at bind"
- **ITC may not include all appointed carriers** — cross-reference with the carrier appointment list in CRM
- **Logic portal has aggressive session timeouts** — complete the quote in one session or you'll need to re-login and re-enter data
- **Logic City/County fields require Space-press validation** — auto-filled values alone are NOT sufficient (see `logic-quoting` skill)
- **Logic Coverage A is DISABLED** — set via Replacement Value field, and it must be within the carrier's valid range
- **Logic "Warning! Locality Change" is NOT blocking** — ignore it and proceed
- **Foremost STAR via Browserbase** — sessions timeout; don't leave the session idle

### Process
- **Don't re-quote the client's current carrier** (unless requested) — they know that rate. Quote alternatives.
- **Don't run just one carrier** — comparative quotes are the value proposition. Minimum 3 options.
- **Don't forget to check for bundling** — if client has HO with us and wants auto, or vice versa, the multi-policy discount can be significant
- **Don't assume the cheapest option is the best recommendation** — consider carrier financial strength, claims service, coverage differences
- **Don't send a quote without comparing it to the client's current coverage** — a lower premium might mean less coverage
- **Don't quote without checking the effective date** — if it's past, the quote is invalid. Always confirm or default to a future date.
- **Watch for duplicate requests** — the same client may email multiple times or submit a website form AND email. Check CRM for recent activity before starting work.

### Communication
- **Set realistic expectations on timeline** — standard quotes take 1-2 business days; Logic/Foremost manual quotes may take 2-3; commercial can take a week
- **Always include a call to action** — "Let me know which option works best and we can get it bound"
- **Always mention what's needed to bind** — signed app, down payment, current dec page, etc.
- **Never promise a specific rate** — rates change until bound. Use "based on current rates" or "subject to final underwriting review"

## CRM Integration

- **Search contacts** by name, email, phone, address before creating new records
- **Log all quote activity** on the contact record: date requested, LOB, rater used, carriers quoted, premiums, outcome
- **Set follow-up tasks** with due dates (3 business days after quote sent)
- **Update status**: "Quote Requested" → "Quote in Progress" → "Quote Sent" → "Bound" or "Lost" or "No Response"
- **Record lost quote reasons** — "went with State Farm for $200 less" is valuable retention intelligence

## Related Skills

- **`logic-quoting`** — Full Logic EZ*Insure HO-A/HO-B automation with Playwright-over-CDP, field maps, iframe navigation, and pitfalls
- **`ezlynx-operations`** — EZLynx platform operations, TurboRater access, browser automation patterns
- **`libertas-agency-ops`** — Carrier portal research, master login sheet access, CRM data pipeline
- **`libertas-daily-sync`** — Daily CRM sync pipeline (for checking current policy data)
- **`libertas-crm-reference`** — CRM schema, tables, and data paths
