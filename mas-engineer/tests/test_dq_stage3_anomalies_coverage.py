"""Targeted coverage push for tools/dq_stage3_anomalies.py — R110-508.

Target: dq_stage3_anomalies.py (478 lines, ~307 stmts, 0% → goal 70%+).

Strategy:
- The module is a procedural SCRIPT (no functions, all module-level).
- Use runpy.run_path() with sys.argv manipulation to execute it.
- Coverage tracks the file via run_path when invoked under coverage.
- Create various test CSVs to exercise different code paths:
  - Normal data (no anomalies)
  - Statistical outliers (age=150, -5)
  - Missing values
  - Temporal gaps (>60 days between signups)
  - Duplicates
  - Distribution drift (>15% delta)
  - Country violations
  - Date format errors
  - Negative/excessive age
"""
import json
import os
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
SCRIPT = TOOLS_DIR / "dq_stage3_anomalies.py"


def _make_csv(tmp_path, rows):
    """Write a CSV with the standard 4 columns (id, age, country, signup_date)."""
    path = tmp_path / "data.csv"
    with open(path, "w") as f:
        f.write("id,age,country,signup_date\n")
        for row in rows:
            f.write(",".join(row) + "\n")
    return path


def _run_stage3(csv_path):
    """Execute the script via runpy with --data flag, capture stdout."""
    saved_argv = sys.argv
    saved_stdout = sys.stdout
    import io
    sys.argv = ["dq_stage3_anomalies.py", "--data", str(csv_path)]
    buf = io.StringIO()
    sys.stdout = buf
    try:
        try:
            runpy.run_path(str(SCRIPT), run_name="__main__")
        except SystemExit:
            pass  # script doesn't call sys.exit, but be safe
    finally:
        sys.stdout = saved_stdout
        sys.argv = saved_argv
    return buf.getvalue()


def _read_findings_json(tmp_path):
    """Read the JSON findings file written to tempfile.gettempdir()."""
    p = Path(tempfile.gettempdir()) / "anomaly_findings.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


# ─────────────────────────────────────────────────────────
# _resolve_data_path() — 5 fallback branches
# ─────────────────────────────────────────────────────────

def test_resolve_data_path_via_cli(tmp_path):
    """--data <explicit-path> returns it as abspath (≥2 numeric ages for stdev)."""
    csv = _make_csv(tmp_path, [
        ("1", "25", "DE", "2024-01-01"),
        ("2", "30", "US", "2024-01-15"),
    ])
    out = _run_stage3(csv)
    assert "STAGE 1" in out
    assert "Rows: 2" in out


def test_resolve_data_path_missing_explicit_raises(tmp_path, monkeypatch, capsys):
    """--data <non-existent> → FileNotFoundError (fail-fast)."""
    import io
    monkeypatch.setattr(sys, "argv", ["dq_stage3_anomalies.py", "--data", "/nonexistent/x.csv"])
    with pytest.raises(FileNotFoundError, match="--data path not found"):
        # Run the resolver function directly (don't need full script)
        sys.path.insert(0, str(TOOLS_DIR))
        import dq_stage3_anomalies as mod
        # Re-trigger resolution by calling the module-level call
        # Easier: just call the function via runpy
        runpy.run_path(str(SCRIPT), run_name="__main__")
    # cleanup
    if str(TOOLS_DIR) in sys.path:
        sys.path.remove(str(TOOLS_DIR))


def test_resolve_data_path_env_fallback(tmp_path, monkeypatch, capsys):
    """DQ_DATA_PATH env var works as fallback when --data absent (≥2 ages for stdev)."""
    csv = _make_csv(tmp_path, [
        ("1", "25", "DE", "2024-01-01"),
        ("2", "30", "US", "2024-01-15"),
    ])
    monkeypatch.setenv("DQ_DATA_PATH", str(csv))
    monkeypatch.setattr(sys, "argv", ["dq_stage3_anomalies.py"])
    # Capture via capsys by redirecting runpy's stdout
    import io
    saved_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    finally:
        captured = sys.stdout.getvalue()
        sys.stdout = saved_stdout
    assert "Rows: 2" in captured


def test_resolve_data_path_relative_fallback(tmp_path, monkeypatch, capsys):
    """No --data, no env, no glob → ./sample-input/data.csv relative fallback."""
    # Create ./sample-input/data.csv in tmp_path and chdir there
    sample_dir = tmp_path / "sample-input"
    sample_dir.mkdir()
    csv = sample_dir / "data.csv"
    csv.write_text("id,age,country,signup_date\n1,25,DE,2024-01-01\n2,30,US,2024-01-15\n")
    monkeypatch.delenv("DQ_DATA_PATH", raising=False)
    monkeypatch.setattr(sys, "argv", ["dq_stage3_anomalies.py"])
    monkeypatch.chdir(tmp_path)
    import io
    saved_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    finally:
        captured = sys.stdout.getvalue()
        sys.stdout = saved_stdout
    assert "Rows: 2" in captured


def test_resolve_data_path_completely_missing(monkeypatch, capsys):
    """No --data, no env, no file → FileNotFoundError at module level."""
    monkeypatch.delenv("DQ_DATA_PATH", raising=False)
    monkeypatch.setattr(sys, "argv", ["dq_stage3_anomalies.py"])
    # No chdir → uses CWD which may have data.csv or not.
    # Force into an empty tmp dir:
    import tempfile
    empty = tempfile.mkdtemp()
    monkeypatch.chdir(empty)
    import io
    saved_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        with pytest.raises(FileNotFoundError, match="data.csv not found"):
            runpy.run_path(str(SCRIPT), run_name="__main__")
    finally:
        sys.stdout = saved_stdout


# ─────────────────────────────────────────────────────────
# Stage 1 — Data Profile
# ─────────────────────────────────────────────────────────

def test_stage1_numeric_column_stats(tmp_path):
    """Numeric columns: min/max/mean/median/std/Q1/Q3/IQR/z-scores printed."""
    csv = _make_csv(tmp_path, [
        ("1", "10", "DE", "2024-01-01"),
        ("2", "20", "DE", "2024-01-15"),
        ("3", "30", "DE", "2024-02-01"),
        ("4", "40", "DE", "2024-02-15"),
        ("5", "50", "DE", "2024-03-01"),
    ])
    out = _run_stage3(csv)
    assert "Min=10" in out
    assert "Max=50" in out
    assert "Mean=30.00" in out
    assert "Std=" in out
    assert "Q1=" in out
    assert "Q3=" in out
    assert "IQR=" in out
    assert "Inner fences:" in out


def test_stage1_categorical_column_stats(tmp_path):
    """Categorical columns: distinct values + Counter output."""
    csv = _make_csv(tmp_path, [
        ("1", "", "DE", "2024-01-01"),     # empty age → not numeric
        ("2", "", "US", "2024-01-15"),
        ("3", "", "UK", "2024-02-01"),
        ("4", "", "UK", "2024-02-15"),
    ])
    out = _run_stage3(csv)
    assert "categorical" in out
    # 'UK' should appear as the most common
    assert "'UK'" in out


def test_stage1_missing_count(tmp_path):
    """Missing values counted + percentage printed."""
    csv = _make_csv(tmp_path, [
        ("1", "", "DE", "2024-01-01"),
        ("2", "25", "DE", "2024-01-15"),
        ("3", "30", "DE", "2024-02-01"),
    ])
    out = _run_stage3(csv)
    # age has 1 missing out of 3 → "Missing: 1/3"
    assert "Missing: 1/3" in out


def test_stage1_z_score_outlier_marker(tmp_path):
    """Z-score > 3 → OUTLIER marker printed; > 2 → SUSPECT."""
    # 10 rows of 32, 1 row of 53 → mean=32.3, std=6.9, z(53)=3.0 → OUTLIER
    csv = _make_csv(tmp_path, [
        ("1", "32", "DE", "2024-01-01"),
        ("2", "32", "DE", "2024-01-02"),
        ("3", "32", "DE", "2024-01-03"),
        ("4", "32", "DE", "2024-01-04"),
        ("5", "32", "DE", "2024-01-05"),
        ("6", "32", "DE", "2024-01-06"),
        ("7", "32", "DE", "2024-01-07"),
        ("8", "32", "DE", "2024-01-08"),
        ("9", "32", "DE", "2024-01-09"),
        ("10", "53", "DE", "2024-01-10"),  # z=3.0 → OUTLIER
    ])
    out = _run_stage3(csv)
    assert "OUTLIER" in out
    # SUSPECT (2 < |z| < 3): 11 spread rows (mean=25.42, std=3.66), +33 → z=2.07 → SUSPECT
    csv2 = _make_csv(tmp_path, [
        ("1",  "20", "DE", "2024-01-01"),
        ("2",  "22", "DE", "2024-01-02"),
        ("3",  "24", "DE", "2024-01-03"),
        ("4",  "26", "DE", "2024-01-04"),
        ("5",  "28", "DE", "2024-01-05"),
        ("6",  "22", "DE", "2024-01-06"),
        ("7",  "24", "DE", "2024-01-07"),
        ("8",  "26", "DE", "2024-01-08"),
        ("9",  "28", "DE", "2024-01-09"),
        ("10", "30", "DE", "2024-01-10"),
        ("11", "22", "DE", "2024-01-11"),
        ("12", "33", "DE", "2024-01-12"),  # z=2.07 → SUSPECT (between 2 and 3)
    ])
    out2 = _run_stage3(csv2)
    assert "SUSPECT" in out2


def test_stage1_z_score_skipped_when_sigma_zero(tmp_path):
    """When all values identical → sigma=0 → z-scores skipped (no crash)."""
    csv = _make_csv(tmp_path, [
        ("1", "30", "DE", "2024-01-01"),
        ("2", "30", "DE", "2024-01-02"),
        ("3", "30", "DE", "2024-01-03"),
    ])
    out = _run_stage3(csv)
    # Should not crash; z-score block simply skips
    assert "Std=0.00" in out


# ─────────────────────────────────────────────────────────
# Stage 2 — Validation
# ─────────────────────────────────────────────────────────

def test_stage2_age_negative_violation(tmp_path):
    """Negative age → 'age NEGATIVE' violation (≥2 numeric ages for stdev)."""
    csv = _make_csv(tmp_path, [
        ("1", "-5", "DE", "2024-01-01"),
        ("2", "25", "DE", "2024-01-15"),
        ("3", "30", "DE", "2024-02-01"),
    ])
    out = _run_stage3(csv)
    assert "age NEGATIVE" in out
    assert "Total rows with violations: 1/3" in out


def test_stage2_age_exceeds_max_violation(tmp_path):
    """Age > 120 → 'age EXCEEDS MAX' violation (≥2 numeric ages for stdev)."""
    csv = _make_csv(tmp_path, [
        ("1", "150", "DE", "2024-01-01"),
        ("2", "25", "DE", "2024-01-15"),
        ("3", "30", "DE", "2024-02-01"),
    ])
    out = _run_stage3(csv)
    assert "age EXCEEDS MAX" in out


def test_stage2_age_missing_violation(tmp_path):
    """Empty age → 'age MISSING' violation (≥2 numeric ages for stdev)."""
    csv = _make_csv(tmp_path, [
        ("1", "", "DE", "2024-01-01"),
        ("2", "25", "DE", "2024-01-15"),
        ("3", "30", "DE", "2024-02-01"),
    ])
    out = _run_stage3(csv)
    assert "age MISSING" in out


def test_stage2_age_non_numeric_violation(tmp_path):
    """Non-numeric age → 'age non-numeric' violation (≥2 numeric ages for stdev)."""
    csv = _make_csv(tmp_path, [
        ("1", "twenty", "DE", "2024-01-01"),
        ("2", "25", "DE", "2024-01-15"),
        ("3", "30", "DE", "2024-02-01"),
    ])
    out = _run_stage3(csv)
    assert "age non-numeric" in out


def test_stage2_country_missing_violation(tmp_path):
    """Empty country → 'country MISSING' violation (≥2 numeric ages for stdev)."""
    csv = _make_csv(tmp_path, [
        ("1", "25", "", "2024-01-01"),
        ("2", "30", "DE", "2024-01-15"),
        ("3", "35", "DE", "2024-02-01"),
    ])
    out = _run_stage3(csv)
    assert "country MISSING" in out


def test_stage2_country_unknown_violation(tmp_path):
    """Country not in {DE,US,UK,FR} → 'country UNKNOWN' violation (≥2 numeric ages)."""
    csv = _make_csv(tmp_path, [
        ("1", "25", "ZZ", "2024-01-01"),
        ("2", "30", "DE", "2024-01-15"),
        ("3", "35", "DE", "2024-02-01"),
    ])
    out = _run_stage3(csv)
    assert "country UNKNOWN" in out


def test_stage2_country_case_insensitive(tmp_path):
    """Country is uppercased before check — 'de' → 'DE' → valid (≥2 numeric ages)."""
    csv = _make_csv(tmp_path, [
        ("1", "25", "de", "2024-01-01"),
        ("2", "30", "us", "2024-01-15"),
        ("3", "35", "uk", "2024-02-01"),
    ])
    out = _run_stage3(csv)
    # Should NOT have 'country UNKNOWN'
    assert "country UNKNOWN" not in out


def test_stage2_date_missing_violation(tmp_path):
    """Empty signup_date → 'signup_date MISSING' (≥2 numeric ages)."""
    csv = _make_csv(tmp_path, [
        ("1", "25", "DE", ""),
        ("2", "30", "DE", "2024-01-15"),
        ("3", "35", "DE", "2024-02-01"),
    ])
    out = _run_stage3(csv)
    assert "signup_date MISSING" in out


def test_stage2_date_invalid_format_violation(tmp_path):
    """Bad date format → 'signup_date invalid format' (≥2 numeric ages)."""
    csv = _make_csv(tmp_path, [
        ("1", "25", "DE", "01.15.2024"),  # US format
        ("2", "30", "DE", "2024-01-15"),
        ("3", "35", "DE", "2024-02-01"),
    ])
    out = _run_stage3(csv)
    assert "signup_date invalid format" in out


def test_stage2_violation_summary_counter(tmp_path):
    """Violation summary aggregates by first word."""
    csv = _make_csv(tmp_path, [
        ("1", "-5", "ZZ", "2024-01-01"),     # age + country violations
        ("2", "150", "ZZ", "2024-01-15"),    # age + country
        ("3", "25", "DE", "2024-02-01"),     # clean
    ])
    out = _run_stage3(csv)
    assert "Violation summary:" in out


# ─────────────────────────────────────────────────────────
# Stage 3a — Statistical Outliers
# ─────────────────────────────────────────────────────────

def test_stage3a_outlier_critical_with_150(tmp_path):
    """age=150 → CRITICAL anomaly with 'Likely data-entry error' cause."""
    csv = _make_csv(tmp_path, [
        ("1", "30", "DE", "2024-01-01"),
        ("2", "30", "DE", "2024-01-15"),
        ("3", "30", "DE", "2024-02-01"),
        ("4", "30", "DE", "2024-02-15"),
        ("5", "30", "DE", "2024-03-01"),
        ("6", "30", "DE", "2024-03-15"),
        ("7", "30", "DE", "2024-04-01"),
        ("8", "30", "DE", "2024-04-15"),
        ("9", "30", "DE", "2024-05-01"),
        ("10", "30", "DE", "2024-05-15"),
        ("11", "150", "DE", "2024-06-01"),
    ])
    findings = _read_findings_json(tmp_path) or _run_and_get_findings(csv)
    # Look for the 150 outlier
    outliers = [f for f in findings if f.get("type") == "statistical_outlier" and f.get("value") == 150.0]
    assert len(outliers) >= 1
    o = outliers[0]
    assert o["severity"] == "CRITICAL"
    assert "data-entry error" in o["likely_cause"]


def _run_and_get_findings(csv_path):
    """Helper: run script + return JSON findings."""
    import tempfile
    out_path = Path(tempfile.gettempdir()) / "anomaly_findings.json"
    if out_path.exists():
        out_path.unlink()
    _run_stage3(csv_path)
    if not out_path.exists():
        return []
    return json.loads(out_path.read_text())


def test_stage3a_outlier_negative_age(tmp_path):
    """age=-5 → CRITICAL anomaly with 'Impossible negative' cause."""
    csv = _make_csv(tmp_path, [
        ("1", "30", "DE", "2024-01-01"),
        ("2", "30", "DE", "2024-01-15"),
        ("3", "30", "DE", "2024-02-01"),
        ("4", "30", "DE", "2024-02-15"),
        ("5", "30", "DE", "2024-03-01"),
        ("6", "-5", "DE", "2024-03-15"),
    ])
    findings = _run_and_get_findings(csv)
    neg = [f for f in findings if f.get("value") == -5.0]
    assert len(neg) >= 1
    assert "Impossible negative" in neg[0]["likely_cause"]


def test_stage3a_outlier_moderate(tmp_path):
    """Non-extreme outlier (>120) → CRITICAL; (>fence, <120) → MODERATE."""
    # 11 rows of 30, 1 row of 110 (>fence but <120)
    csv = _make_csv(tmp_path, [
        (str(i+1), "30", "DE", f"2024-01-{i+1:02d}") for i in range(10)
    ] + [("11", "110", "DE", "2024-04-01")])
    findings = _run_and_get_findings(csv)
    outliers = [f for f in findings if f.get("type") == "statistical_outlier"]
    assert any(o["severity"] == "MODERATE" for o in outliers)


def test_stage3a_no_outliers(tmp_path):
    """All ages within range → no statistical_outlier findings."""
    csv = _make_csv(tmp_path, [
        (str(i+1), "30", "DE", f"2024-01-{i+1:02d}") for i in range(10)
    ])
    findings = _run_and_get_findings(csv)
    assert not any(f.get("type") == "statistical_outlier" for f in findings)


def test_stage3a_std_zero_no_anomaly(tmp_path):
    """std_age=0 (all same) → no outliers, no division-by-zero."""
    csv = _make_csv(tmp_path, [
        ("1", "30", "DE", "2024-01-01"),
        ("2", "30", "DE", "2024-01-02"),
        ("3", "30", "DE", "2024-01-03"),
    ])
    # Should not crash even though std=0
    findings = _run_and_get_findings(csv)
    # No statistical_outlier findings (because is_z requires abs(z) > 2, z=0)
    stat = [f for f in findings if f.get("type") == "statistical_outlier"]
    assert stat == []


# ─────────────────────────────────────────────────────────
# Stage 3b — Duplicates
# ─────────────────────────────────────────────────────────

def test_stage3b_no_duplicates(tmp_path):
    """All unique rows → 'No duplicate records found'."""
    csv = _make_csv(tmp_path, [
        ("1", "25", "DE", "2024-01-01"),
        ("2", "30", "US", "2024-01-15"),
    ])
    out = _run_stage3(csv)
    assert "No duplicate records found" in out


def test_stage3b_duplicates_found(tmp_path):
    """Duplicate rows → listed in output (≥3 numeric ages for stdev)."""
    csv = _make_csv(tmp_path, [
        ("1", "25", "DE", "2024-01-01"),
        ("1", "25", "DE", "2024-01-01"),  # exact dup of row 1 (incl. id)
        ("2", "30", "US", "2024-01-15"),
        ("3", "35", "UK", "2024-02-01"),
    ])
    out = _run_stage3(csv)
    assert "Found 1 duplicate rows" in out
    assert "[2]" in out


# ─────────────────────────────────────────────────────────
# Stage 3c — Temporal Anomalies
# ─────────────────────────────────────────────────────────

def test_stage3c_temporal_gap(tmp_path):
    """Gap > 60 days between consecutive dates → anomaly finding."""
    csv = _make_csv(tmp_path, [
        ("1", "25", "DE", "2024-01-01"),
        ("2", "30", "DE", "2024-01-15"),
        ("3", "35", "DE", "2024-06-01"),  # >60 day gap
    ])
    findings = _run_and_get_findings(csv)
    gaps = [f for f in findings if f.get("type") == "temporal_gap"]
    assert len(gaps) == 1
    assert gaps[0]["gap_days"] >= 60


def test_stage3c_no_gaps(tmp_path):
    """All dates within 60 days → no temporal_gap anomaly."""
    csv = _make_csv(tmp_path, [
        ("1", "25", "DE", "2024-01-01"),
        ("2", "30", "DE", "2024-01-15"),
        ("3", "35", "DE", "2024-02-01"),
    ])
    findings = _run_and_get_findings(csv)
    assert not any(f.get("type") == "temporal_gap" for f in findings)
    out = _run_stage3(csv)
    assert "No unusual gaps" in out


def test_stage3c_weekend_signups_high_pct(tmp_path):
    """Weekend signup >30% → 'notable' printed."""
    # All dates on Sat (weekday=5)
    csv = _make_csv(tmp_path, [
        ("1", "25", "DE", "2024-01-06"),  # Saturday
        ("2", "30", "DE", "2024-01-13"),  # Saturday
        ("3", "35", "DE", "2024-01-20"),  # Saturday
    ])
    out = _run_stage3(csv)
    assert "Weekend signups" in out
    assert "notable" in out


def test_stage3c_single_date_no_interval(tmp_path):
    """Only one valid date → no interval computation (no crash)."""
    csv = _make_csv(tmp_path, [
        ("1", "25", "DE", "2024-01-01"),
        ("2", "30", "DE", "bad-date"),  # invalid → skipped
    ])
    out = _run_stage3(csv)
    # Should not crash
    assert "Date range" in out or "--- 3c" in out


# ─────────────────────────────────────────────────────────
# Stage 3d — Missing Value Patterns
# ─────────────────────────────────────────────────────────

def test_stage3d_missing_data_finding(tmp_path):
    """Missing values → HIGH anomaly with pattern analysis."""
    csv = _make_csv(tmp_path, [
        ("1", "", "DE", "2024-01-01"),
        ("2", "25", "DE", "2024-01-15"),
        ("3", "", "DE", "2024-02-01"),
        ("4", "30", "DE", "2024-02-15"),
        ("5", "35", "DE", "2024-03-01"),
    ])
    findings = _run_and_get_findings(csv)
    missing = [f for f in findings if f.get("type") == "missing_data"]
    assert len(missing) >= 1
    assert missing[0]["severity"] == "HIGH"


def test_stage3d_no_missing(tmp_path):
    """No missing values → 'No missing values found'."""
    csv = _make_csv(tmp_path, [
        ("1", "25", "DE", "2024-01-01"),
        ("2", "30", "US", "2024-01-15"),
    ])
    out = _run_stage3(csv)
    assert "No missing values found" in out


# ─────────────────────────────────────────────────────────
# Stage 3e — Distribution Drift
# ─────────────────────────────────────────────────────────

def test_stage3e_distribution_drift(tmp_path):
    """Country distribution drift (>15% delta) → DRIFT marker."""
    # 100% DE, 0% others → drift for US/FR/UK
    csv = _make_csv(tmp_path, [
        ("1", "25", "DE", "2024-01-01"),
        ("2", "30", "DE", "2024-01-15"),
        ("3", "35", "DE", "2024-02-01"),
        ("4", "40", "DE", "2024-02-15"),
    ])
    out = _run_stage3(csv)
    assert "DRIFT" in out


# ─────────────────────────────────────────────────────────
# Stage 3f — Correlation
# ─────────────────────────────────────────────────────────

def test_stage3f_correlation_high(tmp_path):
    """|r| > 0.5 → 'Moderate id-age correlation observed'."""
    # id=1,age=1; id=2,age=2; ... perfect correlation
    csv = _make_csv(tmp_path, [
        (str(i), str(i), "DE", f"2024-01-{i+1:02d}") for i in range(1, 11)
    ])
    out = _run_stage3(csv)
    assert "Pearson r" in out


def test_stage3f_correlation_too_few(tmp_path):
    """<3 pairs → skip correlation (no crash)."""
    csv = _make_csv(tmp_path, [
        ("1", "25", "DE", "2024-01-01"),
        ("2", "30", "US", "2024-01-15"),
    ])
    out = _run_stage3(csv)
    # Should still print "--- 3f. Correlation Check ---" but skip the r calc
    assert "Correlation Check" in out


# ─────────────────────────────────────────────────────────
# Final Report + JSON output
# ─────────────────────────────────────────────────────────

def test_final_report_printed(tmp_path):
    """Final report with severity breakdown printed."""
    csv = _make_csv(tmp_path, [
        ("1", "150", "DE", "2024-01-01"),  # outlier
        ("2", "25", "DE", "2024-01-15"),
        ("3", "", "DE", "2024-02-01"),     # missing
    ])
    out = _run_stage3(csv)
    assert "FINAL ANOMALY FINDINGS REPORT" in out
    assert "SEVERITY BREAKDOWN" in out
    assert "PER-COLUMN HEALTH" in out


def test_anomaly_findings_json_written(tmp_path):
    """anomaly_findings.json written to tempfile.gettempdir()."""
    csv = _make_csv(tmp_path, [
        ("1", "150", "DE", "2024-01-01"),
        ("2", "25", "DE", "2024-01-15"),
    ])
    # Clean any pre-existing file
    import tempfile
    out_path = Path(tempfile.gettempdir()) / "anomaly_findings.json"
    if out_path.exists():
        out_path.unlink()
    out = _run_stage3(csv)
    assert "Machine-readable findings written" in out
    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert isinstance(data, list)


def test_anomaly_finding_structure(tmp_path):
    """Each anomaly finding has the expected keys."""
    csv = _make_csv(tmp_path, [
        ("1", "150", "DE", "2024-01-01"),
        ("2", "30", "DE", "2024-01-15"),
        ("3", "30", "DE", "2024-02-01"),
    ])
    findings = _run_and_get_findings(csv)
    for f in findings:
        assert "id" in f
        assert "type" in f
        assert "severity" in f
        assert "likely_cause" in f
        assert "recommendation" in f


def test_clean_data_no_anomalies(tmp_path):
    """Clean dataset → no anomaly findings (all 4 fields valid)."""
    csv = _make_csv(tmp_path, [
        ("1", "25", "DE", "2024-01-01"),
        ("2", "30", "US", "2024-01-15"),
        ("3", "35", "FR", "2024-02-01"),
        ("4", "40", "UK", "2024-02-15"),
        ("5", "45", "DE", "2024-03-01"),
    ])
    findings = _run_and_get_findings(csv)
    assert findings == []
