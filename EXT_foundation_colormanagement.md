# EXT_foundation_colormanagement

Draft status: Foundation private extension.

This root extension stores the Foundation editor display transform selection authored from Blender color management.

## Extension Placement

Root object: `extensions.EXT_foundation_colormanagement`.

## Example

```json
{
  "extensionsUsed": ["EXT_foundation_colormanagement"],
  "extensions": {
    "EXT_foundation_colormanagement": {
      "postExposure": 0.0,
      "sdr": "SDR / ACES 1.3 / No Look",
      "hdr": "HDR / ACES 1.3 - HDR 1000 nits / No Look"
    }
  }
}
```

## Properties

- `postExposure`: number, optional.
  Blender color-management exposure, in EV.

- `sdr`: string, optional.
  Foundation SDR LUT tuple formatted as `SDR / View / Look`.

- `hdr`: string, optional.
  Foundation HDR LUT tuple formatted as `HDR / View / Look`.

Foundation matches imported LUT tuples against its built-in LUT catalog by `(View, Look)`.
If one display side cannot be represented by Blender's single active display setting, the exporter writes the active side and defaults the other side to ACES 1.3.
