# EXT_materials_subsurface

Draft status: Foundation private extension.

This extension stores Foundation's Burley subsurface profile parameters on a glTF material. It is intentionally narrow: the fields mirror Blender's artist-facing Burley controls and do not try to standardize a general BSSRDF, volume, or diffusion material model.

## Motivation

Blender exposes a compact Burley subsurface model through three artist-facing controls:

- `Weight`
- `Radius`
- `Scale`

Foundation should preserve these controls through its Blender exporter, cgltf fork, scene import, and shader material path without guessing a broader physical material model. The extension declares the profile explicitly as Burley, then stores Blender's RGB radius scale and uniform scene scale separately.

## Extension Object

The extension is attached to `material.extensions`.

```json
{
  "materials": [
    {
      "extensions": {
        "EXT_materials_subsurface": {
          "subsurfaceProfile": "burley",
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

- `subsurfaceProfile`: string, optional, default `"burley"`.
  BSSRDF profile identifier. Initial valid value is `"burley"`.

- `subsurfaceWeight`: number, optional, default `0`.
  Blender Subsurface Weight. Range is `[0, 1]`.

- `subsurfaceRadius`: number array of length 3, optional, default `[1, 0.2, 0.1]`.
  Blender RGB radius scale.

- `subsurfaceScale`: number, optional, default `0.05`.
  Blender Subsurface Scale in scene units. Foundation treats glTF scene units as meters unless the exporter bakes a different unit convention.

## Foundation Mapping

For current Foundation materials:

```text
FMaterial::subsurfaceFactor = subsurfaceWeight
FMaterial::subsurfaceColor  = [1, 1, 1]
FMaterial::subsurfaceRadius = subsurfaceRadius
FMaterial::subsurfaceScale  = subsurfaceScale
```

The shader may use `baseColor * subsurfaceColor` for local Burley approximation. Since Blender's exposed Subsurface panel has no separate subsurface color in this mode, the extension keeps `subsurfaceColor` neutral and lets base color tint the lobe. Runtime Burley diffusion distance should match Blender's `bssrdf.h` setup:

```text
A = baseColor * subsurfaceColor
s = 1.9 - A + 3.5 * (A - 0.8)^2
d = (0.25 / pi) * (FMaterial::subsurfaceRadius * FMaterial::subsurfaceScale) / s
```

The renderer should use `d` as the per-channel Burley profile radius.

## Non-Goals

- No texture slots in the first draft.
- No support for random-walk-only parameters.
- No attempt to replace `KHR_materials_volume`.
- No diffuse BTDF semantics; use `KHR_materials_diffuse_transmission` for thin diffuse transmission.

## TODO

- Add JSON schema.
