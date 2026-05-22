# Logic EZ*Insure HO-A Quote Form — Complete Field Map

## Portal Info
- URL: https://logicunderwriters.com/beyontecsuite/
- Login: Agent mode, ID 2527
- Product: Home Owners A (HOA)

## Navigation Flow
1. Login → Portal Home
2. Click "Quotes" → "New Quote HO-A"
3. Customer Details tab → fill name, DOB, address, phone, email → Save
4. Confirm/Next → Risk Info screen (risk type HOA, dates) → Confirm/Next
5. Quote Details tab loads → sub-tabs: R_EDIT (property details), NOTE, CONDITIONS, QUESTIONS
6. R_EDIT sub-tab → the HO-A underwriting form (uwp2hoa_LUW.do) — 112 fields

## Frame Structure
- Parent: fullquotelist.do (outer layout, Save/Next buttons, tab nav)
  - Child 1: fullquoterisk.do (risk info intermediate screen)
  - Child 2: uwp2hoa_LUW.do (THE QUOTE FORM — nested inside fullquoterisk frame)
    - This is a deeply nested iframe: parent → fullquoterisk → uwp2hoa_LUW

## Tab Navigation
- Customer Details: fQPageNavigate('UTDS_LEVEL_M_ID')
- Quote Details: fQPageNavigate('UTDS_LEVEL_R_ID')
- Business Rule: fQPageNavigate('TDS_LEVEL_BR_DTLS_ID')
- Sub-tab R_EDIT: menuSelection('UTDS_LEVEL_R_EDIT')
- Sub-tab NOTE: menuSelection('NOTE')
- Sub-tab CONDITIONS: menuSelection('CONDITIONS')
- Sub-tab QUESTIONS: menuSelection('QUESTIONS')

## Action Buttons (in parent frame)
- Save: fQDBSave() or click #spansaveAction
- Calculate/Rate: fullQuoteCalc() or click #spancalcAction
- Freeze: fullQuoteApprove()
- Reset: resetQuickQuote()
- Iteration: quickQuoteIteration()

## Customer Details Fields (Frame: quickquotecustomer.do)
| Field | ID | Type | Notes |
|-------|-----|------|-------|
| Individual/Entity | custIndividualId / custCorporateId | radio | I=Individual, C=Entity |
| First Name | customerFirstNameId | text | |
| Middle Initial | txt_customerMiddleInitial | text | |
| Last Name | txt_customerLastName | text | |
| Entity Type | cmb_EntityType | select | |
| DOB | customerDateOfBirthId | text | MM/DD/YYYY |
| ID Type | idTypeId | select | |
| ID Number | idNumberId | text | |
| Currently Insured | currentlyInsuredId | checkbox | |
| Insured Name | currentlyInsuredName | text | |
| Address Type | opt_AddressType | select | W=Work, H=Home |
| Zip Code | txt_ZipCode | text | Triggers city/state/county lookup |
| Address Line 1 | txt_Address1 | text | |
| Address Line 2 | txt_Address2 | text | |
| County | txt_County | text | Auto-filled from zip |
| City | txt_City | text | Auto-filled from zip |
| State | txt_State | text | Auto-filled from zip |
| Country | txt_Country | text | Auto-filled (US) |
| Phone # | txt_SPQQ_PhoneNo | text | Must be valid/connected |
| E-Delivery | chk_ulm_edel_qq_yn | checkbox | |
| Work Phone | txt_SPQQ_WorkPhoneNo | text | |
| E-Delivery Mode | opt_edel_qq_mode | select | E=Email |
| Mobile | txt_SPQQ_CellNo | text | |
| Fax | txt_SPQQ_FaxNo | text | |
| Email | txt_SPQQ_EmailId | text | Required |
| Req Eff Date | fullQuoteEffDateId | text | MM-DD-YYYY |
| Term | FQ_CD_term_Id | select | 01|D = 12 months |
| Expiration Date | fullQuoteExpDateId | text | |
| Agent # | txt_ULM_AGENT_ID | text | Auto-filled (2527) |

## HO-A Property Details Fields (Frame: uwp2hoa_LUW.do) — THE KEY FORM

### Location/Address
| Field | ID | Type | Options/Notes |
|-------|-----|------|------|
| Same as Customer | chk_DEFAULT_CUSTOMER | checkbox | |
| Zip Code | txt_PIN_CODE_1 | text | |
| Address Type | opt_Other_RiskTyp_Address | select | |
| Address 1 | txt_ADDR1_1 | text | |
| Address 2 | txt_ADDR2_1 | text | |
| County | txt_ADDR4_1 | text | |
| City | txt_CITY_1 | text | |
| State | txt_STATE_1 | text | |
| Country | txt_COUNTRY_1 | text | |
| Address Question | cmb_Ulrp_Addr_Qn_1 | select | ---Select---, Yes, No |

### Dwelling/Property Info
| Field | ID | Type | Options/Notes |
|-------|-----|------|------|
| Occupancy Type | cmb_ULRP_OCCUPANCY_TYP | select | Owner, Secondary, Vacant, Tenant, Seasonal/Vacation |
| Building Type | cmb_ULRP_BUILD_TYP | select | Dwelling, Townhome, Condo, Log Home, Historical Home, Other, Manufactured/Modular Homes |
| Fire Hydrant <=1000ft | cmb_ULRP_DIST_FIRE_HYDR | select | Yes, No |
| Fire Dept <=5 miles | cmb_ULRP_DIST_FIRE_STN | select | Yes, No |
| Fire District | txt_ULRP_FIRE_DISTRICT | text | |
| Protection Class | txt_ULRP_PROTECT_CLS | select | |
| Territory | txt_ULR_TERRITORY_ID | text | Auto |
| Zip Tier | txt_ULRP_ZIP_TIER_ID | text | Auto |
| Year Built | txt_ULRP_YEAR_BUILT | text | |
| Square Feet | txt_ULRP_SQ_FEET | text | |
| Construction Type | cmb_ULRP_CONST_TYP | select | Asbestos, Brick, Brick Veneer, Frame, Hardi/Concrete Board, Metal, Other |
| # of Stories | txt_ULRP_NO_OF_FLOORS | select | 1, 1.5, 2, 2.5, 3 |
| Roof Cover Year | txt_ULRP_ROOF_CR_YEAR | text | |
| Roof Construction Type | txt_ULRP_ROOF_CONS_TYP | select | Asphalt, Composition, Concrete/Slate, Metal, Other, Tile, Wood |
| # of Families | txt_ULRP_NO_OF_RES_HH | select | 1, 2 |
| Roof Impact Class | cmb_ULRP_ROOF_CR_CLASS | select | Class I, II, III, IV, None |
| Burglar Alarm Type | cmb_ULRP_BURG_ALM_TYP | select | None, Fire, Burglary, Burglary & Fire |
| Loan Year | txt_ULRP_LOAN_YR | text | |
| Hip Roof | cmb_ULRP_ROOF_TYP | select | Yes, No |
| Fire Protection | cmb_ULRP_FIRE_PROTECT_TYP | select | None, Fire Extinguisher, Smoke Alarm, In-door Sprinkler System, Fire Ext & Smoke Alarm |
| Misrepresentation | opt_Intenal_Misreption | select | Yes, No |
| Solar Panels | opt_solar_panels | select | Yes, No |
| Remove Roof Exclusion | opt_remove_roofExclson | select | No, Yes |
| Coverage Desired | opt_coverage_desired | select | Yes, No |
| # of Solar Panels | txt_no_of_panels | text | |
| ITIN | chk_ULRP_USS_ITIN | checkbox | |
| ITIN Number | txt_ULRP_USS_ITIN_NUM | text | |
| Dump Surcharge | chk_ULRP_DUMP_SUR | checkbox | |
| Appraisal/Fair Market Value | txt_ULRP_FAIR_MKT_VAL | text | |
| Replacement Cost Description | cmb_ULRP_REP_COST | select | Contents, None, Dwelling, Both |
| Replacement Value | txt_ULRP_REPLACEMENT_VAL | text | |
| Actual Value | txt_ULRP_ACTUAL_VAL | text | |
| Dwelling Style (# corners) | cmb_ULRP_NO_OF_CORS | select | 1-4 corner, 2-6 corner, 3-8 corner, 4-10 corner |
| Special Class | cmb_ULRP_SPL_CLASS | select | Manufactured homes, Best, Best/Good, Good, Good/Avg, Average, Avg/Low |
| Garage Type | cmb_ULRP_GARAGE_TYP | select | No Garage, Attached Garage, Detached Carport, Attached Carport, Detached Garage |
| Garage Sq Ft | txt_ULRP_GAR_SQ_FEET | text | |
| Central HVAC | cmb_ULRP_CENT_HVAC_YN | select | Yes, No |
| Wood/Fireplace | cmb_ULRP_WB_GFIRE_PLACE_YN | select | Yes, No |
| Companion Policy | chk_ULRP_COMPANION_POLICY_YN | checkbox | |
| Secondary Bldg Credit | chk_ULRP_SEC_BLDG_CR_YN | checkbox | |
| Prior Coverage | cmb_ULRP_COV_CONT_YN | select | Prior Coverage, New Purchase, Refinance |
| Prior Ins Co | txt_Ulrp_Prv_Ins_Comp | text | |
| Other Ins Co | txt_Ulrp_Oth_Ins_Comp | text | |
| Prior Cov Date | txt_Ulrp_Prior_Cov_Dt | text | |
| Prior Underwriting Damage | chk_Ulrp_Prior_Ur_Dmg | checkbox | |
| # of Mortgagee | addlEntityYnId | select | 0, 1, 2 |
| # Addl Insured | txt_ULRP_NO_OF_ADDL_INSD | text | |

### Coverage Limits
| Field | ID | Type | Options/Notes |
|-------|-----|------|------|
| Coverage A - Dwelling | txt_CVRA | text | Dollar amount (KEY FIELD) |
| Coverage Other Structures | rate\|OTHSTRU | select | 10%, 15%, 20%, 25%, 30%, 35%, 40%, 45% |
| Coverage B - Personal Property | rate\|PP | select | 40%, 60% |
| Coverage B - PP Off Premises | rate\|PPOP | select | 10% |
| Coverage Loss of Use | rate\|LOU | select | 10% |
| Coverage C - Personal Liability | txt_CVRC | select | 25,000 / 50,000 / 100,000 / 300,000 |
| Coverage D - Medical Payments | txt_CVRD | select | 500 / 1,000 / 2,000 / 3,000 / 4,000 / 5,000 |
| Firearm & Animal Liability | ANILIA | checkbox | |
| HO 105 Residence Glass | HO105 | checkbox | |
| HO 110 Jewelry/Watches/Furs | txt_UNSJS | text | Dollar limit |
| HO 111 Business Personal | txt_HO111 | text | Dollar limit |
| HO 112 Money/Bank Cards | txt_HO112 | text | Dollar limit |
| HO 113 Bullion/Valuable Papers | txt_HO113 | text | Dollar limit |
| HO 120 TV/Radio Antenna | txt_HO120 | text | Dollar limit |
| HO 126 Personal Computer | txt_HO126 | select | $1,000 / $2,000 / $3,000 |
| HO 135 Constr Building Laws | rate\|HO135 | select | 10%, 15%, 25% |
| HO 160 Scheduled Personal Prop | txt_HO160 | text | Dollar limit |
| HO 225 Addl Premises Liability | txt_HO225L | text | |
| HO 225 Addl Premises Med Pay | txt_HO225MP | text | |
| HO 301 Additional Insured | HO301 | checkbox | |
| Addl Insured Perils & Ltd Water | txt_SADW | select | $5,000 / $10,000 / $15,000 / $25,000 |
| Extended Repl Cost Protection | rate\|ERCP | select | 125%, 150% |
| Ltd Loss Settlement Endorsement | SCLRCHOA01 | checkbox | |
| Loss Settlement Endorsement | SCRCHOA01 | checkbox | |
| Enhanced Partial Loss | NLH011 | checkbox | |
| Excl Cosmetic Dmg Non-Hail Roof | EXDMGNHR | checkbox | |
| Excl Cosmetic Dmg Metal Struct | EXDMGMET | checkbox | |

### Deductibles
| Field | ID | Type | Options/Notes |
|-------|-----|------|------|
| Wind/Hail/Hurricane Ded | txtXS_CLAUSE1 | select | 1%, 1.5%, 2%, 2.5%, 3%, 4%, 5% |
| All Other Perils Ded | txtXS_CLAUSE2 | select | 1%, 1.5%, 2%, 2.5%, 3%, 4%, 5% |

### Claims History
| Field | ID | Type | Options/Notes |
|-------|-----|------|------|
| Losses in last 5 years | txt_ULRP_NON_WEATHER_CLM | select | Yes, No |
| # Weather Claims | txt_ULRP_NUM_WEATHER_CLM | text | Default 0 |

## Validation Rules
- Phone number must be valid/connected (carrier validates against a DB)
- Zip code triggers city/state/county auto-lookup
- City field: must press SPACE to trigger lookup, then click the matching DIV by ID (e.g. #WACO)
- County field: same SPACE lookup pattern (e.g. #MCLENNAN)
- "Warning! Locality Change" appears when property address differs from mailing — NOT BLOCKING, informational only, can proceed past it
- Coverage A (dwelling) is DISABLED — auto-populated from Replacement Value field
- Replacement Value must be within carrier's calculated range (e.g. "Valid Range is between 186,854 and 228,377")
- County is required, Email is required
- Prior Coverage Date is required when Prior Coverage selected
- Replacement Cost Description is required
- Effective date must be today or future (no backdating)
- Expiration date auto-calculated from effective date + term

## Chrome Autofill
- Chrome "Save address" popup appears constantly on address fields
- Disable via chrome://settings/addresses — toggle off "Save and fill addresses"
- Also check chrome://settings/payments for payment-related toggles
- In automation: press Escape to dismiss if it appears

## Complete Dropdown Options (HO-A)

### Occupancy Type (cmb_ULRP_OCCUPANCY_TYP)
---Select--- | Owner(01) | Secondary(02) | Vacant(05) | Tenant(04) | Seasonal/Vacation(03)

### Building Type (cmb_ULRP_BUILD_TYP)
---Select--- | Dwelling(D) | Townhome(T) | Condo(C) | Log Home(L) | Historical Home(H) | Other(O) | Manufactured/Modular Homes(MM)

### Fire Hydrant (cmb_ULRP_DIST_FIRE_HYDR)
---Select--- | Yes(01) | No(02)

### Fire Dept <=5 miles (cmb_ULRP_DIST_FIRE_STN)
---Select--- | Yes(01) | No(02)

### Protection Class (txt_ULRP_PROTECT_CLS)
2 | 1 | 3 | 4 | 5 | 6 | 7 | 8 | 8B | 9 | 10

### Construction Type (cmb_ULRP_CONST_TYP)
---Select--- | Asbestos(07) | Brick(05) | Brick Veneer(01) | Frame(02) | Hardi/Concrete Board(03) | Metal(06) | Other(08) | Stucco(04) | Manufactured/Modular Homes(09)

### # of Stories (txt_ULRP_NO_OF_FLOORS)
---Select--- | 1 | 1.5 | 2 | 2.5 | 3

### Roof Construction Type (txt_ULRP_ROOF_CONS_TYP)
---Select--- | Asphalt(07) | Composition(06) | Concrete/Slate(03) | Metal(01) | Other(05) | Tile(02) | Wood(04)

### # of Families (txt_ULRP_NO_OF_RES_HH)
---Select--- | 1 | 2

### Roof Impact Class (cmb_ULRP_ROOF_CR_CLASS)
---Select--- | Class I(Class 1) | Class II(Class 2) | Class III(Class 3) | Class IV(Class 4) | None(N)

### Burglar Alarm Type (cmb_ULRP_BURG_ALM_TYP)
---Select--- | None(N) | Fire(F) | Burglary(BU) | Burglary & Fire(BF)

### Hip Roof (cmb_ULRP_ROOF_TYP)
---Select--- | Yes(Y) | No(N)

### Fire Protection (cmb_ULRP_FIRE_PROTECT_TYP)
---Select--- | None(N) | Fire Extinguisher(FE) | Smoke Alarm(SA) | In-door Sprinkler System(IS) | Fire Ext & Smoke Alarm(FS)

### Solar Panels (opt_solar_panels)
---Select--- | Yes(Y) | No(N)

### Replacement Cost Description (cmb_ULRP_REP_COST)
---Select--- | Contents(C) | None(N) | Dwelling(D) | Both(B)

### Dwelling Style (cmb_ULRP_NO_OF_CORS)
---Select--- | 1-4 corner(1) | 2-6 corner(2) | 3-8 corner(3) | 4-10 corner(4)

### Special Class (cmb_ULRP_SPL_CLASS)
---Select--- | Manufactured homes(MH) | Best(B) | Best/Good(BG) | Good(G) | Good/Avg(GA) | Average(A) | Avg/Low(AV) | Low(L)

### Garage Type (cmb_ULRP_GARAGE_TYP)
---Select--- | No Garage(01) | Attached Garage(02) | Detached Carport(05) | Attached Carport(04) | Detached Garage(03)

### Central HVAC (cmb_ULRP_CENT_HVAC_YN)
--Select-- | Yes(Y) | No(N)

### Wood/Fireplace (cmb_ULRP_WB_GFIRE_PLACE_YN)
--Select-- | Yes(Y) | No(N)

### Prior Coverage (cmb_ULRP_COV_CONT_YN)
---Select--- | Prior Coverage(PC) | New Purchase(NP) | Refinance(RF)

### # of Mortgagee (addlEntityYnId)
---Select--- | 0 | 1 | 2

### Coverage Other Structures (rate|OTHSTRU)
10% | 15% | 20% | 25% | 30% | 35% | 40% | 45% | 50%

### Coverage B - Personal Property (rate|PP)
40% | 60%

### Coverage B - PP Off Premises (rate|PPOP)
10%

### Coverage Loss of Use (rate|LOU)
10%

### Coverage C - Personal Liability (txt_CVRC)
25,000 | 50,000 | 100,000 | 300,000

### Coverage D - Medical Payments (txt_CVRD)
500 | 1,000 | 2,000 | 3,000 | 4,000 | 5,000

### HO 161 Mold/Fungi Coverage (rate|HO161)
---Select--- | 100% | 25% | 50%

### HO 126 Personal Computer (txt_HO126)
---Select--- | $1,000 | $2,000 | $3,000

### HO 135 Increased Costs Construction (rate|HO135)
---Select--- | 10% | 15% | 25%

### Additional Insured Perils & Ltd Water (txt_SADW)
---Select--- | $5,000 | $10,000 | $15,000 | $25,000

### Extended Replacement Cost Protection (rate|ERCP)
---Select--- | 125% | 150%

### Wind/Hail/Hurricane Deductible (txtXS_CLAUSE1)
---Select--- | 2% | 2.5% | 3% | 4% | 5%

### All Other Perils Deductible (txtXS_CLAUSE2)
---Select--- | 1% | 1.5% | 2% | 2.5% | 3% | 4% | 5%

### Losses in last 5 years (txt_ULRP_NON_WEATHER_CLM)
---Select--- | Yes(1) | No(0)

## Checkbox Endorsements (HO-A)

### Basic Coverages (checked by default)
- CVRA: Coverage A - Dwelling [CHECKED]
- OTHSTRU: Coverage Other Structures [CHECKED]
- PP: Coverage B - Personal Property [CHECKED]
- PPOP: Coverage B - Personal Property Off Premises [CHECKED]
- LOU: Coverage Loss of Use [CHECKED]
- CVRC: Coverage C - Personal Liability [CHECKED]
- CVRD: Coverage D - Medical Payments [CHECKED]
- ANILIA: Firearm and Animal Liability Limitation [CHECKED]
- CLAUSE1_*: Wind, Hail & Hurricane deductible [CHECKED]
- CLAUSE2_*: All Other Perils deductible [CHECKED]
- SCRCHOA01: Loss Settlement Endorsement [CHECKED]

### Optional Endorsements (unchecked by default)
- HO105: HO 105 Residence Glass Coverage
- UNSJS: HO 110 Increased Limit on Jewelry, Watches & Furs (text input for limit)
- HO111: HO 111 Increased Limit on Business Personal Property (text input for limit)
- HO112: HO 112 Increased Limit on Money/Bank Cards (text input for limit)
- HO161: Mold, Fungi, or Other Microbes coverage (dropdown: 25%, 50%, 100%)
- HO113: HO 113 Increased Limit on Bullion, Valuable Papers (text input for limit)
- HO120: HO 120 Television and Radio Antenna (text input for limit)
- HO126: HO 126 Personal Computer Coverage (dropdown: $1,000/$2,000/$3,000)
- HO135: HO 135 Increased Costs of Construction-Building Laws (dropdown: 10%/15%/25%)
- HO160: HO 160 Scheduled Personal Property (text input, default 0)
- HO225L: HO 225 Additional Premises Liability (text input for limit)
- HO225MP: HO 225 Additional Premises Med Pay (text input for limit)
- HO301: HO 301 Additional Insured
- SADW: Additional Insured Perils & Limited Water Damage (dropdown: $5K/$10K/$15K/$25K)
- ERCP: Extended Replacement Cost Protection (dropdown: 125%/150%)
- SCLRCHOA01: Limited Loss Settlement Endorsement
- NLH011: Enhanced Partial Loss
- EXDMGNHR: Exclusion of Cosmetic Damage to Non-Hail Resistant Metal Roof
- EXDMGMET: Exclusion of Cosmetic Damage to Metal Structures Caused by Hail

### Other Checkboxes
- chk_DEFAULT_CUSTOMER: Same as Customer address
- chk_ULRP_DUMP_SUR: Delinquent or Unverifiable surcharge
- chk_ULRP_COMPANION_POLICY_YN: Companion Policy
- chk_ULRP_SEC_BLDG_CR_YN: Secondary Building Credit
- chk_Ulrp_Prior_Ur_Dmg: Prior Underwriting Damage

### Hidden Fields
- opt_Other_RiskTyp_Address: Address type (hidden select)
- cmb_Ulrp_Addr_Qn_1: Address question (Yes/No, hidden)
- opt_Intenal_Misreption: Misrepresentation (Yes/No, hidden)
- opt_remove_roofExclson: Remove Roof Exclusion (No/Yes, hidden)
- opt_coverage_desired: Coverage Desired (Yes/No, hidden)
- chk_ULRP_USS_ITIN: ITIN checkbox (hidden)
- txt_ULRP_USS_ITIN_NUM: ITIN number (hidden)

## Workflow for Automated Quoting
1. Login (Agent, ID, password)
2. Navigate to New Quote HO-A
3. Fill Customer Details → Save → Confirm/Next
4. Confirm Risk info screen → Confirm/Next
5. Fill Property Details (location, dwelling info, construction, roof, etc.)
6. Set Coverage A (dwelling limit) — this drives all other coverages as percentages
7. Set deductibles (Wind/Hail % and All Other Perils %)
8. Adjust optional coverages as needed
9. Click Calculate/Rate (fullQuoteCalc) to get premium
10. Review premium → Freeze if acceptable
