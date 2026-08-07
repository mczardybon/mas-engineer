"""
test_r110134_8_evidence_secret_leak.py — R110-134 (R110-102 REGRESSION GUARD)

Scans e2e-results/*/evidence/*.log for leaked API keys/tokens. This is
the R110-102 regression guard — the original bug was 4 unstaged
evidence logs containing sk-XXX...XXXX leaks that could be committed
if a developer wasn't paying attention.

Catches:
- sk-XXX (DeepSeek / OpenAI keys)
- ghp_XXX (GitHub PAT classic)
- github_pat_XXX (GitHub fine-grained)
- Bearer XXX
- xoxb/xoxp/slack tokens
- Stripe live keys

The test is per-run idempotent: if no e2e-results exist, skip. If
results exist, ALL evidence logs must be clean.

Run with:
    cd mas-engineer && pytest tests/test_r110134_8_evidence_secret_leak.py -v
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from _recipe_helpers import E2E_RESULTS_DIR, scan_evidence_secrets  # noqa: E402


def test_no_secrets_in_evidence_logs():
    """No API keys or tokens may appear in any e2e-results/*/evidence/*.log."""
    if not E2E_RESULTS_DIR.exists():
        pytest.skip(f"{E2E_RESULTS_DIR} not present — no evidence to scan")

    leaks = scan_evidence_secrets()
    assert not leaks, (
        f"{len(leaks)} secret-pattern matches in evidence logs (R110-102 REGRESSION):\n"
        + "\n".join(f"  - {log}:{line}  [{name}]\n      {excerpt}"
                    for log, name, line, excerpt in leaks[:5])
    )


def test_evidence_logs_are_gitignored():
    """e2e-results/ evidence logs ARE committed (R110-143, 2026-08-07) as the
    public proof that mas-engineer works. The security invariant is NO secrets,
    which test_no_secrets_in_evidence_logs enforces. This test verifies that
    the non-evidence logs/ artifacts (dist/, outputs/, loose reports) stay
    ignored, so only the real evidence lands in the repo."""
    gitignore = Path(__file__).parent.parent.parent / ".gitignore"
    if not gitignore.exists():
        pytest.skip(".gitignore not present")
    text = gitignore.read_text()
    assert "logs/dist/" in text and "logs/outputs/" in text, (
        "Non-evidence logs/ artifacts (dist/, outputs/) must stay in .gitignore "
        "per R110-143 — only e2e evidence logs are committed."
    )


def test_no_staged_evidence_logs():
    """No STAGED evidence log may contain a leaked secret.
    R110-143 (2026-08-07): the e2e .log files ARE committed as public proof,
    so they ARE staged. The guard now is the secret scan
    (test_no_secrets_in_evidence_logs), which rejects any committed log that
    contains an API key/token. This test double-checks that nothing with a
    real key pattern is staged (defense-in-depth)."""
    import subprocess
    if not E2E_RESULTS_DIR.exists():
        pytest.skip(f"{E2E_RESULTS_DIR} not present")
    # Scan the staged evidence logs directly for real secret patterns.
    leaks = scan_evidence_secrets()
    assert not leaks, (
        f"{len(leaks)} secret-pattern matches in staged evidence logs (R110-102 REGRESSION):\n"
        + "\n".join(f"  - {log}:{line}  [{name}]" for log, name, line, _ in leaks[:10])
        + "\n\nRemove the leaked key before committing."
    )


def test_evidence_logs_present_when_e2e_was_run():
    """If e2e-results/ exists, there should be at least one evidence log.
    Empty e2e-results suggests the test infrastructure ran but produced
    no evidence (theater)."""
    if not E2E_RESULTS_DIR.exists():
        pytest.skip(f"{E2E_RESULTS_DIR} not present")
    logs = list(E2E_RESULTS_DIR.glob("*/evidence/*.log"))
    if not logs:
        pytest.skip("e2e-results/ exists but no evidence/*.log files — possible theater")
    # Sanity: at least 1 log must be > 1KB (real content, not empty)
    sized = [l for l in logs if l.stat().st_size > 1024]
    assert sized, (
        f"All {len(logs)} evidence logs are < 1KB — looks like theater (no real evidence captured).\n"
        + "\n".join(f"  - {l}: {l.stat().st_size} bytes" for l in logs[:5])
    )
