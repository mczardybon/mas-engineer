"""R110-177 PHASE 6 tests: general-improver STEP 2.7 interactive wontfix
prompt + reason validation + in-run exclusion.

Spec: .mase/directives/R110-177-im-pipeline-issue-db.md PHASE 6.4 (6 tests).
The prompt-parsing logic mirrors the recipe's STEP 2.7 procedure and
uses `dev_issue_db.validate_wontfix_reason()` for validation.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from dev_issue_db import (  # noqa: E402
    IssueDB,
    compute_issue_hash,
    validate_wontfix_reason,
)


def _mk_issue(db, ftype, file, pat):
    h = compute_issue_hash(file, ftype, pat)
    db.register(hash=h, type=ftype, severity="medium", file=file,
                structural_pattern=pat, issue_summary=f"{ftype} issue",
                fix_summary="fix", instance={})
    return h


def parse_wontfix_response(response):
    """Mirror of recipe STEP 2.7 parsing.

    Returns (pairs, skipped): list of (hash, reason) to mark, and a flag
    for invalid entries the user must re-prompt.
    """
    if not response or response.strip().lower() in ("no", ""):
        return [], False
    if response.strip().lower() == "all":
        return [], False  # list all, let user pick individually
    pairs = []
    invalid = False
    for chunk in response.split(","):
        chunk = chunk.strip()
        if not chunk:
            invalid = True
            continue
        # last token is the reason (may contain no commas per format)
        parts = chunk.split(None, 1)
        if len(parts) < 2:
            invalid = True
            continue
        h, reason = parts
        if validate_wontfix_reason(reason) is not None:
            invalid = True
            continue
        pairs.append((h, reason))
    return pairs, invalid


# ---------- 1. 'no' -> skip ----------

def test_wontfix_prompt_skipped_with_no_response(tmp_path):
    db = IssueDB(str(tmp_path / "issue_db.json"))
    h = _mk_issue(db, "K1", "recipe/sub/a.yaml", "k1:1-5")
    db.save()
    pairs, invalid = parse_wontfix_response("no")
    assert pairs == [] and invalid is False
    for hh, reason in pairs:
        db.mark_wontfix(hh, reason)
    db.save()
    assert IssueDB(str(tmp_path / "issue_db.json")).get(h)["status"] == "open"


# ---------- 2. single mark ----------

def test_wontfix_prompt_marks_single(tmp_path):
    db = IssueDB(str(tmp_path / "issue_db.json"))
    h = _mk_issue(db, "K1", "recipe/sub/a.yaml", "k1:1-5")
    db.save()
    pairs, invalid = parse_wontfix_response(
        f"{h} not applicable for this single-purpose recipe")
    assert invalid is False and len(pairs) == 1
    for hh, reason in pairs:
        db.mark_wontfix(hh, reason)
    db.save()
    issue = IssueDB(str(tmp_path / "issue_db.json")).get(h)
    assert issue["status"] == "wontfix"
    assert issue["wontfix_reason"] == "not applicable for this single-purpose recipe"


# ---------- 3. empty reason -> re-prompt ----------

def test_wontfix_prompt_rejects_empty_reason(tmp_path):
    db = IssueDB(str(tmp_path / "issue_db.json"))
    h = _mk_issue(db, "K1", "recipe/sub/a.yaml", "k1:1-5")
    db.save()
    pairs, invalid = parse_wontfix_response(f"{h} ")
    assert invalid is True, "empty reason must trigger re-prompt"


# ---------- 4. short reason -> re-prompt ----------

def test_wontfix_prompt_rejects_short_reason(tmp_path):
    db = IssueDB(str(tmp_path / "issue_db.json"))
    h = _mk_issue(db, "K1", "recipe/sub/a.yaml", "k1:1-5")
    db.save()
    pairs, invalid = parse_wontfix_response(f"{h} no")
    assert invalid is True, "short reason must trigger re-prompt"


# ---------- 5. multiple pairs ----------

def test_wontfix_prompt_marks_multiple(tmp_path):
    db = IssueDB(str(tmp_path / "issue_db.json"))
    h1 = _mk_issue(db, "K1", "recipe/sub/a.yaml", "k1:1-5")
    h2 = _mk_issue(db, "K3", "recipe/sub/b.yaml", "k3:1-5")
    h3 = _mk_issue(db, "NN1", "recipe/sub/c.yaml", "nn1:1-5")
    db.save()
    response = (
        f"{h1} not applicable for single-purpose recipe, "
        f"{h2} covered by external linter rule X, "
        f"{h3} superseded by upcoming refactor"
    )
    pairs, invalid = parse_wontfix_response(response)
    assert invalid is False and len(pairs) == 3
    for hh, reason in pairs:
        db.mark_wontfix(hh, reason)
    db.save()
    db2 = IssueDB(str(tmp_path / "issue_db.json"))
    assert db2.get(h1)["status"] == "wontfix"
    assert db2.get(h2)["status"] == "wontfix"
    assert db2.get(h3)["status"] == "wontfix"


# ---------- 6. in-run exclusion ----------

def test_wontfix_excludes_from_this_run(tmp_path):
    db = IssueDB(str(tmp_path / "issue_db.json"))
    h1 = _mk_issue(db, "K1", "recipe/sub/a.yaml", "k1:1-5")
    h2 = _mk_issue(db, "K3", "recipe/sub/b.yaml", "k3:1-5")
    db.save()
    pairs, invalid = parse_wontfix_response(
        f"{h1} not applicable for this single-purpose recipe")
    assert invalid is False and len(pairs) == 1
    wontfix_hashes = {hh for hh, _ in pairs}
    # STEP 3 input (ranked findings for this run)
    findings = [
        {"id": "F-001", "type": "K1", "issue_hash": h1},
        {"id": "F-002", "type": "K3", "issue_hash": h2},
    ]
    step3_input = [f for f in findings if f["issue_hash"] not in wontfix_hashes]
    assert [f["id"] for f in step3_input] == ["F-002"], \
        "marked-wontfix issues must be excluded from this run's STEP 3"
