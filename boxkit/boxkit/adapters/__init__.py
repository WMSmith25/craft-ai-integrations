"""Optional bridges to FilmCraft / SoundCraft CLIs (off by default)."""

from __future__ import annotations

from boxkit.adapters.filmcraft_cli import filmcraft_preflight
from boxkit.adapters.soundcraft_cli import soundcraft_preflight
from boxkit.spec import EditSpec


def run_optional_adapters(spec: EditSpec, *, dry_run: bool = False) -> None:
    """Run enabled adapters before render; never required for core ffmpeg path."""
    fc = spec.adapters.get("filmcraft_cli") or {}
    if fc.get("enabled"):
        filmcraft_preflight(fc, dry_run=dry_run)
    sc = spec.adapters.get("soundcraft_cli") or {}
    if sc.get("enabled"):
        soundcraft_preflight(sc, dry_run=dry_run)
