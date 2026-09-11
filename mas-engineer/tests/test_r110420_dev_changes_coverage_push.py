"""R110-420 — coverage-push r4: tools/dev_changes.py 0% → ~95%.

Pure-stdlib CLI module, 350 stmts, currently 0% covered
(except indirectly via dev_editor tests that mock it).

Targets:
- resolve_state_dir() both arms (--workspace arg + default)
- init_state() create-from-scratch + load-existing
- load() legacy-list-format migration (R110-233 era)
- save() round-trip
- add_change() default-fill + stats update + last_24h math
- show_status() with-empty / with-data
- show_history() default + custom limit + empty
- show_change() found + not-found
- generate_rollback() with-backup + without-backup + not-found
- mark_rolled_back() found + not-found
- add_cli() json-as-arg + json-from-stdin + fallback-on-bad-json
- main() all 6 CLI commands + no-args help + unknown-cmd exit 1
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Module under test
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import dev_changes as dc  # noqa: E402


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """Redirect STATE_DIR/CHANGES_FILE to a tmp dir."""
    mase = tmp_path / ".mase"
    mase.mkdir()
    monkeypatch.setattr(dc, "STATE_DIR", mase)
    monkeypatch.setattr(dc, "CHANGES_FILE", mase / "changes.json")
    return mase


# =============================================================================
# resolve_state_dir (line 26)
# =============================================================================
class TestResolveStateDir:
    def test_workspace_arg(self, monkeypatch, tmp_path):
        """--workspace flag wins over default."""
        ws = tmp_path / "custom"
        monkeypatch.setattr(sys, "argv", ["dev_changes.py", "--workspace", str(ws), "--status"])
        out = dc.resolve_state_dir()
        assert out == (ws / ".mase").resolve()

    def test_default_no_workspace_arg(self, monkeypatch):
        """No --workspace → parent.parent/.mase resolved."""
        monkeypatch.setattr(sys, "argv", ["dev_changes.py", "--status"])
        out = dc.resolve_state_dir()
        # parent.parent = mas-engineer-cleanup/, /mase is appended
        assert out.name == ".mase"
        assert out.is_absolute()


# =============================================================================
# init_state (line 38)
# =============================================================================
class TestInitState:
    def test_creates_empty_when_missing(self, ws):
        """No changes.json → init_state() creates one with defaults."""
        assert not (ws / "changes.json").exists()
        data = dc.init_state()
        assert "metadata" in data
        assert data["metadata"]["total_changes"] == 0
        assert data["changes"] == []
        assert (ws / "changes.json").exists()

    def test_returns_existing_when_present(self, ws):
        """If changes.json exists, init_state() should just load it."""
        pre = {
            "metadata": {"agent": "x", "version": "0", "last_updated": "t", "total_changes": 3},
            "changes": [{"id": "ch_001"}],
            "stats": {"harden": 1, "evolve": 0, "patch": 0, "other": 0,
                      "rolled_back": 0, "last_24h": 0},
        }
        (ws / "changes.json").write_text(json.dumps(pre))
        data = dc.init_state()
        assert data["metadata"]["total_changes"] == 3


# =============================================================================
# load + legacy migration (line 61)
# =============================================================================
class TestLoad:
    def test_loads_current_format(self, ws):
        data = {"metadata": {"agent": "x", "total_changes": 1}, "changes": [{"id": "ch_001"}],
                "stats": {"harden": 0, "evolve": 0, "patch": 0, "other": 0,
                          "rolled_back": 0, "last_24h": 0}}
        (ws / "changes.json").write_text(json.dumps(data))
        loaded = dc.load()
        assert loaded["metadata"]["agent"] == "x"
        assert loaded["changes"][0]["id"] == "ch_001"

    def test_migrates_legacy_list(self, ws):
        """Pre-R110-233 list format → wrapped in dict."""
        legacy = [
            {"timestamp": "2026-08-01T00:00:00Z", "action": "CREATE",
             "description": "sub_mas-clone init", "directive": "R110-99"},
            {"timestamp": "2026-08-02T00:00:00Z", "action": "APPLY",
             "description": "apply_directive foo", "directive": "R110-100"},
        ]
        (ws / "changes.json").write_text(json.dumps(legacy))
        loaded = dc.load()
        assert "metadata" in loaded
        assert loaded["metadata"].get("migrated_from_legacy_list") is True
        assert len(loaded["changes"]) == 2
        assert loaded["changes"][0]["id"] == "ch_legacy_001"
        assert loaded["changes"][0]["type"] == "legacy"
        assert loaded["changes"][0]["legacy_data"]["action"] == "CREATE"

    def test_init_when_no_file(self, ws):
        """load() on missing file → delegates to init_state()."""
        loaded = dc.load()
        assert loaded["metadata"]["total_changes"] == 0


# =============================================================================
# save (line 121)
# =============================================================================
class TestSave:
    def test_save_updates_metadata_and_total(self, ws):
        dc.init_state()
        data = dc.load()
        data["changes"].append({"id": "ch_001"})
        dc.save(data)
        re = dc.load()
        assert re["metadata"]["total_changes"] == 1
        assert "last_updated" in re["metadata"]


# =============================================================================
# add_change (line 129)
# =============================================================================
class TestAddChange:
    def test_first_change_gets_ch_001(self, ws):
        dc.init_state()
        e = dc.add_change({"file": "x.py", "von": "1", "nach": "2", "grund": "test"})
        assert e["id"] == "ch_001"
        assert e["file"] == "x.py"
        assert e["rolled_back"] is False

    def test_increments_id_after_existing(self, ws):
        dc.init_state()
        dc.add_change({"file": "a.py"})
        e = dc.add_change({"file": "b.py"})
        assert e["id"] == "ch_002"

    def test_handles_legacy_ids_for_next_number(self, ws):
        """ch_legacy_005 + ch_legacy_007 → next = ch_008 (max-trailing-int)."""
        pre = {
            "metadata": {"agent": "x", "version": "0", "last_updated": "t",
                         "total_changes": 0, "migrated_from_legacy_list": True},
            "changes": [
                {"id": "ch_legacy_005", "timestamp": "2026-08-01T00:00:00Z"},
                {"id": "ch_legacy_007", "timestamp": "2026-08-02T00:00:00Z"},
            ],
            "stats": {"harden": 0, "evolve": 0, "patch": 0, "other": 0,
                      "rolled_back": 0, "last_24h": 0},
        }
        (ws / "changes.json").write_text(json.dumps(pre))
        e = dc.add_change({"file": "c.py"})
        assert e["id"] == "ch_008"

    def test_stats_update_known_art(self, ws):
        dc.init_state()
        dc.add_change({"file": "x.py", "art": "patch"})
        data = dc.load()
        assert data["stats"]["patch"] == 1

    def test_stats_unknown_art_routes_to_other(self, ws):
        dc.init_state()
        dc.add_change({"file": "x.py", "art": "totally_new_thing"})
        data = dc.load()
        assert data["stats"]["other"] == 1

    def test_default_user_is_marius(self, ws):
        dc.init_state()
        e = dc.add_change({"file": "x.py"})
        assert e["user"] == "Marius"

    def test_non_string_id_in_existing_changes(self, ws):
        """_id_num(c.get('id', 0)) branch: existing change with int id."""
        pre = {
            "metadata": {"agent": "x", "version": "0", "last_updated": "t",
                         "total_changes": 0},
            "changes": [
                {"id": 12345, "timestamp": "2026-08-01T00:00:00Z"},  # non-string id → _id_num returns 0
            ],
            "stats": {"harden": 0, "evolve": 0, "patch": 0, "other": 0,
                      "rolled_back": 0, "last_24h": 0},
        }
        (ws / "changes.json").write_text(json.dumps(pre))
        e = dc.add_change({"file": "x.py"})
        assert e["id"] == "ch_001"  # no integer found → fallback 0+1


# =============================================================================
# show_status / show_history / show_change / generate_rollback / mark_rolled_back
# =============================================================================
class TestShowStatus:
    def test_no_changes_yet(self, ws, capsys):
        dc.init_state()
        out = dc.show_status()
        assert "No changes yet" in out
        assert "CHANGE status" in out

    def test_with_changes(self, ws, capsys):
        dc.init_state()
        dc.add_change({"file": "x.py", "von": "1", "nach": "2", "grund": "test"})
        out = dc.show_status()
        assert "Last Change" in out
        assert "x.py" in out


class TestShowHistory:
    def test_empty(self, ws):
        dc.init_state()
        out = dc.show_history()
        assert "No changes yet" in out

    def test_default_limit(self, ws):
        dc.init_state()
        for i in range(15):
            dc.add_change({"file": f"f{i}.py"})
        out = dc.show_history()  # default 10
        assert "LAST CHANGES" in out
        # 15 entries, only last 10 shown
        assert out.count("ch_0") == 10

    def test_custom_limit(self, ws):
        dc.init_state()
        for i in range(5):
            dc.add_change({"file": f"f{i}.py"})
        out = dc.show_history(limit=3)
        assert out.count("ch_0") == 3

    def test_shows_rolled_back_marker(self, ws):
        dc.init_state()
        dc.add_change({"file": "x.py"})
        dc.mark_rolled_back("ch_001")
        out = dc.show_history()
        assert "🔙" in out


class TestShowChange:
    def test_found(self, ws):
        dc.init_state()
        dc.add_change({"file": "x.py"})
        out = dc.show_change("ch_001")
        assert "CHANGE #ch_001" in out
        assert "x.py" in out

    def test_not_found(self, ws):
        dc.init_state()
        out = dc.show_change("ch_999")
        assert "not found" in out


class TestGenerateRollback:
    def test_with_backup(self, ws):
        dc.init_state()
        dc.add_change({"file": "x.py", "backup": "/some/path"})
        out = dc.generate_rollback("ch_001")
        assert "ROLLBACK" in out
        assert "cp /some/path" in out

    def test_without_backup(self, ws):
        dc.init_state()
        dc.add_change({"file": "x.py"})  # no backup field
        out = dc.generate_rollback("ch_001")
        assert "No Backup" in out

    def test_not_found(self, ws):
        dc.init_state()
        out = dc.generate_rollback("ch_999")
        assert "not found" in out


class TestMarkRolledBack:
    def test_found(self, ws):
        dc.init_state()
        dc.add_change({"file": "x.py"})
        out = dc.mark_rolled_back("ch_001", reason="buggy")
        assert "rolled_back" in out
        data = dc.load()
        assert data["changes"][0]["rolled_back"] is True
        assert data["changes"][0]["rolled_back_reason"] == "buggy"
        assert data["stats"]["rolled_back"] == 1

    def test_not_found(self, ws):
        dc.init_state()
        out = dc.mark_rolled_back("ch_999")
        assert "not found" in out


# =============================================================================
# add_cli (line 301)
# =============================================================================
class TestAddCli:
    def test_json_as_arg(self, monkeypatch, ws):
        dc.init_state()
        payload = json.dumps({"file": "from-arg.py", "von": "a", "nach": "b"})
        monkeypatch.setattr(sys, "argv", ["dev_changes.py", "--add", payload])
        out = dc.add_cli()
        assert "from-arg.py" in out
        assert "ch_001" in out

    def test_fallback_when_bad_json_as_arg(self, monkeypatch, ws):
        """sys.argv[2] is not JSON → graceful fallback to bare-string entry."""
        dc.init_state()
        monkeypatch.setattr(sys, "argv", ["dev_changes.py", "--add", "not-a-json"])
        out = dc.add_cli()
        # The fallback treats sys.argv[2] as the file name
        assert "not-a-json" in out

    def test_json_from_stdin(self, monkeypatch, ws):
        dc.init_state()
        monkeypatch.setattr(sys, "argv", ["dev_changes.py", "--add"])
        monkeypatch.setattr(sys, "stdin", type("S", (), {
            "read": staticmethod(lambda: json.dumps({"file": "from-stdin.py"}))
        })())
        out = dc.add_cli()
        assert "from-stdin.py" in out


# =============================================================================
# main (line 315)
# =============================================================================
class TestMain:
    def test_no_args_prints_help(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_changes.py"])
        dc.main()
        out = capsys.readouterr().out
        assert "Usage" in out
        assert "--status" in out

    def test_unknown_command_exits_1(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["dev_changes.py", "--bogus"])
        with pytest.raises(SystemExit) as exc:
            dc.main()
        assert exc.value.code == 1

    def test_status_cmd(self, monkeypatch, ws, capsys):
        dc.init_state()
        monkeypatch.setattr(sys, "argv", ["dev_changes.py", "--status"])
        dc.main()
        out = capsys.readouterr().out
        assert "CHANGE status" in out

    def test_history_cmd_default(self, monkeypatch, ws, capsys):
        dc.init_state()
        dc.add_change({"file": "x.py"})
        monkeypatch.setattr(sys, "argv", ["dev_changes.py", "--history"])
        dc.main()
        out = capsys.readouterr().out
        assert "LAST CHANGES" in out

    def test_history_cmd_with_limit(self, monkeypatch, ws, capsys):
        dc.init_state()
        for i in range(5):
            dc.add_change({"file": f"f{i}.py"})
        monkeypatch.setattr(sys, "argv", ["dev_changes.py", "--history", "2"])
        dc.main()
        out = capsys.readouterr().out
        assert out.count("ch_0") == 2

    def test_add_cmd(self, monkeypatch, ws, capsys):
        dc.init_state()
        monkeypatch.setattr(sys, "argv", ["dev_changes.py", "--add",
                                          json.dumps({"file": "via-main.py"})])
        dc.main()
        out = capsys.readouterr().out
        assert "via-main.py" in out

    def test_get_cmd(self, monkeypatch, ws, capsys):
        dc.init_state()
        dc.add_change({"file": "x.py"})
        monkeypatch.setattr(sys, "argv", ["dev_changes.py", "--get", "ch_001"])
        dc.main()
        out = capsys.readouterr().out
        assert "CHANGE #ch_001" in out

    def test_rollback_cmd_with_backup(self, monkeypatch, ws, capsys):
        dc.init_state()
        dc.add_change({"file": "x.py", "backup": "/bk"})
        monkeypatch.setattr(sys, "argv", ["dev_changes.py", "--rollback", "ch_001"])
        dc.main()
        out = capsys.readouterr().out
        assert "ROLLBACK" in out

    def test_rollback_cmd_no_backup(self, monkeypatch, ws, capsys):
        dc.init_state()
        dc.add_change({"file": "x.py"})
        monkeypatch.setattr(sys, "argv", ["dev_changes.py", "--rollback", "ch_001"])
        dc.main()
        out = capsys.readouterr().out
        assert "No Backup" in out

    def test_mark_rolled_cmd_no_reason(self, monkeypatch, ws, capsys):
        dc.init_state()
        dc.add_change({"file": "x.py"})
        monkeypatch.setattr(sys, "argv", ["dev_changes.py", "--mark-rolled", "ch_001"])
        dc.main()
        out = capsys.readouterr().out
        assert "rolled_back" in out


# =============================================================================
# CLI subprocess smoke (catches sys.argv parsing edge cases)
# =============================================================================
class TestCliSubprocess:
    """Run the actual script as a subprocess to verify CLI dispatch end-to-end."""

    def test_help(self):
        r = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "tools" / "dev_changes.py")],
            capture_output=True, text=True,
        )
        assert "Usage" in r.stdout
        assert r.returncode == 0

    def test_status_subprocess_init_via_tmp_workspace(self, tmp_path):
        """--status with no prior state file → init_state() in subprocess.
        Uses cd to a tmp dir so resolve_state_dir() defaults to that dir/.mase.
        """
        script = Path(__file__).resolve().parents[1] / "tools" / "dev_changes.py"
        r = subprocess.run(
            [sys.executable, str(script), "--status"],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert r.returncode == 0
        assert "CHANGE status" in r.stdout

    def test_unknown_subprocess_exits_1(self):
        script = Path(__file__).resolve().parents[1] / "tools" / "dev_changes.py"
        r = subprocess.run(
            [sys.executable, str(script), "--bogus-cmd"],
            capture_output=True, text=True,
        )
        assert r.returncode == 1
        assert "Unknown" in r.stdout
