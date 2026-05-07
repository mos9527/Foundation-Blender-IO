# EXT_foundation_materials

Draft status: Foundation private extension.

This material extension selects the Foundation shader block to use for a glTF material. It is intentionally small: the standard glTF material fields still carry base color, textures, IOR, and ordinary Principled parameters, while this extension carries Foundation-specific shader selection and hair controls.

## Material Extension Object

```json
{
  "materials": [
    {
      "extensions": {
        "EXT_foundation_materials": {
          "shaderBlock": "hair",
          "model": "chiang",
          "betaM": 0.3,
          "betaN": 0.3,
          "alpha": 2.0
        }
      }
    }
  ]
}
```

- `shaderBlock`: string, required when the extension is present.
  Supported values are `principled` and `hair`.

- `model`: string, required for `shaderBlock: "hair"`.
  The current implementation supports only `chiang`.

- `betaM`: number, optional.
  Longitudinal hair roughness in `[0, 1]`.

- `betaN`: number, optional.
  Azimuthal hair roughness in `[0, 1]`.

- `alpha`: number, optional.
  Hair scale tilt in degrees.

## Blender Mapping

The Foundation Blender exporter chooses the shader block from the active material shader:

- Active Principled BSDF node exports `shaderBlock: "principled"`.
- Active Principled Hair BSDF node exports `shaderBlock: "hair"` with `model: "chiang"`.

For Principled Hair, scalar socket values are mapped as:

- `Roughness` -> `betaM`
- `Radial Roughness` -> `betaN`
- `Offset` -> `alpha`

Only the Chiang Principled Hair model is exported. Other hair models fail export so Foundation does not silently import a different scattering model.
