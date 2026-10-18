# LendingClub Second-Look Rejection Analysis

This analysis asks whether rejected LendingClub applicants contain segments worth reviewing again under normal underwriting controls.

## Executive Summary

The strongest candidate identified by the historical segment comparison is:

- **DTI:** 10% or less
- **Requested amount:** $5,000 or less
- **Rejected applications:** 3,808,633 in the later full-data aggregate
- **Accepted loans with resolved outcomes:** 41,524
- **Defaults:** 5,090
- **Paid loans:** 36,434
- **Observed default rate among resolved accepted loans:** 12.26%

This is a **review candidate**, not an approval rule. The 12.26% rate describes accepted loans with resolved outcomes in the same segment. It does not estimate how rejected applicants would perform, and it does not establish profitability or eligibility for automatic approval.

One material reconciliation issue remains: another saved full-data table lists 3,280,432 rejected applications for the same segment. The exact search, time range, index scope, source version, and aggregation logic must be checked before the rejected volume is treated as final.

## Question and Scope

The working question is:

> Which rejected-applicant segments combine high rejection volume with enough resolved accepted-loan outcomes to make an observed default rate meaningful, and which segment should be reviewed first?

The analysis compares DTI bands and requested-loan amount bands, then examines the leading segment by purpose and employment length. It is a retrospective segment screen. It is not:

- a credit scorecard;
- a causal study;
- a loan-level prediction model;
- evidence that rejected applicants would have performed like accepted applicants; or
- a basis for automatic approval.

The comparison fields are `dti_band`, `amount_band`, `purpose` or `purpose_clean`, `employment_length` or `employment_clean`, `rejected_applications`, `paid_loans`, `defaults`, `other`, `terminal_loans`, `resolved_outcomes`, and the observed default rate.

## Data, Processing, and Analysis Environment

The data was processed in Google Colab with Python. The processed data was then indexed and analyzed in Splunk Cloud. Splunk Cloud was used for the segment aggregations, outcome comparisons, saved result tables, and sample-data checks described below.

| Item | Detail |
| --- | --- |
| Dataset | Kaggle LendingClub dataset (`wordsforthewise/lending-club`) |
| Source coverage | Accepted and rejected application files covering 2007 through 2018 Q4 |
| Analysis platform | Splunk Cloud |
| Splunk index | `club` |
| Sourcetypes | `lendingclub:rejected`, `lendingclub:accepted`, `lendingclub:sample` |
| Full-data rejected total | 27,648,741 applications, as recorded in project notes |
| Full-data accepted total | 2,260,701 loans, as recorded in project notes |
| Full-data defaults | 269,360 |
| Full-data paid loans | 1,078,739 |
| Full-data other outcomes | 912,602 |
| Sample file | `lendingclub_splunk_sample.csv`, described as 100,000 accepted and 100,000 rejected records |
| Time range | `All Time` for historical totals |

The totals above require reconciliation against the live Splunk Cloud index before being used as an official data inventory. A `Last 24 Hours` search returned only 19,201,880 rejected applications, which is incomplete for the historical 2007-2018 coverage.

### Outcome grouping

- **Paid:** accepted loans recorded as paid.
- **Default:** accepted loans recorded as default.
- **Other:** current, late, unresolved, or otherwise non-terminal statuses.
- **Resolved outcomes / terminal loans:** `defaults + paid`.

The `other` group is shown for transparency but excluded from the observed default-rate denominator.

### Data sourcing and preparation

The source data was obtained from the Kaggle LendingClub dataset (`wordsforthewise/lending-club`) and processed in Google Colab. The preparation script expects these compressed source files beneath `/content/lendingclub`:

- `rejected_2007_to_2018Q4.csv.gz`
- `accepted_2007_to_2018Q4.csv.gz`

The rejected and accepted files were handled separately because they have different schemas and different analytical roles. Rejected applications provide segment volume; accepted loans provide observed historical outcomes for comparison. The source files were not combined row-for-row.

The Colab preparation flow was:

1. Read each compressed CSV in 50,000-row chunks so the full files did not need to be loaded into memory at once.
2. Inspect the headers and map the source columns used by each file. Rejected fields include requested amount, application date, loan title, DTI, state, and employment length. Accepted fields include loan amount, issue date, purpose, DTI, state, employment length, and loan status.
3. Convert amount and DTI values to numeric values, removing commas and percent signs where needed.
4. Normalize purpose labels by lowercasing, trimming whitespace, replacing underscores and hyphens, and mapping known aliases such as `debt consolidation` to `debt_consolidation`, `car financing` to `car`, and `moving and relocation` to `moving`.
5. Normalize employment length and replace missing values with `unknown`.
6. Create amount bands of `<=5k`, `5-10k`, `10-15k`, `15-20k`, `20-25k`, and `>25k`.
7. Create DTI bands of `<=10`, `10-20`, `20-30`, `30-40`, and `>40`; values that cannot be parsed are assigned `Unknown`.
8. Classify accepted-loan statuses as `paid`, `default`, or `other`. `Fully Paid` is treated as paid, `Charged Off` and `Default` as default, and unresolved or unmatched statuses as other.
9. Aggregate rejected applications by DTI band, amount band, purpose, and employment length. Aggregate accepted loans by the same fields and outcome group.
10. Record field-level missingness for both source files.
11. Keep a reproducible random sample of up to 100,000 rejected and 100,000 accepted records using seed `42` for the separate Splunk sample checks.

The preparation step writes `rejected_full_counts.csv`, `accepted_full_outcomes.csv`, `data_quality.csv`, and `lendingclub_splunk_sample.csv` to `/content/lendingclub_outputs`. Those outputs were then indexed into Splunk Cloud under the `club` index with the `lendingclub:rejected`, `lendingclub:accepted`, and `lendingclub:sample` sourcetypes.

## Metrics

| Metric | Definition | Interpretation |
| --- | --- | --- |
| `rejected_applications` | Rejected applications counted in a segment | May not represent unique people and is not a forecast of approvals |
| `paid_loans` | Accepted loans recorded as paid | Historical outcome |
| `defaults` | Accepted loans recorded as default | Historical outcome |
| `other` | Accepted loans that are neither paid nor default | Excluded from the resolved-outcome denominator |
| `resolved_outcomes` / `terminal_loans` | `defaults + paid` | Denominator for the observed default rate |
| `observed_default_rate` | `defaults / (defaults + paid) * 100` | Rate among accepted loans with resolved outcomes in the segment |

If `resolved_outcomes` is zero, the rate is undefined and must be reported as `N/A`, not `0%`.

## Method

1. **Fix the historical time window.** Use `All Time` for the 2007-2018 dataset and record the time range with every saved search.
2. **Rank rejection volume.** Aggregate rejected applications by DTI band and amount band.
3. **Attach accepted outcomes.** Aggregate accepted defaults, paid loans, and other outcomes by the same segment.
4. **Calculate the reference rate.** Use only defaults and paid loans in the denominator.
5. **Inspect the leading segment.** Break it down by purpose and employment length.
6. **Standardize labels before combining categories.** Preserve the original values and document every mapping.
7. **Run sample checks separately.** Sample counts validate query shape only; they must never be added to full-data counts.
8. **Design a bounded pilot.** Use the segment as a candidate for additional underwriting review, with existing controls intact.

## Full-Data Results

### Candidate segment

| Measure | Value |
| --- | ---: |
| Segment | DTI <=10%, amount <=$5,000 |
| Rejected applications, later table | 3,808,633 |
| Rejected applications, earlier table | 3,280,432 |
| Accepted defaults | 5,090 |
| Accepted paid loans | 36,434 |
| Other outcomes | 26,605 |
| Resolved accepted outcomes | 41,524 |
| Observed default rate | 12.26% |

The accepted-outcome arithmetic checks: `5,090 + 36,434 = 41,524`, and `5,090 / 41,524 = 12.26%` after rounding. The rejected count does not yet reconcile.

### DTI and amount comparison

| DTI band | Amount band | Rejected apps | Resolved outcomes | Defaults | Paid | Observed default rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| <=10 | <=5k | 3,808,633 | 41,524 | 5,090 | 36,434 | 12.26% |
| <=10 | 5-10k | 1,811,024 | 76,839 | 10,043 | 66,796 | 13.07% |
| 10-20 | <=5k | 2,182,679 | 72,795 | 10,583 | 62,212 | 14.54% |
| <=10 | 10-15k | 631,455 | 48,749 | 7,221 | 41,528 | 14.81% |
| 10-20 | 5-10k | 1,583,016 | 155,227 | 24,138 | 131,089 | 15.55% |
| <=10 | 15-20k | 534,739 | 33,150 | 5,588 | 27,562 | 16.86% |
| <=10 | 20-25k | 288,894 | 20,160 | 3,490 | 16,670 | 17.31% |
| 10-20 | 10-15k | 638,461 | 119,295 | 21,745 | 97,550 | 18.23% |
| 20-30 | <=5k | 1,483,572 | 51,653 | 9,527 | 42,126 | 18.44% |
| 10-20 | 15-20k | 553,248 | 90,243 | 17,911 | 72,332 | 19.85% |
| 10-20 | 20-25k | 273,473 | 57,399 | 11,486 | 45,913 | 20.01% |
| 20-30 | 5-10k | 1,203,560 | 107,729 | 21,703 | 86,026 | 20.15% |
| <=10 | >25k | 896,953 | 26,613 | 5,434 | 21,179 | 20.42% |
| 10-20 | >25k | 636,476 | 68,389 | 14,813 | 53,576 | 21.66% |
| 30-40 | <=5k | 863,013 | 16,314 | 3,555 | 12,759 | 21.79% |
| 20-30 | 10-15k | 558,624 | 87,851 | 21,170 | 66,681 | 24.10% |
| 30-40 | 5-10k | 772,643 | 33,083 | 8,240 | 24,843 | 24.91% |
| 20-30 | 20-25k | 269,984 | 42,865 | 11,064 | 31,801 | 25.81% |
| 20-30 | 15-20k | 514,577 | 69,217 | 17,876 | 51,341 | 25.83% |
| 20-30 | >25k | 636,058 | 49,720 | 12,969 | 36,751 | 26.08% |
| >40 | 5-10k | 1,386,688 | 1,532 | 423 | 1,109 | 27.61% |
| >40 | <=5k | 1,641,285 | 649 | 182 | 467 | 28.04% |
| >40 | 10-15k | 746,782 | 1,199 | 374 | 825 | 31.19% |
| >40 | 15-20k | 741,329 | 1,161 | 372 | 789 | 32.04% |
| >40 | >25k | 1,047,967 | 1,450 | 465 | 985 | 32.07% |
| >40 | 20-25k | 423,711 | 775 | 251 | 524 | 32.39% |
| 30-40 | 15-20k | 387,704 | 20,544 | 6,765 | 13,779 | 32.93% |
| 30-40 | >25k | 517,722 | 12,563 | 4,182 | 8,381 | 33.29% |
| 30-40 | 20-25k | 212,918 | 12,003 | 4,095 | 7,908 | 34.12% |

These values are preserved as separate saved output. Several rejection counts and some accepted outcomes differ from the earlier table, so this comparison is not a substitute for query reconciliation.

### Purpose within the candidate segment

| Purpose | Rejected apps | Resolved outcomes | Defaults | Paid | Observed default rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| credit_card | 210,386 | 6,642 | 607 | 6,035 | 9.14% |
| car | 268,168 | 1,645 | 156 | 1,489 | 9.48% |
| wedding | 3,810 | 178 | 17 | 161 | 9.55% |
| major_purchase | 178,788 | 2,553 | 251 | 2,302 | 9.83% |
| home improvement | 149,699 | 3,629 | 368 | 3,261 | 10.14% |
| vacation | 93,766 | 1,071 | 121 | 950 | 11.30% |
| debt_consolidation | 1,011,008 | 15,759 | 2,085 | 13,674 | 13.23% |
| other | 1,211,205 | 6,556 | 904 | 5,652 | 13.79% |
| house | 22,573 | 301 | 47 | 254 | 15.61% |
| medical | 202,694 | 1,177 | 185 | 992 | 15.72% |
| moving | 269,749 | 1,083 | 180 | 903 | 16.62% |
| renewable energy | 10,296 | 90 | 15 | 75 | 16.67% |
| small business | 49,989 | 742 | 135 | 607 | 18.19% |
| educational | 556 | 98 | 19 | 79 | 19.39% |

Purpose-level rejected counts do not add to the candidate total. The output includes only some categories, and labels may not align across datasets. No missing categories are inferred.

### Purpose and employment length

The highest-volume rows are dominated by employment length `< 1 year`. This is a pattern in the aggregate output, not evidence that short tenure causes rejection or predicts repayment.

| Purpose | Employment length | Rejected apps | Terminal loans | Defaults | Paid | Observed default rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| other | < 1 year | 921,918 | 780 | 132 | 648 | 16.92% |
| debt_consolidation | < 1 year | 842,494 | 1,727 | 256 | 1,471 | 14.82% |
| moving | < 1 year | 213,616 | 263 | 50 | 213 | 19.01% |
| car | < 1 year | 201,608 | 225 | 27 | 198 | 12.00% |
| medical | < 1 year | 163,987 | 104 | 23 | 81 | 22.12% |
| credit_card | < 1 year | 162,403 | 749 | 71 | 678 | 9.48% |
| major_purchase | < 1 year | 140,662 | 307 | 36 | 271 | 11.73% |
| home improvement | < 1 year | 115,413 | 232 | 22 | 210 | 9.48% |
| debt_consolidation | 5 years | 91,435 | 964 | 117 | 847 | 12.14% |
| vacation | < 1 year | 67,469 | 73 | 6 | 67 | 8.22% |
| car | 5 years | 38,598 | 110 | 5 | 105 | 4.55% |
| moving | 5 years | 36,582 | 58 | 7 | 51 | 12.07% |
| other | 1 year | 28,647 | 574 | 93 | 481 | 16.20% |
| business | < 1 year | 23,475 | 0 | 0 | 0 | N/A |
| medical | 5 years | 20,079 | 54 | 5 | 49 | 9.26% |
| home improvement | 5 years | 19,243 | 222 | 23 | 199 | 10.36% |
| business loan | < 1 year | 15,659 | 0 | 0 | 0 | N/A |
| house | < 1 year | 15,133 | 42 | 9 | 33 | 21.43% |
| other | 2 years | 12,533 | 653 | 108 | 545 | 16.54% |
| other | 3 years | 12,016 | 527 | 74 | 453 | 14.04% |
| debt_consolidation | 1 year | 11,523 | 1,374 | 210 | 1,164 | 15.28% |
| other | 10+ years | 9,006 | 1,710 | 172 | 1,538 | 10.06% |
| debt_consolidation | 10+ years | 8,150 | 3,793 | 383 | 3,410 | 10.10% |
| other | 4 years | 6,982 | 437 | 53 | 384 | 12.13% |
| car | 1 year | 5,885 | 167 | 12 | 155 | 7.19% |
| debt_consolidation | 3 years | 5,795 | 1,372 | 186 | 1,186 | 13.56% |
| debt_consolidation | 2 years | 5,667 | 1,640 | 229 | 1,411 | 13.96% |
| vacation | unknown | 4,391 | 87 | 12 | 75 | 13.79% |
| moving | 1 year | 3,921 | 115 | 15 | 100 | 13.04% |
| wedding | < 1 year | 3,648 | 33 | 3 | 30 | 9.09% |

Two rows have no terminal loans. Their rate is `N/A`, not zero.

## Sample-Data Validation

The sample is a separate scope. Its counts are in the thousands and cannot be combined with full-data aggregates.

### Highest rejected volume in the sample

| DTI band | Amount band | Rejected sample records |
| --- | --- | ---: |
| <=10 | <=5k | 13,689 |
| 10-20 | <=5k | 7,922 |
| <=10 | 5-10k | 6,564 |
| >40 | <=5k | 6,072 |
| 10-20 | 5-10k | 5,729 |
| 20-30 | <=5k | 5,235 |
| >40 | 5-10k | 5,043 |
| 20-30 | 5-10k | 4,392 |
| >40 | >25k | 3,862 |
| <=10 | >25k | 3,348 |
| 30-40 | <=5k | 3,056 |
| >40 | 10-15k | 2,726 |
| 30-40 | 5-10k | 2,721 |
| >40 | 15-20k | 2,710 |
| 10-20 | 10-15k | 2,365 |
| 10-20 | >25k | 2,324 |
| 20-30 | >25k | 2,277 |
| <=10 | 10-15k | 2,231 |
| 20-30 | 10-15k | 2,075 |
| 10-20 | 15-20k | 2,019 |

### Rejected volume and accepted outcomes by sample segment

| DTI band | Amount band | Rejected sample records | Accepted terminal loans | Accepted defaults | Observed default rate |
| --- | --- | ---: | ---: | ---: | ---: |
| <=10 | <=5k | 13,689 | 1,785 | 193 | 10.81% |
| 10-20 | <=5k | 7,922 | 3,279 | 467 | 14.24% |
| <=10 | 5-10k | 6,564 | 3,405 | 464 | 13.63% |
| >40 | <=5k | 6,072 | 22 | 7 | 31.82% |
| 10-20 | 5-10k | 5,729 | 6,848 | 1,055 | 15.41% |
| 20-30 | <=5k | 5,235 | 2,295 | 414 | 18.04% |
| >40 | 5-10k | 5,043 | 63 | 18 | 28.57% |
| 20-30 | 5-10k | 4,392 | 4,700 | 941 | 20.02% |
| >40 | >25k | 3,862 | 75 | 25 | 33.33% |
| <=10 | >25k | 3,348 | 1,179 | 227 | 19.25% |
| 30-40 | <=5k | 3,056 | 733 | 153 | 20.87% |
| >40 | 10-15k | 2,726 | 48 | 17 | 35.42% |
| 30-40 | 5-10k | 2,721 | 1,495 | 355 | 23.75% |
| >40 | 15-20k | 2,710 | 58 | 21 | 36.21% |
| 10-20 | 10-15k | 2,365 | 5,232 | 961 | 18.37% |
| 10-20 | >25k | 2,324 | 3,052 | 627 | 20.54% |
| 20-30 | >25k | 2,277 | 2,196 | 554 | 25.23% |
| <=10 | 10-15k | 2,231 | 2,169 | 346 | 15.95% |
| 20-30 | 10-15k | 2,075 | 3,865 | 898 | 23.23% |
| 10-20 | 15-20k | 2,019 | 3,994 | 791 | 19.80% |
| <=10 | 15-20k | 1,876 | 1,474 | 249 | 16.89% |
| 20-30 | 15-20k | 1,840 | 3,075 | 800 | 26.02% |
| 30-40 | >25k | 1,779 | 513 | 177 | 34.50% |
| >40 | 20-25k | 1,571 | 35 | 12 | 34.29% |
| 30-40 | 10-15k | 1,449 | 1,228 | 364 | 29.64% |
| 30-40 | 15-20k | 1,351 | 933 | 318 | 34.08% |
| <=10 | 20-25k | 1,006 | 902 | 139 | 15.41% |
| 10-20 | 20-25k | 1,002 | 2,502 | 515 | 20.58% |
| 20-30 | 20-25k | 952 | 1,919 | 492 | 25.64% |
| 30-40 | 20-25k | 814 | 529 | 185 | 34.97% |

### Sample label-quality checks

Observed variants include:

- `Other` and `other`;
- `Debt consolidation` and `debt_consolidation`;
- `Moving`, `moving`, and `moving and relocation`;
- `Car` and `car financing`;
- `Medical` and `medical expenses`;
- `Major purchase` and `major_purchase`.

A sample table titled `accepted-loan outcomes by standardized fields` repeats rejected counts rather than accepted-loan measures. It is invalid for accepted-outcome comparison until its join or aggregation is repaired.

## Findings

### What the outputs support

- In the later full-data table, DTI <=10% and requested amounts <=$5,000 is the largest rejected segment shown and has the lowest observed default rate shown: 3,808,633 rejected applications and 12.26% among 41,524 resolved accepted outcomes.
- Observed default rates generally increase as DTI rises. DTI above 40% ranges from 27.61% to 32.39% in the comparison, while some 30-40% cells are higher.
- Within the candidate segment, credit card (9.14%), car (9.48%), major purchase (9.83%), and home improvement (10.14%) are below debt consolidation (13.23%) and other (13.79%) on the accepted-loan reference rate.
- The sample reproduces the broad shape of the segment comparison at a smaller scale, but it does not replace full-data verification.

### What the outputs do not support

- That 3,808,633 distinct people would qualify.
- That rejected applicants in the candidate segment would default at 12.26%.
- That approving the segment would be profitable or produce a particular revenue increase.
- That purpose or employment tenure causes rejection or repayment outcomes.
- That the segment is safe enough for automatic approval.
- That a predictive model was trained, validated, or shown to generalize.

## Limitations

### Selection bias

Accepted applicants are not a random sample of rejected applicants. Their outcomes are a reference point only. The counterfactual outcome for rejected applicants is unobserved.

### Aggregation and identity

Rejected counts may count applications rather than unique people. The exports do not establish whether duplicate applications, resubmissions, or multiple loans are present.

### Outcome maturity

`Other` contains open or unresolved statuses. Excluding it from the rate denominator avoids treating unresolved loans as resolved, but it also means the observed rate is conditional on resolution.

### Label consistency

Purpose and employment labels require explicit standardization. Original values must be retained, and category mappings must be versioned and reviewed.

### Schema uncertainty

The reconstructed SPL assumes pre-aggregated events in some full-data searches and application-level events in the sample searches. The live schema must be checked before execution. If events are raw, use counts; if events are pre-aggregated, sum the appropriate count fields.

## Data-Quality Log

| Issue | Handling |
| --- | --- |
| Candidate rejected count is 3,280,432 in one table and 3,808,633 in another | Re-run the exact search over `All Time`; verify index, sourcetype, filters, double-counting, and dataset scope |
| Earlier and later full-data tables differ in several values | Treat them as separate saved outputs until the query and scope are verified |
| Sample and full-data scales differ | Label sample output as validation and never merge counts |
| Purpose labels vary by capitalization, underscores, and synonyms | Keep the raw field, apply a documented mapping, and validate category coverage |
| Sample accepted-outcome table repeats rejected counts | Do not use it; repair the join or aggregation and validate the result |
| Rows have zero terminal loans | Report `N/A`, not `0%` |
| `other` outcomes exist | Show them separately and exclude them from the default-rate denominator |
| Unknown DTI rows show accepted outcomes with zero rejected volume | Treat as reference-only or exclude from volume ranking until coverage is verified |

## SPL Querybook

The analysis was run in Splunk Cloud. The SPL files in [`scripts/`](scripts/) contain the searches used to aggregate rejection volume, accepted outcomes, DTI and amount bands, purpose, employment length, and sample checks.

Key assumptions:

- Full-data rejected and accepted events may be pre-aggregated and expose `rejected_applications` and `loan_count`.
- Sample events may be one application or one loan per event.
- `outcome_group` contains `default`, `paid`, and `other`.
- `dti_band`, `amount_band`, `purpose`, and `employment_length` are available on both sides of the comparison.

The searches assume the indexed fields and event grain described above. Confirm the index, sourcetypes, time range, and count fields in Splunk Cloud before rerunning them.

See:

- [`scripts/01_candidate_rejected_volume.spl`](scripts/01_candidate_rejected_volume.spl)
- [`scripts/02_candidate_accepted_outcomes.spl`](scripts/02_candidate_accepted_outcomes.spl)
- [`scripts/03_dti_amount_comparison.spl`](scripts/03_dti_amount_comparison.spl)
- [`scripts/04_purpose_breakdown.spl`](scripts/04_purpose_breakdown.spl)
- [`scripts/05_purpose_employment_breakdown.spl`](scripts/05_purpose_employment_breakdown.spl)
- [`scripts/06_sample_checks.spl`](scripts/06_sample_checks.spl)

## Proposed Pilot Validation Plan

No pilot has been run. The next evidence needed is prospective and application-level.

1. Reconcile the competing rejected counts.
2. Freeze the query, time range, index, sourcetypes, dataset version, and field definitions.
3. Define pilot eligibility from documented lender policy; do not infer a new approval cutoff from aggregate tables.
4. Keep normal affordability, verification, fraud, credit, compliance, and fair-lending controls in force.
5. Log every reviewed application, decision, reason codes, offered terms, and acceptance or take-up.
6. Track repayment at consistent maturity windows, keeping paid, default, current, late, and still-open accounts distinct.
7. Define a comparison group before the pilot begins.
8. Report approval rate, take-up, default rate, loss severity, contribution margin, and lawful fairness and compliance metrics.
9. Agree stop and go thresholds before launch. The available aggregates do not provide defensible thresholds.
10. Review the pilot independently before expanding eligibility or changing underwriting policy.

## Processing Script

[`python/processing.py`](python/processing.py) is the Python preprocessing script used in Google Colab before indexing data in Splunk Cloud. It reads the accepted and rejected compressed CSV files, processes them in chunks, creates standardized fields and bands, samples records, and writes aggregate outputs for Splunk Cloud.

```bash
python python/processing.py
```

The input and output locations are configured at the top of the script for the Google Colab workspace. It keeps the source purpose and employment values, adds standardized labels, creates DTI and amount bands, maps loan statuses into `default`, `paid`, or `other`, and exports the aggregates used by the Splunk searches. The `other` group includes statuses that are not resolved and is excluded from the observed default-rate denominator.

