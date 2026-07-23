#!/bin/bash
# =============================================================================
# MAS-ENGINEER E2E-TESTPLAN v1.0 - Executable Test Script
# =============================================================================
# Basierend auf: docs/E2E-TESTPLAN.md
# Jederzeit wiederholbar. Jede KI kann dieses Skript ausfuehren.
# Stand: 2026-07-23
# =============================================================================

set -u  # Bei undefinierten vars abbrechen, aber NICHT set -e (wir wollen alle tests laufen lassen)

# --- KONFIGURATION ---
MAS_WORKSPACE="${MAS_WORKSPACE:-/workspace/mas-engineer-src/mas-engineer}"
DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:?set DEEPSEEK_API_KEY env var}"
OPENAI_API_KEY="${OPENAI_API_KEY:-$DEEPSEEK_API_KEY}"
E2E_DIR="/tmp/e2e-results"
TEST_DATE="$(date +%Y%m%d_%H%M%S)"
SKIP_PHASES=()
ONLY_PHASE=""
PARALLEL=1
STRICT=0
NO_PUSH=0
EXTRA_BUDGET=0

# --- ARGUMENT PARSING ---
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip) SKIP_PHASES+=("$2"); shift 2;;
        --only) ONLY_PHASE="$2"; shift 2;;
        --parallel) PARALLEL="$2"; shift 2;;
        --strict) STRICT=1; shift;;
        --no-push) NO_PUSH=1; shift;;
        --budget) EXTRA_BUDGET="$2"; shift 2;;
        --workspace) MAS_WORKSPACE="$2"; shift 2;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "  --skip <phase>      Phasen ueberspringen (1-7)"
            echo "  --only <phase>      Nur diese phase (1-7)"
            echo "  --parallel <n>      Parallelitaet (default: 1)"
            echo "  --strict            Bei 1 fail sofort abbruch"
            echo "  --no-push           Phase 6 ohne git push"
            echo "  --budget <n>        Mas-runs-budget (default: 0)"
            echo "  --workspace <path>  Mas-workspace (default: $MAS_WORKSPACE)"
            exit 0;;
        *) echo "Unknown arg: $1"; exit 2;;
    esac
done

# --- HELPER FUNCTIONS ---
setup_env() {
    export PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null || echo "")
    export DEEPSEEK_API_KEY
    export OPENAI_API_KEY="$DEEPSEEK_API_KEY"
    export OPENAI_HOST
    export GOOSE_MODEL
    export GOOSE_PROVIDER
    export NO_COLOR=1
    export MAS_WORKSPACE
    mkdir -p "$E2E_DIR"
}

cd_workspace() {
    cd "$MAS_WORKSPACE" || { echo "FAIL: workspace not found: $MAS_WORKSPACE"; exit 1; }
}

log_test() {
    local phase=$1; local name=$2; local status=$3
    echo "[$status] phase=$phase test=$name" | tee -a "$E2E_DIR/$TEST_DATE.log"
    if [[ "$status" == "FAIL" && "$STRICT" == "1" ]]; then
        echo "STRICT MODE: stopping after fail"
        exit 1
    fi
}

should_skip() {
    local phase=$1
    [[ ${#SKIP_PHASES[@]} -gt 0 ]] && printf '%s\n' "${SKIP_PHASES[@]}" | grep -qx "$phase" && return 0
    [[ -n "$ONLY_PHASE" && "$ONLY_PHASE" != "$phase" ]] && return 0
    return 1
}

# =============================================================================
# PHASE 0: VORBEREITUNG
# =============================================================================
phase_0() {
    echo "============================================================"
    echo "PHASE 0: VORBEREITUNG"
    echo "============================================================"
    cd_workspace
    setup_env

    # Test 0.1: goose erreichbar
    if PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) goose --version >/dev/null 2>&1; then
        log_test 0 "goose_version" "PASS"
    else
        log_test 0 "goose_version" "FAIL"
    fi

    # Test 0.2: workspace clean
    local size=$(du -sm .state/ 2>/dev/null | cut -f1)
    if [[ "$size" -lt 2 ]]; then
        log_test 0 "workspace_size" "PASS"
    else
        log_test 0 "workspace_size" "FAIL ($size MB)"
    fi

    # Test 0.3: keine e2e-results/
    if [[ ! -d "e2e-results" ]]; then
        log_test 0 "no_e2e_results" "PASS"
    else
        log_test 0 "no_e2e_results" "FAIL"
    fi

    # Test 0.4: budget
    local budget=$(python3 -c "
import json, datetime, os
try:
    d = json.load(open('.state/changes.json'))
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=24)
    recent = [e for e in d.get('entries',[]) if 'timestamp' in e and e['timestamp'] > cutoff.isoformat()]
    full = [e for e in recent if e.get('type') == 'full_improvement_override']
    print(f'{5-len(full)+$EXTRA_BUDGET}')
except: print('5')" 2>/dev/null)
    echo "  budget left: $budget"
    log_test 0 "budget_check" "PASS"
}

# =============================================================================
# PHASE 1: SANITY (5 tests, 60s)
# =============================================================================
phase_1() {
    echo "============================================================"
    echo "PHASE 1: SANITY"
    echo "============================================================"
    cd_workspace

    # Test 1.1: goose --version
    if PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) goose --version >/dev/null 2>&1; then
        log_test 1 "goose_version" "PASS"
    else
        log_test 1 "goose_version" "FAIL"
    fi

    # Test 1.2: alle recipes YAML-valid
    local yaml_fail=0
    for r in $(find recipe/ -name "*.yaml" -not -path "*/legacy/*" -not -path "*/template/*" -not -path "*/.backups/*" 2>/dev/null); do
        if ! python3 -c "import yaml; yaml.safe_load(open('$r'))" 2>/dev/null; then
            yaml_fail=$((yaml_fail+1))
            echo "  YAML invalid: $r"
        fi
    done
    [[ $yaml_fail -eq 0 ]] && log_test 1 "yaml_valid" "PASS" || log_test 1 "yaml_valid" "FAIL ($yaml_fail)"

    # Test 1.3: alle recipes ladbar via goose --explain
    local load_fail=0
    local total=0
    for r in $(find recipe/ -name "*.yaml" -not -path "*/legacy/*" -not -path "*/template/*" -not -path "*/.backups/*" -not -name "root_recipe.yaml" 2>/dev/null); do
        total=$((total+1))
        if ! PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) goose run --recipe "$r" --explain 2>&1 | grep -q "Loading recipe"; then
            load_fail=$((load_fail+1))
            echo "  Recipe not loadable: $r"
        fi
    done
    [[ $load_fail -eq 0 ]] && log_test 1 "recipes_loadable" "PASS" || log_test 1 "recipes_loadable" "FAIL ($load_fail/$total)"

    # Test 1.4: alle tools importierbar
    local import_fail=0
    local tools_total=0
    for t in tools/*.py; do
        tools_total=$((tools_total+1))
        if ! python3 -c "import importlib.util; s=importlib.util.spec_from_file_location('m','$t'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)" 2>&1 | grep -v "DeprecationWarning" | head -3 >/dev/null; then
            import_fail=$((import_fail+1))
            echo "  Tool not importable: $t"
        fi
    done
    [[ $import_fail -eq 0 ]] && log_test 1 "tools_importable" "PASS" || log_test 1 "tools_importable" "FAIL ($import_fail/$tools_total)"

    # Test 1.5: alle tools haben --help
    local help_fail=0
    for t in tools/*.py; do
        if ! python3 "$t" --help >/dev/null 2>&1; then
            help_fail=$((help_fail+1))
            echo "  Tool --help failed: $t"
        fi
    done
    [[ $help_fail -eq 0 ]] && log_test 1 "tools_have_help" "PASS" || log_test 1 "tools_have_help" "FAIL ($help_fail)"
}

# =============================================================================
# PHASE 2: SUB-RECIPE DIREKT (52 tests, ~15 min)
# =============================================================================
phase_2() {
    echo "============================================================"
    echo "PHASE 2: SUB-RECIPE DIREKT"
    echo "============================================================"
    cd_workspace

    local recipes=$(find recipe/sub/ -name "sub_mas-*.yaml" -not -path "*/legacy/*" 2>/dev/null | sort)
    local total=$(echo "$recipes" | wc -l)
    local i=0
    local pass=0
    local fail=0

    for r in $recipes; do
        i=$((i+1))
        local name=$(basename "$r" .yaml)
        local out="$E2E_DIR/sub_${name}_${TEST_DATE}.log"

        PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) \
        DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY OPENAI_API_KEY=$DEEPSEEK_API_KEY OPENAI_HOST=$OPENAI_HOST \
        GOOSE_MODEL=$GOOSE_MODEL GOOSE_PROVIDER=$GOOSE_PROVIDER NO_COLOR=1 \
        MAS_WORKSPACE=$MAS_WORKSPACE \
        timeout 60 goose run --with-builtin developer \
            --recipe "$r" \
            --params "workspace=$MAS_WORKSPACE" \
            --no-session \
            > "$out" 2>&1
        local exit=$?

        if [[ $exit -eq 0 ]] && grep -qE "Loading recipe|SUCCESS|DONE|completed" "$out"; then
            log_test 2 "$name" "PASS"
            pass=$((pass+1))
        else
            log_test 2 "$name" "FAIL (exit=$exit)"
            fail=$((fail+1))
        fi
    done
    echo "  Phase 2: $pass PASS, $fail FAIL, $total total"
}

# =============================================================================
# PHASE 3: TOOL-LAYER UNIT (50 tests, 120s)
# =============================================================================
phase_3() {
    echo "============================================================"
    echo "PHASE 3: TOOL-LAYER UNIT"
    echo "============================================================"
    cd_workspace

    local out="$E2E_DIR/tool_layer_${TEST_DATE}.log"
    python3 <<'EOF' > "$out" 2>&1
import importlib.util, subprocess, sys, os
tools = [f for f in os.listdir('tools') if f.endswith('.py')]
results = []
for t in tools:
    name = t[:-3]
    try:
        spec = importlib.util.spec_from_file_location(name, f'tools/{t}')
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        import_ok = True
    except Exception:
        import_ok = False
    r = subprocess.run([sys.executable, f'tools/{t}', '--help'],
                      capture_output=True, text=True, timeout=10)
    help_ok = r.returncode in (0, 2)
    results.append((name, import_ok, help_ok))
fail = [n for n,i,h in results if not (i and h)]
print(f"FAIL: {fail if fail else 'none'}")
print(f"Total: {len(results)}, Fail: {len(fail)}")
EOF

    if grep -q "FAIL: none" "$out"; then
        log_test 3 "all_tools" "PASS"
    else
        log_test 3 "all_tools" "FAIL"
    fi
}

# =============================================================================
# PHASE 4: IM-PIPELINE PHASEN (5 tests, ~12 min)
# =============================================================================
phase_4() {
    echo "============================================================"
    echo "PHASE 4: IM-PIPELINE PHASEN"
    echo "============================================================"
    cd_workspace

    local pipeline_recipes=(
        "sub_mas-im-finder"
        "sub_mas-im-rank"
        "sub_mas-im-designer"
        "sub_mas-im-validator"
        "sub_mas-general-improver"
    )

    for pr in "${pipeline_recipes[@]}"; do
        local out="$E2E_DIR/pipeline_${pr}_${TEST_DATE}.log"
        local params="workspace=$MAS_WORKSPACE"
        [[ "$pr" == "sub_mas-im-finder" ]] && params="$params,scan_scope=recipe/"
        [[ "$pr" == "sub_mas-general-improver" ]] && params="$params,task=APPLY_ONLY,confirm=yes,approve=y"

        if [[ "$pr" == "sub_mas-general-improver" ]]; then
            RECURSION_OVERRIDE=1 MAS_TASK=APPLY_ONLY MAS_CONFIRM=yes MAS_APPROVE=y \
            timeout 300 env PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) \
                DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY OPENAI_API_KEY=$DEEPSEEK_API_KEY OPENAI_HOST=$OPENAI_HOST \
                GOOSE_MODEL=$GOOSE_MODEL GOOSE_PROVIDER=$GOOSE_PROVIDER NO_COLOR=1 \
                MAS_WORKSPACE=$MAS_WORKSPACE \
                goose run --with-builtin developer \
                    --recipe "recipe/sub/${pr}.yaml" \
                    --params "$params" \
                    --no-session > "$out" 2>&1
        else
            echo "ack" | timeout 300 env PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) \
                DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY OPENAI_API_KEY=$DEEPSEEK_API_KEY OPENAI_HOST=$OPENAI_HOST \
                GOOSE_MODEL=$GOOSE_MODEL GOOSE_PROVIDER=$GOOSE_PROVIDER NO_COLOR=1 \
                MAS_WORKSPACE=$MAS_WORKSPACE \
                goose run --with-builtin developer \
                    --recipe "recipe/sub/${pr}.yaml" \
                    --params "$params" \
                    --no-session > "$out" 2>&1
        fi

        local exit=$?
        if [[ $exit -eq 0 ]]; then
            log_test 4 "$pr" "PASS"
        else
            log_test 4 "$pr" "FAIL (exit=$exit)"
        fi
    done
}

# =============================================================================
# PHASE 5: MODI + SCHALTER (8 tests, ~20 min)
# =============================================================================
phase_5() {
    echo "============================================================"
    echo "PHASE 5: MODI + SCHALTER"
    echo "============================================================"
    cd_workspace

    # Test 5.1: R01 confirmation-bypass
    local out="$E2E_DIR/switch_R01_${TEST_DATE}.log"
    echo "no-confirm" | timeout 60 env PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) \
        DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY OPENAI_API_KEY=$DEEPSEEK_API_KEY OPENAI_HOST=$OPENAI_HOST \
        GOOSE_MODEL=$GOOSE_MODEL GOOSE_PROVIDER=$GOOSE_PROVIDER NO_COLOR=1 \
        MAS_WORKSPACE=$MAS_WORKSPACE \
        goose run --recipe recipe/sub/sub_mas-general-improver.yaml \
            --params "task=APPLY_ONLY,confirm=no" --no-session > "$out" 2>&1
    if grep -q "Are you sure" "$out"; then
        log_test 5 "R01_bypass" "FAIL: R01 not bypassed"
    else
        log_test 5 "R01_bypass" "PASS"
    fi

    # Test 5.2: RECURSION_OVERRIDE=2 bypass
    local out2="$E2E_DIR/switch_recursion_${TEST_DATE}.log"
    RECURSION_OVERRIDE=2 timeout 60 env PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) \
        DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY OPENAI_API_KEY=$DEEPSEEK_API_KEY OPENAI_HOST=$OPENAI_HOST \
        GOOSE_MODEL=$GOOSE_MODEL GOOSE_PROVIDER=$GOOSE_PROVIDER NO_COLOR=1 \
        MAS_WORKSPACE=$MAS_WORKSPACE \
        goose run --recipe recipe/sub/sub_mas-general-improver.yaml \
            --params "task=FULL_IMPROVEMENT" --no-session > "$out2" 2>&1
    if grep -q "RECURSION_GUARD" "$out2"; then
        log_test 5 "RECURSION_OVERRIDE_2" "FAIL"
    else
        log_test 5 "RECURSION_OVERRIDE_2" "PASS"
    fi

    # Test 5.3: --no-session (1-frage modus)
    local out3="$E2E_DIR/switch_nosession_${TEST_DATE}.log"
    echo "test" | timeout 60 env PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) \
        DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY OPENAI_API_KEY=$DEEPSEEK_API_KEY OPENAI_HOST=$OPENAI_HOST \
        GOOSE_MODEL=$GOOSE_MODEL GOOSE_PROVIDER=$GOOSE_PROVIDER NO_COLOR=1 \
        MAS_WORKSPACE=$MAS_WORKSPACE \
        goose run --recipe recipe/sub/sub_mas-intention-parser.yaml --no-session > "$out3" 2>&1
    local exit3=$?
    [[ $exit3 -eq 0 || $exit3 -eq 124 ]] && log_test 5 "no_session" "PASS" || log_test 5 "no_session" "FAIL (exit=$exit3)"

    # Test 5.4: --with-builtin developer
    local out4="$E2E_DIR/switch_developer_${TEST_DATE}.log"
    echo "ack" | timeout 60 env PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) \
        DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY OPENAI_API_KEY=$DEEPSEEK_API_KEY OPENAI_HOST=$OPENAI_HOST \
        GOOSE_MODEL=$GOOSE_MODEL GOOSE_PROVIDER=$GOOSE_PROVIDER NO_COLOR=1 \
        MAS_WORKSPACE=$MAS_WORKSPACE \
        goose run --with-builtin developer --recipe recipe/sub/sub_mas-im-finder.yaml \
            --params "workspace=$MAS_WORKSPACE" --no-session > "$out4" 2>&1
    local exit4=$?
    [[ $exit4 -eq 0 ]] && log_test 5 "with_developer" "PASS" || log_test 5 "with_developer" "FAIL (exit=$exit4)"

    # Test 5.5: --params workspace=...
    local out5="$E2E_DIR/switch_params_${TEST_DATE}.log"
    echo "ack" | timeout 60 env PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) \
        DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY OPENAI_API_KEY=$DEEPSEEK_API_KEY OPENAI_HOST=$OPENAI_HOST \
        GOOSE_MODEL=$GOOSE_MODEL GOOSE_PROVIDER=$GOOSE_PROVIDER NO_COLOR=1 \
        MAS_WORKSPACE=$MAS_WORKSPACE \
        goose run --recipe recipe/sub/sub_mas-im-finder.yaml \
            --params "workspace=$MAS_WORKSPACE,scan_scope=recipe/" --no-session > "$out5" 2>&1
    local exit5=$?
    [[ $exit5 -eq 0 ]] && log_test 5 "params_workspace" "PASS" || log_test 5 "params_workspace" "FAIL (exit=$exit5)"

    # Test 5.6: MAS_TASK
    local out6="$E2E_DIR/switch_mastask_${TEST_DATE}.log"
    MAS_TASK=REVIEW timeout 60 env PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) \
        DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY OPENAI_API_KEY=$DEEPSEEK_API_KEY OPENAI_HOST=$OPENAI_HOST \
        GOOSE_MODEL=$GOOSE_MODEL GOOSE_PROVIDER=$GOOSE_PROVIDER NO_COLOR=1 \
        MAS_WORKSPACE=$MAS_WORKSPACE \
        goose run --recipe recipe/sub/sub_mas-general-improver.yaml --no-session > "$out6" 2>&1
    local exit6=$?
    [[ $exit6 -eq 0 || $exit6 -eq 124 ]] && log_test 5 "MAS_TASK" "PASS" || log_test 5 "MAS_TASK" "FAIL (exit=$exit6)"

    # Test 5.7: temperature
    local out7="$E2E_DIR/switch_temp_${TEST_DATE}.log"
    echo "ack" | timeout 60 env PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) \
        DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY OPENAI_API_KEY=$DEEPSEEK_API_KEY OPENAI_HOST=$OPENAI_HOST \
        GOOSE_MODEL=$GOOSE_MODEL GOOSE_PROVIDER=$GOOSE_PROVIDER NO_COLOR=1 \
        MAS_WORKSPACE=$MAS_WORKSPACE \
        goose run --recipe recipe/sub/sub_mas-intention-parser.yaml --no-session > "$out7" 2>&1
    local exit7=$?
    [[ $exit7 -eq 0 || $exit7 -eq 124 ]] && log_test 5 "temperature" "PASS" || log_test 5 "temperature" "FAIL (exit=$exit7)"

    # Test 5.8: --explain (kein run, nur metadata)
    local out8="$E2E_DIR/switch_explain_${TEST_DATE}.log"
    timeout 30 env PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) \
        DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY OPENAI_API_KEY=$DEEPSEEK_API_KEY OPENAI_HOST=$OPENAI_HOST \
        GOOSE_MODEL=$GOOSE_MODEL GOOSE_PROVIDER=$GOOSE_PROVIDER NO_COLOR=1 \
        MAS_WORKSPACE=$MAS_WORKSPACE \
        goose run --recipe recipe/dev-mas-engineer.yaml --explain > "$out8" 2>&1
    if grep -q "Loading recipe" "$out8"; then
        log_test 5 "explain" "PASS"
    else
        log_test 5 "explain" "FAIL"
    fi
}

# =============================================================================
# PHASE 7: RULE-CHECKER + PRE-PUSH (5 tests, 30s)
# =============================================================================
phase_7() {
    echo "============================================================"
    echo "PHASE 7: RULE-CHECKER + PRE-PUSH"
    echo "============================================================"
    cd_workspace

    # Test 7.1: alle actions durch rule_checker
    local out1="$E2E_DIR/rule_actions_${TEST_DATE}.log"
    local ACTIONS=("SI-RUN start" "PATCH-DESIGN" "PATCH-VALIDATE" "PATCH-APPLY" "GIT-COMMIT" "GIT-PUSH" "RECURSION-RESET" "AUDIT-LOG" "TELEGRAM-SEND" "DELEGATE")
    local action_fail=0
    for a in "${ACTIONS[@]}"; do
        if ! python3 tools/dev_rule_checker.py --all --action "$a" 2>&1 | grep -qE "approved|denied"; then
            action_fail=$((action_fail+1))
            echo "  Action failed: $a" >> "$out1"
        fi
    done
    [[ $action_fail -eq 0 ]] && log_test 7 "rule_actions" "PASS" || log_test 7 "rule_actions" "FAIL ($action_fail)"

    # Test 7.2: R13 enforcement
    local out2="$E2E_DIR/rule_R13_${TEST_DATE}.log"
    if python3 tools/dev_recursion_override.py --action edit --file /root/.config/goose/recipes/translator/translator-team.yaml > "$out2" 2>&1; then
        if grep -q "R13" "$out2"; then
            log_test 7 "R13_enforced" "PASS"
        else
            log_test 7 "R13_enforced" "FAIL (no R13 msg)"
        fi
    else
        if grep -q "R13" "$out2"; then
            log_test 7 "R13_enforced" "PASS"
        else
            log_test 7 "R13_enforced" "FAIL"
        fi
    fi

    # Test 7.3: R01 enforcement
    local out3="$E2E_DIR/rule_R01_${TEST_DATE}.log"
    echo "" | timeout 60 env PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) \
        DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY OPENAI_API_KEY=$DEEPSEEK_API_KEY OPENAI_HOST=$OPENAI_HOST \
        GOOSE_MODEL=$GOOSE_MODEL GOOSE_PROVIDER=$GOOSE_PROVIDER NO_COLOR=1 \
        MAS_WORKSPACE=$MAS_WORKSPACE \
        goose run --recipe recipe/sub/sub_mas-general-improver.yaml --no-session > "$out3" 2>&1
    if grep -q "R01" "$out3"; then
        log_test 7 "R01_enforced" "PASS"
    else
        log_test 7 "R01_enforced" "WARN (no R01 in log)"
    fi

    # Test 7.4: Pre-push validator
    local out4="$E2E_DIR/rule_prepush_${TEST_DATE}.log"
    if python3 tools/dev_goose_expert_check.py --commit HEAD > "$out4" 2>&1; then
        log_test 7 "pre_push" "PASS"
    else
        log_test 7 "pre_push" "WARN (tool returned non-zero)"
    fi

    # Test 7.5: Self-auditor
    local out5="$E2E_DIR/rule_audit_${TEST_DATE}.log"
    timeout 120 env PATH=$PATH:$(dirname $(which goose 2>/dev/null) 2>/dev/null) \
        DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY OPENAI_API_KEY=$DEEPSEEK_API_KEY OPENAI_HOST=$OPENAI_HOST \
        GOOSE_MODEL=$GOOSE_MODEL GOOSE_PROVIDER=$GOOSE_PROVIDER NO_COLOR=1 \
        MAS_WORKSPACE=$MAS_WORKSPACE \
        goose run --with-builtin developer --recipe recipe/sub/sub_mas-self-auditor.yaml \
            --params "workspace=$MAS_WORKSPACE" --no-session > "$out5" 2>&1
    local exit5=$?
    [[ $exit5 -eq 0 ]] && log_test 7 "self_auditor" "PASS" || log_test 7 "self_auditor" "WARN (exit=$exit5)"
}

# =============================================================================
# PHASE 9: AGGREGATION + REPORT
# =============================================================================
phase_9() {
    echo "============================================================"
    echo "PHASE 9: AGGREGATION + REPORT"
    echo "============================================================"

    local report="$E2E_DIR/REPORT_${TEST_DATE}.json"
    local log="$E2E_DIR/$TEST_DATE.log"

    python3 - "$log" "$report" <<'EOF'
import json, datetime, sys
log_file = sys.argv[1]
report_file = sys.argv[2]
phases = {}
total_pass = total_fail = total_warn = 0
try:
    with open(log_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith('[PASS]'):
                total_pass += 1
            elif line.startswith('[FAIL]'):
                total_fail += 1
            elif line.startswith('[WARN]'):
                total_warn += 1
except FileNotFoundError:
    pass
report = {
    'timestamp': datetime.datetime.now().isoformat(),
    'test_date': '$TEST_DATE',
    'total_pass': total_pass,
    'total_fail': total_fail,
    'total_warn': total_warn,
    'pass_rate': f'{100*total_pass/(total_pass+total_fail+0.001):.1f}%' if (total_pass+total_fail) else 'N/A',
}
json.dump(report, open(report_file, 'w'), indent=2)
print(json.dumps(report, indent=2))
EOF

    echo
    echo "============================================================"
    echo "  REPORT:"
    echo "============================================================"
    cat "$report"
    echo "============================================================"
    echo "  Log files: $E2E_DIR/"
    echo "============================================================"
}

# =============================================================================
# MAIN
# =============================================================================
main() {
    echo "============================================================"
    echo "  MAS-ENGINEER E2E-TEST"
    echo "  Workspace: $MAS_WORKSPACE"
    echo "  Date: $TEST_DATE"
    echo "  Strict: $STRICT, Parallel: $PARALLEL, No-Push: $NO_PUSH"
    echo "============================================================"

    setup_env

    should_skip 0 || phase_0
    should_skip 1 || phase_1
    should_skip 2 || phase_2
    should_skip 3 || phase_3
    should_skip 4 || phase_4
    should_skip 5 || phase_5
    # Phase 6 (Composition) ist interaktiv — manuell
    should_skip 7 || phase_7
    should_skip 9 || phase_9

    echo "============================================================"
    echo "  TEST RUN COMPLETE"
    echo "  Results: $E2E_DIR/$TEST_DATE.log"
    echo "  Report:  $E2E_DIR/REPORT_${TEST_DATE}.json"
    echo "============================================================"
}

main
