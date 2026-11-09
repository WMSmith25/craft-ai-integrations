"""Optional SoundCraft CLI adapter for offline audio bounce (disabled by default).

`soundcraft-cli convert` can normalize/resample audio (peak -0.1 dBFS by default). Boxkit maps
similar targets via ffmpeg loudnorm/alimiter; use this adapter to pre-bounce WAVs when the CLI is built.
"""

from __future__ import annotations

import shutil
from typing import Any

from boxkit.adapters.filmcraft_cli import AdapterError


def soundcraft_preflight(config: dict[str, Any], *, dry_run: bool = False) -> None:
    binary = str(config.get("binary", "soundcraft-cli"))
    if not config.get("enabled"):
        return
    if shutil.which(binary) is None:
        raise AdapterError(
            f"adapters.soundcraft_cli.enabled but {binary} not on PATH. "
            "Build from https://github.com/WMSmith25/soundcraft (apps/soundcraft-cli). "
            "No paid API; GPU is only for the desktop UI, not CLI bounce."
        )
    _ = dry_run
