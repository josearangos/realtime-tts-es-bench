import filecmp
import os
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKUP, RESTORE = ROOT / "evaluation/scripts/backup.sh", ROOT / "evaluation/scripts/restore.sh"


def tree(p: Path):
    return {str(f.relative_to(p)): f.read_bytes() for f in sorted(p.rglob("*")) if f.is_file()}


def setup(tmp_path):
    vol, out, bk = tmp_path / "vol", tmp_path / "out", tmp_path / "bk"
    (vol / "sub").mkdir(parents=True)
    (vol / "label_studio.sqlite3").write_bytes(b"db-bytes")
    (vol / "sub" / "m.bin").write_bytes(b"\x00\x01")
    (out / "served").mkdir(parents=True)
    (out / "private").mkdir()
    (out / "served" / "aaaaaaaaaaaa.wav").write_bytes(b"RIFFdata")
    (out / "private" / "mapping.jsonl").write_text('{"item_id": "x"}\n')
    (out / "batch.json").write_text('{"batch_id": "b-1"}')
    env = dict(os.environ, EVAL_VOLUME_DIR=str(vol), EVAL_OUTPUT_DIR=str(out), EVAL_BACKUP_DIR=str(bk))
    return vol, out, bk, env


def run(script, env, *args):
    return subprocess.run([str(script), *args], env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)


def test_backup_then_restore_roundtrip(tmp_path):
    vol, out, bk, env = setup(tmp_path)
    before_vol, before_out = tree(vol), tree(out)
    r = run(BACKUP, env)
    assert r.returncode == 0, r.stderr
    (archive,) = list(bk.glob("*.tar.gz"))
    with tarfile.open(archive) as t:
        assert "./MANIFEST.json" in t.getnames()
    for p in (vol, out):  # simulate eval-reset
        for f in sorted(p.rglob("*"), reverse=True):
            f.unlink() if f.is_file() else f.rmdir()
    r = run(RESTORE, env, str(archive))
    assert r.returncode == 0, r.stderr
    assert tree(vol) == before_vol and tree(out) == before_out


def test_restore_refuses_when_data_exists_without_confirmation(tmp_path):
    vol, out, bk, env = setup(tmp_path)
    run(BACKUP, env)
    (archive,) = list(bk.glob("*.tar.gz"))
    (vol / "label_studio.sqlite3").write_bytes(b"newer")
    r = run(RESTORE, env, str(archive))
    assert r.returncode != 0 and "CONFIRM=RESTORE" in r.stderr
    assert (vol / "label_studio.sqlite3").read_bytes() == b"newer"
    r = run(RESTORE, {**env, "CONFIRM": "RESTORE"}, str(archive))
    assert r.returncode == 0 and (vol / "label_studio.sqlite3").read_bytes() == b"db-bytes"


def test_corrupted_archive_rejected_and_nothing_changed(tmp_path):
    vol, out, bk, env = setup(tmp_path)
    run(BACKUP, env)
    (archive,) = list(bk.glob("*.tar.gz"))
    bad = tmp_path / "bad.tar.gz"
    bad.write_bytes(archive.read_bytes()[:40])
    snapshot = tree(vol), tree(out)
    r = run(RESTORE, {**env, "CONFIRM": "RESTORE"}, str(bad))
    assert r.returncode != 0 and "corrupted" in r.stderr or "cannot be extracted" in r.stderr
    assert (tree(vol), tree(out)) == snapshot


def test_tampered_member_rejected(tmp_path):
    vol, out, bk, env = setup(tmp_path)
    run(BACKUP, env)
    (archive,) = list(bk.glob("*.tar.gz"))
    work = tmp_path / "w"
    work.mkdir()
    with tarfile.open(archive) as t:
        t.extractall(work)
    (work / "ls-data" / "label_studio.sqlite3").write_bytes(b"tampered")
    tampered = tmp_path / "t.tar.gz"
    with tarfile.open(tampered, "w:gz") as t:
        t.add(work, arcname=".")
    r = run(RESTORE, {**env, "CONFIRM": "RESTORE"}, str(tampered))
    assert r.returncode != 0 and "checksum" in r.stderr
