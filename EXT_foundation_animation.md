# EXT_foundation_animation

Draft status: Foundation private extension.

This extension stores a scene-wide non-linear animation (NLA) arrangement: named tracks that place references to glTF animations as strips on a shared timeline. It lets an asset ship several clips (glTF `animations`) plus the layout that arranges, offsets, retimes, and loops them, instead of collapsing everything into a single baked animation.

## Motivation

glTF core `animations[]` are a flat list of independent clips. It has no notion of arranging those clips on tracks, offsetting them along a shared timeline, retiming or looping a clip within a region, or layering tracks by priority. Foundation and Blender both model this with an NLA (tracks of strips referencing actions). This extension carries that arrangement so Foundation can reproduce the authored playback without re-baking, and so Blender NLA layouts survive a round trip.

The referenced glTF `animations[]` are the source clips ("actions"); this extension only describes how they are arranged. Sampler data, channels, and targets stay in core glTF.

## Extension Placement

Root object only: `extensions.EXT_foundation_animation.tracks[]`.

Each strip references a source clip by index into the top-level `animations[]` array, so ordinary glTF animation semantics (channels, samplers, node/weights targets) are unchanged. A single glTF animation may be referenced by any number of strips.

## Example

```json
{
  "extensionsUsed": ["EXT_foundation_animation"],
  "animations": [
    { "name": "Idle" },
    { "name": "Run" }
  ],
  "extensions": {
    "EXT_foundation_animation": {
      "tracks": [
        {
          "name": "Base",
          "strips": [
            {
              "animation": 0,
              "stripStart": 0.0,
              "stripEnd": 2.0,
              "clipStart": 0.0,
              "clipEnd": 2.0,
              "timeScale": 1.0,
              "influence": 1.0,
              "cyclic": true
            },
            {
              "animation": 1,
              "stripStart": 2.0,
              "stripEnd": 5.0,
              "clipStart": 0.0,
              "clipEnd": 1.0,
              "timeScale": 1.0,
              "influence": 1.0,
              "cyclic": true
            }
          ]
        }
      ]
    }
  }
}
```

## Track Object

- `name`: string, optional.
  Human-readable track name.

- `mute`: boolean, optional, default `false`.
  When `true`, the track contributes nothing and is skipped during evaluation.

- `strips`: array of Strip objects, required.
  Strips placed on this track. Strips on one track are expected to be non-overlapping; if they overlap, the last strip in array order wins for the overlapping range.

## Strip Object

All time fields are in seconds, matching glTF animation sampler input time.

- `animation`: integer, required.
  Index into the top-level `animations[]` array. The referenced animation is the source clip sampled by this strip.

- `stripStart`: number, required.
  Timeline position where the strip becomes active (Strip Frame Start).

- `stripEnd`: number, required.
  Timeline position where the strip stops being active (Strip Frame End). Must be `>= stripStart`.

- `clipStart`: number, optional, default `0.0`.
  Start of the source-clip window used by the strip, in the referenced animation's local time (Clip Start).

- `clipEnd`: number, optional, default: the referenced animation's duration.
  End of the source-clip window (Clip End). Must be `> clipStart`.

- `timeScale`: number, optional, default `1.0`.
  Clip-local seconds advanced per timeline second (Clip Timescale). Must be `> 0`.

- `influence`: number, optional, default `1.0`.
  Strip weight in `[0, 1]`. Stored for round-trip and future blending. With blending out of scope, a consumer MAY treat `influence <= 0` as inactive and `influence > 0` as full.

- `cyclic`: boolean, optional, default `false`.
  When `true`, the clip window loops (restarts) to fill the strip; when `false`, clip time clamps at `clipEnd`.

## Evaluation (normative)

Tracks are evaluated in array order, lowest index first, so a later track overwrites an earlier one for any channel they share (Replace semantics; no cross-strip blending in this version).

For a timeline time `t`, for each non-muted track, select the active strip where `stripStart <= t <= stripEnd` (last in array order on overlap). Map to clip-local time:

```text
L = clipEnd - clipStart                 # clip window, > 0
u = (t - stripStart) * timeScale         # elapsed clip time
clipLocal = cyclic ? clipStart + mod(u, L)
                   : clipStart + min(u, L)
```

Sample the referenced glTF animation at `clipLocal` and apply its channels to their targets. Strips outside `[stripStart, stripEnd]` contribute nothing.

## Blender Mapping

### Export

The Foundation Blender exporter does not change how glTF `animations[]` are baked; whatever `gltf_animation_mode` the user has configured runs unmodified. After animations are gathered, a separate additive pass walks `object.animation_data.nla_tracks` for every exported object (i.e. what the NLA editor shows with all objects selected) and writes `EXT_foundation_animation.tracks[]` mirroring that arrangement, matching each strip's action to an already-exported glTF animation by name.

This name match is only reliable in `ACTIONS` animation mode. Each strip is matched independently by its action's name against the already-exported animation list; whether a given action ends up individually exported depends on the exporter's own `ACTIONS`-mode rules (single-strip tracks, the active action, or — for a lone armature — the "export all actions" fallback). A strip whose action wasn't individually baked is skipped with a warning. In other animation modes, baked animation names don't correspond 1:1 to actions at all, so the extension is omitted entirely (the plain glTF animations still import and play in Foundation, just without NLA arrangement metadata).

Baked sampler input keeps Blender's raw frame numbers converted to seconds (`frame / fps`, no renormalization to zero), so the strip/clip fields below use that same absolute conversion, with `fps = scene.render.fps * scene.render.fps_base`:

```text
track.name    = NlaTrack.name
track.mute    = NlaTrack.mute
strip.animation  = index of the baked glTF animation for NlaStrip.action
strip.stripStart = NlaStrip.frame_start / fps
strip.stripEnd   = NlaStrip.frame_end   / fps
strip.clipStart  = NlaStrip.action_frame_start / fps
strip.clipEnd    = NlaStrip.action_frame_end   / fps
strip.timeScale  = 1.0 / NlaStrip.scale          # Blender scale=2 plays at half speed (stretches the strip)
strip.influence  = 1.0                            # animated influence is not exported in this version
strip.cyclic     = NlaStrip.repeat > 1.0
```

Only Replace strips are represented; `blend_type` other than Replace and animated influence/strip-time are out of scope for this version. Muted strips are skipped. A strip whose action was not exported as its own named glTF animation (filtered action, sound/transition strip, etc.) is skipped with a warning; a track left with zero strips is omitted entirely.

### Import

Blender import of this extension is out of scope for this version (export-from-Blender and import-by-Foundation is the required path). A future revision will stash each referenced animation as an action and rebuild `nla_tracks`/`strips` from the track/strip fields.

## Foundation Mapping

Foundation imports `tracks[]` into its scene NLA (`FNlaTrack` / `FNlaStrip`). Each strip's `animation` resolves to the Foundation clip group imported from that glTF animation. The runtime evaluates tracks exactly as in Evaluation above: reset to rest, walk tracks low-to-high priority, sample each active strip's clips into the pose, higher tracks overwrite. `influence` is stored and shown in the editor and gates the strip on/off at runtime.

## Non-Goals

- No blending between overlapping strips or across tracks (Replace only).
- No animated influence or animated strip time curves.
- No blend-in/blend-out, reversed playback, or `use_sync_length` round trip.
- No morph-target (`weights`) NLA arrangement in this draft; weight animations still play on the base timeline.

## TODO

- Add JSON schema once field names settle.
- Add Blender import (stash actions, rebuild NLA tracks/strips).
- Add Foundation export (`cgltf_write`) for full round trip.
- Consider blend-in/out and animated influence.
