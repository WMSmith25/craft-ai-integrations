# Boxkit edit spec (version 1)

Boxkit specs are YAML or JSON files describing a **timeline**, **output settings**, and optional **audio**, **overlays**, and **color** adjustments. The planner turns them into a single `ffmpeg -filter_complex` render on Linux (no GPU).

## Top-level fields

| Field | Required | Description |
|-------|----------|-------------|
| `version` | yes | Must be `1` |
| `output` | yes | Container path, resolution, codecs |
| `timeline.clips` | yes | Ordered video clips |
| `timeline.transitions` | no | `xfade` between clips (after clip id) |
| `crop_resize` | no | Crop and fit/fill to output size |
| `overlays` | no | `drawtext` captions |
| `audio` | no | Extra tracks, ducking, loudness |
| `color` | no | `eq` filter (brightness, contrast, saturation, gamma) |
| `adapters` | no | Optional FilmCraft/SoundCraft CLI hooks |

## Output block

```yaml
output:
  path: ./renders/final.mp4
  width: 1920
  height: 1080
  fps: 25
  video_codec: libx264
  audio_codec: aac
  crf: 23
  preset: medium
  video_bitrate: null   # optional; if set, overrides crf-style VBR hint
  audio_bitrate: 192k
  pixel_format: yuv420p
```

FilmCraft’s short-form web presets target about **−14 LUFS** and **−1 dBTP** (`filmcraft_export::presets::SHORT_FORM_*`). Boxkit mirrors that under `audio.loudness` (see below), not in `output`.

## Clips

Each clip needs a stable `id` and a `source`:

```yaml
timeline:
  clips:
    - id: main
      in: 0
      out: 12.5        # or use duration: 12.5
      speed: 1.0       # >1 faster, <1 slower
      source: /data/clip.mp4
    - id: bumper
      duration: 3
      source:
        lavfi_video: "testsrc=size=1280x720:rate=25:duration=3"
        lavfi_audio: "sine=frequency=440:sample_rate=48000:duration=3"
```

- **File** sources: path string or `{ path: ... }`.
- **Synthetic** sources (tests, placeholders): `lavfi_video` / `lavfi_audio` ffmpeg lavfi graphs.
- When `lavfi_audio` is set, set `audio.use_video_audio: false` so audio comes from the sine (or noise) graph, not the silent video input.

## Transitions

```yaml
timeline:
  transitions:
    - after: main      # clip id — transition into the *next* clip
      kind: fade       # fade, fadeblack, dissolve, wipeleft, ...
      duration: 0.5
```

If no transitions are listed, clips are concatenated with the `concat` filter.

## Crop / resize

```yaml
crop_resize:
  x: 100
  y: 50
  width: 1600
  height: 900
  mode: fit   # fit (letterbox pad) or fill (crop to cover)
```

Output `width` / `height` always define the final frame size.

## Text overlays

```yaml
overlays:
  - text: "Episode 3"
    start: 1.0
    end: 4.0
    x: "(w-text_w)/2"
    y: "h-80"
    fontsize: 42
    fontcolor: white
    box: true
    boxcolor: black@0.5
```

Requires a fontconfig-capable ffmpeg build (default on Ubuntu).

## Audio

```yaml
audio:
  use_video_audio: true
  tracks:
    - id: music
      source: ./assets/bed.wav
      gain_db: -6
      offset: 0.5
  ducking:
    enabled: true
    voice_track: main    # clip id or audio track id
    music_tracks: [music]
    threshold: 0.02
    ratio: 6
    attack_ms: 20
    release_ms: 400
  loudness:
    enabled: true
    target_lufs: -14
    true_peak_dbtp: -1.0
  peak_normalize_dbfs: -0.1   # optional ceiling (SoundCraft CLI default), uses alimiter
```

- **Mixing**: main timeline audio (from clips) plus `tracks`, merged with `amix`.
- **Ducking**: ffmpeg `sidechaincompress` (not SoundCraft’s full Essential Sound ducking UI).
- **Loudness**: `loudnorm` when `loudness.enabled` is true.

## Color

```yaml
color:
  brightness: 0.0
  contrast: 1.0
  saturation: 1.1
  gamma: 1.0
```

Maps to `eq=brightness=…:contrast=…:saturation=…:gamma=…`. FilmCraft’s effect stack is far richer; unported effects stay out of scope (see `INVENTORY.md`).

## Adapters (optional, default off)

```yaml
adapters:
  filmcraft_cli:
    enabled: false
    binary: filmcraft-cli
  soundcraft_cli:
    enabled: false
    binary: soundcraft-cli
```

When `enabled: true`, boxkit checks that the binary exists before render. It does **not** call paid APIs or download models.

## Examples

- `examples/smoke.yaml` — single testsrc + sine + title
- `examples/multi-clip.yaml` — two clips, xfade, loudnorm

## Validate / plan

```bash
boxkit validate myedit.yaml
boxkit plan myedit.yaml
boxkit render myedit.yaml -n    # print ffmpeg plan only
```
