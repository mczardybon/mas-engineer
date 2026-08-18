"""
test_dev_pre_push_validator_check21.py — R110-198.

3-test pytest suite for the Check 21 bash block added to
recipe/instructions/sub_mas-pre-push-validator.md in R110-198.

Check 21: MQ topic caller-chain audit.  Goal: every MQ
topic that is PRODUCED (mq.enqueue() call in tools/ or
recipe/) must have at least one CONSUMER (workflow recipe,
sub_recipe with --processor, or test that verifies the
consumer-side contract).  Prevents the R110-194-B bug
pattern from recurring: a topic is defined, a producer
publishes to it, but nothing consumes it — so messages
sit in pending.ndjson forever and the producer is a
dead end.

We do NOT run the full pre-push validator (it's a
goose recipe that takes ~120s).  We extract just the
Check 21 bash block from the validator's instructions
and run it on (a) the live repo, (b) a fixture with
only consumers (PASS), and (c) a fixture with a
dead-end producer (BLOCK).  The bash block is the
authoritative behavior — the tests are regression-guards
for the regex / output-format / exit-code contracts.

The 3 tests:

  1. test_check21_passes_on_live_repo — current repo
     state has 2 producer topics (dispatches,
     monitor.health.degraded) and BOTH have caller-chains
     (R110-156 dispatch_done is consumed by the
     dashboard, monitor.health.degraded is consumed
     by recovery defib).  Block exits 0.

  2. test_check21_blocks_on_dead_end_topic — fixture
     with a producer that has no caller-chain (the
     fictional "dead_end_topic_no_consumer" and
     "another_dead_end_topic") → block exits 1 with
     both uncovered topics listed.

  3. test_check21_passes_on_balanced_fixture — fixture
     with a producer AND a consumer reference for
     that topic (via a mock wf_*.yaml) → block exits 0.

Run with:
    python3 -m pytest tests/test_dev_pre_push_validator_check21.py -v
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
VALIDATOR_INSTRUCTIONS = (
    REPO_ROOT / "recipe" / "instructions" / "sub_mas-pre-push-validator.md"
)


# ─── Helpers ─────────────────────────────────────────────────────

def _extract_check21_bash() -> str:
    """Extract the Check 21 bash block from the validator's
    instructions.  Block is delimited by ```bash ... ``` and
    starts with `# Check 21:`.  This is the AUTHORITATIVE
    block — if the validator's instructions change, the
    test will pick up the new block and the test will
    need to be updated."""
    text = VALIDATOR_INSTRUCTIONS.read_text()
    # Find all ```bash blocks, pick the one that starts
    # with `# Check 21:`
    for m in re.finditer(r"```bash\n(.*?)```", text, re.DOTALL):
        if m.group(1).lstrip().startswith("# Check 21:"):
            return m.group(1) + "\n"
    raise RuntimeError(
        "Check 21 bash block not found in "
        f"{VALIDATOR_INSTRUCTIONS}.  Has the validator been refactored?"
    )


def _run_check21(workdir: Path) -> subprocess.CompletedProcess:
    """Run the Check 21 bash block in `workdir`.  Returns
    the CompletedProcess.  workdir should contain a tools/
    and recipe/ subdir."""
    bash = _extract_check21_bash()
    script = workdir / "_check21_runner.sh"
    script.write_text(bash)
    try:
        return subprocess.run(
            ["bash", str(script)],
            capture_output=True, text=True,
            cwd=str(workdir),
            timeout=30,
        )
    finally:
        script.unlink(missing_ok=True)


@pytest.fixture
def consumer_fixture(tmp_path):
    """A fixture with a producer AND a consumer reference
    for the same topic.  Used by test 3 (balanced fixture
    PASSES)."""
    tools = tmp_path / "tools"
    tools.mkdir()
    # Producer: dev_myapp.py uses _mq.enqueue with a string
    # literal that lives on the next line (the mas-engineer
    # call-site pattern).
    (tools / "dev_myapp.py").write_text(
        "def _mq(): pass\n"
        "def publish():\n"
        "    _mq.enqueue(\n"
        "        'my.app.events',\n"
        "        {},\n"
        "    )\n"
    )
    # Consumer: a mock workflow recipe that mentions the
    # topic in --topic=  (Check 21 grep pattern: `wf_*.yaml`).
    recipe_wf = tmp_path / "recipe"
    recipe_wf.mkdir()
    (recipe_wf / "wf_my_app.yaml").write_text(
        "name: wf_my_app\n"
        "version: 1.0.0\n"
        "prompt: |\n"
        "  Run dev_mq_consumer --topic my.app.events\n"
    )
    return tmp_path


@pytest.fixture
def dead_end_fixture(tmp_path):
    """A fixture with a producer that has NO consumer
    reference anywhere.  Used by test 2 (dead-end
    fixture BLOCKS)."""
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "dev_orphan.py").write_text(
        "def _mq(): pass\n"
        "def publish():\n"
        "    _mq.enqueue(\n"
        "        'dead_end_topic_no_consumer',\n"
        "        {},\n"
        "    )\n"
    )
    # Also a *_TOPIC constant style
    (tools / "dev_orphan2.py").write_text(
        "MQ_TOPIC = 'another_dead_end_topic'\n"
        "def _mq(): pass\n"
        "def publish():\n"
        "    _mq.enqueue(MQ_TOPIC, {})\n"
    )
    # Empty recipe dir so grep -l on wf_*.yaml returns nothing
    (tmp_path / "recipe").mkdir()
    return tmp_path


# ─── Tests ───────────────────────────────────────────────────────

def test_check21_passes_on_live_repo():
    """The current repo has 2 producer topics (dispatches,
    monitor.health.degraded) and BOTH have caller-chains.
    Run the Check 21 bash block in REPO_ROOT and expect
    exit 0."""
    r = _run_check21(REPO_ROOT)
    # On PASS the block exits 0 and prints "all N producer
    # topic(s) have caller chains"
    assert r.returncode == 0, (
        f"Check 21 unexpectedly BLOCKED on live repo:\n"
        f"STDOUT: {r.stdout}\n"
        f"STDERR: {r.stderr}"
    )
    assert "caller chains" in r.stdout
    # Both known live producers should be mentioned
    assert "dispatches" in r.stdout, (
        f"expected 'dispatches' in output, got: {r.stdout}"
    )
    assert "monitor.health.degraded" in r.stdout, (
        f"expected 'monitor.health.degraded' in output, got: {r.stdout}"
    )


def test_check21_blocks_on_dead_end_topic(dead_end_fixture):
    """A fixture with a producer that has NO consumer-side
    caller chain must trigger Check 21 BLOCK.  Exit 1
    with both uncovered topics listed in the error."""
    r = _run_check21(dead_end_fixture)
    assert r.returncode == 1, (
        f"Check 21 should BLOCK on dead-end fixture:\n"
        f"STDOUT: {r.stdout}\n"
        f"STDERR: {r.stderr}"
    )
    # Both dead-end topics must be listed in the BLOCK
    # error message
    assert "dead_end_topic_no_consumer" in r.stdout, (
        f"expected 'dead_end_topic_no_consumer' in BLOCK output: {r.stdout}"
    )
    assert "another_dead_end_topic" in r.stdout, (
        f"expected 'another_dead_end_topic' in BLOCK output: {r.stdout}"
    )
    # Uncovered topics line is the action item
    assert "Uncovered topics" in r.stdout
    # Fix hint must point at R110-195 (the pattern to copy)
    assert "R110-195" in r.stdout, (
        f"expected R110-195 fix-hint in BLOCK output: {r.stdout}"
    )


def test_check21_passes_on_balanced_fixture(consumer_fixture):
    """A fixture with a producer AND a matching workflow
    recipe must PASS.  This is the round-trip: every
    topic has BOTH a producer call-site AND a consumer
    reference.  Check 21 sees the wf_*.yaml and exits 0."""
    r = _run_check21(consumer_fixture)
    assert r.returncode == 0, (
        f"Check 21 should PASS on balanced fixture:\n"
        f"STDOUT: {r.stdout}\n"
        f"STDERR: {r.stderr}"
    )
    # The single producer topic should be acknowledged
    assert "my.app.events" in r.stdout, (
        f"expected 'my.app.events' in output: {r.stdout}"
    )
    # The hits-count must be > 0
    m = re.search(
        r"topic 'my\.app\.events' has (\d+) caller-chain reference", r.stdout
    )
    assert m, f"expected hits-count line for my.app.events: {r.stdout}"
    assert int(m.group(1)) >= 1
