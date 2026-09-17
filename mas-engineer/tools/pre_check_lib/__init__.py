"""Pre-check profiles for e2e-verify recipes.

Each .py file in this directory defines a profile with:
    - DESCRIPTION (str): one-line description (used by `pre_check --list`)
    - run(workspace: Path) -> dict: returns the check result

Result dict format:
    {
        "title": str,           # human-readable profile title
        "passed": int,          # number of passed checks
        "failed": int,          # number of failed checks
        "duration_s": float,    # total runtime in seconds
        "checks": [
            {
                "id": str,      # e.g. "T1", "T2", ...
                "name": str,    # short description
                "passed": bool,
                "detail": str,  # optional: extra info ("5/5 workflows")
            },
            ...
        ],
    }
"""
