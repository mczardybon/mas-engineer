# R110-326 Evidence — dev_workspace latent-bug fixes

## 1. Why

R110-321 (d56ec64) picked tools/dev_workspace.py (1445 stmts)
as candidate #2 from the R-sprint cov-push queue:
  im_finder_scan(1660), workspace(1445), template_gen(901),
  dashboard(566).
R110-326 took dev_workspace.py and probed the testable
(non-# pragma: no cover) functions for latent bugs. Two
real bugs found and fixed. This EVIDENCE.md closes the
evidence gap per the R110-316/318/319/323 pattern.

R-sprint pattern is now: every code-fix R-commit (🔧) gets
paired with an evidence-closure R-commit (📝) that documents
the bug(s), the fix, the regression tests, and the pre-push
gate results. This is a 2-layer defense: (1) the code-fix
itself + the regression tests lock the bug in; (2) this
EVIDENCE.md creates a discoverable artifact for future
readers who hit a related issue.

## 2. Refs (the loop R110-326 closes)

- R110-321 (d56ec64) — R-sprint candidate list picking R110-326.
  The list was: im_finder_scan(1660), workspace(1445),
  template_generator(901), dashboard_data(566). R110-323
  took item #1, R110-326 took item #2.
- R110-325 (4f83886) — SOT cleanup (parent). Moved 4
  R-evidence files from anti-SOT (mas-engineer/logs/) to
  SOT (logs/, REPO-ROOT). This EVIDENCE.md is written
  directly to the SOT location.
- R110-323 (53a6144) — the R-sprint pattern R110-326
  follows (BUG-1 + BUG-2 in dev_im_finder_scan).
- R110-322 (7247571) — the R-sprint before that.
- R110-320 (e7ef060) — the R-sprint pattern origin.
- R110-311 — sitecustomize.py: auto-instrument subprocesses
  for coverage when COVERAGE_PROCESS_START is set. R110-326
  uses in-process import (no subprocess) because the testable
  functions are pure-Python with no GOOSE dependencies.
- R110-310 — subprocess-cov pattern. R110-326 inherits
  the test-design philosophy but uses in-process for speed
  (subprocess test takes ~3s for setup + JSON parse,
  in-process is ~0.08s).
- R110-305 — 4-round `git diff --numstat` re-verify
  protocol. R110-326 used this in section 3 below.
- R110-257 (7e74f4e) — SOT bulk-move + 4 prevention layers.
  R110-326 follows the SOT rule (this EVIDENCE.md is at
  REPO-ROOT, not mas-engineer/logs/).
- R110-114 — the 1,961-findings descriptive-prose lesson.
  BUG-A's empty-description fallback follows the same
  spirit: user input that looks empty should be handled
  gracefully, not crash.

## 3. Pre-push gate (R110-326 commit 360b526)

- Secrets: 0 in staged diff (grep -cE `sk-[a-f0-9]{30,}|ghp_...` = 0)
- 4 rounds `git diff --numstat` re-verify (R110-305):
    ROUND 1: 2 files / +309 / -27
    ROUND 2: 2 files / +309 / -27  (stable)
    ROUND 3: 2 files / +309 / -27  (stable)
    ROUND 4: 2 files / +309 / -27  (stable)
  Per-file:
    M mas-engineer/tools/dev_workspace.py                    +60 / -27
    A mas-engineer/tests/test_r110324_workspace_bug_fixes.py +249 (NEW)
- `git diff --check` clean (no trailing whitespace, no merge markers)
- Branch: mas-t-tests (R110-269 branch-lock)
- Push: via credential-helper, NO `https://${GH_PAT}@...` (R110-281)
- Pushed commit: 360b526 (parent: 4f83886 R110-325)

## 4. Body-claim-drift audit (R110-305 protocol)

The R110-322 commit had a body-claim-drift bug. R110-305
protocol was applied: 4 rounds of `git diff --cached
--numstat` re-verify before commit. This R110-326 commit's
numbers were stable from draft through final, no correction
needed.

Specifically checked claims:
  - "2 files changed, 309 insertions(+), 27 deletions(-)" →
    real 2/309/27 ✓ (4/4 rounds)
  - "+60/-27 on tools/dev_workspace.py" → real +60/-27 ✓
  - "+249 (NEW) on test_r110324_workspace_bug_fixes.py" →
    real +249 ✓
  - "0 secrets" → `git diff --cached | grep -cE` returned 0 ✓
  - "9/9 R110-326 tests PASS" → pytest tests/test_r110324
    -q returns 9/9 ✓
  - "127/127 cross-sprint workspace tests PASS" → pytest
    tests/ -k "workspace" returns 127 passed ✓
  - "12/12 SOT tests PASS" → pytest tests/test_dev_evidence_sot
    -q returns 12/12 ✓
  - "Pushed commit: 360b526" → git log --oneline -1 ✓
  - "parent: 4f83886" → git log --oneline -2 ✓

## 5. Cov delta

In-process test pattern (R110-310 lesson) means cov tracking
works without the subprocess dance. R110-326 functions
tested:
  - _ask_description (5 tests): covered both branches
    (empty desc, non-empty desc), EOF, KeyboardInterrupt
  - _generate_agent (4 tests): covered framework minimum-YAML
    generation, malicious description sanitization, emoji
    preservation, overwrite-prompt path

Cov delta for these functions: from 0% (no tests) to ~85%
(line coverage including the new BUG-B fix code).

But the tool as a whole (1445 stmts, most # pragma: no cover
because they touch real GOOSE paths) is still ~0%. The
R110-326 goal is "lock in the 2 latent-bug fixes", not
"100% cov". The 9 regression tests serve as the regression
lock for BUG-A and BUG-B.

The 2nd R-sprint candidate from R110-321
(template_generator.py, 901 stmts) is next, per the queue.
If template_gen has similar latent bugs, the same pattern
applies.

## 6. Test pattern (in-process + monkeypatch)

Each test in test_r110324_workspace_bug_fixes.py:
  1. Imports dev_workspace.py directly (sys.path.insert +
     import). Faster than subprocess.run (~0.08s vs ~3s).
  2. For _ask_description tests: mocks builtin input() via
     monkeypatch.setattr('builtins.input', lambda _: next(inputs))
     and uses an iterator for sequential inputs.
  3. For _generate_agent tests: passes a tmp_path as workspace
     and asserts on the generated file's content using
     yaml.safe_load (also confirms the fix works for the
     YAML-injection case).
  4. No GOOSE environment needed (functions are pure-Python).

This pattern is similar to R110-310's dev_spec_invariant
subprocess tests but FASTER (in-process) and MORE PRECISE
(function-scoped mocks vs subprocess stdout parsing). The
R110-326 test file's docstring explicitly calls out this
distinction so future maintainers know when to use which
pattern.

## 7. R-sprint summary (R110-320 → R110-321 → R110-322 → R110-323 → R110-325 → R110-326)

- R110-320 (e7ef060): 🔧 code-fix (registry merge empty
  findings) + 5 tests. First R-sprint of the new pattern.
- R110-321 (d56ec64): 📝 R-sprint candidate list documentation.
- R110-322 (7247571): 🔧 code-fix (spec invariant scalar yaml
  top-level drop) + 8 tests.
- R110-322-EVIDENCE (2a8842f): 📝 evidence closure for R110-322.
- R110-323 (53a6144): 🔧 code-fix (im_finder_scan BUG-1 + BUG-2)
  + 6 tests.
- R110-323-EVIDENCE (96b9660): 📝 evidence closure for R110-323.
- R110-325 (4f83886): 🔧 SOT cleanup (4 renames, 0 content).
  Not an R-sprint code-fix per se, but a maintenance commit
  to bring the working tree back into SOT compliance.
- R110-326 (360b526, this commit's parent): 🔧 code-fix
  (dev_workspace BUG-A + BUG-B) + 9 tests.
- R110-326-EVIDENCE (this file): 📝 evidence closure for
  R110-326. Located at CORRECT SOT (logs/e2e-evidence-gen2/
  REPO-ROOT), per R110-325 cleanup.
- R110-327+ (next): candidates #3 and #4 from the R110-321
  list (template_generator.py 901 stmts, dashboard_data.py
  566 stmts).

## 8. R110-326 bug details

### BUG-A: _ask_description() references undefined `name`

LOCATION: tools/dev_workspace.py, line 823 (original)

BEFORE (buggy):
    def _ask_description():
        """Interaktive query from Description und Emoji."""
        print()
        try:
            desc = input("  Description (z.B. 'Database-Cleanup'): ").strip()
            emoji = input("  Emoji (z.B. 🛡️, 🧪, 🖥️): ").strip() or "🤖"
        except (EOFError, KeyboardInterrupt):
            print("\n  ❌ Abgebrochen")
            return None, None
        return desc or name.replace("-", " ").title(), emoji  # ← `name` UNDEFINED

The `name` variable is not in scope. The function
references it in the empty-description fallback branch.

AFTER (fixed):
    def _ask_description(name):  # ← explicit parameter
        """Interaktive query from Description und Emoji.

        `name` is the agent name (already validated). When the
        user enters an empty description, we fall back to a
        human-friendly form of `name`. R110-326-BUG-A.
        """
        print()
        try:
            desc = input("  Description (z.B. 'Database-Cleanup'): ").strip()
            emoji = input("  Emoji (z.B. 🛡️, 🧪, 🖥️): ").strip() or "🤖"
        except (EOFError, KeyboardInterrupt):
            print("\n  ❌ Abgebrochen")
            return None, None
        return desc or name.replace("-", " ").title(), emoji

Caller update (line 1286):
    BEFORE: desc, emoji = _ask_description()
    AFTER:  desc, emoji = _ask_description(name)  # R110-326-BUG-A: pass name explicitly

Regression test: test_empty_description_no_longer_raises_NameError
  - Mocks input() to return ["", "🛡️"] (empty desc, valid emoji)
  - Calls dev_workspace._ask_description(name="my-cool-agent")
  - Asserts result == ("My Cool Agent", "🛡️")
  - This test FAILS with `NameError: name 'name' is not defined`
    without the fix.
  - This test PASSES with the fix.

Sanity tests (4):
  - test_nonempty_description_is_returned_as_is (no regression)
  - test_default_emoji_when_user_skips (no regression)
  - test_EOF_returns_None (no regression)
  - test_keyboard_interrupt_returns_None (no regression)

### BUG-B: _generate_agent() YAML-injection

LOCATION: tools/dev_workspace.py, lines 858-887 (original)

BEFORE (buggy, framework minimum-YAML path):
    else:
        # minimum-YAML for framework
        display_name = name.upper().replace("-", " ")
        content = f"""version: 1.0.0
title: "{display_name} — {description}"            # ← UNSAFE
description: 'v1.0.0 | framework: {description}'  # ← UNSAFE

prompt: |
  {emoji} {display_name} (v1.0.0)                  # ← UNSAFE
  ...
  🎯 {description}                                 # ← UNSAFE

settings:
  timeout: 600
  ...
"""
        dst.write_text(content)

User input `description = "x'\ntitle: 'INJECTED'\nfoo: '"`
breaks out of the single-quoted `description` field
and injects arbitrary YAML keys (`foo: ''`) and
hijacks the `title` field.

AFTER (fixed, framework minimum-YAML path):
    else:
        # R110-326-BUG-B: use yaml.safe_dump for user-controlled fields
        import yaml
        display_name = name.upper().replace("-", " ")
        safe_desc = " ".join(description.split())  # collapse whitespace
        safe_emoji = emoji.replace("\n", "").replace("\r", "")
        metadata = {
            "version": "1.0.0",
            "title": f"{display_name} — {safe_desc}",
            "description": f"v1.0.0 | framework: {safe_desc}",
            "prompt": (
                f"{safe_emoji} {display_name} (v1.0.0)\n"
                f"⛔ Reasonrulen:\n"
                f"   1. NOTHING automatically applied\n"
                f"   2. framework-governance.md noten\n"
                f"🎯 {safe_desc}\n"
            ),
            "settings": {
                "timeout": 600, "max_steps": 100,
                "provider": "openai",
                "model": "filtered/deepseek/deepseek-v4-flash",
            },
        }
        content = yaml.safe_dump(metadata, default_flow_style=False,
                                  allow_unicode=True, sort_keys=False)
        dst.write_text(content)

`yaml.safe_dump` guarantees proper escaping for all
string values. The user input is also pre-sanitized
(whitespace collapsed, CR/LF stripped) for additional
defense-in-depth.

AFTER (fixed, MAS_TEMPLATE path):
    if agent_type == "mas_sub" and MAS_TEMPLATE.exists():
        content = MAS_TEMPLATE.read_text()
        # R110-326-BUG-B: sanitize user input before string substitution
        safe_name = " ".join(name.split())
        safe_emoji_str = emoji.replace("\n", "").replace("\r", "")
        safe_desc = " ".join(description.split())
        content = content.replace("{NAME}", safe_name.upper().replace("-", " "))
        content = content.replace("{name}", safe_name.lower())
        content = content.replace("{EMOJI}", safe_emoji_str)
        content = content.replace("{BESCHREIBUNG}", safe_desc)
        content = content.replace("{TASK}", safe_desc)
        content = content.replace("{Titel}", safe_desc)
        dst.write_text(content)

Also removed the redundant duplicate `{name}` replace
(was on line 862 twice in the original).

Regression test: test_unsafe_description_does_not_inject_yaml
  - Calls dev_workspace._generate_agent with
    description = "x'\ntitle: 'INJECTED'\nfoo: '"
  - Reads the generated YAML file
  - Asserts no `foo` key in parsed YAML
  - Asserts `title` is NOT the string 'INJECTED'
  - This test FAILS without the fix (yaml.safe_load returns
    `{..., 'foo': '', ...}` with the f-string path).
  - This test PASSES with the fix (yaml.safe_dump escapes
    the malicious input as a string value).

Sanity tests (3):
  - test_framework_minimum_yaml_is_valid (no regression)
  - test_emoji_in_description_does_not_break_yaml (no
    regression: emoji + colons are common in desc)
  - test_existing_file_overwrite_prompt (no regression)

## 9. Refs

Skills used:
  - pre-push-gate (full pre-push checklist)
  - pre-push-body-claim-verification (R110-305 4-round numstat)
  - mas-engineer-coverage-push-workflow (R110-321 candidate list)
  - mas-engineer-r110-78-verification-theater-fix (verify the
    bug is real, verify the fix works)
  - mas-engineer-r110-224-pytest-100pct-green-pass (in-process
    test pattern for fast feedback)

Commits referenced:
  - 360b526 (this commit's code-fix)
  - 4f83886 (R110-325, SOT cleanup, parent)
  - 96b9660 (R110-323-EVIDENCE)
  - 53a6144 (R110-323, code-fix)
  - 2a8842f (R110-322-EVIDENCE)
  - 7247571 (R110-322, code-fix)
  - d56ec64 (R110-321, candidate list)
  - e7ef060 (R110-320, R-sprint pattern origin)
  - 0fb0fdf (R110-318, conftest cleanup)
  - ab43dbc (R110-316, first R-sprint code-fix)
  - 7e74f4e (R110-257, SOT bulk-move + 4 prevention layers)

Lessons applied:
  - R110-78 verification-theater guard (real bug, real test,
    real fix, real EVIDENCE)
  - R110-114 1,961-findings descriptive-prose lesson
    (graceful handling of empty input)
  - R110-281 force-push-verbot (push via credential-helper)
  - R110-269 branch-lock (mas-t-tests only)
  - R110-305 4-round numstat (no body-claim drift)
  - R110-310 subprocess-cov pattern (philosophy inherited,
    in-process for speed)
  - R110-316/318/319/323 evidence-closure pattern
  - R110-321 cov-push candidate list
  - R110-325 SOT cleanup (this EVIDENCE.md is at SOT location)