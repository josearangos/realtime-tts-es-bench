from __future__ import annotations

import importlib

_REGISTRY: dict[str, str] = {}


def register(name: str, target: str) -> None:
    _REGISTRY[name] = target


def registered_names() -> list[str]:
    return sorted(_REGISTRY)


def get_adapter(engine: str, **kwargs):
    if engine not in _REGISTRY:
        raise KeyError(f"Unknown engine '{engine}'. Registered: {registered_names()}")
    module, _, cls = _REGISTRY[engine].partition(":")
    return getattr(importlib.import_module(module), cls)(**kwargs)
