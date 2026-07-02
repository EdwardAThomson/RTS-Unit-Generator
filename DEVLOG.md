# Dev Log

## 2026-06-30

Brought the README back in line with what the project actually ships. Several features had landed since the README was last touched, so it was documenting a stale surface: the `animation_definitions.py` module, sprite animation, and GLB 3D mesh export were all missing. Updated the module list and the project/output structure sections to reflect them, and reconciled the "Future Enhancements" list against `ROADMAP.md`, which is now the canonical source for planned work.

**Decisions & notes:** ROADMAP.md is treated as the single source of truth for forward-looking plans; the README's Future Enhancements section now defers to it rather than duplicating (and drifting from) it.

## 2026-06-21

Reworked the unit preview into an interactive, drag-to-rotate experience. Instead of rendering single frames on demand behind sliders, the preview now bakes a 24×13 azimuth/elevation grid once (in a single reused GL context via `render_preview_grid`) and snaps to the nearest cached frame as you click and drag — giving instant rotation, with a progress bar shown during the initial bake. A follow-up fixed the rotation itself: the mesh was orbiting the world origin rather than spinning in place because the geometry wasn't centred there. The model is now centred on the origin before rotating, and the camera orbits around it (looking at it) at every elevation rather than depending on the previously hand-tuned `camera_y_offset` that only framed one angle.

**Decisions & notes:** Pre-rendering the whole grid trades a one-time bake cost for instant, jitter-free rotation — preferred over per-frame on-demand rendering. Centring fix verified: model centroid stays within ~1px of frame centre across all azimuths (previously drifted with rotation).
