"""Semantic validation beyond YAML parsing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from boxkit.plan import build_plan
from boxkit.spec import EditSpec, SpecError, load_spec


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


def validate_spec(spec: EditSpec) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not spec.clips:
        errors.append("timeline must include at least one clip")

    ids = {c.id for c in spec.clips}
    if len(ids) != len(spec.clips):
        errors.append("clip ids must be unique")

    for c in spec.clips:
        if c.speed <= 0:
            errors.append(f"clip {c.id}: speed must be positive")
        src = c.source
        if src.path:
            if not Path(src.path).is_file():
                errors.append(f"clip {c.id}: missing file {src.path}")
        elif not src.lavfi_video:
            errors.append(f"clip {c.id}: needs path or lavfi_video")

    for t in spec.transitions:
        if t.after_clip not in ids:
            errors.append(f"transition after unknown clip {t.after_clip}")
        if t.duration <= 0:
            errors.append(f"transition after {t.after_clip}: duration must be positive")

    if spec.ducking.enabled:
        if not spec.ducking.voice_track:
            errors.append("ducking.enabled requires voice_track")
        vt = spec.ducking.voice_track or ""
        if vt and vt not in ids and vt not in {a.id for a in spec.audio_tracks}:
            errors.append(f"ducking voice_track {vt} not found")
        for mid in spec.ducking.music_tracks:
            if mid not in ids and mid not in {a.id for a in spec.audio_tracks}:
                errors.append(f"ducking music_track {mid} not found")

    for a in spec.audio_tracks:
        if a.source.path and not Path(a.source.path).is_file():
            errors.append(f"audio {a.id}: missing file {a.source.path}")

    if spec.adapters.get("filmcraft_cli", {}).get("enabled"):
        warnings.append("filmcraft_cli adapter enabled: requires built filmcraft-cli binary")
    if spec.adapters.get("soundcraft_cli", {}).get("enabled"):
        warnings.append("soundcraft_cli adapter enabled: requires built soundcraft-cli binary")

    try:
        build_plan(spec)
    except Exception as e:  # noqa: BLE001 — surface planner bugs as validation errors
        errors.append(f"ffmpeg plan: {e}")

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def validate_path(path: str | Path) -> ValidationResult:
    try:
        spec = load_spec(path)
    except (SpecError, OSError) as e:
        return ValidationResult(ok=False, errors=[str(e)], warnings=[])
    return validate_spec(spec)
