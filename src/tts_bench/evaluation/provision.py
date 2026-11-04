"""`provision` (idempotent projects/tasks), `purge-voice`, `inspect`, `annotator`."""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import labelconfig, scales
from .batch import ScaleMismatch, load_batch, paths
from .blind import read_mapping, write_mapping
from .lsclient import LSClient, LSError
from .tasks import PROJECTS

DESC_PREFIX = "scale_hash="
ANNOTATOR_RE = re.compile(r"^a\d{2,}$")


class UsageError(ValueError):
    """Bad arguments (CLI exit code 2)."""


def provision(client: LSClient, out_dir: str | Path, storage_path: str, wait_timeout: float = 120.0) -> dict:
    p = paths(out_dir)
    batch = load_batch(out_dir)
    if batch is None or not p["tasks"].exists():
        raise UsageError("no batch prepared; run `prepare` first")
    if batch["scale_hash"] != scales.scale_hash():
        raise ScaleMismatch("scale definitions differ from the frozen batch")
    client.wait_healthy(wait_timeout)
    tasks = json.loads(p["tasks"].read_text(encoding="utf-8"))
    existing = {pr["title"]: pr for pr in client.list_projects()}
    report = {}
    for key in PROJECTS:
        title = labelconfig.TITLES[key]
        proj = existing.get(title)
        if proj is None:
            proj = client.create_project(title, labelconfig.label_config(key), labelconfig.instructions(),
                                         labelconfig.SAMPLING, DESC_PREFIX + scales.scale_hash())
        elif (proj.get("description") or "") != DESC_PREFIX + scales.scale_hash():
            raise ScaleMismatch(f"project {title!r} was created with different scale definitions")
        pid = proj["id"]
        if not any((s.get("path") or "").rstrip("/") == storage_path.rstrip("/") for s in client.list_storages(pid)):
            client.create_local_storage(pid, storage_path, "Audio ciego")
        have = {t.get("data", {}).get("item_id") for t in client.list_tasks(pid)}
        missing = [t for t in tasks.get(key, []) if t["item_id"] not in have]
        if missing:
            client.import_tasks(pid, missing)
        report[key] = {"created": len(missing), "skipped": len(tasks.get(key, [])) - len(missing)}
    return report


def inspect(client: LSClient) -> dict:
    out = {}
    projects = {pr["title"]: pr for pr in client.list_projects()}
    for key in PROJECTS:
        pr = projects.get(labelconfig.TITLES[key])
        out[key] = [t["data"] for t in client.list_tasks(pr["id"])] if pr else []
    return out


_SET_PASSWORD_CODE = (
    "import sys\n"
    "from users.models import User\n"
    "email, pw = sys.stdin.read().split('\\n')[:2]\n"
    "u = User.objects.get(email=email); u.set_password(pw); u.save()\n"
    "print('PASSWORD_SET' if u.check_password(pw) else 'PASSWORD_FAILED')\n"
)


def set_password_in_container(email: str, password: str, container: str | None = None) -> None:
    """Label Studio's users API ignores `password`, so set it with Django inside the container (stdin, not argv)."""
    container = container or os.environ.get("LS_CONTAINER", "tts-bench-eval-label-studio-1")
    cmd = ["docker", "exec", "-i", container, "sh", "-c",
           f"cd /label-studio && python label_studio/manage.py shell -c \"{_SET_PASSWORD_CODE}\""]
    try:
        r = subprocess.run(cmd, input=f"{email}\n{password}\n", capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UsageError(f"could not set the password through docker: {exc}") from None
    if "PASSWORD_SET" not in r.stdout:
        raise UsageError(f"could not set the password in container {container!r}: {(r.stderr or r.stdout)[-300:]}")


def create_annotator(client: LSClient, annotator_id: str, set_password=set_password_in_container,
                     reset: bool = False) -> tuple[str, str]:
    if not ANNOTATOR_RE.match(annotator_id):
        raise UsageError("annotator id must look like a01, a02, ...")
    email = f"{annotator_id}@eval.invalid"
    exists = any(u.get("email") == email for u in client.list_users())
    if exists and not reset:
        raise UsageError(f"annotator {annotator_id} already exists (use --reset-password to issue a new password)")
    if not exists:
        client.create_user(email, secrets.token_urlsafe(24))
    password = secrets.token_urlsafe(12)
    set_password(email, password)
    return email, password


def purge_voice(client: LSClient | None, out_dir: str | Path, voice: str) -> dict:
    """Consent withdrawal: delete a voice's served audio, its tasks and its mapping rows."""
    p = paths(out_dir)
    rows = read_mapping(p["mapping"]) if p["mapping"].exists() else []

    def hit(r) -> bool:
        for meta in (r, r.a, r.b):
            m = meta if isinstance(meta, dict) else (meta.__dict__ if meta is not None else {})
            v, e = m.get("voice"), m.get("engine")
            if v == voice or (e and v and f"{e}/{v}" == voice):
                return True
        return False

    doomed = [r for r in rows if hit(r)]
    doomed_ids = {r.item_id for r in doomed}
    files = {f for r in doomed for f in r.served_files}
    for f in files:
        (p["served"] / f).unlink(missing_ok=True)
    removed_tasks = 0
    if client is not None and doomed_ids:
        titles = {k: labelconfig.TITLES[k] for k in PROJECTS}
        projects = {pr["title"]: pr for pr in client.list_projects()}
        for key, title in titles.items():
            pr = projects.get(title)
            if not pr:
                continue
            for t in client.list_tasks(pr["id"]):
                if t.get("data", {}).get("item_id") in doomed_ids:
                    client.delete_task(t["id"])
                    removed_tasks += 1
    write_mapping(p["mapping"], [r for r in rows if r.item_id not in doomed_ids])
    if p["tasks"].exists():
        tf = json.loads(p["tasks"].read_text(encoding="utf-8"))
        tf = {k: [t for t in v if t["item_id"] not in doomed_ids] for k, v in tf.items()}
        p["tasks"].write_text(json.dumps(tf, ensure_ascii=False, indent=1), encoding="utf-8")
    record = {"voice": voice, "purged_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "items": len(doomed_ids), "files": len(files), "ls_tasks": removed_tasks}
    with (p["private"] / "purges.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return record
