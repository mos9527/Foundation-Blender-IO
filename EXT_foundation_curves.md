# EXT_foundation_curves (Deprecated)

This private extension is deprecated and no longer emitted or consumed.

Foundation curve interchange now uses standard glTF mesh primitives:

- `mode: 1` (`LINES`) with indexed segment pairs
- `POSITION` — polyline sample positions
- `_RADIUS` — per-vertex scalar radius (custom attribute; no glTF core equivalent)
- `TEXCOORD_0.x` — normalized strand parameter `u` in `[0, 1]`

Blender export accepts `POLY` splines only (legacy `CURVE` and hair `CURVES`). Bézier/NURBS must be converted to POLY before export; subdivision/LOD is an export-time authoring choice.

Blender import maps meshes whose primitives are all `LINES` / `LINE_STRIP` / `LINE_LOOP` with `_RADIUS` back to legacy `CURVE` objects with `POLY` splines (absolute radii on points, `bevel_depth = 1`).

Foundation imports these line primitives and bakes Disjoint Orthogonal Triangle Strips (DOTS) for hardware triangle ray tracing.
