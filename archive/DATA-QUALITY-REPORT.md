# 📋 Data Quality Report

**File:** `sample-input/data.csv`  
**Generated:** 2026-07-29 13:46 UTC  
**Pipeline:** DQ Stage 5 (Final Report) — Multi-Arch 30-Agent MAS  
**Dataset:** 15 rows × 4 columns (`id`, `age`, `country`, `signup_date`)

---

## 🏆 Overall DQ Score: **86.7 / 100**

| Dimension      | Score   | Assessment                |
|----------------|---------|---------------------------|
| Completeness   | 95.0%   | ✅ Good (3 cells missing) |
| Validity       | 91.7%   | ⚠️ Moderate (5 violations)|
| Accuracy       | 60.0%   | 🔴 Poor (critical anomalies) |
| Consistency    | 100.0%  | ✅ Perfect                |

---

## 1. Executive Summary

This report presents the findings of a comprehensive data quality assessment of `sample-input/data.csv` across four dimensions: completeness, validity, accuracy, and consistency.

**Bottom Line:** The dataset is structurally sound but has significant quality issues concentrated in a single column — **`age`**. Of the 15 records, 5 (33%) exhibit problems: 3 missing values, 1 impossible negative value (−5), and 1 extreme outlier (150). The remaining three columns (`id`, `country`, `signup_date`) are entirely clean.

**Risk Level:** 🟡 **MODERATE** — The age column is unusable in its current state for any analysis requiring accurate age data. However, remediation is straightforward via imputation and validation.

**Recommendation:** Apply the remediation steps below before using this dataset. Estimated effort: **30 minutes** for a data engineer.

---

## 2. Dataset Overview

```
┌──────────────────────────────────────────────────────────────┐
│                      DATASET PROFILE                         │
├───────────────┬────────┬──────────┬──────────┬──────────────┤
│ METRIC        │ id     │ age      │ country  │ signup_date  │
├───────────────┼────────┼──────────┼──────────┼──────────────┤
│ Type          │ int    │ int      │ string   │ date (str)   │
│ Count         │ 15     │ 12 (3 ∅) │ 15       │ 15           │
│ Missing       │ 0      │ 3 (20%)  │ 0        │ 0            │
│ Unique        │ 15     │ 12       │ 4        │ 15           │
│ Min           │ 1      │ -5 ❌    │ DE       │ 2020-01-15   │
│ Max           │ 15     │ 150 ❌   │ UK       │ 2021-03-22   │
│ Mean          │ 8.0    │ 44.33    │ —        │ —            │
│ Median        │ 8.0    │ 34       │ —        │ —            │
│ Std Dev       │ 4.32   │ 35.98    │ —        │ —            │
│ IQR           │ —      │ 26       │ —        │ —            │
└───────────────┴────────┴──────────┴──────────┴──────────────┘
```

**Country Distribution:** DE=6, US=4, FR=3, UK=2  
**Date Range:** 2020-01-15 → 2021-03-22 (~14 months, ~30.9 day avg interval)  
**IDs:** Sequential 1–15, no gaps, no duplicates  

---

## 3. Findings by Column

### ✅ `id` — CLEAN (No Issues)
- **Completeness:** 15/15 (100%)
- **Validity:** All positive integers
- **Consistency:** Sequential 1–15, no gaps
- **Findings:** None

### 🔴 `age` — 5 ISSUES (3 Types)
| # | Row | Value   | Issue Type      | Severity | Detection Method        |
|---|-----|---------|-----------------|----------|-------------------------|
| 1 |  3  | *(empty)* | Missing value   | 🟡 HIGH  | Column profiling        |
| 2 |  5  | 150     | Extreme outlier | 🔴 CRITICAL | IQR (≥94 = outlier, Z=2.81σ) |
| 3 |  7  | *(empty)* | Missing value   | 🟡 HIGH  | Column profiling        |
| 4 | 13  | −5      | Impossible value| 🔴 CRITICAL | IQR (≤−10 = outlier, negative age) |
| 5 | 15  | *(empty)* | Missing value   | 🟡 HIGH  | Column profiling        |

**Impact:** 33.3% of age values are problematic. The mean (44.33) is heavily skewed — without the two outliers (−5, 150), the mean drops to ~40.9. The median (34) is robust and recommended as an imputation baseline.

**Root Cause Analysis:**
- **Missing values (rows 3, 7, 15):** Systematic — age appears to have been an optional field during data entry. All missing values are in the same column (not random across columns). 2 of 3 are DE records.
- **Value 150 (row 5):** Probable data-entry typo (digit reversal/addition — likely intended 15 or 50).
- **Value −5 (row 13):** Sign error or data corruption. Could be a missing leading digit (e.g., intended 25 or 35).

### ✅ `country` — CLEAN (No Issues)
- **Completeness:** 15/15 (100%)
- **Validity:** All values ∈ {DE, US, UK, FR} — valid codes per spec
- **Note:** `UK` is non-standard ISO 3166-1 alpha-2 (should be `GB`). While accepted by the validation rules, this may cause issues with downstream geo-enrichment tools.

### ✅ `signup_date` — CLEAN (No Issues)
- **Completeness:** 15/15 (100%)
- **Format:** All `YYYY-MM-DD`, parseable
- **Consistency:** No gaps or jumps exceeding expected intervals
- **Findings:** None

---

## 4. Anomaly Detail

### 🔴 ANOM-001 — Row 5: `age = 150` (CRITICAL)
| Attribute      | Value                                       |
|----------------|---------------------------------------------|
| **Detection**  | IQR outlier (upper fence = 94.0) + Z-score = 2.81σ |
| **Likely Cause** | Data-entry error — digit reversal (`150` instead of `15` or `50`) |
| **Validation** | 150 > 120 — out of valid range [0, 120]     |

### 🔴 ANOM-002 — Row 13: `age = −5` (CRITICAL)
| Attribute      | Value                                       |
|----------------|---------------------------------------------|
| **Detection**  | IQR outlier (lower fence = −10.0) — negative value |
| **Likely Cause** | Sign error or missing leading digit (`−5` instead of `25` or `35`) |
| **Validation** | −5 < 0 — out of valid range [0, 120]        |

### 🟡 ANOM-003 — Rows 3, 7, 15: Missing `age` (HIGH)
| Attribute      | Value                                       |
|----------------|---------------------------------------------|
| **Detection**  | Column profiling — 20% null rate            |
| **Pattern**    | All missing in `age` only — systematic, not random |
| **By Country** | DE: 2 rows, FR: 1 row                       |
| **Likely Cause** | `age` was an optional/non-required data-entry field |

---

## 5. Remediation Steps

### 🔴 Critical Priority (Fix Before Use)

| # | Action | Details | Effort |
|---|--------|---------|--------|
| 1 | **Add input validation** | Enforce `age` ∈ [0, 120] at data-entry point; reject empty/null values | ⏱️ 15 min |
| 2 | **Handle value 150 (row 5)** | Impute with median (34) or correct to `15`/`50` if source record available | ⏱️ 5 min |
| 3 | **Handle value −5 (row 13)** | Impute with median (34) or correct if source record available | ⏱️ 5 min |
| 4 | **Impute missing ages (rows 3, 7, 15)** | Fill with overall median (34) or country-stratified median (DE=33, FR=32) | ⏱️ 5 min |

### 🟡 High Priority (Recommended)

| # | Action | Details | Effort |
|---|--------|---------|--------|
| 5 | **Normalize UK → GB** | `UK` is non-standard ISO 3166-1 alpha-2; convert to `GB` for geo-tool compatibility | ⏱️ 2 min |
| 6 | **Add `age_imputed` flag** | Boolean column tracking which age values were imputed, enabling sensitivity analysis | ⏱️ 2 min |
| 7 | **Add `age_band` column** | Bucket ages: 18-24, 25-34, 35-44, 45-54, 55-64, 65+ | ⏱️ 5 min |
| 8 | **Enrich with `country_name`** | Lookup: DE→Germany, US→United States, FR→France, UK→United Kingdom | ⏱️ 2 min |

### 🟢 Medium Priority (Nice-to-have)

| # | Action | Details | Effort |
|---|--------|---------|--------|
| 9 | **Add `tenure_days` column** | Days since signup_date to a reference date | ⏱️ 3 min |
| 10 | **Add `signup_cohort` column** | Year-Quarter cohort (2020-Q1, 2020-Q2, etc.) | ⏱️ 3 min |
| 11 | **Add `continent` column** | Europe for DE/FR/UK, North America for US | ⏱️ 2 min |

### 🔧 Recommended Remediation Pipeline (Execution Order)
```
Step 1  🔴 Age Validation → Reject negative & >120, require non-empty
Step 2  🔴 Impute / Correct anomalies (rows 5, 13, 3, 7, 15)
Step 3  🔴 Flag imputed values (age_imputed)
Step 4  🟡 Normalize UK → GB
Step 5  🟢 Enrich: age_band, country_name, continent
Step 6  🟢 Enrich: tenure_days, signup_cohort
```

---

## 6. Clean Data Preview (After Remediation)

```
┌─────┬─────┬─────────┬─────────────┬──────────┬──────────────┐
│ id  │ age │ country │ signup_date │ age_band │ age_imputed  │
├─────┼─────┼─────────┼─────────────┼──────────┼──────────────┤
│  1  │  25 │ DE      │ 2020-01-15  │ 25-34    │ ✗ original   │
│  2  │  34 │ US      │ 2020-02-20  │ 25-34    │ ✗ original   │
│  3  │  34 │ FR      │ 2020-03-10  │ 25-34    │ ✓ imputed    │
│  4  │  45 │ DE      │ 2020-04-05  │ 45-54    │ ✗ original   │
│  5  │  34 │ US      │ 2020-05-12  │ 25-34    │ ✓ imputed    │
│  6  │  28 │ UK      │ 2020-06-18  │ 25-34    │ ✗ original   │
│  7  │  34 │ DE      │ 2020-07-22  │ 25-34    │ ✓ imputed    │
│  8  │  33 │ FR      │ 2020-08-30  │ 25-34    │ ✗ original   │
│  9  │  67 │ US      │ 2020-09-05  │ 65+      │ ✗ original   │
│ 10  │  29 │ DE      │ 2020-10-14  │ 25-34    │ ✗ original   │
│ 11  │  40 │ DE      │ 2020-11-20  │ 35-44    │ ✗ original   │
│ 12  │  31 │ US      │ 2020-12-25  │ 25-34    │ ✗ original   │
│ 13  │  34 │ FR      │ 2021-01-08  │ 25-34    │ ✓ imputed    │
│ 14  │  55 │ UK      │ 2021-02-14  │ 55-64    │ ✗ original   │
│ 15  │  34 │ DE      │ 2021-03-22  │ 25-34    │ ✓ imputed    │
└─────┴─────┴─────────┴─────────────┴──────────┴──────────────┘
```
*(Imputation used: median age = 34)*

---

## 7. Column Health Summary

```
┌────────────────────────────────────────────────────────────────┐
│  COLUMN        │ HEALTH │ VALID │ INVALID │ % GOOD │ PRIORITY │
├────────────────┼────────┼───────┼─────────┼────────┼──────────┤
│  id            │ ✅     │  15   │    0    │ 100%   │ —        │
│  age           │ 🔴     │  10   │    5    │  67%   │ CRITICAL │
│  country       │ ✅     │  15   │    0    │ 100%   │ —        │
│  signup_date   │ ✅     │  15   │    0    │ 100%   │ —        │
└────────────────┴────────┴───────┴─────────┴────────┴──────────┘
```

---

## 8. Stage Pipeline Trace

| Stage | Agent | Status | Time | Bytes | Finding |
|-------|-------|--------|------|-------|---------|
| 1️⃣ Profile | `dq-stage-1-profile` | ✅ PASS | 19.0s | 8.9KB | Identified 3 missing ages, −5 outlier, 150 outlier |
| 2️⃣ Validate | `dq-stage-2-validate` | ✅ PASS | 13.6s | 5.5KB | 5 validation violations (all in `age`) |
| 3️⃣ Anomalies | `dq-stage-3-anomalies` | ✅ PASS | 81.8s | 53.1KB | 3 anomalies: 2 critical (IQR), 1 high (missing) |
| 4️⃣ Enrich | `dq-stage-4-enrich` | ✅ PASS | 20.0s | 9.0KB | 7 enrichment strategies proposed |
| 5️⃣ **Report** | **`dq-stage-5-report`** | **✅ THIS** | — | — | **Final report generated** |

---

## 9. Recommendations for Stakeholders

1. **Do not use `age` in its current state** for any analysis. All 5 affected rows must be remediated first.
2. **Address the root cause:** Add input validation to prevent missing, negative, and extreme age values at the point of data entry. This is a one-time fix that prevents recurrence.
3. **Impute missing ages using the median (34)** — this is the most statistically robust approach for a small dataset. For larger datasets, consider country-stratified imputation.
4. **Retain an `age_imputed` flag** so downstream analysts can perform sensitivity analyses comparing results with and without imputed values.
5. **Normalize `UK` → `GB`** for standard ISO compliance if using geo-enrichment tools.
6. **After remediation, re-score:** Expected DQ Score after fixes → **98/100** (only minor enrichment items remaining).

---

*Report generated by the DQ Pipeline (Stage 5) as part of the Multi-Arch 30-Agent MAS evaluation (R110-27).*
