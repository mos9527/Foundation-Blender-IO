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
        }
      ]
    }
  }
}
```

## Properties

- `angularDiameter`: number, optional, default `0.0`.
  The apparent size of the light source disk in radians.
