# EXT_foundation_environment

Draft status: Foundation private extension.

This extension stores the scene environment used by Foundation. It is attached to `scene.extensions` and supports either a constant HDR color or a longlat/equirectangular Radiance HDR image.

## Extension Object

Uniform color:

```json
{
  "scenes": [
    {
      "extensions": {
        "EXT_foundation_environment": {
          "type": "color",
          "color": [1.0, 1.0, 1.0],
          "strength": 0.05
        }
      }
    }
  ]
}
```

HDRI:

```json
{
  "scenes": [
    {
      "extensions": {
        "EXT_foundation_environment": {
          "type": "hdri",
          "uri": "studio.hdr",
          "projection": "longlat",
          "strength": 1.0
        }
      }
    }
  ]
}
```

## Properties

- `type`: string, required. Either `"color"` or `"hdri"`.
- `color`: number array of length 3, required for `"color"`. Linear RGB environment radiance before `strength`.
- `uri`: string, required for `"hdri"`. Relative URI to a `.hdr` or `.hdri` Radiance HDR file.
- `projection`: string, optional for `"hdri"`, default `"longlat"`. Foundation supports `"longlat"` and `"equirectangular"`.
- `strength`: number, optional, default `1.0` for exported Blender worlds. Multiplies the color or HDRI radiance.
- `azimuthOffset`: number, optional, default `0.0`. Rotation in degrees around the vertical axis.
