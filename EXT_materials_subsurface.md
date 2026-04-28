# EXT_materials_subsurface

Draft status: Foundation private extension.

This extension stores Blender-compatible subsurface parameters on a glTF material. It is intentionally narrow: the fields mirror Blender's Subsurface UI and do not try to standardize a general BSSRDF, volume, or diffusion material model.

## Motivation

Blender exposes a compact Christensen-Burley subsurface model through four artist-facing controls:

- `Method`
- `Weight`
- `Radius`
- `Scale`

Foundation should preserve these controls through its Blender exporter, cgltf fork, scene import, and shader material path without guessing a broader physical material model. Renderers may choose a local Disney/Burley approximation, a separable BSSRDF, or a future random-walk implementation from the same parameters.

## Extension Object

The extension is attached to `material.extensions`.

```json
{
  "materials": [
    {
      "extensions": {
        "EXT_materials_subsurface": {
          "subsurfaceMethod": "christensenBurley",
          "subsurfaceWeight": 0.5,
          "subsurfaceRadius": [1.0, 0.2, 0.1],
          "subsurfaceScale": 0.05
        }
      }
    }
  ]
}
```

## Properties

- `subsurfaceMethod`: string, optional, default `"christensenBurley"`.
  Blender method identifier. Initial valid value is `"christensenBurley"`.

- `subsurfaceWeight`: number, optional, default `0`.
  Blender Subsurface Weight. Range is `[0, 1]`.

- `subsurfaceRadius`: number array of length 3, optional, default `[1, 0.2, 0.1]`.
  Blender RGB radius multiplier.

- `subsurfaceScale`: number, optional, default `0.05`.
  Blender Subsurface Scale in scene units. Foundation treats glTF scene units as meters unless the exporter bakes a different unit convention.

## Foundation Mapping

For current Foundation materials:

```text
FMaterial::subsurfaceFactor = subsurfaceWeight
FMaterial::subsurfaceColor  = [1, 1, 1]
FMaterial::subsurfaceRadius = subsurfaceRadius * subsurfaceScale
```

The shader may use `baseColor * subsurfaceColor` for local Disney-style approximation. Since Blender's exposed Subsurface panel has no separate subsurface color in this mode, the extension keeps `subsurfaceColor` neutral and lets base color tint the lobe. A true BSSRDF implementation should use `subsurfaceRadius * subsurfaceScale` as the per-channel scatter distance input.

## Non-Goals

- No texture slots in the first draft.
- No support for random-walk-only parameters.
- No attempt to replace `KHR_materials_volume`.
- No diffuse BTDF semantics; use `KHR_materials_diffuse_transmission` for thin diffuse transmission.

## TODO

- Add matching structs to the Foundation cgltf fork.
- Export these values from `Foundation-Blender-IO`.
- Decide whether Blender method values beyond Christensen-Burley should be accepted or ignored.
- Add JSON schema once the field names settle.
