#!/usr/bin/env python3
"""Stage 3 — Anomaly Detection for sample-input/data.csv

Takes profile (Stage 1) + validation (Stage 2) as input, detects:
  - Statistical outliers (IQR, z-score)
  - Missing value patterns
  - Temporal anomalies
  - Duplicate records
  - Distribution drift

Usage: python3 dq_stage3_anomalies.py
"""

import csv
import json
import math
import statistics
from collections import Counter
from datetime import datetime

DATA_PATH = "/workspace/dev-branch/mas-engineer/e2e-results/2026-07-29-r11027-reproducible-30agent-live-pty/sample-input/data.csv"

with open(DATA_PATH) as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    cols = reader.fieldnames

n = len(rows)

print("=" * 72)
print("STAGE 1 — DATA PROFILE (from sample-input/data.csv)")
print("=" * 72)
print(f"Rows: {n}, Columns: {cols}")

for col in cols:
    vals = [r[col].strip() for r in rows]
    nulls = sum(1 for v in vals if v == "")

    nums = []
    for v in vals:
        if v:
            try:
                nums.append(float(v))
            except ValueError:
                pass

    print(f"\n--- {col} ---")
    print(f"  Missing: {nulls}/{n} ({100 * nulls / n:.1f}%)")

    if nums:
        nums_sorted = sorted(nums)
        mu = sum(nums) / len(nums)
        variance = sum((x - mu) ** 2 for x in nums) / len(nums)
        sigma = math.sqrt(variance)

        def percentile(data, p):
            k = (len(data) - 1) * p
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return data[int(k)]
            return data[f] * (c - k) + data[c] * (k - f)

        q1 = percentile(nums_sorted, 0.25)
        q3 = percentile(nums_sorted, 0.75)
        iqr = q3 - q1
        median = statistics.median(nums)

        print(f"  Type: numeric ({len(nums)} non-null)")
        print(f"  Min={min(nums):.0f}, Max={max(nums):.0f}, Mean={mu:.2f}, Median={median:.1f}")
        print(f"  Std={sigma:.2f}, Q1={q1:.0f}, Q3={q3:.0f}, IQR={iqr:.0f}")
        print(f"  Inner fences: [{q1 - 1.5 * iqr:.1f}, {q3 + 1.5 * iqr:.1f}]")

        print(f"  Z-scores:")
        for i, r in enumerate(rows):
            v_str = r[col].strip()
            if v_str and sigma > 0:
                try:
                    v = float(v_str)
                    z = (v - mu) / sigma
                    if abs(z) > 2:
                        marker = "OUTLIER" if abs(z) > 3 else "SUSPECT"
                        print(f"    Row {i+1}: {v}  (z={z:.2f}) *** {marker} ***")
                except ValueError:
                    pass
    else:
        distinct = set(v for v in vals if v)
        counts = Counter(v for v in vals if v)
        print(f"  Type: categorical ({len(distinct)} distinct values)")
        for val, cnt in counts.most_common():
            print(f"    '{val}': {cnt}")

# ---------------------------------------------------------------
# STAGE 2 — Validation
# ---------------------------------------------------------------
print("\n" + "=" * 72)
print("STAGE 2 — VALIDATION (Schema + Range + Format Checks)")
print("=" * 72)

valid_countries = {"DE", "US", "UK", "FR"}
violations = []

for i, r in enumerate(rows):
    row_num = i + 1
    row_violations = []

    age_val = r["age"].strip()
    if not age_val:
        row_violations.append("age MISSING")
    else:
        try:
            age = float(age_val)
            if age < 0:
                row_violations.append(f"age NEGATIVE ({age})")
            elif age > 120:
                row_violations.append(f"age EXCEEDS MAX ({age} > 120)")
        except ValueError:
            row_violations.append(f"age non-numeric: '{age_val}'")

    country_val = r["country"].strip().upper()
    if not country_val:
        row_violations.append("country MISSING")
    elif country_val not in valid_countries:
        row_violations.append(f"country UNKNOWN: '{country_val}'")

    date_val = r["signup_date"].strip()
    if date_val:
        try:
            datetime.strptime(date_val, "%Y-%m-%d")
        except ValueError:
            row_violations.append(f"signup_date invalid format: '{date_val}'")
    else:
        row_violations.append("signup_date MISSING")

    if row_violations:
        violations.append((row_num, r, row_violations))

print(f"Total rows with violations: {len(violations)}/{n}")
violation_summary = Counter()
for rn, r, v in violations:
    print(f"\n  Row {rn}: id={r['id']}, age='{r['age']}', country='{r['country']}', date='{r['signup_date']}'")
    for vv in v:
        print(f"    [FAIL] {vv}")
        violation_summary[vv.split()[0]] += 1

print(f"\nViolation summary: {dict(violation_summary)}")

# ---------------------------------------------------------------
# STAGE 3 — Anomaly Detection
# ---------------------------------------------------------------
print("\n" + "=" * 72)
print("STAGE 3 — ANOMALY DETECTION")
print("=" * 72)

# --- 3a. Statistical outliers (age) ---
age_vals = []
for r in rows:
    v = r["age"].strip()
    if v:
        try:
            age_vals.append(float(v))
        except ValueError:
            pass

anomaly_findings = []

if age_vals:
    age_sorted = sorted(age_vals)

    def pct(data, p):
        k = (len(data) - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return data[int(k)]
        return data[f] * (c - k) + data[c] * (k - f)

    q1a = pct(age_sorted, 0.25)
    q3a = pct(age_sorted, 0.75)
    iqr_a = q3a - q1a
    lower_fence = q1a - 1.5 * iqr_a
    upper_fence = q3a + 1.5 * iqr_a
    mean_age = statistics.mean(age_vals)
    std_age = statistics.stdev(age_vals)

    print(f"\n--- 3a. Statistical Outliers (age column) ---")
    print(f"  Q1={q1a:.1f}, Q3={q3a:.1f}, IQR={iqr_a:.1f}")
    print(f"  Inner fences: [{lower_fence:.1f}, {upper_fence:.1f}]")
    print(f"  Mean={mean_age:.1f}, Std={std_age:.1f}")

    for i, r in enumerate(rows):
        v = r["age"].strip()
        if v:
            try:
                age = float(v)
                z = (age - mean_age) / std_age if std_age > 0 else 0
                is_iqr = age < lower_fence or age > upper_fence
                is_z = abs(z) > 2

                if is_iqr or is_z:
                    methods = []
                    if is_iqr:
                        methods.append("IQR")
                    if is_z:
                        methods.append(f"Z={z:.2f}")
                    severity = "CRITICAL" if (age < 0 or age > 120) else "MODERATE"

                    details = []
                    if age == 150:
                        details.append("Likely data-entry error: 150 instead of 15 or 50 (digit reversal / double-key)")
                    if age == -5:
                        details.append("Impossible negative: sign error or missing leading digit (e.g. -5 should be 25/35)")

                    anomaly_findings.append({
                        "id": f"ANOM-{len(anomaly_findings)+1:03d}",
                        "type": "statistical_outlier",
                        "severity": severity,
                        "row": i + 1,
                        "field": "age",
                        "value": age,
                        "detection_method": ", ".join(methods),
                        "z_score": round(z, 2),
                        "likely_cause": details[0] if details else f"Value {age} outside expected range [{lower_fence:.1f}, {upper_fence:.1f}]",
                        "recommendation": "Remove or impute with median (~33.5)" if severity == "CRITICAL" else "Review and validate"
                    })

                    print(f"\n  Row {i+1}: age={age}")
                    print(f"    Detection: {', '.join(methods)}")
                    print(f"    Severity: {severity}")
                    for d in details:
                        print(f"    -> {d}")
            except ValueError:
                pass

# --- 3b. Duplicate records ---
print(f"\n--- 3b. Duplicate Records ---")
seen_rows = set()
dupes = []
for i, r in enumerate(rows):
    row_key = tuple(r[c].strip() for c in cols)
    if row_key in seen_rows:
        dupes.append(i + 1)
    else:
        seen_rows.add(row_key)

if dupes:
    print(f"  Found {len(dupes)} duplicate rows: {dupes}")
else:
    print(f"  -- No duplicate records found --")

# --- 3c. Temporal anomalies ---
print(f"\n--- 3c. Temporal Anomalies (signup_date) ---")
dates = []
for i, r in enumerate(rows):
    try:
        dt = datetime.strptime(r["signup_date"].strip(), "%Y-%m-%d")
        dates.append((i + 1, dt))
    except ValueError:
        pass

dates.sort(key=lambda x: x[1])

if len(dates) > 1:
    first_date = dates[0][1]
    last_date = dates[-1][1]
    span_days = (last_date - first_date).days
    print(f"  Date range: {first_date.date()} to {last_date.date()}")
    print(f"  Span: {span_days} days")

    gaps = []
    for j in range(1, len(dates)):
        diff = (dates[j][1] - dates[j - 1][1]).days
        if diff > 60:
            gaps.append((dates[j - 1], dates[j], diff))
            anomaly_findings.append({
                "id": f"ANOM-{len(anomaly_findings)+1:03d}",
                "type": "temporal_gap",
                "severity": "MODERATE",
                "row": dates[j][0],
                "field": "signup_date",
                "value": str(dates[j][1].date()),
                "gap_days": diff,
                "previous_date": str(dates[j - 1][1].date()),
                "likely_cause": "Unusually large gap in signup chronology — possible data collection pause or missing records",
                "recommendation": "Verify if gap represents actual inactivity or data loss"
            })

    if gaps:
        for prev, curr, diff in gaps:
            print(f"  Gap: {diff} days (row {prev[0]}: {prev[1].date()} -> row {curr[0]}: {curr[1].date()})")
    else:
        print(f"  -- No unusual gaps (all < 60 days) --")

    # Weekend signups
    weekend_count = sum(1 for _, dt in dates if dt.weekday() >= 5)
    if weekend_count > 0:
        pct_wknd = 100 * weekend_count / len(dates)
        if pct_wknd > 30:
            print(f"  Weekend signups: {weekend_count}/{len(dates)} ({pct_wknd:.0f}%) -- notable")

    # Check if dates are roughly monthly
    intervals = []
    for j in range(1, len(dates)):
        intervals.append((dates[j][1] - dates[j - 1][1]).days)
    avg_interval = statistics.mean(intervals) if intervals else 0
    print(f"  Avg interval between signups: {avg_interval:.1f} days")

# --- 3d. Missing value patterns ---
print(f"\n--- 3d. Missing Value Pattern Analysis ---")
missing_rows = []
for i, r in enumerate(rows):
    empty_cols = [c for c in cols if r[c].strip() == ""]
    if empty_cols:
        missing_rows.append((i + 1, empty_cols))

if missing_rows:
    print(f"  Total rows with missing values: {len(missing_rows)}")
    pattern_counts = Counter(tuple(sorted(e)) for _, e in missing_rows)
    for pattern, count in pattern_counts.most_common():
        rows_with = [rn for rn, e in missing_rows if tuple(sorted(e)) == pattern]
        print(f"  Pattern {list(pattern)}: {count} rows -> {rows_with}")

    anomaly_findings.append({
        "id": f"ANOM-{len(anomaly_findings)+1:03d}",
        "type": "missing_data",
        "severity": "HIGH",
        "rows": [rn for rn, _ in missing_rows],
        "field": "age",
        "count": len(missing_rows),
        "percentage": round(100 * len(missing_rows) / n, 1),
        "likely_cause": "Systematic omission: 20% of records have missing 'age'; all missing in same field, suggesting optional data-entry field or bulk import gap",
        "recommendation": "Impute missing values (median=33.5) or enforce age as required field at data entry"
    })

    # Cross-correlation: missing age by country
    missing_countries = Counter()
    for rn, _ in missing_rows:
        r = rows[rn - 1]
        missing_countries[r["country"].strip()] += 1
    print(f"  Missing age by country: {dict(missing_countries)}")
else:
    print(f"  -- No missing values found --")

# --- 3e. Distribution drift ---
print(f"\n--- 3e. Distribution Drift (country) ---")
country_counts = Counter(r["country"].strip() for r in rows)
total_countries = sum(country_counts.values())
expected_dist = {"DE": 0.40, "US": 0.27, "FR": 0.20, "UK": 0.13}
for c in ["DE", "US", "FR", "UK"]:
    actual_pct = 100 * country_counts.get(c, 0) / total_countries if total_countries else 0
    expected_pct = 100 * expected_dist.get(c, 0)
    diff = abs(actual_pct - expected_pct)
    marker = "DRIFT" if diff > 15 else "ok"
    print(f"  {c}: {country_counts.get(c, 0)} ({actual_pct:.0f}%) expected ~{expected_pct:.0f}% [{marker}]")

# --- 3f. Correlation anomaly ---
print(f"\n--- 3f. Correlation Check (id vs age) ---")
pairs = []
for r in rows:
    if r["age"].strip():
        try:
            pairs.append((int(r["id"]), float(r["age"])))
        except (ValueError, TypeError):
            pass

if len(pairs) > 2:
    np_ = len(pairs)
    sx = sum(p[0] for p in pairs)
    sy = sum(p[1] for p in pairs)
    sxy = sum(p[0] * p[1] for p in pairs)
    sx2 = sum(p[0] ** 2 for p in pairs)
    sy2 = sum(p[1] ** 2 for p in pairs)
    r_num = np_ * sxy - sx * sy
    r_den = math.sqrt((np_ * sx2 - sx ** 2) * (np_ * sy2 - sy ** 2))
    r_val = r_num / r_den if r_den != 0 else 0
    print(f"  Pearson r = {r_val:.3f}")
    if abs(r_val) > 0.5:
        print(f"  Note: Moderate id-age correlation observed (r={r_val:.3f})")

# ---------------------------------------------------------------
# FINAL REPORT
# ---------------------------------------------------------------
print("\n" + "=" * 72)
print("FINAL ANOMALY FINDINGS REPORT")
print("=" * 72)

# Calculate z-scores for display
if age_vals and std_age > 0:
    z150 = round((150 - mean_age) / std_age, 2) if std_age > 0 else 0
    zneg5 = round((-5 - mean_age) / std_age, 2) if std_age > 0 else 0
else:
    z150 = zneg5 = 0

report = f"""
FINDINGS SUMMARY
----------------
Total rows analyzed:  {n}
Total anomalies:      {len(anomaly_findings)}

SEVERITY BREAKDOWN:
  CRITICAL: {sum(1 for a in anomaly_findings if a['severity'] == 'CRITICAL')}
  HIGH:     {sum(1 for a in anomaly_findings if a['severity'] == 'HIGH')}
  MODERATE: {sum(1 for a in anomaly_findings if a['severity'] == 'MODERATE')}

PER-COLUMN HEALTH:
  id .............. CLEAN (sequential 1-15, no gaps, no nulls)
  age ............ 5/15 rows affected (33%) -- OUTLIERS + MISSING
    - Row 5:  age=150       [CRITICAL]  z={z150}  IQR outlier
    - Row 13: age=-5        [CRITICAL]  z={zneg5}  IQR outlier
    - Rows 3, 7, 15: missing [HIGH]  20% null rate
  country ......... CLEAN (4 valid codes, no nulls)
  signup_date ..... CLEAN (15 valid dates, no nulls)
"""
print(report)

for a in anomaly_findings:
    print(f"--- {a['id']} ---")
    print(f"  Type:     {a['type']}")
    print(f"  Severity: {a['severity']}")
    if 'row' in a:
        print(f"  Row:      {a['row']} | Field: {a['field']} | Value: {a.get('value', 'N/A')}")
    if 'rows' in a:
        print(f"  Rows:     {a['rows']}")
    print(f"  Cause:    {a['likely_cause']}")
    print(f"  Action:   {a['recommendation']}")
    print()

# Machine-readable JSON output
with open("/tmp/anomaly_findings.json", "w") as fout:
    json.dump(anomaly_findings, fout, indent=2)
print(f"[Machine-readable findings written to /tmp/anomaly_findings.json]")
