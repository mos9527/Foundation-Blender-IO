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
          "strength": 0.25
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

Embedded HDRI for GLB:

```json
{
  "scenes": [
    {
      "extensions": {
        "EXT_foundation_environment": {
          "type": "hdri",
          "bufferView": 3,
          "projection": "longlat",
          "strength": 1.0
        }
      }
    }
  ],
  "bufferViews": [
    "... regular glTF buffer views ...",
    {
      "buffer": 0,
      "byteOffset": 123456,
      "byteLength": 7890
    }
  ]
}
```

## Properties

- `type`: string, required. Either `"color"` or `"hdri"`.
- `color`: number array of length 3, required for `"color"`. Linear RGB environment radiance before `strength`.
- `uri`: string, required for sidecar `"hdri"` and mutually exclusive with `bufferView`. Relative URI to a `.hdr` or `.hdri` Radiance HDR file. For non-GLB exports, the exporter copies the source HDR next to the exported glTF file, using the configured texture sub-directory when one is set. The URI is always relative to the glTF file's directory.
- `bufferView`: integer, required for embedded `"hdri"` and mutually exclusive with `uri`. References a buffer view containing the raw Radiance HDR file bytes. For GLB exports, the exporter stores the HDRI in the GLB BIN chunk and writes this property instead of a sidecar `uri`.
- `projection`: string, optional for `"hdri"`, default `"longlat"`. Foundation supports `"longlat"` and `"equirectangular"`.
- `strength`: number, optional, default `1.0` for exported Blender worlds. Multiplies the color or HDRI radiance.
- `azimuthOffset`: number, optional, default `0.0`. Rotation in degrees around the vertical axis.
