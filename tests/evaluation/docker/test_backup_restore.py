"""annotate, export, backup, reset, restore, export again -> identical rows (SC-003). Opt-in: -m docker."""
import json
from pathlib import Path

import pytest

from .conftest import ROOT, api, make

pytestmark = pytest.mark.docker


def rows(path: Path):
    return [json.loads(l) for l in (path / "annotations.jsonl").read_text().splitlines()]


def test_backup_restore_roundtrip(env_file, tmp_path):
    try:
        assert make("eval-reset", stdin="RESET\n").returncode == 0
        assert make("eval-up").returncode == 0, "eval-up failed"
        assert make("eval-annotator", "ID=a01").returncode == 0
        users = api("/api/users/")
        uid = next(u["id"] for u in (users["results"] if isinstance(users, dict) else users) if u["email"] == "a01@eval.invalid")
        projects = api("/api/projects")
        projects = projects["results"] if isinstance(projects, dict) else projects
        mos = next(p for p in projects if p["title"].startswith("MOS"))
        tasks = api(f"/api/projects/{mos['id']}/tasks/?page_size=5")
        tasks = tasks["tasks"] if isinstance(tasks, dict) and "tasks" in tasks else tasks
        for t in tasks[:5]:
            result = [{"from_name": k, "to_name": "audio", "type": "rating", "value": {"rating": 4}}
                      for k in ("naturalidad", "pronunciacion", "prosodia")]
            api(f"/api/tasks/{t['id']}/annotations", "POST", {"result": result, "completed_by": uid, "lead_time": 3.0})
        before = tmp_path / "before"
        assert make("eval-export", f"OUT={before}").returncode == 0
        assert make("eval-backup").returncode == 0
        archive = sorted((ROOT / "backups" / "evaluation").glob("*.tar.gz"))[-1]
        assert make("eval-reset", stdin="RESET\n").returncode == 0
        assert make("eval-restore", f"FILE={archive}", env={"CONFIRM": "RESTORE"}).returncode == 0
        after = tmp_path / "after"
        assert make("eval-export", f"OUT={after}").returncode == 0
        assert rows(before) and rows(before) == rows(after)
    finally:
        make("eval-down")
