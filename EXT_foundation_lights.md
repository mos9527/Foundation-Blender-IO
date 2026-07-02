# EXT_foundation_lights

Draft status: Foundation private extension.

This extension serves as a central hub for any new per-light additions that the official `KHR_lights_punctual` lacks.

## Extension Placement

The extension is attached to `light.extensions` (inside a `KHR_lights_punctual` light object).

## Example

```json
{
  "extensionsUsed": [
    "KHR_lights_punctual",
    "EXT_foundation_lights"
  ],
  "extensions": {
    "KHR_lights_punctual": {
      "lights": [
        {
          "type": "directional",
          "color": [1.0, 1.0, 1.0],
          "intensity": 1.0,
          "extensions": {
            "EXT_foundation_lights": {
              "angularDiameter": 0.00925
            }
          }
        },
        {
          "type": "point",
          "color": [1.0, 0.92, 0.78],
          "intensity": 10.0,
          "extensions": {
            "EXT_foundation_lights": {
              "radius": 0.25,
              "useShadow": false
            }
          }
        }
      ]
    }
  }
}
```

## Properties

- `angularDiameter`: number, optional, default `0.0`.
  The apparent size of the light source disk in radians.

- `radius`: number, optional, default `0.0`.
  Point and spot emitter sphere radius in glTF scene units. `0.0` means punctual.

- `useShadow`: boolean, optional, default `true`.
  Whether this light casts shadows.
