# R110-328 Evidence — dev_template_generator latent-bug fixes

## 1. Why

R110-321 (d56ec64) picked 4 candidates for the R-sprint
cov-push queue:
  im_finder_scan(1660), workspace(1445), template_gen(901),
  dashboard(566).
R110-323 took #1, R110-326 took #2, R110-328 took #3
(dev_template_generator.py, 901 stmts).

R110-328 probed 18 top-level functions for latent bugs.
Found 3 real bugs + 1 code smell. All locked in with
34 regression tests. This EVIDENCE.md closes the
evidence gap per the R110-316/318/319/323/326/327
pattern.

R-sprint pattern: every code-fix R-commit (🔧) gets
paired with an evidence-closure R-commit (📝) that
documents the bug(s), the fix, the regression tests,
and the pre-push gate results.

## 2. Refs (the loop R110-328 closes)

- R110-321 (d56ec64) — candidate list picking R110-328
  as item #3 (template_generator.py, 901 stmts)
- R110-327 (bb80d77) — parent (R110-326-EVIDENCE)
- R110-326 (360b526) — R-sprint code-fix (dev_workspace)
- R110-325 (4f83886) — SOT cleanup
- R110-323 (53a6144) — R-sprint pattern origin
- R110-322 (7247571) — R-sprint before that
- R110-320 (e7ef060) — R-sprint pattern origin
- R110-311 (sitecustomize.py) — cov infrastructure
- R110-310 (subprocess cov pattern)
- R110-305 (4-round numstat re-verify)
- R110-281 (force-push-verbot) — push via credential-helper
- R110-257 (7e74f4e) — SOT bulk-move + 4 prevention layers
- R110-114 (1,961-findings descriptive-prose lesson)

## 3. Pre-push gate (R110-328 commit 8948379)

- Secrets: 0 in staged diff
- 4 rounds `git diff --numstat` re-verify (R110-305):
    ROUND 1: 2 files / +485 / -15
    ROUND 2: 2 files / +485 / -15  (stable)
    ROUND 3: 2 files / +485 / -15  (stable)
    ROUND 4: 2 files / +485 / -15  (stable)
  Per-file:
    M mas-engineer/tools/dev_template_generator.py           +54 / -15
    A mas-engineer/tests/test_r110328_template_generator_bug_fixes.py +431 (NEW)
- `git diff --check` clean (after `rstrip` on test file,
  one trailing blank at EOF stripped)
- Branch: mas-t-tests (R110-269 branch-lock)
- Push: via credential-helper, NO force-push
- Pushed commit: 8948379 (parent: bb80d77 R110-327)

## 4. Body-claim-drift audit (R110-305 protocol)

Numbers stable from draft through final. 4 rounds of
`git diff --cached --numstat` confirm 2/485/15.
Per-file: tools +54/-15, tests +431/0.

Specifically checked claims:
  - "2 files changed, 485 insertions(+), 15 deletions(-)"
    → real 2/485/15 ✓ (4/4 rounds)
  - "+54/-15 on tools/dev_template_generator.py" → real ✓
  - "+431 (NEW) on test_r110328_template_generator_bug_fixes.py"
    → real ✓
  - "0 secrets" → grep -cE returned 0 ✓
  - "34/34 R110-328 tests PASS" → pytest returns 34 passed ✓
  - "74/74 R-sprint regression PASS" → pytest returns 74 ✓
  - "290/290 cross-sprint workspace+template PASS" → 290 ✓
  - "Pushed commit: 8948379" → git log --oneline -1 ✓
  - "parent: bb80d77" → git log --oneline -2 ✓

## 5. Bug details

### BUG-1: _format_dict_block() newline handling

LOCATION: tools/dev_template_generator.py, lines 140-160 (pre-fix)

BEFORE (buggy):
    def _format_dict_block(data, prefix="# ", indent=""):
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{indent}{prefix}{key}:")
                for sk, sv in value.items():
                    s = str(sv)[:120]  # ← had newline-handling
                    if "\n" in s:       # ← (lines 147-149)
                        s = s.split("\n")[0] + "..."
                    lines.append(f"{indent}  {prefix}{sk}: {s}")
            elif isinstance(value, list):
                lines.append(f"{indent}{prefix}{key}:")
                for item in value[:5]:
                    s = str(item)[:100]  # ← NO newline-handling
                    lines.append(f"{indent}  {prefix}- {s}")
                if len(value) > 5:
                    lines.append(f"{indent}  {prefix}... +5 mehr")
            else:
                lines.append(f"{indent}{prefix}{key}: {str(value)[:120]}")
                # ← NO newline-handling
        return "\n".join(lines)

AFTER (fixed):
    def _truncate_value(s, maxlen):  # NEW helper
        """Truncate a value to a single line + '...'.

        A multiline value would otherwise break the YAML-
        comment block. Take only the first line, truncate
        to maxlen, add '...' if truncated. Same pattern as
        the nested-dict branch had (line 147-149 pre-fix);
        now extracted to a helper for consistency.
        """
        s = s.split("\n", 1)[0]
        if len(s) > maxlen:
            s = s[:maxlen - 3] + "..."
        return s

    def _format_dict_block(data, prefix="# ", indent=""):
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{indent}{prefix}{key}:")
                for sk, sv in value.items():
                    lines.append(f"{indent}  {prefix}{sk}: "
                                 f"{_truncate_value(str(sv), 120)}")
            elif isinstance(value, list):
                lines.append(f"{indent}{prefix}{key}:")
                for item in value[:5]:
                    lines.append(f"{indent}  {prefix}- "
                                 f"{_truncate_value(str(item), 100)}")
                if len(value) > 5:
                    lines.append(f"{indent}  {prefix}... +5 mehr")
            else:
                lines.append(f"{indent}{prefix}{key}: "
                             f"{_truncate_value(str(value), 120)}")
        return "\n".join(lines)

Regression tests (9):
  - test_value_with_newline_is_truncated_to_first_line
  - test_value_with_newline_and_long_first_line_truncates_with_ellipsis
  - test_list_item_with_newline_is_truncated_to_first_line
  - test_nested_dict_value_with_newline_truncated (no-regression)
  - test_simple_value_no_newline_unchanged
  - test_list_of_strings_no_newline (no-regression)
  - test_list_truncation_at_5_still_works (no-regression)
  - test_dict_with_int_value (no-regression)
  - test_dict_with_bool_value (no-regression)
  - test_empty_dict (no-regression)

### BUG-2: _format_bp_rules() TypeError

LOCATION: tools/dev_template_generator.py, line 179 (pre-fix)

BEFORE (buggy):
    rules = data if isinstance(data, list) else []
    for rule in rules:
        if isinstance(rule, dict) and rule.get("auto_apply"):
            rid = rule.get("id", "?")
            rtext = rule.get("rule", "")[:150]  # ← TypeError if
                                                # rule["rule"] is
                                                # not a string
            lines.append(f"  • [{rid}] {rtext}")

AFTER (fixed):
    rules = data if isinstance(data, list) else []
    for rule in rules:
        if isinstance(rule, dict) and rule.get("auto_apply"):
            rid = rule.get("id", "?")
            # R110-328-BUG-2 fix: rule["rule"] can be any YAML
            # scalar (int, None, dict, list, str). Pre-fix code
            # did `rule.get("rule", "")[:150]` which crashed with
            # TypeError on non-string types. str() wrapper makes
            # the slice safe.
            rtext = str(rule.get("rule", ""))[:150]
            lines.append(f"  • [{rid}] {rtext}")

Process note: First BUG-2 patch dedented the
`rules = data if isinstance(data, list) else []` block
one level too far, breaking the per-section_key loop
(only the LAST section_key's rules appeared in output).
Caught by a manual 2-section probe test before pushing.
Re-patched to re-indent inside the loop. Lesson: when
refactoring inside a loop, ALWAYS re-test with multiple
iterations to catch dedent-induced logic breakage.

Regression tests (10):
  - test_rule_with_int_value_does_not_crash
  - test_rule_with_None_value_does_not_crash
  - test_rule_with_list_value_does_not_crash
  - test_rule_with_dict_value_does_not_crash
  - test_rule_with_missing_rule_field_uses_empty
  - test_string_rule_truncated_to_150 (no-regression)
  - test_no_auto_apply_skipped (no-regression)
  - test_section_key_with_dotted_path (no-regression)
  - test_section_key_with_missing_intermediate (no-regression)
  - test_list_with_string_items_skipped (no-regression)

### BUG-3: fill_template() silent placeholders

LOCATION: tools/dev_template_generator.py, lines 366-377 (pre-fix)

BEFORE (buggy):
    # Nicht-replacese placeholder (aus Template, not in
    # replacements?) -> Als empty String replace
    all_found = re.findall(r"\{[A-Z_]+\}", result)  # ← too restrictive
    for ph in all_found:
        if ph not in replacements:
            unreplaced.append(ph)
            result = result.replace(ph, "")

    if unreplaced:
        print(f"  ℹ️  Nicht-replacese placeholder: "
              f"{', '.join(unreplaced)}")  # ← misleading message

AFTER (fixed):
    # R110-328-BUG-3: Find any {placeholder} in the result
    # that wasn't in `replacements`. Pre-fix regex was
    # r"\{[A-Z_]+\}" which missed lowercase + mixed-case
    # placeholders (e.g. {name}, {Mixed_Case},
    # {unknown_lower}), so they were silently kept in the
    # output. New regex r"\{[^}]+\}" matches any non-empty
    # braces content. Pre-fix warning message also
    # misnamed these as "Nicht-replacese" (mixing in unused
    # and unfilled placeholders with different semantic
    # meanings). Now we separate them:
    #   unused_in_template: in replacements but template
    #     didn't use it (info-level)
    #   unfilled_in_output: in result but not in replacements
    #     (was silent pre-fix, now warn-level)
    unfilled_in_output = []
    all_found = re.findall(r"\{[^}]+\}", result)
    for ph in all_found:
        if ph not in replacements:
            unfilled_in_output.append(ph)
            result = result.replace(ph, "")

    if unreplaced:
        # R110-328-BUG-3: Distinguish "unused in template"
        # (placeholder in replacements but template didn't
        # use it — informational) from "unfilled in output"
        # (placeholder in template but not in replacements
        # — was a silent bug pre-fix, now a warning).
        print(f"  ℹ️  Unused replacements (template did not use): "
              f"{', '.join(unreplaced)}")
    if unfilled_in_output:
        # This is the one that was silent pre-fix. Now we
        # WARN so the user knows they have a placeholder in
        # the template that wasn't provided a value.
        print(f"  ⚠️  Unfilled placeholders in template (replaced "
              f"with ''): {', '.join(unfilled_in_output)}")

Regression tests (8):
  - test_lowercase_unfilled_placeholder_warns
  - test_mixed_case_unfilled_placeholder_warns
  - test_known_uppercase_unfilled_placeholder_replaced_with_empty
  - test_known_uppercase_placeholder_in_replacements (no-regression)
  - test_known_lowercase_placeholder_in_replacements (no-regression)
  - test_no_duplicate_TASK_in_replacements (code smell)
  - test_empty_name_does_not_crash (no-regression)
  - test_template_with_known_and_unknown_placeholders

### Code smell: duplicate {TASK} entry

LOCATION: tools/dev_template_generator.py, lines 350-351 (pre-fix)

BEFORE (buggy):
    replacements = {
        "{NAME}": name.upper(),
        "{name}": name.lower() if name else name,
        "{EMOJI}": emoji,
        "{TASK}": task,
        "{TASK}": task,  # ← duplicate, no functional effect
        "{DESCRIPTION}": _shorten(task, 80),
        "{Titel}": titel,
    }

AFTER (fixed):
    # R110-328: removed duplicate "{TASK}" entry (was a no-op
    # since Python takes the last value, but a code smell —
    # same anti-pattern we fixed in R110-326 BUG-B in
    # dev_workspace.py).
    replacements = {
        "{NAME}": name.upper(),
        "{name}": name.lower() if name else name,
        "{EMOJI}": emoji,
        "{TASK}": task,
        "{DESCRIPTION}": _shorten(task, 80),
        "{Titel}": titel,
    }

## 6. Test pattern (in-process + regression lock)

The 34 tests in test_r110328_template_generator_bug_fixes.py
follow the in-process test pattern from R110-326:
  1. Import dev_template_generator.py directly
     (sys.path.insert + import)
  2. Call testable (non-# pragma: no cover) functions
  3. No GOOSE environment needed (pure-Python functions)
  4. No subprocess.run, no JSON parsing — direct calls

In-process is faster than subprocess (~0.09s vs ~3s for
the bug-probing) and more precise (can call private
helpers like _format_dict_block directly).

The 6 _shorten edge-case tests (no bugs found, but
documented for future regression safety) include
short-circuit with "..." at maxlen=0 and negative
maxlen. These document the BEHAVIOR for future readers
who may think it's a bug. It's not — it's just a quirk
of Python slicing ("abc"[:-3] = ""), which combined
with the "+..." suffix gives a "..." result.

## 7. R-sprint summary (R110-320 → R110-329)

- R110-320 (e7ef060): 🔧 code-fix (registry merge empty
  findings) + 5 tests
- R110-321 (d56ec64): 📝 candidate list documentation
- R110-322 (7247571): 🔧 code-fix (spec invariant scalar
  yaml) + 8 tests
- R110-322-EVIDENCE (2a8842f): 📝 evidence closure
- R110-323 (53a6144): 🔧 code-fix (im_finder_scan BUG-1
  + BUG-2) + 6 tests
- R110-323-EVIDENCE (96b9660): 📝 evidence closure
- R110-325 (4f83886): 🔧 SOT cleanup
- R110-326 (360b526): 🔧 code-fix (dev_workspace BUG-A +
  BUG-B) + 9 tests
- R110-327 (bb80d77): 📝 R110-326-EVIDENCE at SOT
- R110-328 (8948379, this commit's parent): 🔧 code-fix
  (dev_template_generator BUG-1 + BUG-2 + BUG-3 + smell)
  + 34 tests
- R110-328-EVIDENCE (this file): 📝 evidence closure at
  SOT, per R110-325 lesson
- R110-330+ (next): candidates #4 from R110-321 list
  (dashboard_data.py, 566 stmts)

## 8. Refs

Skills used:
  - pre-push-gate (full pre-push checklist)
  - pre-push-body-claim-verification (R110-305 4-round
    numstat)
  - mas-engineer-coverage-push-workflow (R110-321 queue)
  - mas-engineer-r110-78-verification-theater-fix
    (verify the bug is real, verify the fix works)
  - mas-engineer-r110-224-pytest-100pct-green-pass
    (in-process test pattern for fast feedback)

Commits referenced:
  - 8948379 (this commit's code-fix)
  - bb80d77 (R110-327, parent)
  - 360b526 (R110-326 code-fix)
  - 96b9660 (R110-323-EVIDENCE)
  - 53a6144 (R110-323 code-fix)
  - 2a8842f (R110-322-EVIDENCE)
  - 7247571 (R110-322 code-fix)
  - d56ec64 (R110-321 candidate list)
  - e7ef060 (R110-320 R-sprint origin)
  - 4f83886 (R110-325 SOT cleanup)
  - 7e74f4e (R110-257 SOT bulk-move)

Lessons applied:
  - R110-78 verification-theater guard (real bug, real
    test, real fix, real EVIDENCE)
  - R110-114 1,961-findings descriptive-prose lesson
    (graceful handling of empty input — the BUG-3
    regex change follows this spirit: descriptive
    warning instead of silent failure)
  - R110-281 force-push-verbot (push via
    credential-helper)
  - R110-269 branch-lock (mas-t-tests only)
  - R110-305 4-round numstat (no body-claim drift)
  - R110-310 subprocess-cov pattern (inherited, used
    in-process for speed)
  - R110-316/318/319/323 evidence-closure pattern
  - R110-321 cov-push candidate list
  - R110-325 SOT cleanup (this EVIDENCE.md at SOT)
  - R110-326 BUG-B code smell (duplicate {name} in
    dict) — R110-328 found same anti-pattern
    (duplicate {TASK}) and applied the same fix