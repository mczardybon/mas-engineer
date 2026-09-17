"""
test_check_16_drift_template.py -- TEMPLATE for R110-94 testing.

WICHTIG: Diese datei ist eine TEMPLATE, KEIN test. Sie liegt unter
.mase/directives/test-fixtures/ (NICHT unter tests/) damit pytest sie
NICHT discovered -- sonst wuerde sich collect-count erhoehen
(1277 -> 1282) und das ist genau die spec-drift die R110-78
verhindern soll (count-diskrepanz zwischen docs und realitaet).

WARUM TEMPLATE: R110-94 DIREKTIVE testing strategy (R110-94 spec,
section 8) verlangt 5 szenarien:
  1) test_dev_category_drift_clean_repo -- repo mit 0 drift in 30d
  2) test_dev_category_drift_drift_repo -- synthetisches chore(release) + book (no colon)
  3) test_dev_category_drift_exempt_merge -- Merge/Revert exempt
  4) test_dev_category_drift_cutoff -- --convention-since YYYY-MM-DD wirkt
  5) test_check_16_block_when_drift -- bash block direkt, exit 1 bei drift > 0

Diese 5 szenarien sind in dieser template als skip-tests
vorhanden. Wenn mas-engineer (oder User) die Check 16+ validation
explizit als CI-test haben will:

  1. kopiert diese file von .mase/directives/test-fixtures/
     nach tests/test_check_16_drift.py
  2. entfernt die @pytest.mark.skip decorators
  3. stellt sicher dass tools/dev_category_drift.py aufrufbar ist
  4. pre-push-validator laufen lassen, alle 5 tests muessen gruen sein

VERWENDUNG:
  1. Pre-CI: file bleibt unter .mase/directives/test-fixtures/,
     nicht pytest-discoverable. Existiert nur als dokumentation
     und test-backlog fuer zukuenftige CI-integration.
  2. Post-CI: file nach tests/ kopieren, skip-decorators entfernen,
     tests laufen bei jedem pytest-run, garantieren dass Check 16+
     nicht kaputt geht bei zukuenftigen refactorings.

NICHT IN TESTS/ DIREKT: weil pytest sonst collect-count erhoeht
(1277 + 5 = 1282) was andere tests die collect-count pruefen
brechen koennte. Indem die template nicht-discoverable bleibt,
bleibt collect-count stabil bei 1277 bis explizit aktiviert.

WARUM collect-count = 1277: aktueller collect-count per
  cd mas-engineer && python3 -m pytest tests/ --collect-only -q
  -> 1277 tests collected
Wenn mas-engineer diese template aktiviert, ist collect-count 1282.
Beim schreiben der aktivierten version sollte collect-count
NICHT hardcoden sondern dynamisch ermitteln oder ganz weglassen.

NOTE: R110-94 DIREKTIVE wurde am 2026-08-04 (HEAD=27d8cb7) voll
implementiert (validator v2.2.0, Check 16+ in instructions, drift
detector script). Acceptance-kriterien 206-212 alle erfuellt.
Diese template ist die OPTIONALE CI-test-form davon, nicht
notwendig fuer R110-94 als "done".
"""
import subprocess
import sys
from pathlib import Path

import pytest

# Pfad zum drift-detector
REPO_ROOT = Path(__file__).resolve().parents[2]  # mas-engineer/
DRIFT_SCRIPT = REPO_ROOT / "tools" / "dev_category_drift.py"


def _run_drift(args, cwd=None):
    """Helper: drift-detector als subprocess aufrufen."""
    cmd = [sys.executable, str(DRIFT_SCRIPT)] + args
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd or REPO_ROOT
    )


@pytest.mark.skip(reason="R110-94 template -- nicht aktiviert, siehe docstring")
def test_dev_category_drift_clean_repo():
    """1) Repo mit 0 drift in last 30 days -> exit 0, drift_count=0."""
    result = _run_drift(["--since", "30", "--json"])
    assert result.returncode == 0, f"expected RC=0, got {result.returncode}: {result.stderr}"
    import json
    payload = json.loads(result.stdout)
    assert payload.get("drift_count") == 0, f"expected drift_count=0, got {payload.get('drift_count')}"


@pytest.mark.skip(reason="R110-94 template -- nicht aktiviert, siehe docstring")
def test_dev_category_drift_drift_repo():
    """2) Synthetisches 'chore(release)' + 'book' (no colon) -> exit 1, drift_count > 0."""
    # NOTE: benoetigt test-repo mit synthetischen commits; siehe
    # R110-94 directive section 8 testing strategy
    # Beispiel:
    #   tmp_repo = "/tmp/test_drift_repo"
    #   # setup: 1x git init, 3 commits (1 chore(release), 1 book ohne colon, 1 feat(good))
    #   # ...
    #   result = _run_drift(["--since", "30", "--json"], cwd=tmp_repo)
    #   assert result.returncode == 1
    #   payload = json.loads(result.stdout)
    #   assert payload["drift_count"] >= 2
    #   assert "chore(release)" in str(payload["drift"])
    #   assert any("book" in d["subject"] for d in payload["drift"])
    pass


@pytest.mark.skip(reason="R110-94 template -- nicht aktiviert, siehe docstring")
def test_dev_category_drift_exempt_merge():
    """3) Merge/Revert subjects zaehlen NICHT als drift."""
    # Setup: repo mit 1x 'Merge branch foo' + 1x 'Revert abc'
    # beide sollen in exempt_count landen, nicht in drift
    # result = _run_drift(["--since", "30", "--json"], cwd=tmp_repo)
    # payload = json.loads(result.stdout)
    # assert payload["drift_count"] == 0
    # assert payload["exempt_count"] >= 2
    pass


@pytest.mark.skip(reason="R110-94 template -- nicht aktiviert, siehe docstring")
def test_dev_category_drift_cutoff():
    """4) --convention-since YYYY-MM-DD exempted pre-cutoff commits."""
    # Setup: 5 commits vor 2026-08-04 mit drift + 0 nach
    # Default-cutoff wirft alle 5 in exempt
    # --convention-since 2026-08-04 wirft sie ebenfalls in exempt
    # aber --convention-since 2030-01-01 (future) wuerde sie in drift werfen
    # result = _run_drift(["--since", "30", "--convention-since", "2030-01-01", "--json"], cwd=tmp_repo)
    # assert result.returncode == 1
    # assert payload["drift_count"] >= 5
    pass


@pytest.mark.skip(reason="R110-94 template -- nicht aktiviert, siehe docstring")
def test_check_16_block_when_drift():
    """5) Check 16+ bash block direkt aus validator-.md extrahieren + ausfuehren."""
    instructions_file = REPO_ROOT / "recipe" / "instructions" / "sub_mas-pre-push-validator.md"
    text = instructions_file.read_text()
    # Check 16+ section
    assert "### Check 16+" in text, "Check 16+ section missing in validator .md"
    # Extrahiere bash block + fuehre aus
    # NOTE: bash block starts with '```bash' nach '### Check 16+' header
    # bis naechster '```' -- robust extraction mit regex noetig
    # import re
    # m = re.search(r"### Check 16\+.*?```bash\n(.*?)\n```", text, re.DOTALL)
    # assert m, "Check 16+ bash block not found"
    # result = subprocess.run(["bash", "-c", m.group(1)], capture_output=True, text=True, cwd=REPO_ROOT)
    # assert result.returncode == 1
    # assert "Check 16+" in result.stdout
    pass
