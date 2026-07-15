# Copyright 2018-2026 The glTF-Blender-IO authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
from mathutils import Vector

from ...io.com import gltf2_io
from ...io.com import constants as gltf2_io_constants
from ...io.exp import binary_data as gltf2_io_binary_data
from .accessors import gather_accessor, array_to_accessor
from .material.materials import gather_material


CURVES_DEFAULT_RADIUS = 0.01
# Blender Curves curve_type: 0=CATMULL_ROM, 1=POLY, 2=BEZIER, 3=NURBS
_CURVES_POLY_TYPE = 1


def gather_curve_mesh(blender_object, export_settings):
    """Export POLY curve objects as an indexed LINES mesh with POSITION/_RADIUS/TEXCOORD_0."""
    if blender_object is None or blender_object.type not in ["CURVE", "CURVES"]:
        return None

    if blender_object.type == "CURVE":
        positions, radii, texcoords, indices = __gather_legacy_poly_curve(blender_object, export_settings)
    else:
        positions, radii, texcoords, indices = __gather_curves_poly_curve(blender_object, export_settings)

    if len(positions) == 0 or len(indices) == 0:
        raise RuntimeError("'{}' does not contain any renderable POLY segments.".format(blender_object.name))

    positions = np.asarray(positions, dtype=np.float32).reshape(-1, 3)
    radii = np.asarray(radii, dtype=np.float32)
    texcoords = np.asarray(texcoords, dtype=np.float32).reshape(-1, 2)
    indices = np.asarray(indices, dtype=np.uint32)

    attributes = {
        "POSITION": array_to_accessor(
            positions,
            export_settings,
            component_type=gltf2_io_constants.ComponentType.Float,
            data_type=gltf2_io_constants.DataType.Vec3,
            include_max_and_min=True,
        ),
        "_RADIUS": array_to_accessor(
            radii,
            export_settings,
            component_type=gltf2_io_constants.ComponentType.Float,
            data_type=gltf2_io_constants.DataType.Scalar,
        ),
        "TEXCOORD_0": array_to_accessor(
            texcoords,
            export_settings,
            component_type=gltf2_io_constants.ComponentType.Float,
            data_type=gltf2_io_constants.DataType.Vec2,
        ),
    }

    index_accessor = gather_accessor(
        gltf2_io_binary_data.BinaryData(
            indices.tobytes(),
            gltf2_io_constants.BufferViewTarget.ELEMENT_ARRAY_BUFFER,
        ),
        gltf2_io_constants.ComponentType.UnsignedInt,
        len(indices),
        None,
        None,
        gltf2_io_constants.DataType.Scalar,
        export_settings,
    )

    primitive = gltf2_io.MeshPrimitive(
        attributes=attributes,
        extensions=None,
        extras=None,
        indices=index_accessor,
        material=__gather_curve_material(blender_object, export_settings),
        mode=1,  # LINES
        targets=None,
    )

    return gltf2_io.Mesh(
        extensions=None,
        extras=None,
        name=blender_object.name,
        weights=None,
        primitives=[primitive],
    )


def __gather_curve_material(blender_object, export_settings):
    if export_settings.get("gltf_materials") not in ["EXPORT", "VIEWPORT"]:
        return None

    material = None
    if blender_object.material_slots:
        material = blender_object.material_slots[0].material
    if material is None and getattr(blender_object.data, "materials", None):
        material = blender_object.data.materials[0] if len(blender_object.data.materials) > 0 else None
    if material is None:
        return None

    gathered_material, _ = gather_material(material, export_settings)
    return gathered_material


def __gather_legacy_poly_curve(blender_object, export_settings):
    curve = blender_object.data
    positions = []
    radii = []
    texcoords = []
    indices = []
    default_radius = max(float(getattr(curve, "bevel_depth", 0.0)), 0.001)

    for spline in curve.splines:
        if spline.type != "POLY":
            raise RuntimeError(
                "Foundation curve export requires every spline in '{}' to be POLY; found {}.".format(
                    blender_object.name, spline.type))

        points = list(spline.points)
        if len(points) < 2:
            raise RuntimeError(
                "Foundation curve export requires at least two points per POLY spline in '{}'.".format(
                    blender_object.name))

        first = len(positions) // 3
        cyclic = bool(getattr(spline, "use_cyclic_u", False))
        count = len(points)
        for i, point in enumerate(points):
            __append_vertex(
                positions, radii, texcoords,
                point.co, default_radius * float(getattr(point, "radius", 1.0)),
                float(i) / float(count if cyclic else max(count - 1, 1)),
                export_settings)

        segment_count = count if cyclic else count - 1
        for i in range(segment_count):
            indices.extend([first + i, first + ((i + 1) % count)])

    return positions, radii, texcoords, indices


def __gather_curves_poly_curve(blender_object, export_settings):
    curves = blender_object.data
    point_count = len(curves.points)
    curve_count = len(curves.curves)
    if point_count == 0 or curve_count == 0:
        raise RuntimeError("'{}' does not contain any curves.".format(blender_object.name))

    __assert_curves_object_is_poly(curves, blender_object.name)

    raw_positions = [0.0] * (point_count * 3)
    curves.points.foreach_get("position", raw_positions)
    point_radii = __read_curves_float_attribute(curves, "radius", point_count, CURVES_DEFAULT_RADIUS)
    cyclic = __read_curves_bool_attribute(curves, "cyclic", curve_count)

    first_point_indices = [0] * curve_count
    curve_point_counts = [0] * curve_count
    curves.curves.foreach_get("first_point_index", first_point_indices)
    curves.curves.foreach_get("points_length", curve_point_counts)

    positions = []
    radii = []
    texcoords = []
    indices = []
    for curve_index, (first_point, count) in enumerate(zip(first_point_indices, curve_point_counts)):
        if count < 2:
            raise RuntimeError(
                "Foundation curve export requires at least two points per POLY curve in '{}'.".format(
                    blender_object.name))

        first = len(positions) // 3
        is_cyclic = cyclic[curve_index]
        for i in range(count):
            src = first_point + i
            co = Vector((raw_positions[src * 3], raw_positions[src * 3 + 1], raw_positions[src * 3 + 2]))
            u = float(i) / float(count if is_cyclic else max(count - 1, 1))
            __append_vertex(positions, radii, texcoords, co, point_radii[src], u, export_settings)

        segment_count = count if is_cyclic else count - 1
        for i in range(segment_count):
            indices.extend([first + i, first + ((i + 1) % count)])

    return positions, radii, texcoords, indices


def __assert_curves_object_is_poly(curves, object_name):
    curve_type_attr = curves.attributes.get("curve_type") if hasattr(curves, "attributes") else None
    if curve_type_attr is None:
        raise RuntimeError(
            "Foundation curve export requires '{}' to expose a curve_type attribute.".format(object_name))

    curve_types = [0] * len(curves.curves)
    curve_type_attr.data.foreach_get("value", curve_types)
    for curve_type in curve_types:
        if not __is_poly_curve_type(curve_type):
            raise RuntimeError(
                "Foundation curve export requires every curve in '{}' to be POLY.".format(object_name))


def __is_poly_curve_type(curve_type):
    if curve_type == "POLY":
        return True
    try:
        return int(curve_type) == _CURVES_POLY_TYPE
    except (TypeError, ValueError):
        return False


def __read_curves_float_attribute(curves, name, point_count, default_value):
    attr = curves.attributes.get(name) if hasattr(curves, "attributes") else None
    values = [default_value] * point_count
    if attr is not None:
        attr.data.foreach_get("value", values)
    return values


def __read_curves_bool_attribute(curves, name, curve_count):
    attr = curves.attributes.get(name) if hasattr(curves, "attributes") else None
    if attr is None:
        return [False] * curve_count

    values = [False] * curve_count
    attr.data.foreach_get("value", values)
    return values


def __append_vertex(positions, radii, texcoords, co, radius, u, export_settings):
    co = __convert_swizzle_location(co, export_settings)
    positions.extend([float(co[0]), float(co[1]), float(co[2])])
    radii.append(max(float(radius), 0.0))
    texcoords.extend([float(u), 0.0])


def __convert_swizzle_location(loc, export_settings):
    if export_settings["gltf_yup"]:
        return Vector((loc[0], loc[2], -loc[1]))
    return Vector((loc[0], loc[1], loc[2]))
