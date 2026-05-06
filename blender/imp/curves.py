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

        name = pycurve.get("name") or vnode.name or "Curve_%d" % curve_id
        curve = bpy.data.curves.new(name, "CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 1
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
            if count <= 1:
                point_cursor += count
                continue

            spline = curve.splines.new("POLY")
            spline.points.add(count - 1)
            for i in range(count):
                co = locs[point_cursor + i]
                point = spline.points[i]
                point.co = (float(co[0]), float(co[1]), float(co[2]), 1.0)
                point.radius = max(__radius_gltf_to_blender(gltf, float(radii[point_cursor + i])), 0.0)
            point_cursor += count

        if "material" in pycurve:
            material_idx = pycurve["material"]
            pymaterial = gltf.data.materials[material_idx]
            if None not in pymaterial.blender_material:
                BlenderMaterial.create(gltf, material_idx, None)
            curve.materials.append(bpy.data.materials[pymaterial.blender_material[None]])

        import_user_extensions('gather_import_curve_after_hook', gltf, vnode, pycurve, curve)
        return curve


def __radius_gltf_to_blender(gltf, radius):
    return gltf.loc_gltf_to_blender([radius, 0.0, 0.0]).length
