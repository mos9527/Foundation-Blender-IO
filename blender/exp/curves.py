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
        points, curve_vertex_counts = __gather_legacy_curve(blender_object, export_settings)
    else:
        points, curve_vertex_counts = __gather_curves(blender_object, export_settings)

    if len(points) == 0 or len(curve_vertex_counts) == 0:
        return None

    return {
        "name": blender_object.name,
        "basis": "linear",
        "renderMode": "capsule",
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


def __gather_legacy_curve(blender_object, export_settings):
    curve = blender_object.data
    points = []
    curve_vertex_counts = []
    default_radius = max(float(getattr(curve, "bevel_depth", 0.0)), 0.001)

    for spline in curve.splines:
        first_point = len(points) // 4
        if spline.type == "BEZIER":
            for point in spline.bezier_points:
                __append_point(points, point.co, default_radius * float(getattr(point, "radius", 1.0)), export_settings)
        else:
            for point in spline.points:
                co = point.co
                weight = co[3] if len(co) > 3 and abs(co[3]) > 1e-8 else 1.0
                __append_point(points, Vector((co[0] / weight, co[1] / weight, co[2] / weight)),
                               default_radius * float(getattr(point, "radius", 1.0)), export_settings)

        point_count = len(points) // 4 - first_point
        if point_count > 1 and getattr(spline, "use_cyclic_u", False):
            points.extend(points[first_point * 4:first_point * 4 + 4])
            point_count += 1
        if point_count > 1:
            curve_vertex_counts.append(point_count)
        else:
            del points[first_point * 4:]

    return points, curve_vertex_counts


def __gather_curves(blender_object, export_settings):
    curves = blender_object.data
    point_count = len(curves.points)
    if point_count == 0:
        return [], []

    positions = [0.0] * (point_count * 3)
    curves.points.foreach_get("position", positions)

    radii = [0.001] * point_count
    radius_attr = curves.attributes.get("radius") if hasattr(curves, "attributes") else None
    if radius_attr is not None:
        for i, item in enumerate(radius_attr.data):
            radii[i] = max(float(getattr(item, "value", radii[i])), 0.0)

    first_point_indices = [0]
    curve_vertex_counts = [point_count]
    try:
        curve_vertex_counts = [0] * len(curves.curves)
        curves.curves.foreach_get("points_length", curve_vertex_counts)
        first_point_indices = [0] * len(curves.curves)
        curves.curves.foreach_get("first_point_index", first_point_indices)
    except Exception:
        pass

    points = []
    exported_curve_vertex_counts = []
    for first_point, count in zip(first_point_indices, curve_vertex_counts):
        if count <= 1:
            continue
        for i in range(first_point, first_point + count):
            __append_point(points, Vector((positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2])),
                           radii[i], export_settings)
        exported_curve_vertex_counts.append(count)
    return points, exported_curve_vertex_counts


def __append_point(points, co, radius, export_settings):
    co = __convert_swizzle_location(co, export_settings)
    points.extend([float(co[0]), float(co[1]), float(co[2]), max(float(radius), 0.0)])


def __convert_swizzle_location(loc, export_settings):
    if export_settings["gltf_yup"]:
        return Vector((loc[0], loc[2], -loc[1]))
    return Vector((loc[0], loc[1], loc[2]))
