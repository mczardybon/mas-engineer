"""
dev_guardian_scan.py — static guardian scan for sub_mas-*.yaml agents.

Mode-agnostic v1.0.0. Scans recipe/sub/sub_mas-*.yaml, evaluates 5
dimensions (Schema, Semantic, Death, Loop, Drift), writes
.mase/guardian.yaml in the format consumed by dev_dashboard_data.py.

This is the OPERATOR-side replacement for the runtime guardian
(sub_mas-agent-guardian.md), which requires a live goose LLM
session. The static scan covers dimensions that can be evaluated
from YAML alone (1-4); dimension 5 (context drift) requires
runtime delegation history and is reported as 0 with a clear note.

Output: .mase/guardian.yaml
  guardian:
    last_scan: <iso8601>
    healthy: N
    degraded: N
    broken: N
    total_yamls: N
    note: "static scan v1.0.0, 5-dim check, no LLM"
    categories: { healthy_agents: [...], degraded_agents: [...], critical_agents: [...] }
    findings_summary: { total_issues: N, long_instructions: N, missing_prompt: N, ... }
    agents:
      sub_mas-X.yaml:
        status: healthy|degraded|broken
        score: 0-100
        checks: { schema: ok|warn|fail, semantic: ..., death: ..., loop: ..., drift: ... }
        issues: [ "missing prompt", "instructions too long", ... ]
    drift_log: [...]
    drift_summary: { total_drifts: N, by_type: {...}, by_agent: {...}, trend: stable }

Scoring (per agent, 0-100):
  - Each of 5 dims contributes max 20 points
  - Penalty per issue: schema -20, semantic -10, death -50, loop -30, drift -10
  - Floor: 0, Ceiling: 100
  - Status from score: >=80 healthy, 50-79 degraded, <50 broken

Usage:
  python3 tools/dev_guardian_scan.py [--workspace <repo>] [--verbose]

Exit codes: 0=ok, 1=fatal-error, 2=no-agents-found
"""
import argparse
import glob
import os
import sys
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    print("FATAL: PyYAML not installed", file=sys.stderr)
    sys.exit(1)


# ─── CONSTANTS ────────────────────────────────────────────────────

EXPECTED_TOP_KEYS = {"name", "title", "description", "prompt", "instructions"}
PROMPT_MIN_LEN = 30          # R110-78 / validator Check 1.5
INSTRUCTIONS_MAX_LEN = 30000 # dev_generic_init.py uses similar bound
DRIFT_LOG_MAX = 100          # bounded, never grows unbounded
FINDINGS_LOG_MAX = 50

# Substring patterns that indicate semantic issues
SEMANTIC_BAD_PATTERNS = [
    ("typee", "typo: typee should be type"),
    ("recipit", "typo: recipit should be recipe"),
    ("heoldh", "typo: heoldh should be health"),
    ("imperver", "typo: imperver should be improver"),
    ("ditign", "typo: ditign should be design"),
    ("titt", "typo: titt should be test"),
    ("refrith", "typo: refrith should be refresh"),
]


# ─── HELPERS ──────────────────────────────────────────────────────

def detect_mas_root(ws):
    """Find mas-engineer root (may be ws itself or ws/mas-engineer)."""
    ws_abs = os.path.abspath(ws)
    if os.path.isdir(os.path.join(ws_abs, "recipe")):
        return ws_abs
    cand = os.path.join(ws_abs, "mas-engineer")
    if os.path.isdir(os.path.join(cand, "recipe")):
        return cand
    return ws_abs


def yaml_load(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        return {"_yaml_error": str(e)}


def evaluate_agent(filepath, verbose=False):
    """Run 5-dim check on a single sub-agent YAML. Return (status, score, issues, checks)."""
    issues = []
    checks = {"schema": "ok", "semantic": "ok", "death": "ok", "loop": "ok", "drift": "ok"}
    score = 100

    # 1. SCHEMA CHECK
    raw = open(filepath).read()
    try:
        d = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        return "broken", 0, [f"yaml-parse-error: {e}"], \
            {"schema": "fail", "semantic": "fail", "death": "ok",
             "loop": "ok", "drift": "ok"}

    if not isinstance(d, dict):
        return "broken", 0, ["yaml-not-dict"], \
            {"schema": "fail", "semantic": "fail", "death": "ok",
             "loop": "ok", "drift": "ok"}

    missing = EXPECTED_TOP_KEYS - set(d.keys())
    if missing:
        issues.append(f"missing-top-keys: {sorted(missing)}")
        checks["schema"] = "fail"
        score -= 20 * len(missing)

    # 2. SEMANTIC CHECK
    prompt = d.get("prompt", "")
    if not prompt or len(str(prompt)) < PROMPT_MIN_LEN:
        issues.append(f"prompt-too-short (len={len(str(prompt))}, min={PROMPT_MIN_LEN})")
        checks["semantic"] = "warn"
        score -= 10

    instructions = d.get("instructions", "")
    if not instructions:
        issues.append("missing-instructions")
        checks["semantic"] = "warn"
        score -= 10
    elif len(str(instructions)) > INSTRUCTIONS_MAX_LEN:
        issues.append(f"instructions-too-long (len={len(str(instructions))})")
        checks["semantic"] = "warn"
        score -= 5  # minor penalty, not a hard fail

    # Typo patterns
    full_text = (str(d.get("prompt", "")) + str(d.get("instructions", ""))).lower()
    for bad, msg in SEMANTIC_BAD_PATTERNS:
        if bad in full_text:
            issues.append(msg)
            checks["semantic"] = "warn"
            score -= 5

    # 3. DEATH CHECK (static: parse success + non-empty)
    # If YAML is valid and has at least prompt+instructions, agent is "alive"
    # The runtime "death" (status=error/timeout) requires goose session;
    # we mark it as ok here and let the runtime update it.
    if not d.get("prompt"):
        issues.append("death: empty-prompt")
        checks["death"] = "fail"
        score -= 50

    # 4. LOOP CHECK (static: recipe references itself = loop risk)
    sub_recipes = d.get("sub_recipes", []) or []
    base = os.path.basename(filepath)
    for sr in sub_recipes:
        ref = sr.get("path", "") if isinstance(sr, dict) else str(sr)
        if base in ref or ref in base:
            issues.append(f"loop-risk: self-reference {ref}")
            checks["loop"] = "warn"
            score -= 30

    # 5. DRIFT CHECK (static: missing standard fields)
    if "constitution" not in d:
        issues.append("drift: no-constitution-ref")
        checks["drift"] = "warn"
        score -= 5

    # Floor
    score = max(0, min(100, score))

    if score >= 80:
        status = "healthy"
    elif score >= 50:
        status = "degraded"
    else:
        status = "broken"

    return status, score, issues, checks


# ─── MAIN ────────────────────────────────────────────────────────

def run_scan(workspace, verbose=False):
    mas_root = detect_mas_root(workspace)
    sub_dir = os.path.join(mas_root, "recipe", "sub")
    state_dir = os.path.join(mas_root, ".mase")
    guardian_path = os.path.join(state_dir, "guardian.yaml")

    sub_files = sorted(glob.glob(os.path.join(sub_dir, "sub_mas-*.yaml")))
    if not sub_files:
        print(f"FATAL: no sub_mas-*.yaml in {sub_dir}", file=sys.stderr)
        return 2

    agents = {}
    healthy = degraded = broken = 0
    findings = {"total_issues": 0, "long_instructions": 0,
                "missing_prompt": 0, "missing_instructions": 0,
                "missing_top_keys": 0, "yaml_errors": 0,
                "loop_risks": 0, "typos": 0, "drift": 0}
    drift_log = []
    healthy_names = []
    degraded_names = []
    critical_names = []

    for f in sub_files:
        name = os.path.basename(f)
        status, score, issues, checks = evaluate_agent(f, verbose=verbose)

        if status == "healthy":
            healthy += 1
            healthy_names.append(name)
        elif status == "degraded":
            degraded += 1
            degraded_names.append(name)
        else:
            broken += 1
            critical_names.append(name)

        # Update findings summary
        for iss in issues:
            findings["total_issues"] += 1
            if "instructions-too-long" in iss:
                findings["long_instructions"] += 1
            if "prompt-too-short" in iss or "missing-prompt" in iss:
                findings["missing_prompt"] += 1
            if "missing-instructions" in iss:
                findings["missing_instructions"] += 1
            if "missing-top-keys" in iss:
                findings["missing_top_keys"] += 1
            if "yaml-parse-error" in iss or "yaml-not-dict" in iss:
                findings["yaml_errors"] += 1
            if "loop-risk" in iss:
                findings["loop_risks"] += 1
            if "typo:" in iss:
                findings["typos"] += 1
            if iss.startswith("drift:"):
                findings["drift"] += 1

        # Drift log (only warn/fail entries, bounded)
        if checks["drift"] != "ok" or checks["schema"] != "ok":
            drift_log.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "agent": name,
                "type": "schema" if checks["schema"] != "ok" else "drift",
                "severity": checks["schema"],
                "issues": issues,
            })

        agents[name] = {
            "status": status,
            "score": score,
            "checks": checks,
            "issues": issues,
            "last_checked": datetime.now(timezone.utc).isoformat(),
        }

        if verbose:
            tag = {"healthy": "OK", "degraded": "WARN", "broken": "FAIL"}[status]
            print(f"  [{tag:4}] {score:5.1f}  {name}  ({len(issues)} issues)")

    # Bound drift log
    drift_log = drift_log[-DRIFT_LOG_MAX:]

    # Drift summary
    by_type = {}
    by_agent = {}
    for d in drift_log:
        by_type[d["type"]] = by_type.get(d["type"], 0) + 1
        by_agent[d["agent"]] = by_agent.get(d["agent"], 0) + 1

    guardian = {
        "guardian": {
            "last_scan": datetime.now(timezone.utc).isoformat(),
            "healthy": healthy,
            "degraded": degraded,
            "broken": broken,
            "total_yamls": len(sub_files),
            "note": "static scan v1.0.0, 5-dim check (schema/semantic/death/loop/drift), no LLM",
            "categories": {
                "healthy_agents": healthy_names,
                "degraded_agents": degraded_names,
                "critical_agents": critical_names,
            },
            "findings_summary": findings,
            "agents": agents,
            "drift_log": drift_log,
            "drift_summary": {
                "total_drifts": len(drift_log),
                "by_type": by_type,
                "by_agent": by_agent,
                "trend": "stable",
            },
        }
    }

    os.makedirs(state_dir, exist_ok=True)
    with open(guardian_path, "w") as f:
        yaml.dump(guardian, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False)

    # Print summary
    print(f"OK guardian scan complete")
    print(f"  workspace: {mas_root}")
    print(f"  scanned:   {len(sub_files)} sub-agents")
    print(f"  healthy:   {healthy}")
    print(f"  degraded:  {degraded}")
    print(f"  broken:    {broken}")
    print(f"  findings:  {findings['total_issues']} total "
          f"({findings['missing_top_keys']} missing-top-keys, "
          f"{findings['missing_prompt']} missing-prompt, "
          f"{findings['missing_instructions']} missing-instructions, "
          f"{findings['long_instructions']} long-instructions, "
          f"{findings['yaml_errors']} yaml-errors, "
          f"{findings['loop_risks']} loop-risks, "
          f"{findings['typos']} typos, "
          f"{findings['drift']} drift)")
    print(f"  written:   {guardian_path}")

    return 0


def main():
    ap = argparse.ArgumentParser(description="Static guardian scan for sub-agents")
    ap.add_argument("--workspace", default=".",
                    help="Path to mas-engineer (or its parent) [default: .]")
    ap.add_argument("--verbose", action="store_true",
                    help="Per-agent output")
    args = ap.parse_args()

    try:
        sys.exit(run_scan(args.workspace, verbose=args.verbose))
    except Exception as e:
        print(f"FATAL: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    main()
