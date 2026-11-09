# Craft Boxkit

Headless **declarative video editing** for Grok Bot’s persistent Linux box. Boxkit reads a YAML/JSON **edit spec**, builds an **ffmpeg** `filter_complex`, and renders H.264/AAC (or still-image sequences) without a GPU or paid APIs.

It consolidates **box-runnable** ideas from:

- [craft-ai-integrations](https://github.com/WMSmith25/craft-ai-integrations) (this repo)
- [filmcraft](https://github.com/WMSmith25/filmcraft) (export loudness targets, effect vocabulary — via ffmpeg, not the Rust compositor)
- [soundcraft](https://github.com/WMSmith25/soundcraft) (peak normalize reference −0.1 dBFS — via `alimiter` / optional CLI adapter)

Full cross-repo inventory: [`docs/INVENTORY.md`](docs/INVENTORY.md). Spec reference: [`docs/SPEC.md`](docs/SPEC.md).

## Quick start (Ubuntu)

```bash
git clone https://github.com/WMSmith25/craft-ai-integrations.git
cd craft-ai-integrations/boxkit
chmod +x install-ubuntu.sh
./install-ubuntu.sh          # apt: ffmpeg, python3, venv; pip install -e .[dev]
source .venv/bin/activate
boxkit validate examples/smoke.yaml
boxkit plan examples/smoke.yaml
boxkit render examples/smoke.yaml
```

Without sudo (ffmpeg already installed):

```bash
BOXKIT_SKIP_APT=1 ./install-ubuntu.sh
```

## Commands

| Command | Purpose |
|---------|---------|
| `boxkit validate SPEC…` | Schema + file checks; tries to build ffmpeg plan |
| `boxkit plan SPEC` | Dry-run: print shell-ready ffmpeg argv + filter graph |
| `boxkit render SPEC [-o OUT]` | Run ffmpeg |
| `boxkit render SPEC -n` | Same as `plan` |

## What boxkit does today

- Multi-clip timeline: trim, speed (`setpts` / chained `atempo`), concat or **xfade** transitions
- Fit/fill scale, pad, optional crop, `fps`, color (`eq`)
- Text overlays (`drawtext`)
- Extra audio tracks, `amix`, optional **sidechain ducking**, **EBU-style loudnorm** (FilmCraft short-form −14 LUFS defaults in examples), peak ceiling near SoundCraft’s −0.1 dBFS
- `lavfi` sources (`testsrc`, `sine`) for tests and synthetic renders

## Optional adapters (off by default)

```yaml
adapters:
  filmcraft_cli:
    enabled: false
    binary: filmcraft-cli
  soundcraft_cli:
    enabled: false
    binary: soundcraft-cli
```

Enabling these only checks that the binary exists; rendering still uses ffmpeg in boxkit v0.1. Building FilmCraft/SoundCraft on the box is documented in `docs/INVENTORY.md` — no cloud keys required for CLI bounce/export.

## Tests

```bash
cd boxkit && source .venv/bin/activate && pytest -q
```

## Licence

Same as craft-ai-integrations (MIT OR Apache-2.0). Third-party attribution: [`ATTRIBUTION.md`](ATTRIBUTION.md).
