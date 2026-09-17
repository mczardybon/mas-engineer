#!/usr/bin/env python3
"""
test_check_24_wf_yaml_clone_sideeffect_template.py

R110-223 test-fixture TEMPLATE — copy to tests/test_dev_check_wf_yaml_clone_sideeffect.py
when the real test is needed. NOT pytest-discoverable in test-fixtures/.

Companion to:
- tools/dev_check_wf_yaml_clone_sideeffect.py (R110-223, NEW)
- recipe/sub/sub_mas-pre-push-validator.yaml Check 24 (R110-223, NEW)
- recipe/instructions/sub_mas-pre-push-validator.md Check 24 section (R110-223, NEW)

5 cases (mirror R110-204 test_dev_check_orphan_recipes.py 4-case pattern,
extended to 5):
- (a) clean state (no recent sub_mas-clone CREATE in changes.json): exit 0
- (b) simulate a CREATE entry within 7 days: exit 1, table contains the row
- (c) simulate a CREATE entry 30 days old: exit 0 (out of window)
- (d) simulate sub_test-agent CREATE within 7 days: exit 0
      (test-agent is excluded by regex `sub_mas-(?!test-agent)`)
- (e) verify companion check: write a temp recipe/sub/sub_mas-clone.yaml
      with a fake recipe, run the script, expect exit 1, then remove
      the temp file

Run with: pytest tests/test_dev_check_wf_yaml_clone_sideeffect.py -v

See: .mase/directives/R110-223-wf-yaml-clone-sideeffect.md (9-section spec)
"""
# STUB TEMPLATE — implement when R110-223 im-pipeline run produces the real test.
