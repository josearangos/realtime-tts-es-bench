"""Merge results files into Markdown tables, refusing incomparable inputs."""

from __future__ import annotations

from pathlib import Path

from .results import read_results

NA = "not available"


class CompareRefusedError(ValueError):
    pass


def _get(env: dict, dotted: str):
    cur = env
    for part in dotted.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
    return cur


HARDWARE_FIELDS = ("hardware.cpu_model", "hardware.logical_cores", "hardware.ram_gib", "hardware.gpu_model",
                   "hardware.os_name", "hardware.os_release")
STRICT_FIELDS = ("corpus.corpus_version", "corpus.corpus_hash", "config.subset", "config.limit", "engine.locality")
INFO_FIELDS = ("software.python", "software.libraries", "config.thread_settings", "software.git_commit")


def _differs(files, fields) -> list[str]:
    out = []
    for f in fields:
        vals = []
        for r in files:
            v = _get(r.environment, f)
            if f == "hardware.os_release" and isinstance(v, str):
                v = v.split(".")[0]
            if f == "hardware.ram_gib" and isinstance(v, (int, float)):
                v = round(v)
            vals.append(v)
        if any(v != vals[0] for v in vals[1:]):
            out.append(f)
    return out


def _fmt(v, spec="{:.1f}") -> str:
    if v is None:
        return "-"
    if isinstance(v, str):
        return v
    return spec.format(v)


def _row(r) -> list[str]:
    s, res, env = r.summary, r.resources, r.environment
    ttfa = s["ttfa_ms"]
    thr = s["throughput_audio_s_per_s"]
    return [
        env["engine"]["name"],
        env["engine"]["voice"]["name"],
        env["engine"]["streaming_granularity"],
        _fmt(s.get("load_time_ms"), "{:.0f} ms"),
        NA if isinstance(ttfa, str) else f"{_fmt(ttfa['p50'])} / {_fmt(ttfa['p95'])} ms",
        f"{_fmt(s['rtf']['p50'], '{:.3f}')} / {_fmt(s['rtf']['p95'], '{:.3f}')}",
        thr if isinstance(thr, str) else _fmt(thr["median"], "{:.2f}"),
        _fmt(res.get("peak_ram_mib_final"), "{:.0f} MiB"),
        _fmt(res.get("cpu_percent_of_one_core"), "{:.0f}%"),
        _fmt(res.get("peak_vram_mib"), "{:.0f} MiB"),
        "yes" if s["reliable"] else "NO",
        str(s["n_ok"]),
    ]


HEADER = ["engine", "voice", "granularity", "load time", "TTFA p50/p95", "RTF p50/p95",
          "throughput (audio s/s)", "peak RAM", "CPU", "VRAM", "reliable", "n"]


def compare_results(paths, allow_mixed_hardware: bool = False) -> str:
    files = [read_results(Path(p)) for p in paths]
    strict = _differs(files, STRICT_FIELDS)
    if strict:
        raise CompareRefusedError("results differ in " + ", ".join(strict) + "; these cannot be compared")
    hw = _differs(files, HARDWARE_FIELDS)
    if hw and not allow_mixed_hardware:
        raise CompareRefusedError(
            "results come from different hardware (" + ", ".join(hw) + "); pass --allow-mixed-hardware to override"
        )
    lines = []
    if hw:
        lines.append(f"> Warning: mixed hardware ({', '.join(hw)}); figures are not directly comparable.\n")
    info = _differs(files, INFO_FIELDS)
    if info:
        lines.append(f"> Note: environments also differ in {', '.join(info)}.\n")
    for mode in ("cold", "warm"):
        group = [r for r in files if r.environment["config"]["mode"] == mode]
        if not group:
            continue
        lines += [f"## {mode}", "", "| " + " | ".join(HEADER) + " |", "|" + "---|" * len(HEADER)]
        lines += ["| " + " | ".join(_row(r)) + " |" for r in group]
        lines.append("")
    return "\n".join(lines)
