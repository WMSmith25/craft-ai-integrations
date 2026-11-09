"""Build ffmpeg argv and filter_complex from an EditSpec."""

from __future__ import annotations

import math
import shlex
from dataclasses import dataclass

from boxkit.spec import ClipSpec, ColorFilter, CropResize, EditSpec, TextOverlay


@dataclass
class FfmpegPlan:
    argv: list[str]
    filter_complex: str
    output_path: str

    def shell_line(self) -> str:
        return shlex.join(self.argv)

    def describe(self) -> str:
        lines = ["# Boxkit ffmpeg plan", self.shell_line(), "", "# filter_complex:", self.filter_complex]
        return "\n".join(lines)


def _clip_duration(c: ClipSpec) -> float:
    if c.duration is not None:
        return float(c.duration)
    if c.out_point is not None:
        return max(0.0, float(c.out_point) - c.in_point)
    return 5.0


def _video_fit_filters(out: EditSpec, vin: str, vout: str) -> str:
    w, h, fps = out.output.width, out.output.height, out.output.fps
    cr = out.crop_resize
    steps: list[str] = []
    cur = vin
    if cr and cr.width and cr.height and cr.x is not None and cr.y is not None:
        steps.append(f"[{cur}]crop={cr.width}:{cr.height}:{cr.x}:{cr.y}[vc1]")
        cur = "vc1"
    elif cr and cr.width and cr.height:
        steps.append(f"[{cur}]crop={cr.width}:{cr.height}[vc1]")
        cur = "vc1"
    mode = (cr.mode if cr else "fit") or "fit"
    if mode == "fill":
        steps.append(f"[{cur}]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}[vf1]")
    else:
        steps.append(
            f"[{cur}]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black[vf1]"
        )
    cur = "vf1"
    steps.append(f"[{cur}]fps={fps}[{vout}]")
    return ";".join(steps)


def _color_eq(c: ColorFilter | None, vin: str, vout: str) -> str | None:
    if not c:
        return None
    return (
        f"[{vin}]eq=brightness={c.brightness}:contrast={c.contrast}:"
        f"saturation={c.saturation}:gamma={c.gamma}[{vout}]"
    )


def _drawtext_chain(overlays: list[TextOverlay], vin: str) -> tuple[str, str]:
    if not overlays:
        return "", vin
    chains: list[str] = []
    cur = vin
    for i, o in enumerate(overlays):
        nxt = f"vt{i}"
        end = f":enable='between(t,{o.start},{o.end})'" if o.end is not None else ""
        box = ":box=1:boxcolor=" + o.boxcolor if o.box else ":box=0"
        esc = o.text.replace("'", r"\'").replace(":", r"\:")
        chains.append(
            f"[{cur}]drawtext=text='{esc}':x={o.x}:y={o.y}:fontsize={o.fontsize}:"
            f"fontcolor={o.fontcolor}{box}{end}[{nxt}]"
        )
        cur = nxt
    return ";".join(chains), cur


def _xfade_kind(kind: str) -> str:
    k = kind.lower()
    mapping = {
        "fade": "fade",
        "fadeblack": "fadeblack",
        "fadewhite": "fadewhite",
        "dissolve": "dissolve",
        "wipeleft": "wipeleft",
        "wiperight": "wiperight",
    }
    return mapping.get(k, "fade")


def build_plan(spec: EditSpec, output_override: str | None = None) -> FfmpegPlan:
    out_path = output_override or spec.output.path
    argv: list[str] = ["ffmpeg", "-hide_banner", "-y"]

    # One or two inputs per clip (split lavfi video/audio).
    input_idx = 0
    clip_input: dict[str, tuple[int, int | None]] = {}

    for clip in spec.clips:
        v_idx = input_idx
        a_idx: int | None = None
        src = clip.source
        if src.lavfi_video:
            argv.extend(["-f", "lavfi", "-i", src.lavfi_video])
            input_idx += 1
        elif src.path:
            argv.extend(["-i", src.path])
            input_idx += 1
        else:
            raise ValueError(f"clip {clip.id}: no video source")

        if src.lavfi_audio:
            a_idx = input_idx
            argv.extend(["-f", "lavfi", "-i", src.lavfi_audio])
            input_idx += 1
        clip_input[clip.id] = (v_idx, a_idx)

    # Extra audio tracks
    audio_input: dict[str, int] = {}
    for tr in spec.audio_tracks:
        src = tr.source
        if src.path:
            argv.extend(["-i", src.path])
        elif src.lavfi_audio:
            argv.extend(["-f", "lavfi", "-i", src.lavfi_audio])
        else:
            raise ValueError(f"audio {tr.id}: no source")
        audio_input[tr.id] = input_idx
        input_idx += 1

    filters: list[str] = []
    vlabels: list[str] = []
    alabels: list[str] = []

    for clip in spec.clips:
        v_idx, a_idx = clip_input[clip.id]
        vlab = f"v_{clip.id}"
        start = clip.in_point
        if clip.out_point is not None:
            end = clip.out_point
        elif clip.duration is not None:
            end = start + clip.duration
        else:
            end = start + 5.0
        spd = clip.speed if clip.speed > 0 else 1.0
        pts = 1.0 / spd
        atempo_chain = _atempo_chain(spd)
        filters.append(
            f"[{v_idx}:v]trim=start={start}:end={end},setpts=PTS-STARTPTS,setpts={pts}*PTS[{vlab}_raw]"
        )
        filters.append(_video_fit_filters(spec, f"{vlab}_raw", vlab))
        vlabels.append(vlab)

        if a_idx is not None:
            alab = f"a_{clip.id}"
            af = f"[{a_idx}:a]atrim=start=0:end={end - start},asetpts=PTS-STARTPTS"
            if atempo_chain:
                af += f",{atempo_chain}"
            filters.append(f"{af}[{alab}]")
            alabels.append(alab)
        elif spec.use_video_audio:
            alab = f"a_{clip.id}"
            af = f"[{v_idx}:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS"
            if atempo_chain:
                af += f",{atempo_chain}"
            filters.append(f"{af}[{alab}]")
            alabels.append(alab)

    # Concatenate video
    trans_by_after = {t.after_clip: t for t in spec.transitions}
    vout = vlabels[0]
    if len(vlabels) == 1:
        pass
    elif not trans_by_after:
        concat_v = " ".join(f"[{x}]" for x in vlabels)
        filters.append(f"{concat_v}concat=n={len(vlabels)}:v=1:a=0[vcat]")
        vout = "vcat"
    else:
        # Chain xfade; offset = sum(prev durations) - sum(prior transition durations)
        durations = [_clip_duration(spec.clips[i]) / max(spec.clips[i].speed, 1e-6) for i in range(len(spec.clips))]
        vout = vlabels[0]
        t_acc = 0.0
        for i in range(len(vlabels) - 1):
            clip_id = spec.clips[i].id
            tr = trans_by_after.get(clip_id)
            td = tr.duration if tr else 0.0
            nxt = vlabels[i + 1]
            if tr and td > 0:
                offset = t_acc + durations[i] - td
                kind = _xfade_kind(tr.kind)
                outl = f"vx{i}"
                filters.append(
                    f"[{vout}][{nxt}]xfade=transition={kind}:duration={td}:offset={offset}[{outl}]"
                )
                vout = outl
                t_acc = offset + td
            else:
                concat_v = f"[{vout}][{nxt}]"
                outl = f"vx{i}"
                filters.append(f"{concat_v}concat=n=2:v=1:a=0[{outl}]")
                vout = outl
                t_acc += durations[i]

    color_out = vout
    if spec.color:
        cq = _color_eq(spec.color, vout, "vcolor")
        if cq:
            filters.append(cq)
            color_out = "vcolor"

    dt, color_out = _drawtext_chain(spec.overlays, color_out)
    if dt:
        filters.append(dt)

    # Audio: concat clip audios then mix extras
    aout: str | None = None
    if alabels:
        if len(alabels) == 1:
            aout = alabels[0]
        else:
            concat_a = " ".join(f"[{x}]" for x in alabels)
            filters.append(f"{concat_a}concat=n={len(alabels)}:v=0:a=1[amain]")
            aout = "amain"

    mix_inputs: list[tuple[str, float, float]] = []
    if aout:
        mix_inputs.append((aout, 0.0, 0.0))

    for tr in spec.audio_tracks:
        idx = audio_input[tr.id]
        lab = f"atr_{tr.id}"
        start = tr.in_point
        end = tr.out_point
        gain = tr.gain_db
        g = f"volume={gain}dB" if gain else None
        trim = f"atrim=start={start}"
        if end is not None:
            trim += f":end={end}"
        chain = f"[{idx}:a]{trim},asetpts=PTS-STARTPTS"
        if tr.offset_seconds > 0:
            chain += f",adelay={int(tr.offset_seconds * 1000)}|{int(tr.offset_seconds * 1000)}"
        if g:
            chain += f",{g}"
        filters.append(f"{chain}[{lab}]")
        mix_inputs.append((lab, tr.offset_seconds, gain))

    if spec.ducking.enabled and spec.ducking.voice_track and spec.ducking.music_tracks:
        vid = spec.ducking.voice_track
        voice = f"atr_{vid}" if vid in audio_input else f"a_{vid}"
        d = spec.ducking
        for music_id in spec.ducking.music_tracks:
            mlab = f"atr_{music_id}" if music_id in audio_input else f"a_{music_id}"
            vlab = f"duck_{music_id}"
            filters.append(
                f"[{mlab}][{voice}]sidechaincompress=threshold={d.threshold}:ratio={d.ratio}:"
                f"attack={d.attack_ms}:release={d.release_ms}:makeup={d.makeup_db}[{vlab}]"
            )
            new_mix: list[tuple[str, float, float]] = []
            for lbl, off, gdb in mix_inputs:
                new_mix.append((vlab, off, gdb) if lbl == mlab else (lbl, off, gdb))
            mix_inputs = new_mix

    if len(mix_inputs) > 1:
        parts = "".join(f"[{m[0]}]" for m in mix_inputs)
        filters.append(f"{parts}amix=inputs={len(mix_inputs)}:duration=longest:dropout_transition=0[amix]")
        aout = "amix"
    elif len(mix_inputs) == 1:
        aout = mix_inputs[0][0]

    if aout and spec.loudness.enabled:
        l = spec.loudness
        filters.append(
            f"[{aout}]loudnorm=I={l.target_lufs}:TP={l.true_peak_dbtp}:LRA=11:linear=true[aloud]"
        )
        aout = "aloud"
    elif aout and spec.loudness.peak_normalize_dbfs is not None:
        # Ceiling near SoundCraft CLI peak target (-0.1 dBFS); not a full peak-normalize pass.
        peak_lin = _dbfs_to_linear(spec.loudness.peak_normalize_dbfs)
        filters.append(f"[{aout}]alimiter=limit={peak_lin}:level=false[anorm]")
        aout = "anorm"

    filter_complex = ";".join(filters)
    argv.extend(["-filter_complex", filter_complex])
    argv.extend(["-map", f"[{color_out}]"])
    if aout:
        argv.extend(["-map", f"[{aout}]"])
    else:
        argv.append("-an")

    vcodec = spec.output.video_codec
    argv.extend(["-c:v", vcodec, "-pix_fmt", spec.output.pixel_format])
    if spec.output.crf is not None and spec.output.video_bitrate is None:
        argv.extend(["-crf", str(spec.output.crf)])
    if spec.output.preset and vcodec == "libx264":
        argv.extend(["-preset", spec.output.preset])
    if spec.output.video_bitrate:
        argv.extend(["-b:v", spec.output.video_bitrate])
    if aout:
        argv.extend(["-c:a", spec.output.audio_codec, "-b:a", spec.output.audio_bitrate])

    argv.append(out_path)
    return FfmpegPlan(argv=argv, filter_complex=filter_complex, output_path=out_path)


def _dbfs_to_linear(dbfs: float) -> float:
    return math.pow(10.0, dbfs / 20.0)


def _atempo_chain(speed: float) -> str:
    """ffmpeg atempo only supports 0.5–2.0 per filter; chain if needed."""
    if abs(speed - 1.0) < 1e-6:
        return ""
    parts: list[str] = []
    remaining = speed
    while remaining > 2.0:
        parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5
    parts.append(f"atempo={remaining:.6f}")
    return ",".join(parts)
