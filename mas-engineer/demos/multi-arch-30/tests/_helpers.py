"""
demos/multi-arch-30/tests/_helpers.py

Internal helpers for the multi-arch-30 demo test suite.

R110-53b: demos/ is fully autonomous — no imports from tests/.
This file is a COPY of `classify_domain` from
tests/test_recipe_registry_consistency.py (intentional DRY
violation, kept in sync manually) so that the demo test suite
has zero dependencies on the central tests/ directory.

If classify_domain logic changes upstream, this copy must be
updated too. Both files should be kept in sync.

Used only by demos/multi-arch-30/tests/test_multi_arch_30.py.
"""
import re


# DOMAIN 3 demo-team filename tokens (summon-platform, per skill
# mas-engineer-recipe-yaml-pytest-coverage)
DOMAIN3_TOKENS=("social-media-manager", "email-campaign-manager", "seo-researcher", "content-writer", "analytics-reporter", "web-researcher",)


# DOMAIN 1 filename prefix tokens (sub-agents of mas-engineer itself)
DOMAIN1_PREFIXES = (
    "sub_mas-monitor-",       # CONTROLLER-internal
    "sub_mas-im-",            # IM-pipeline sub-agents
    "sub_mas-test-fix-failures-",  # test-fix-failures director chain
)

# DOMAIN 2 filename tokens (mas-generated, team-packager output)
DOMAIN2_TOKENS=("sub_mas-team-packager", "sub_mas-generic-init",)


# DOMAIN 1 description signals
DOMAIN1_DESC = (
    "MAS-internal",
    "MAS-Engineer-internal",
    "CONTROLLER-internal",
    "Code-Review-Team",
)


def classify_domain(stem, data, parent_path=None):
    """Return 'mas-self' (DOMAIN 1), 'mas-generated' (DOMAIN 2),
    'demo-team' (DOMAIN 3), or 'unknown'.

    R110-39 PATH-BASED classification (more robust than stem-only heuristic):
      - parent_path is in MULTI_ARCH_DIR/teams/  -> "demo-team" (R110-30)
      - parent_path is in MULTI_ARCH_DIR/sub/   -> "mas-generated"
      - parent_path is in MULTI_ARCH_DIR/{other} -> "mas-generated" (variants)
      - parent_path is None or otherwise       -> heuristic fallback

    Heuristic fallback (only for SUB_DIR files without path-decision):
    Order matters: more specific signals first.
    """
    # ---- R110-39 PATH-BASED pre-classification (deterministic) ----
    # The demo test only validates the teams/ -> "demo-team" branch.
    # The full logic (sub/ -> mas-generated, other/ -> mas-generated)
    # is included for completeness.
    if parent_path is not None:
        try:
            # Use a duck-typed check: parent_path is a pathlib.Path
            parent_name = parent_path.name
            parent_parent = parent_path.parent
            if parent_name == "teams":
                return "demo-team"
            if parent_name == "sub":
                return "mas-generated"
            if parent_parent.name == "multi-arch-30":
                # test-r11021/, template/, etc. = mas-generated variants
                return "mas-generated"
        except Exception:
            pass

    # ---- Heuristic fallback (for files without strong path signal) ----
    desc = (data.get("description") or "")
    # DOMAIN 2: team-packager
    if any(stem.startswith(t) for t in DOMAIN2_TOKENS):
        return "mas-generated"
    # DOMAIN 3: demo-team filename
    if any(t in stem for t in DOMAIN3_TOKENS):
        return "demo-team"
    # DOMAIN 1: explicit description signal
    if any(sig in desc for sig in DOMAIN1_DESC):
        return "mas-self"
    # DOMAIN 1: filename prefix
    if any(stem.startswith(p) for p in DOMAIN1_PREFIXES):
        return "mas-self"
    # DOMAIN 1: v1.0.0 / v2.0.0 / v3.0.0 prefix + no marketing keyword
    # (R110-30 convention; the existing 34 files like sub_mas-bootstrap,
    # sub_mas-code-reviewer-* all start with "v1.0.0 |")
    if re.match(r"v\d+\.\d+\.\d+\s*\|", desc) and not any(
        kw in desc.lower() for kw in ("marketing", "social media",
                                       "campaign", "seo", "blog")
    ):
        return "mas-self"
    return "unknown"
