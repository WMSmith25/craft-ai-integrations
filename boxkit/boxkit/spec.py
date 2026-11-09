"""Load and validate Boxkit edit specifications (YAML or JSON)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class SpecError(ValueError):
    """Invalid or unsupported spec content."""


@dataclass
class OutputSettings:
    path: str = "output.mp4"
    width: int = 1280
    height: int = 720
    fps: float = 25.0
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    crf: int | None = 23
    video_bitrate: str | None = None
    audio_bitrate: str = "192k"
    pixel_format: str = "yuv420p"
    preset: str | None = "medium"


@dataclass
class ClipSource:
    """File path, or lavfi generator for synthetic / test media."""

    path: str | None = None
    lavfi_video: str | None = None
    lavfi_audio: str | None = None


@dataclass
class ClipSpec:
    id: str
    source: ClipSource
    in_point: float = 0.0
    out_point: float | None = None
    duration: float | None = None
    speed: float = 1.0


@dataclass
class TransitionSpec:
    after_clip: str
    kind: str = "fade"
    duration: float = 0.5


@dataclass
class CropResize:
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None
    aspect: str | None = None
    mode: str = "fit"


@dataclass
class TextOverlay:
    text: str
    start: float = 0.0
    end: float | None = None
    x: str = "(w-text_w)/2"
    y: str = "h-80"
    fontsize: int = 36
    fontcolor: str = "white"
    box: bool = True
    boxcolor: str = "black@0.5"


@dataclass
class AudioTrack:
    id: str
    source: ClipSource
    in_point: float = 0.0
    out_point: float | None = None
    gain_db: float = 0.0
    offset_seconds: float = 0.0


@dataclass
class DuckingSpec:
    enabled: bool = False
    voice_track: str | None = None
    music_tracks: list[str] = field(default_factory=list)
    threshold: float = 0.02
    ratio: float = 6.0
    attack_ms: float = 20.0
    release_ms: float = 400.0
    makeup_db: float = 0.0


@dataclass
class LoudnessSpec:
    enabled: bool = False
    target_lufs: float = -14.0
    true_peak_dbtp: float = -1.0
    # Peak normalize (SoundCraft CLI default is -0.1 dBFS); maps to volume filter when loudnorm off.
    peak_normalize_dbfs: float | None = None


@dataclass
class ColorFilter:
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    gamma: float = 1.0


@dataclass
class EditSpec:
    version: int
    output: OutputSettings
    clips: list[ClipSpec]
    transitions: list[TransitionSpec] = field(default_factory=list)
    crop_resize: CropResize | None = None
    overlays: list[TextOverlay] = field(default_factory=list)
    audio_tracks: list[AudioTrack] = field(default_factory=list)
    ducking: DuckingSpec = field(default_factory=DuckingSpec)
    loudness: LoudnessSpec = field(default_factory=LoudnessSpec)
    color: ColorFilter | None = None
    use_video_audio: bool = True
    adapters: dict[str, Any] = field(default_factory=dict)


def _parse_source(raw: Any, ctx: str) -> ClipSource:
    if isinstance(raw, str):
        return ClipSource(path=raw)
    if not isinstance(raw, dict):
        raise SpecError(f"{ctx}: source must be a path string or object")
    path = raw.get("path") or raw.get("file")
    lavfi_video = raw.get("lavfi_video") or raw.get("lavfi")
    lavfi_audio = raw.get("lavfi_audio")
    if not any([path, lavfi_video, lavfi_audio]):
        raise SpecError(f"{ctx}: source needs path, lavfi_video, or lavfi_audio")
    return ClipSource(path=path, lavfi_video=lavfi_video, lavfi_audio=lavfi_audio)


def _load_raw(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise SpecError("spec root must be a mapping")
    return data


def parse_spec_dict(data: dict[str, Any], base_dir: Path | None = None) -> EditSpec:
    version = int(data.get("version", 1))
    if version != 1:
        raise SpecError(f"unsupported spec version {version} (only 1)")

    out_raw = data.get("output") or {}
    output = OutputSettings(
        path=str(out_raw.get("path", "output.mp4")),
        width=int(out_raw.get("width", 1280)),
        height=int(out_raw.get("height", 720)),
        fps=float(out_raw.get("fps", 25)),
        video_codec=str(out_raw.get("video_codec", "libx264")),
        audio_codec=str(out_raw.get("audio_codec", "aac")),
        crf=out_raw.get("crf", 23),
        video_bitrate=out_raw.get("video_bitrate"),
        audio_bitrate=str(out_raw.get("audio_bitrate", "192k")),
        pixel_format=str(out_raw.get("pixel_format", "yuv420p")),
        preset=out_raw.get("preset", "medium"),
    )

    timeline = data.get("timeline") or data
    clips_raw = timeline.get("clips") or data.get("clips")
    if not clips_raw:
        raise SpecError("timeline.clips is required")
    clips: list[ClipSpec] = []
    for i, c in enumerate(clips_raw):
        if not isinstance(c, dict):
            raise SpecError(f"clip {i} must be a mapping")
        cid = str(c.get("id", f"clip{i}"))
        src = _parse_source(c.get("source") or c.get("src"), f"clip {cid}")
        if src.path and base_dir and not Path(src.path).is_absolute():
            src.path = str((base_dir / src.path).resolve())
        clips.append(
            ClipSpec(
                id=cid,
                source=src,
                in_point=float(c.get("in", c.get("in_point", 0))),
                out_point=c.get("out", c.get("out_point")),
                duration=c.get("duration"),
                speed=float(c.get("speed", 1.0)),
            )
        )

    transitions: list[TransitionSpec] = []
    for t in timeline.get("transitions") or data.get("transitions") or []:
        transitions.append(
            TransitionSpec(
                after_clip=str(t["after"]),
                kind=str(t.get("kind", t.get("type", "fade"))),
                duration=float(t.get("duration", 0.5)),
            )
        )

    crop_resize = None
    cr = data.get("crop_resize") or data.get("video", {}).get("crop_resize")
    if cr:
        crop_resize = CropResize(
            x=cr.get("x"),
            y=cr.get("y"),
            width=cr.get("width"),
            height=cr.get("height"),
            aspect=cr.get("aspect"),
            mode=str(cr.get("mode", "fit")),
        )

    overlays: list[TextOverlay] = []
    for o in data.get("overlays") or data.get("text_overlays") or []:
        overlays.append(
            TextOverlay(
                text=str(o["text"]),
                start=float(o.get("start", 0)),
                end=o.get("end"),
                x=str(o.get("x", "(w-text_w)/2")),
                y=str(o.get("y", "h-80")),
                fontsize=int(o.get("fontsize", 36)),
                fontcolor=str(o.get("fontcolor", "white")),
                box=bool(o.get("box", True)),
                boxcolor=str(o.get("boxcolor", "black@0.5")),
            )
        )

    audio_tracks: list[AudioTrack] = []
    audio_sec = data.get("audio") or {}
    for a in audio_sec.get("tracks") or data.get("audio_tracks") or []:
        tid = str(a.get("id", f"audio{len(audio_tracks)}"))
        src = _parse_source(a.get("source") or a.get("src"), f"audio track {tid}")
        if src.path and base_dir and not Path(src.path).is_absolute():
            src.path = str((base_dir / src.path).resolve())
        audio_tracks.append(
            AudioTrack(
                id=tid,
                source=src,
                in_point=float(a.get("in", 0)),
                out_point=a.get("out"),
                gain_db=float(a.get("gain_db", a.get("gain", 0))),
                offset_seconds=float(a.get("offset", a.get("offset_seconds", 0))),
            )
        )

    duck_raw = audio_sec.get("ducking") or data.get("ducking") or {}
    ducking = DuckingSpec(
        enabled=bool(duck_raw.get("enabled", False)),
        voice_track=duck_raw.get("voice_track"),
        music_tracks=list(duck_raw.get("music_tracks") or []),
        threshold=float(duck_raw.get("threshold", 0.02)),
        ratio=float(duck_raw.get("ratio", 6)),
        attack_ms=float(duck_raw.get("attack_ms", 20)),
        release_ms=float(duck_raw.get("release_ms", 400)),
        makeup_db=float(duck_raw.get("makeup_db", 0)),
    )

    loud_raw = audio_sec.get("loudness") or data.get("loudness") or {}
    loudness = LoudnessSpec(
        enabled=bool(loud_raw.get("enabled", False)),
        target_lufs=float(loud_raw.get("target_lufs", -14)),
        true_peak_dbtp=float(loud_raw.get("true_peak_dbtp", -1)),
        peak_normalize_dbfs=loud_raw.get("peak_normalize_dbfs"),
    )

    color = None
    col = data.get("color") or data.get("video", {}).get("color")
    if col:
        color = ColorFilter(
            brightness=float(col.get("brightness", 0)),
            contrast=float(col.get("contrast", 1)),
            saturation=float(col.get("saturation", 1)),
            gamma=float(col.get("gamma", 1)),
        )

    use_video_audio = bool(audio_sec.get("use_video_audio", data.get("use_video_audio", True)))
    adapters = dict(data.get("adapters") or {})

    return EditSpec(
        version=version,
        output=output,
        clips=clips,
        transitions=transitions,
        crop_resize=crop_resize,
        overlays=overlays,
        audio_tracks=audio_tracks,
        ducking=ducking,
        loudness=loudness,
        color=color,
        use_video_audio=use_video_audio,
        adapters=adapters,
    )


def load_spec(path: str | Path) -> EditSpec:
    p = Path(path).resolve()
    if not p.is_file():
        raise SpecError(f"spec file not found: {p}")
    return parse_spec_dict(_load_raw(p), base_dir=p.parent)
