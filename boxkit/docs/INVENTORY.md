# Cross-repo inventory: video / audio editing components

Verified by reading source in this workspace (craft-ai-integrations @ `/workspace`), and clones of **soundcraft** and **filmcraft** under `/workspace/_repos/`. README claims were checked against code.

**Legend:** 🟢 box-runnable headless without GPU · 🟡 needs GPU/UI/macOS/paid · 🔴 secrets / paid API / hosted inference

---

## 1. craft-ai-integrations (`WMSmith25/craft-ai-integrations`)

**Role:** Shared Rust **AI provider layer** (text, image, some video *generation* routes) for Craft apps — **not** a non-linear editor.

### 1.1 Layout

| Area | Path | Purpose |
|------|------|---------|
| Workspace crates | `crates/ai-*` | Providers (OpenAI, Gemini, BFL, ComfyUI, Vertex, Seedance, ArtCraft, …), engines (Burn, RTen, Candle), client/egui |
| Media storage | `crates/ai-media` | Download/cache provider images (JPEG/WebP/PNG); **no** timeline |
| Declarative workflows | `crates/ai-declarative` | ComfyUI-style graphs for **generation**, not edit timelines |
| Python tooling | `tools/intake`, `tools/mutation` | Integration proposals, mutation tests — **no** video pipeline |
| SAM3 bridge | `crates/ai-sam3/bridge/server.py` | Local mask server for segmentation feature tests |

### 1.2 Components relevant to “editing”

| Component | Path | What it does | Box? |
|-----------|------|--------------|------|
| `craft-ai-media` | `crates/ai-media/src/` | Fetches remote media URLs into temp files | 🟡 network for provider URLs |
| `ai-features` catalogue | `crates/ai-features/src/catalogue/` | Registers capabilities e.g. `video.generate`, inpainting | 🔴 paid cloud models when used |
| `ai-seedance`, `ai-artcraft`, `ai-bfl` | respective crates | **Generative** video/image APIs | 🔴 API keys, spend |
| `ai-comfyui` | `crates/ai-comfyui/` | Local ComfyUI graphs | 🟡/🔴 self-hosted; optional GPU |
| `ai-engine-burn`, `ai-engine-rten`, `ai-engine-candle` | engines | On-device ML (matting, SAM, etc.) | 🟡/🔴 GPU strongly preferred |
| Intake spec | `tools/intake/propose.py` | Schema for **proposing** new integrations | 🟢 validation only |

### 1.3 ffmpeg

**None** in production code. No CLI edit pipeline in this repo before **boxkit/**.

### 1.4 boxkit (new in this PR)

| Path | Role |
|------|------|
| `boxkit/` | Python package + `boxkit` CLI: YAML spec → **ffmpeg** render |
| `boxkit/docs/SPEC.md` | Declarative edit schema |
| `boxkit/install-ubuntu.sh` | apt + pip/venv bootstrap |

---

## 2. soundcraft (`WMSmith25/soundcraft`)

**Role:** Rust **DAW** (Pro Tools–style): sessions, mixer, built-in DSP, CLAP/VST3/AU hosts, MCP automation.

### 2.1 Applications

| Binary | Path | Headless? | Function |
|--------|------|-----------|----------|
| `soundcraft-cli` | `apps/soundcraft-cli/` | 🟢 | `convert`, `run`/`script` JSON commands, `mcp`, `describe` |
| `soundcraft` | `apps/soundcraft/` | 🟡 | egui + **wgpu** UI, cpal playback |
| `soundcraft-web` | `apps/soundcraft-web/` | Browser | WebGPU/WebAudio |

### 2.2 Crate stack (editing-related)

| Crate | Path | Function |
|-------|------|----------|
| `soundcraft-audio-io` | `crates/audio-io/` | Decode (symphonia) / encode WAV, AIFF, FLAC — **no ffmpeg runtime** |
| `soundcraft-dsp` | `crates/dsp/` | 29 built-in plugins; offline normalize, resample, fades |
| `soundcraft-mix` | `crates/mix/` | Realtime/offline mixer, bounce |
| `soundcraft-model` | `crates/model/` | `.scraft` JSON session format |
| `soundcraft-engine` | `crates/engine/` | Command registry (`mix.*`, `file.bounce_*`, `audiosuite.process`, …) |
| `soundcraft-automation` | `crates/automation/` | MCP server |
| `soundcraft-video` | `crates/video/` | MP4 demux, in-tree H.264/ProRes/MJPEG decode (no ffmpeg) |

### 2.3 CLIs / automation

- **`soundcraft-cli convert`:** decode → optional resample → peak **normalize −0.1 dBFS** → encode (`apps/soundcraft-cli/src/convert.rs`). 🟢
- **`soundcraft-cli run` / `script`:** JSONL engine commands, bounce mixes. 🟢 (CPU DSP).
- **`soundcraft-cli mcp`:** agent control; local stdio/TCP. 🟢

### 2.4 Spec / config formats

- Session: **`.scraft`** JSON (`crates/model/src/session.rs`)
- Bundle: **`.scraftz`** zip (web)
- Commands: `CommandSpec` JSON via `describe` / MCP

### 2.5 ffmpeg

**Runtime: none.** Tests may use ffmpeg to generate fixtures (`crates/audio-io/tests/fixtures/README.md`).

### 2.6 Not box-portable / gaps

| Item | Notes |
|------|-------|
| Voiceover **ducking** (Essential Sound) | Not implemented as `duck` in repo (search) |
| VST/AU/CLAP UI editors | Desktop; headless can load some CLAP without UI |
| GPU | **wgpu for UI only**; bounce/mix CPU |
| ASIO | Windows optional feature; Steinberg SDK at build time |
| AAX | Not supported (licence) |
| craft-update | Optional update check to getartcraft.com — not required for CLI |

### 2.7 Used in boxkit

- Peak normalize reference **−0.1 dBFS** → optional `audio.peak_normalize_dbfs` + optional `soundcraft_cli` adapter (binary check only).

---

## 3. filmcraft (`WMSmith25/filmcraft`)

**Role:** Rust **NLE** (Premiere-style): timeline, pure-Rust codecs, CPU/GPU compositor, export mux.

### 3.1 Applications

| Binary | Path | Headless? | Function |
|--------|------|-----------|----------|
| `filmcraft-cli` | `apps/filmcraft-cli/` | 🟢 | `export`, `render`, `exec`, `run`, `probe`, `mcp`, `bench-decode` |
| `filmcraft` | `apps/filmcraft/` | 🟡 | Full UI; `--control` TCP JSON-lines + token |
| `filmcraft-web` | `apps/filmcraft-web/` | Browser | WebCodecs/WebGPU |

### 3.2 Crate stack (51 crates)

**Foundation / codecs:** `h264`, `hevc`, `prores`, `aac`, `opus`, `vp9`, `av1`, containers (`isobmff`, `matroska`, `mxf`, …) — all **in-tree**, no ffmpeg at runtime.

**Edit pipeline:**

| Crate | Path | Function |
|-------|------|----------|
| `filmcraft-project` | `crates/project/` | Timeline model, `effect_defs()` declarative effect metadata |
| `filmcraft-render` | `crates/render/` | **CPU** `render_sequence` compositor, audio mix, transitions |
| `filmcraft-gpu` | `crates/gpu/` | wgpu compositor, `ExportRenderer` |
| `filmcraft-export` | `crates/export/` | Encode/mux, `ExportSettings`, built-in presets |
| `filmcraft-engine` | `crates/engine/` | `Session::execute`, `file.exportMedia`, jobs |
| `filmcraft-format` | `crates/format/` | `.fcproj` JSON I/O, migrations |
| `filmcraft-interchange` | `crates/interchange/` | EDL, FCPXML, AAF, OTIO, … |
| `filmcraft-audio-dsp` | `crates/audio-dsp/` | BS.1770 loudness, effects, 5.1 math |
| `filmcraft-platform` | `crates/platform/` | HW decode/encode (VideoToolbox, MF, NVDEC/VA-API, NVENC) |
| `filmcraft-speech` / `tts` | optional features | Whisper, Kokoro — **feature-gated** |

### 3.3 Project / automation formats

- **`.fcproj`:** JSON `format: "filmcraft.project"` (`docs/project-files.md`, `crates/format/`)
- **JSONL scripts:** `filmcraft-cli run script.jsonl` — `{"id","params"}`
- **Export:** `ExportSettings` JSON; presets in `crates/export/src/presets.rs` (−14 LUFS short-form, H.264, ProRes, …)

### 3.4 ffmpeg

**Shipped product: does not shell out to ffmpeg.**  
**Dev/test only:** `crates/testkit` (`FILMCRAFT_FFMPEG`), `cargo xtask fixtures`, oracle tests.

### 3.5 Headless export path (verified)

`filmcraft-cli export` → `file.exportMedia` → `export::export_range` → per-frame render (CPU or GPU) → encoders.

### 3.6 GPU / HW / paid

| Capability | Requirement |
|------------|-------------|
| Default export on server | 🟢 CPU compositor + software encoders |
| GPU export / playback | 🟡 wgpu adapter (may work with lavapipe) |
| HW H.264/H.265 | 🟡 NVENC/VideoToolbox/MF — opt-in |
| Whisper / Kokoro STT/TTS | 🔴 optional models/downloads |
| UI / voice record | 🟡 desktop |

### 3.7 Used in boxkit

- Loudness targets from export presets (−14 LUFS, −1 dBTP) as **defaults in docs/examples**
- Optional `filmcraft_cli` adapter (existence check); **no** `.fcproj` translation in v0.1

---

## 4. Consolidation matrix (what boxkit implements)

| Capability | FilmCraft | SoundCraft | boxkit (ffmpeg) |
|------------|-----------|------------|----------------|
| Multi-clip timeline | Native | N/A (audio-centric) | concat / xfade |
| Trim / speed | Native | offline ops | trim, setpts, atempo |
| Transitions | Large library | N/A | subset of xfade |
| Color / VFX | `render` + GPU | N/A | `eq` only |
| Text | Native titler | N/A | drawtext |
| Audio mix | `render` + DSP | `mix` engine | amix |
| Ducking | Essential Sound (partial) | **not implemented** | sidechaincompress |
| Loudness | BS.1770 in `audio-dsp` | meter + bounce | loudnorm |
| Peak normalize | export chain | CLI −0.1 dBFS | alimiter optional |
| Session format | `.fcproj` | `.scraft` | boxkit YAML v1 |
| Generative AI | via craft-ai | N/A | **out of scope** |

---

## 5. Left out of boxkit (and why)

| Component | Reason |
|-----------|--------|
| FilmCraft compositor / effect graph | Rust + wgpu; not vendored into Python |
| SoundCraft realtime mixer + 29 plugins | Rust; would need `soundcraft-cli` bounce per asset |
| craft-ai video **generation** providers | Paid APIs, keys, policy |
| Local ML engines (Burn, RTen, Whisper, …) | GPU/model weights |
| Pro Tools / Premiere interchange round-trip | No fcproj/scraft converter in v0.1 |
| Motion tracking, multicam, scopes UI | GUI-only in FilmCraft |
| Hardware encoders | Optional platform registration |

---

## 6. External services summary

| Service | Repo | Trigger |
|---------|------|---------|
| OpenAI, Gemini, BFL, Vertex, Seedance, ArtCraft, … | craft-ai-integrations | User-configured routes |
| ComfyUI | craft-ai | User local server |
| Hugging Face / model hubs | engines | Native model download |
| getartcraft.com updates | soundcraft UI | Optional |
| **ffmpeg** | boxkit | System package only |

No boxkit code paths call cloud inference by default.

---

## 7. Build notes (optional full stack on Ubuntu box)

```bash
# boxkit only (recommended for Grok Bot edit-to-spec)
cd craft-ai-integrations/boxkit && ./install-ubuntu.sh

# Optional: FilmCraft CLI (Rust 1.9x toolchain, long compile)
git clone https://github.com/WMSmith25/filmcraft.git && cd filmcraft
cargo build -p filmcraft-cli --release

# Optional: SoundCraft CLI
git clone https://github.com/WMSmith25/soundcraft.git && cd soundcraft
cargo build -p soundcraft-cli --release
```

Inventory generated for boxkit PR; re-run discovery after major merges on `main` in any of the three repos.
