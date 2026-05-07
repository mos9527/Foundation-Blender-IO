# Copyright 2018-2025 The glTF-Blender-IO authors.
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

from mathutils import Vector

from ...io.com import constants as gltf2_io_constants
from ...io.exp import binary_data as gltf2_io_binary_data
from .accessors import gather_accessor


EXT_FOUNDATION_CURVES = "EXT_foundation_curves"


def gather_curve(blender_object, export_settings):
    if blender_object is None or blender_object.type not in ["CURVE", "CURVES"]:
        return None

    if blender_object.type == "CURVE":
        points, curve_vertex_counts = __gather_legacy_bezier_curve(blender_object, export_settings)
    else:
        points, curve_vertex_counts = __gather_curves_bezier_curve(blender_object, export_settings)

    if len(points) == 0 or len(curve_vertex_counts) == 0:
        raise RuntimeError("'{}' does not contain any renderable Bezier splines.".format(blender_object.name))

    return {
        "name": blender_object.name,
        "basis": "bezier",
        "points": gather_accessor(
            gltf2_io_binary_data.BinaryData.from_list(points, gltf2_io_constants.ComponentType.Float),
            gltf2_io_constants.ComponentType.Float,
            len(points) // 4,
            None,
            None,
            gltf2_io_constants.DataType.Vec4,
            export_settings),
        "curveVertexCounts": gather_accessor(
            gltf2_io_binary_data.BinaryData.from_list(curve_vertex_counts, gltf2_io_constants.ComponentType.UnsignedInt),
            gltf2_io_constants.ComponentType.UnsignedInt,
            len(curve_vertex_counts),
            None,
            None,
            gltf2_io_constants.DataType.Scalar,
            export_settings),
    }


def __gather_legacy_bezier_curve(blender_object, export_settings):
    curve = blender_object.data
    points = []
    curve_vertex_counts = []
    default_radius = max(float(getattr(curve, "bevel_depth", 0.0)), 0.001)

    for spline in curve.splines:
        if spline.type != "BEZIER":
            raise RuntimeError(
                "EXT_foundation_curves Bezier export requires every spline in '{}' to be BEZIER; "
                "found {}.".format(blender_object.name, spline.type))

        bezier_points = list(spline.bezier_points)
        if len(bezier_points) < 2:
            raise RuntimeError(
                "EXT_foundation_curves Bezier export requires at least two points per spline in '{}'.".format(
                    blender_object.name))

        first_point = len(points) // 4
        segment_count = len(bezier_points) if getattr(spline, "use_cyclic_u", False) else len(bezier_points) - 1
        __append_bezier_anchor(points, bezier_points[0], default_radius, export_settings)

        for i in range(segment_count):
            point = bezier_points[i]
            next_point = bezier_points[(i + 1) % len(bezier_points)]
            radius = __point_radius(point, default_radius)
            next_radius = __point_radius(next_point, default_radius)

            __append_point(points, point.handle_right, __lerp(radius, next_radius, 1.0 / 3.0), export_settings)
            __append_point(points, next_point.handle_left, __lerp(radius, next_radius, 2.0 / 3.0), export_settings)
            __append_bezier_anchor(points, next_point, default_radius, export_settings)

        point_count = len(points) // 4 - first_point
        curve_vertex_counts.append(point_count)

    return points, curve_vertex_counts


def __gather_curves_bezier_curve(blender_object, export_settings):
    curves = blender_object.data
    point_count = len(curves.points)
    curve_count = len(curves.curves)
    if point_count == 0 or curve_count == 0:
        raise RuntimeError("'{}' does not contain any curves.".format(blender_object.name))

    __assert_curves_object_is_bezier(curves, blender_object.name)

    positions = [0.0] * (point_count * 3)
    curves.points.foreach_get("position", positions)
    radii = [0.0] * point_count
    curves.points.foreach_get("radius", radii)
    handles_left = __read_curves_vector_attribute(curves, ("handle_position_left", "handle_left"), point_count)
    handles_right = __read_curves_vector_attribute(curves, ("handle_position_right", "handle_right"), point_count)
    cyclic = __read_curves_bool_attribute(curves, "cyclic", curve_count)

    first_point_indices = [0] * curve_count
    curve_point_counts = [0] * curve_count
    curves.curves.foreach_get("first_point_index", first_point_indices)
    curves.curves.foreach_get("points_length", curve_point_counts)

    points = []
    curve_vertex_counts = []
    for curve_index, (first_point, count) in enumerate(zip(first_point_indices, curve_point_counts)):
        if count < 2:
            raise RuntimeError(
                "EXT_foundation_curves Bezier export requires at least two points per curve in '{}'.".format(
                    blender_object.name))

        first_control = len(points) // 4
        segment_count = count if cyclic[curve_index] else count - 1
        __append_curves_control(points, positions, radii, first_point, export_settings)
        for i in range(segment_count):
            point = first_point + i
            next_point = first_point + ((i + 1) % count)
            radius = radii[point]
            next_radius = radii[next_point]

            __append_point(points, __vector_at(handles_right, point), __lerp(radius, next_radius, 1.0 / 3.0), export_settings)
            __append_point(points, __vector_at(handles_left, next_point), __lerp(radius, next_radius, 2.0 / 3.0), export_settings)
            __append_curves_control(points, positions, radii, next_point, export_settings)

        curve_vertex_counts.append(len(points) // 4 - first_control)

    return points, curve_vertex_counts


def __assert_curves_object_is_bezier(curves, object_name):
    curve_type_attr = curves.attributes.get("curve_type") if hasattr(curves, "attributes") else None
    if curve_type_attr is None:
        raise RuntimeError(
            "EXT_foundation_curves Bezier export requires '{}' to expose a curve_type attribute.".format(object_name))

    curve_types = [0] * len(curves.curves)
    curve_type_attr.data.foreach_get("value", curve_types)
    for curve_type in curve_types:
        if not __is_bezier_curve_type(curve_type):
            raise RuntimeError(
                "EXT_foundation_curves Bezier export requires every curve in '{}' to be BEZIER.".format(object_name))


def __is_bezier_curve_type(curve_type):
    if curve_type == "BEZIER":
        return True
    try:
        return int(curve_type) == 2
    except (TypeError, ValueError):
        return False


def __read_curves_vector_attribute(curves, names, point_count):
    attr = None
    for name in names:
        attr = curves.attributes.get(name)
        if attr is not None:
            break
    if attr is None:
        raise RuntimeError("EXT_foundation_curves Bezier export requires point attribute '{}'.".format(names[0]))

    values = [0.0] * (point_count * 3)
    attr.data.foreach_get("vector", values)
    return values


def __read_curves_bool_attribute(curves, name, curve_count):
    attr = curves.attributes.get(name) if hasattr(curves, "attributes") else None
    if attr is None:
        return [False] * curve_count

    values = [False] * curve_count
    attr.data.foreach_get("value", values)
    return values


def __append_bezier_anchor(points, point, default_radius, export_settings):
    __append_point(points, point.co, __point_radius(point, default_radius), export_settings)


def __append_curves_control(points, positions, radii, index, export_settings):
    __append_point(points, __vector_at(positions, index), radii[index], export_settings)


def __vector_at(values, index):
    return Vector((values[index * 3], values[index * 3 + 1], values[index * 3 + 2]))


def __point_radius(point, default_radius):
    return default_radius * float(getattr(point, "radius", 1.0))


def __lerp(a, b, t):
    return a + (b - a) * t


def __append_point(points, co, radius, export_settings):
    co = __convert_swizzle_location(co, export_settings)
    points.extend([float(co[0]), float(co[1]), float(co[2]), max(float(radius), 0.0)])


def __convert_swizzle_location(loc, export_settings):
    if export_settings["gltf_yup"]:
        return Vector((loc[0], loc[2], -loc[1]))
    return Vector((loc[0], loc[1], loc[2]))
