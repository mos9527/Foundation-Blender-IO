# EXT_foundation_curves

Draft status: Foundation private extension.

This extension stores render-ready curve sets for Foundation. It is intentionally narrow: curves are exchanged as linear point/radius strands and can be rendered as capsule or tapered capsule segments by consumers.

## Motivation

glTF core has triangles, lines, and points, but no curve primitive with per-point radius, strand boundaries, or renderer-facing capsule semantics. Foundation needs a compact way to move Blender curve data into its procedural path tracer without tessellating the curves into triangle ribbons or tubes during export.

## Extension Placement

The extension has two parts:

- Root object: `extensions.EXT_foundation_curves.curves[]`
- Node object: `node.extensions.EXT_foundation_curves.curve`

The root array stores reusable curve sets. Node extensions reference entries in that array by index, allowing normal glTF node transforms, parenting, and instancing semantics to remain unchanged.

## Example

```json
{
  "extensionsUsed": ["EXT_foundation_curves"],
  "extensions": {
    "EXT_foundation_curves": {
      "curves": [
        {
          "name": "HairStrands",
          "basis": "linear",
          "renderMode": "capsule",
          "points": 12,
          "curveVertexCounts": 13,
          "material": 0
        }
      ]
    }
  },
  "nodes": [
    {
      "name": "HairStrands",
      "extensions": {
        "EXT_foundation_curves": {
          "curve": 0
        }
      }
    }
  ]
}
```

## Root Curve Object

- `name`: string, optional.
  Human-readable curve set name.

- `basis`: string, optional, default `linear`.
  Authoring basis. The first implementation writes and consumes `linear`. Reserved values are `bezier`, `bspline`, and `catmullRom`.

- `renderMode`: string, optional, default `capsule`.
  Intended procedural render primitive. The first implementation supports `capsule`, meaning each adjacent point pair forms a round segment with endpoint radii.

- `points`: accessor index, required.
  Accessor must be `VEC4` with `FLOAT` components. `xyz` stores point position in glTF local space. `w` stores point radius in glTF scene units.

- `curveVertexCounts`: accessor index, required.
  Accessor must be `SCALAR` with unsigned integer components. Each value is the number of consecutive points in one strand. Strand point ranges are concatenated in `points`.

- `material`: integer, optional.
  glTF material index to use for the curve set. If omitted, consumers use their default material.

## Node Extension Object

- `curve`: integer, required.
  Index into `extensions.EXT_foundation_curves.curves`.

## Blender Mapping

### Export

The Foundation Blender exporter writes `EXT_foundation_curves` for Blender `CURVE` and `CURVES` objects.

For legacy Blender `CURVE`:

```text
point.xyz = spline point coordinate, converted to glTF axes
point.w   = Curve.bevel_depth * SplinePoint.radius
```

For Blender `CURVES`:

```text
point.xyz = Curves point position, converted to glTF axes
point.w   = point-domain radius attribute when present
```

Each spline or strand contributes one `curveVertexCounts` entry. Cyclic legacy splines append the first point again to close the strand.

### Import

The Foundation Blender importer creates legacy Blender `CURVE` objects:

```text
Curve.dimensions       = "3D"
Curve.bevel_depth      = 1.0
Curve.bevel_resolution = 3
Spline type            = "POLY"
SplinePoint.co         = point.xyz converted to Blender axes
SplinePoint.radius     = point.w converted to Blender units
```

This preserves the exchanged linear strands and point radii directly. Native Blender `CURVES` import is out of scope for the first draft.

## Foundation Mapping

Foundation imports each root curve object as an `FCurveSet` and each node reference as an `FCurveInstance`.

For rendering, each adjacent point pair becomes one procedural segment:

```text
p0, r0 -> p1, r1
AABB = bounds(p0, p1) expanded by max(r0, r1)
intersection = linear-radius round segment
```

The path tracer currently renders the segment side as a tapered frustum when `r0 != r1`, plus endpoint sphere caps using `r0` and `r1`.

## Non-Goals

- No NURBS or knot vector representation.
- No native cubic procedural intersection in the first draft.
- No animation semantics in the first draft.
- No material-per-strand or material-per-segment override yet.
- No mandated rasterization behavior.

## TODO

- Add JSON schema once field names settle.
- Decide whether non-linear `basis` values should store original controls or always sampled linear render points.
- Add optional per-curve UV or custom attribute streams if needed.
