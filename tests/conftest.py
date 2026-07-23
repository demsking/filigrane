"""Pytest configuration and environment setup."""

import os
from pathlib import Path

# Ensure GI_TYPELIB_PATH includes devbox and system typelib paths before importing PyGObject / gi
_root = Path(__file__).resolve().parent.parent
_devbox_typelibs = _root / ".devbox/nix/profile/default/lib/girepository-1.0"

_candidates = [
  str(_devbox_typelibs),
  "/usr/lib64/girepository-1.0",
  "/usr/lib/girepository-1.0",
  "/usr/local/lib/girepository-1.0",
]

_existing = [p for p in os.environ.get("GI_TYPELIB_PATH", "").split(os.pathsep) if p]
_new_paths = [p for p in _candidates if Path(p).exists() and p not in _existing]

if _new_paths:
  os.environ["GI_TYPELIB_PATH"] = os.pathsep.join(_existing + _new_paths)
