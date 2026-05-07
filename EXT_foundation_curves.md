# EXT_foundation_curves

Draft status: Foundation private extension.

This extension stores Foundation curve sets. It is intentionally narrow: the current Blender I/O path exchanges cubic Bezier point/radius strands for Foundation's procedural path tracer.

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
          "basis": "bezier",
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

- `basis`: string, required.
  Authoring basis. The current implementation writes and consumes only `bezier`.

- `points`: accessor index, required.
  Accessor must be `VEC4` with `FLOAT` components. `xyz` stores control point position in glTF local space. `w` stores control point radius in glTF scene units.

  For `basis: "bezier"`, each strand stores a cubic control stream with `3n + 1` points:

  ```text
  P0, H0_right, H1_left, P1, H1_right, H2_left, P2, ...
  ```

  Radius is stored for every control point. Blender Bezier handles do not have independent radii, so the exporter writes handle radii by linearly interpolating the neighboring anchor radii at one-third and two-thirds of the segment.

- `curveVertexCounts`: accessor index, required.
  Accessor must be `SCALAR` with unsigned integer components. Each value is the number of consecutive control points in one strand. For `basis: "bezier"`, every count must be `3n + 1`. Strand point ranges are concatenated in `points`.

- `material`: integer, optional.
  glTF material index to use for the curve set. If omitted, consumers use their default material.

## Node Extension Object

- `curve`: integer, required.
  Index into `extensions.EXT_foundation_curves.curves`.

## Blender Mapping

### Export

The Foundation Blender exporter writes `EXT_foundation_curves` for legacy Blender `CURVE` objects and newer Blender `CURVES` objects. Export fails if a curve object contains any non-`BEZIER` splines/curves.

For each legacy Blender `CURVE` Bezier segment from point `i` to point `i + 1`:

```text
P_i.xyz       = BezierPoint.co, converted to glTF axes
H_i_right.xyz = BezierPoint.handle_right, converted to glTF axes
H_next_left.xyz = NextBezierPoint.handle_left, converted to glTF axes
P_next.xyz    = NextBezierPoint.co, converted to glTF axes

anchor radius = Curve.bevel_depth * BezierPoint.radius
handle radius = linear interpolation between neighboring anchor radii
```

For each newer Blender `CURVES` Bezier segment:

```text
P_i.xyz        = CurvePoint.position, converted to glTF axes
H_i_right.xyz  = handle_position_right point attribute, converted to glTF axes
H_next_left.xyz = handle_position_left point attribute, converted to glTF axes
P_next.xyz     = Next CurvePoint.position, converted to glTF axes

anchor radius = CurvePoint.radius
handle radius = linear interpolation between neighboring anchor radii
```

Each spline/curve contributes one `curveVertexCounts` entry. Cyclic splines/curves write the final segment back to the first anchor, so the first anchor appears again as the final control point.

### Import

The Foundation Blender importer creates legacy Blender `CURVE` objects:

```text
Curve.dimensions       = "3D"
Curve.bevel_depth      = 1.0
Curve.bevel_resolution = 3
Spline type            = "BEZIER"
BezierPoint.co         = anchor point.xyz converted to Blender axes
BezierPoint handles    = handle point.xyz converted to Blender axes
BezierPoint.radius     = anchor point.w converted to Blender units
```

The importer rejects non-Bezier payloads. Native Blender `CURVES` import is out of scope for this draft.

## Foundation Mapping

Foundation imports each root curve object as an `FCurveSet` and each node reference as an `FCurveInstance`.

The extension stores the Bezier data exchange only. Consumers choose their own render interpretation, such as ray-facing ribbons, swept cylinders, capsules, or tessellated mesh geometry. Foundation's current path tracer maps one procedural primitive to each cubic Bezier span:

```text
P0, H0, H1, P1
AABB = conservative Bezier bounds expanded by max control radius
intersection = consumer-defined curve/radius test
```

The path tracer currently uses ray-facing flat curve intersection and interprets hits as round fibers for shading.

## Non-Goals

- No NURBS or knot vector representation.
- No B-spline or Catmull-Rom representation.
- No animation semantics in the first draft.
- No material-per-strand or material-per-segment override yet.
- No mandated rasterization behavior.

## TODO

- Add JSON schema once field names settle.
- Add optional per-curve UV or custom attribute streams if needed.
