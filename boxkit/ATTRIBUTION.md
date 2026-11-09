# Boxkit attribution

Boxkit is new Python code in craft-ai-integrations. It does **not** vendor Rust sources from FilmCraft or SoundCraft.

Design references (behaviour documented in `docs/INVENTORY.md`):

- **FilmCraft** (`WMSmith25/filmcraft`): short-form export loudness defaults (−14 LUFS integrated, −1 dBTP) from `crates/export/src/presets.rs`; headless export via `filmcraft-cli` (optional adapter).
- **SoundCraft** (`WMSmith25/soundcraft`): CLI peak-normalize target −0.1 dBFS from `apps/soundcraft-cli/src/convert.rs` (optional `alimiter` / CLI adapter).

Runtime dependency: **FFmpeg** (LGPL/GPL components depending on distro build).

Python dependency: **PyYAML** (MIT).
