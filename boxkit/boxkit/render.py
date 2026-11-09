"""Execute ffmpeg plans."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from boxkit.plan import FfmpegPlan, build_plan
from boxkit.spec import EditSpec, load_spec


class RenderError(RuntimeError):
    pass


def find_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RenderError("ffmpeg not found on PATH")
    return exe


def run_plan(plan: FfmpegPlan, *, dry_run: bool = False, cwd: Path | None = None) -> subprocess.CompletedProcess[str] | None:
    if dry_run:
        return None
    ffmpeg = find_ffmpeg()
    argv = [ffmpeg if plan.argv[0] == "ffmpeg" else plan.argv[0], *plan.argv[1:]]
    proc = subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RenderError(f"ffmpeg failed ({proc.returncode}):\n{proc.stderr}")
    return proc


def render_spec(
    spec_path: str | Path,
    *,
    output: str | None = None,
    dry_run: bool = False,
) -> FfmpegPlan:
    spec = load_spec(spec_path)
    plan = build_plan(spec, output_override=output)
    if not dry_run:
        out = Path(plan.output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
    run_plan(plan, dry_run=dry_run)
    return plan


def render_spec_object(spec: EditSpec, *, output: str | None = None, dry_run: bool = False) -> FfmpegPlan:
    plan = build_plan(spec, output_override=output)
    if not dry_run:
        Path(plan.output_path).parent.mkdir(parents=True, exist_ok=True)
    run_plan(plan, dry_run=dry_run)
    return plan
