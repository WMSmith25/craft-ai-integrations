"""End-to-end renders with lavfi synthetic sources (no network)."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from boxkit.plan import build_plan
from boxkit.render import render_spec_object
from boxkit.spec import ClipSource, ClipSpec, EditSpec, OutputSettings, parse_spec_dict
from boxkit.validate import validate_spec

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _minimal_spec(out: Path) -> EditSpec:
    return EditSpec(
        version=1,
        output=OutputSettings(path=str(out), width=160, height=120, fps=25, crf=30, preset="ultrafast"),
        clips=[
            ClipSpec(
                id="t",
                duration=0.8,
                source=ClipSource(
                    lavfi_video="testsrc=size=160x120:rate=25:duration=0.8",
                    lavfi_audio="sine=frequency=1000:sample_rate=48000:duration=0.8",
                ),
            )
        ],
        use_video_audio=False,
    )


def test_validate_examples():
    for name in ("smoke.yaml", "multi-clip.yaml"):
        from boxkit.validate import validate_path

        res = validate_path(EXAMPLES / name)
        assert res.ok, res.errors


def test_build_plan_has_filter_complex():
    spec = _minimal_spec(Path("/tmp/x.mp4"))
    plan = build_plan(spec)
    assert "-filter_complex" in plan.argv
    assert "testsrc" in plan.shell_line() or "lavfi" in plan.shell_line()


def test_render_lavfi_e2e():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out.mp4"
        spec = _minimal_spec(out)
        assert validate_spec(spec).ok
        render_spec_object(spec)
        assert out.is_file() and out.stat().st_size > 500
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(out)],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc.stdout)
        dur = float(data["format"]["duration"])
        assert 0.5 < dur < 1.2


def test_yaml_multi_clip_render():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "multi.mp4"
        raw = (EXAMPLES / "multi-clip.yaml").read_text(encoding="utf-8")
        data = parse_spec_dict(__import__("yaml").safe_load(raw))
        data.output.path = str(out)
        render_spec_object(data, output=str(out))
        assert out.exists()


def test_cli_plan_subprocess():
    smoke = EXAMPLES / "smoke.yaml"
    proc = subprocess.run(
        ["python", "-m", "boxkit.cli", "plan", str(smoke)],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(smoke.parent.parent),
    )
    assert "ffmpeg" in proc.stdout
