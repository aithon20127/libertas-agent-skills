# ACORD Coverage Code Mappings

Extracted from the production ACORD parser (`/tmp/ezlynx_acord_parser.py`) and verified against 823 scraped policies across Safeco, Allstate, Nationwide, Travelers, NatGen, Liberty County Mutual, and Germania.

## Home / Dwelling Fire Coverage Codes

| ACORD Code | Mapped Name | Description |
|------------|-------------|-------------|
| COVA | coverage_a | Dwelling / Coverage A |
| COVB | coverage_b | Other Structures / Coverage B |
| COVC | coverage_c | Personal Property / Coverage C |
| COVD | coverage_d | Loss of Use / Coverage D |
| COVE | coverage_e | Personal Liability / Coverage E |
| COVF | coverage_f | Medical Payments / Coverage F |
| DED | deductible | Standard deductible |
| HDED | hurricane_deductible | Hurricane deductible |
| STDED | storm_deductible | Storm deductible |
| WDED | wind_hail_deductible | Wind/hail deductible |
| MOLD | mold_limit | Mold limit |
| WTRBK | water_backup_limit | Water backup/sump overflow limit |
| ORDLW | ordinance_law_limit | Ordinance or law limit |
| IDTHF | identity_fraud_limit | Identity fraud limit |
| PIP | personal_injury_protection | Personal injury protection |
| MP | medical_payments | Medical payments (alternate) |
| LL | liability_limit | Liability limit |

### Home-Specific Codes Seen in Production

| Code | Name | Notes |
|------|------|-------|
| DWELL | dwelling_coverage | Coverage A (alternate label used by Safeco, Liberty County) |
| PP | personal_property | Coverage C (alternate label) |
| OS | other_structures | Coverage B (alternate label) |
| PL | personal_liability | Coverage E (alternate label) |
| MEDPM | medical_payments | Coverage F (alternate label) |
| LIAB | liability | General liability |
| FRV | fair_rental_value | Loss of use / rental value |
| HURR | hurricane | Hurricane deductible (percentage) |
| WTRDM | water_damage | Water damage endorsement |
| BOLAW | ordinance_law | Ordinance or law |
| FVREP | replacement_cost | Functional replacement cost |
| LOU | loss_of_use | Coverage D (alternate) |

## Auto Coverage Codes

| ACORD Code | Mapped Name | Description |
|------------|-------------|-------------|
| BI | bodily_injury | Bodily injury liability |
| PD | property_damage | Property damage liability |
| COLL | collision | Collision (has deductible) |
| COMP | comprehensive | Comprehensive/OTC (has deductible) |
| UM | uninsured_motorist | Uninsured motorist (has deductible) |
| UMUIM | um_uim | UM/UIM combined |
| UMPD | um_property_damage | UM property damage |
| UMCSL | um_combined_single_limit | UM combined single limit |
| PIP | personal_injury_protection | PIP |
| MP | medical_payments | Medical payments |
| MPCOV | medical_payments_coverage | Medical payments coverage |
| TL | towing_labor | Towing and labor |
| RREIM | rental_reimbursement | Rental reimbursement |
| ACCTS | accident_coverage | Accident coverage |
| PASSR | passenger_coverage | Passenger coverage |
| ADDA | accidental_death | Accidental death |
| ANTHF | antitheft | Anti-theft device discount |
| GAP | gap_coverage | GAP coverage |
| SPR | special_equipment | Special equipment |
| CSL | combined_single_limit | Combined single limit (BI+PD) |

### Texas-Specific / Carrier-Specific Auto Codes

| Code | Name | Carrier | Notes |
|------|------|---------|-------|
| PPAYD | prompt_pay_discount | Safeco, Liberty County | Discount |
| MCAR | multi_car_discount | Safeco, Liberty County | Discount |
| CLFRE | claim_free_discount | Safeco, Liberty County | Discount |
| AQDIS | acquisition_discount | Safeco, Liberty County | Discount |
| GPAYD | good_payer_discount | Safeco, Liberty County | Discount |
| LOWMI | low_mileage_discount | Safeco | Discount |
| ROAD | roadside_assistance | Safeco | Coverage |
| SUPER | superior_discount | Safeco | Discount |
| VIOFR | violation_free | Safeco | Discount |
| TPAC | telematics | Safeco | Discount/program |
| HODIS | home_discount | Safeco | Home-auto bundle |
| EPPDS | easy_pay_discount | Allstate | Discount |
| ESIGN | early_signing | Allstate | Discount |
| ESMRT | esmart_discount | Allstate | Discount |
| PREFR | preferred_package | Allstate | Discount |
| PREMR | premier_plus | Allstate | Discount |
| GDPAY | good_payer | Allstate | Discount |
| TRNEX | transfer | Allstate | Discount |
| ACCT | account | Allstate | Discount |
| ABS | anti_lock_brakes | Allstate | Discount |

## Discount Codes (Cross-LOB)

| Code | Name | Notes |
|------|------|-------|
| PREFR | preferred_package | Multi-policy or package |
| GDPAY | good_payer | Payment history |
| PREMR | premier_plus | Risk management |
| EPPDS | easy_pay | Auto-pay |
| ESIGN | early_signing | Early renewal |
| ESMRT | esmart | Telematics/digital |
| ABS | anti_lock_brakes | Vehicle safety |
| AIRB | airbag | Vehicle safety |
| ACCT | account | Account-level |
| TRNEX | transfer | Carrier transfer |
| DRL | daytime_running_lights | Vehicle safety |
| NSCLA | no_claim | Claims-free |
| PROTE | protective_device | Alarm/safety |
| MATUR | mature | Senior |
| NEW | new_home | New construction |
| RENEW | renewal | Renewal discount |
| FP01 | fire_protection | Fire alarm/sprinkler |
| HLFC | hail_free | Hail resist roof |
| DMGPO | damage_protection | Safeco |
| LAC | local_agent | Safeco |

## Parsing Notes

- **Home policies**: Coverage codes use space-after-colon format: `Coverage : PP` (note space before code). Regex: `r'^Coverage\s+:\s*(\w+)'`
- **Auto policies**: Coverage codes use no-space format: `Coverage :BI` (no space). Same regex handles both if using `\s*`
- **Per-vehicle coverages**: On multi-vehicle auto, COMP/COLL/ANTHF repeat for each vehicle. Must attach to vehicle object, not top-level
- **Policy-level vs vehicle-level**: BI, PD, CSL, UMCSL, and discount codes are policy-level. COMP, COLL, ANTHF are vehicle-level
- **Germania special case**: Coverage A is NOT in any Coverage line — it's in the Dwelling section as `Estimated Repl Cost Amount`
