"""Optional FilmCraft CLI adapter (disabled by default; requires local Rust build).

FilmCraft's native export path is `filmcraft-cli export` / `file.exportMedia` with JSON
`.fcproj` projects — not invoked automatically here. Enable only when the binary is present.
"""

from __future__ import annotations

import shutil
from typing import Any


class AdapterError(RuntimeError):
    pass


def filmcraft_preflight(config: dict[str, Any], *, dry_run: bool = False) -> None:
    binary = str(config.get("binary", "filmcraft-cli"))
    if not config.get("enabled"):
        return
    if shutil.which(binary) is None:
        raise AdapterError(
            f"adapters.filmcraft_cli.enabled but {binary} not on PATH. "
            "Build from https://github.com/WMSmith25/filmcraft (apps/filmcraft-cli). "
            "Boxkit uses ffmpeg directly; this adapter is optional."
        )
    if dry_run and config.get("project"):
        # Document-only: full fcproj round-trip is out of scope for boxkit v0.1.
        pass
