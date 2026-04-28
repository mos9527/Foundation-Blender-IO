# EXT_camera_lens

Draft status: Foundation private extension.

This extension stores the physical lens parameters needed to preserve Blender depth-of-field settings on a glTF camera. It is intentionally narrow: the fields mirror the Blender camera settings used by Foundation to derive aperture radius and focal plane distance.

## Motivation

glTF core cameras describe projection but do not carry physical aperture or focus information. Blender exposes depth of field through artist-facing camera controls:

- `Sensor Height`
- `F-Stop`
- `Focus Distance`
- `Blades`
- `Rotation`
- `Ratio`

Foundation needs these values to reproduce Blender-authored physical lens blur in its path tracer without baking renderer-specific aperture values into the file.

## Extension Object

The extension is attached to `camera.extensions`.

```json
{
  "cameras": [
    {
      "type": "perspective",
      "perspective": {
        "yfov": 0.785398,
        "znear": 0.1
      },
      "extensions": {
        "EXT_camera_lens": {
          "sensorSize": 36.0,
          "fStop": 2.8,
          "focusDistance": 10.0,
          "apertureBlades": 0,
          "apertureRotation": 0.0,
          "apertureRatio": 1.0
        }
      }
    }
  ]
}
```

## Properties

- `sensorSize`: number, required.
  Vertical camera sensor size in millimeters. This maps to Blender `Camera.sensor_height`.

- `fStop`: number, required.
  Lens f-number. This maps to Blender `Camera.dof.aperture_fstop` and must be greater than zero.

- `focusDistance`: number, required.
  Distance from the camera to the focal plane, in glTF scene units. Foundation treats glTF scene units as meters. This maps to Blender `Camera.dof.focus_distance`.

- `apertureBlades`: integer, optional, default `0`.
  Number of polygonal aperture blades. `0` means circular aperture. This maps to Blender `Camera.dof.aperture_blades`.

- `apertureRotation`: number, optional, default `0`.
  Aperture blade rotation in radians. This maps to Blender `Camera.dof.aperture_rotation`.

- `apertureRatio`: number, optional, default `1`.
  Anamorphic aperture ratio. This maps to Blender `Camera.dof.aperture_ratio`.

## Blender Mapping

For Blender cameras:

```text
Camera.sensor_height          = sensorSize
Camera.dof.aperture_fstop     = fStop
Camera.dof.focus_distance     = focusDistance
Camera.dof.aperture_blades    = apertureBlades
Camera.dof.aperture_rotation  = apertureRotation
Camera.dof.aperture_ratio     = apertureRatio
Camera.dof.use_dof            = true when EXT_camera_lens is present
```

The Foundation Blender exporter writes this extension for perspective cameras when Blender DoF is enabled. Orthographic cameras are out of scope for the first draft.

## Foundation Mapping

Foundation converts `sensorSize` and `fStop` into an aperture radius using the glTF perspective camera's vertical field of view:

```text
sensorHeightMeters = sensorSize * 0.001
focalLengthMeters  = (0.5 * sensorHeightMeters) / tan(yfov * 0.5)
apertureRadius     = focalLengthMeters / (2.0 * fStop)
focalDistance      = focusDistance
apertureBlades     = apertureBlades
apertureRotation   = apertureRotation
apertureRatio      = apertureRatio
```

`focusDistance` maps directly to the path tracer focal distance. `apertureBlades`, `apertureRotation`, and `apertureRatio` map to Foundation's bokeh shape controls.

## Non-Goals

- No lens distortion model.
- No sensor width or aspect-ratio override. `sensorSize` is the vertical sensor size.
- No animation semantics in the first draft.

## TODO

- Add JSON schema once the field names settle.
- Decide whether `sensorSize` should be renamed to `sensorHeight` before wider use.
