"""Optional command modules. Each may define register_cli(subparsers)."""

from __future__ import annotations

import importlib

_MODULES = ("quality", "context", "export", "check")


def register_commands(subparsers) -> None:
    for name in _MODULES:
        try:
            mod = importlib.import_module(f"palimpsest.{name}")
        except ImportError:
            continue
        register = getattr(mod, "register_cli", None)
        if callable(register):
            register(subparsers)
