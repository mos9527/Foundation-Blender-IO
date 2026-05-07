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

import bpy

from ...io.imp.gltf2_io_binary import BinaryData
from ...io.imp.user_extensions import import_user_extensions
from .material import BlenderMaterial


EXT_FOUNDATION_CURVES = "EXT_foundation_curves"


class BlenderCurve():
    """Foundation curve extension importer."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, vnode, curve_id):
        root_ext = (gltf.data.extensions or {}).get(EXT_FOUNDATION_CURVES, {})
        pycurve = root_ext.get("curves", [])[curve_id]
        import_user_extensions('gather_import_curve_before_hook', gltf, vnode, pycurve)

        basis = pycurve.get("basis", "linear")
        if basis != "bezier":
            raise RuntimeError(
                "EXT_foundation_curves import only supports basis 'bezier'; found '{}'.".format(basis))

        name = pycurve.get("name") or vnode.name or "Curve_%d" % curve_id
        curve = bpy.data.curves.new(name, "CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 12
        curve.bevel_depth = 1.0
        curve.bevel_resolution = 3

        points = BinaryData.decode_accessor(gltf, pycurve["points"]).copy()
        locs = points[:, 0:3].copy()
        gltf.locs_batch_gltf_to_blender(locs)
        radii = points[:, 3]

        curve_counts = BinaryData.decode_accessor(gltf, pycurve["curveVertexCounts"]).reshape(-1)
        point_cursor = 0
        for count in curve_counts:
            count = int(count)
            if count < 4 or (count - 1) % 3 != 0:
                raise RuntimeError(
                    "EXT_foundation_curves Bezier strands must contain 3n + 1 controls; found {}.".format(count))

            if point_cursor + count > len(points):
                raise RuntimeError("EXT_foundation_curves curveVertexCounts references more points than stored.")

            segment_count = (count - 1) // 3
            cyclic = _is_repeated_endpoint(locs, radii, point_cursor, count)
            anchor_count = segment_count if cyclic else segment_count + 1

            spline = curve.splines.new("BEZIER")
            spline.bezier_points.add(anchor_count - 1)
            spline.use_cyclic_u = cyclic
            for i in range(anchor_count):
                anchor = point_cursor + i * 3
                point = spline.bezier_points[i]
                _set_bezier_point(point, gltf, locs, radii, anchor)
                _set_handle(point, "handle_left", locs[_left_handle_index(point_cursor, count, i, cyclic)])
                _set_handle(point, "handle_right", locs[_right_handle_index(point_cursor, segment_count, i, cyclic)])
            point_cursor += count

        if point_cursor != len(points):
            raise RuntimeError("EXT_foundation_curves stores unused curve points.")

        if "material" in pycurve:
            material_idx = pycurve["material"]
            pymaterial = gltf.data.materials[material_idx]
            if None not in pymaterial.blender_material:
                BlenderMaterial.create(gltf, material_idx, None)
            curve.materials.append(bpy.data.materials[pymaterial.blender_material[None]])

        import_user_extensions('gather_import_curve_after_hook', gltf, vnode, pycurve, curve)
        return curve


def _radius_gltf_to_blender(gltf, radius):
    return gltf.loc_gltf_to_blender([radius, 0.0, 0.0]).length


def _set_bezier_point(point, gltf, locs, radii, index):
    co = locs[index]
    point.co = (float(co[0]), float(co[1]), float(co[2]))
    point.radius = max(_radius_gltf_to_blender(gltf, float(radii[index])), 0.0)
    point.handle_left_type = "FREE"
    point.handle_right_type = "FREE"


def _set_handle(point, attr, co):
    setattr(point, attr, (float(co[0]), float(co[1]), float(co[2])))


def _left_handle_index(first_point, count, anchor_index, cyclic):
    if anchor_index == 0:
        return first_point + count - 2 if cyclic else first_point
    return first_point + anchor_index * 3 - 1


def _right_handle_index(first_point, segment_count, anchor_index, cyclic):
    if anchor_index == segment_count:
        return first_point + anchor_index * 3 if not cyclic else first_point + anchor_index * 3 + 1
    return first_point + anchor_index * 3 + 1


def _is_repeated_endpoint(locs, radii, first_point, count):
    first = locs[first_point]
    last = locs[first_point + count - 1]
    if abs(float(radii[first_point]) - float(radii[first_point + count - 1])) > 1e-6:
        return False
    return all(abs(float(first[i]) - float(last[i])) <= 1e-6 for i in range(3))
