# Carrier Coverage Data Gap — Active Policies Only — 2026-05-22

**840 active policies | 594 with coverage | 246 missing (29%)**

Dead carriers (no active policies, all expired/canceled): Lighthouse, State Auto, Pacific Specialty, Kemper

## Active policies missing coverage data

| Carrier | Missing | LOBs | Portal URL |
|---------|---------|------|------------|
| Progressive Insurance | 75 | auto, HO, comm | https://www.foragentsonly.com/login/ |
| Logic-Standard Casualty | 31 | HO, dwelling fire | https://logicunderwriters.com/beyontecsuite/ |
| Allstate | 21 | HO, auto | https://myconnection1.allstate.com/IA/ |
| Mercury Insurance | 19 | HO, auto | https://www.mercuryfirst.com/login/home.do |
| FOREMOST INSURANCE | 11 | HO, auto | https://www.foremostagent.com/ia/portal/login |
| Foremost Insurance Group | 7 | HO, dwelling fire | https://www.foremostagent.com/ia/portal/login |
| National General Ins Co. | 8 | HO, auto, dwelling fire | https://www.natgenagency.com/ |
| Burns & Wilcox | 7 | comm prop, GL | https://www.burnsandwilcox.com |
| Homeowners of America | 7 | HO, dwelling fire | https://hoaic60.live.ptsapp.com/logIn.cfm |
| AMERICAN RISK INS CO | 6 | HO | https://isi.americanriskins.com/is/root/logon/index.cfm |
| Allied | 6 | HO, dwelling fire | (Safeco/LLG portal?) |
| Safeco Insurance | 6 | HO, auto | https://safesite.safeco.com/dpec/signin.asp |
| Texas Fair Plan | 5 | HO, flood, wind | (none) |
| Germania Farm Mutual | 4 | HO, auto | https://agents.germaniaconnect.com/producer-engage/ |
| Tower Hill Insurance | 4 | HO, dwelling fire | (none) |
| Hippo Insurance | 3 | HO | (none) |
| National Lloyds | 3 | HO, mobile | (none) |
| REInsurePro | 3 | dwelling fire | (none) |
| American Modern Insurance | 3 | dwelling fire, mobile | (none) |
| Cypress Insurance Group | 2 | HO | https://www.cypressig.com/AgentPortal |
| First Connect | 2 | mobile, HO | (none) |
| Imperial Casualty | 2 | HO | (none) |
| Travelers | 2 | HO | https://signin.travelers.com/ |
| TAPCO Underwriters | 2 | comm, GL | (none) |
| ASI (American Strategic) | 2 | HO, dwelling fire | http://www.americanstrategic.com/ |

## Scraping priority order
1. **Progressive** (75) — biggest gap, portal exists
2. **Logic** (31) — already building the scraper
3. **Allstate** (21) — major carrier
4. **Mercury** (19)
5. **Foremost** (18 combined) — existing Stagehand script already works
6. **National General** (8)
7. **Safeco** (6) — Liberty Mutual Group, may share portal with Allied
8. **American Risk** (6)
9. All others — small volumes, tackle as group

## Notes
- Login credentials in Google Sheet "Libertas PWs"
- Write coverage data to CRM via psycopg2 (SUPABASE_DB_URL/PW) — REST keys broken
- policy_coverages columns: id, policy_id, policy_term_id, coverage_code, coverage_name, limit_per_occurrence, limit_aggregate, deductible, deductible_type, premium, created_at
- Need to create policy_terms row first, then policy_coverages rows
