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

import bpy
import numpy as np
from collections import defaultdict

from ...io.imp.gltf2_io_binary import BinaryData
from ...io.imp.user_extensions import import_user_extensions
from .material import BlenderMaterial


# glTF mesh primitive modes
_LINES = 1
_LINE_LOOP = 2
_LINE_STRIP = 3
_LINE_MODES = {_LINES, _LINE_LOOP, _LINE_STRIP}


class BlenderCurve():
    """Import Foundation curve LINES meshes as Blender POLY curves."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def is_curve_mesh(pymesh):
        if not pymesh.primitives:
            return False
        return all(_is_curve_primitive(prim) for prim in pymesh.primitives)

    @staticmethod
    def create(gltf, mesh_idx):
        pymesh = gltf.data.meshes[mesh_idx]
        import_user_extensions('gather_import_curve_before_hook', gltf, pymesh)

        name = pymesh.name or 'Curve_%d' % mesh_idx
        curve = bpy.data.curves.new(name, 'CURVE')
        curve.dimensions = '3D'
        # Export multiplies bevel_depth by per-point radius; store absolute radii on points.
        curve.bevel_depth = 1.0
        curve.bevel_resolution = 3

        material_idx = None
        for prim in pymesh.primitives:
            _add_primitive_polylines(gltf, curve, prim)
            if material_idx is None and prim.material is not None:
                material_idx = prim.material

        gltf.decode_accessor_cache = {}

        if material_idx is not None:
            pymaterial = gltf.data.materials[material_idx]
            if None not in pymaterial.blender_material:
                BlenderMaterial.create(gltf, material_idx, None)
            curve.materials.append(bpy.data.materials[pymaterial.blender_material[None]])

        import_user_extensions('gather_import_curve_after_hook', gltf, pymesh, curve)
        return curve


def _is_curve_primitive(prim):
    mode = _LINES if prim.mode is None else prim.mode
    if mode not in _LINE_MODES:
        return False
    attrs = prim.attributes or {}
    return 'POSITION' in attrs and '_RADIUS' in attrs


def _add_primitive_polylines(gltf, curve, prim):
    locs = BinaryData.decode_accessor(gltf, prim.attributes['POSITION'], cache=True).copy()
    gltf.locs_batch_gltf_to_blender(locs)

    radii = BinaryData.decode_accessor(gltf, prim.attributes['_RADIUS'], cache=True).reshape(-1)
    if len(radii) != len(locs):
        raise RuntimeError("Curve _RADIUS count ({}) != POSITION count ({})".format(len(radii), len(locs)))

    us = None
    if 'TEXCOORD_0' in prim.attributes:
        uvs = BinaryData.decode_accessor(gltf, prim.attributes['TEXCOORD_0'], cache=True)
        us = uvs[:, 0].copy() if uvs.ndim == 2 else uvs.reshape(-1)

    mode = _LINES if prim.mode is None else prim.mode
    if mode == _LINES:
        polylines = _polylines_from_lines(prim, gltf, len(locs), us)
    else:
        order = _primitive_vertex_order(gltf, prim, len(locs))
        polylines = [(order, mode == _LINE_LOOP)]

    for order, cyclic in polylines:
        if len(order) < 2:
            continue
        order = _orient_polyline(order, us, cyclic)
        _add_poly_spline(curve, locs, radii, order, cyclic, gltf)


def _primitive_vertex_order(gltf, prim, point_count):
    if prim.indices is not None:
        indices = BinaryData.decode_accessor(gltf, prim.indices).reshape(-1)
        return [int(i) for i in indices]
    return list(range(point_count))


def _polylines_from_lines(prim, gltf, point_count, us):
    if prim.indices is not None:
        indices = BinaryData.decode_accessor(gltf, prim.indices).reshape(-1)
        if len(indices) % 2 != 0:
            raise RuntimeError("Indexed LINES index count must be even")
        segments = [(int(indices[i]), int(indices[i + 1])) for i in range(0, len(indices), 2)]
    else:
        if point_count % 2 != 0:
            raise RuntimeError("Non-indexed LINES vertex count must be even")
        segments = [(i, i + 1) for i in range(0, point_count, 2)]

    return _chains_from_segments(segments, us)


def _chains_from_segments(segments, us):
    adj = defaultdict(list)
    edge_set = set()
    for a, b in segments:
        if a == b:
            continue
        edge = (a, b) if a < b else (b, a)
        if edge in edge_set:
            continue
        edge_set.add(edge)
        adj[a].append(b)
        adj[b].append(a)

    unused = set(edge_set)
    polylines = []

    def take_edge(u, v):
        edge = (u, v) if u < v else (v, u)
        if edge not in unused:
            return False
        unused.remove(edge)
        return True

    def walk(start, first_neighbor=None):
        path = [start]
        prev = None
        cur = start
        if first_neighbor is not None:
            if not take_edge(cur, first_neighbor):
                return path, False
            path.append(first_neighbor)
            prev, cur = cur, first_neighbor

        while True:
            nxt = None
            for candidate in adj[cur]:
                edge = (cur, candidate) if cur < candidate else (candidate, cur)
                if edge in unused and candidate != prev:
                    nxt = candidate
                    break
            if nxt is None:
                # Prefer closing a cycle when back at start with one remaining edge.
                for candidate in adj[cur]:
                    edge = (cur, candidate) if cur < candidate else (candidate, cur)
                    if edge in unused and candidate == start and len(path) >= 3:
                        take_edge(cur, candidate)
                        return path, True
                return path, False
            take_edge(cur, nxt)
            if nxt == start and len(path) >= 3:
                return path, True
            path.append(nxt)
            prev, cur = cur, nxt

    # Open strands first (degree-1 endpoints), then remaining cycles.
    endpoints = [v for v, neighbors in adj.items() if len(neighbors) == 1]
    endpoints.sort(key=lambda v: float(us[v]) if us is not None else v)
    for start in endpoints:
        if not any(((start, n) if start < n else (n, start)) in unused for n in adj[start]):
            continue
        path, cyclic = walk(start)
        if len(path) >= 2:
            polylines.append((path, cyclic))

    while unused:
        a, b = next(iter(unused))
        path, cyclic = walk(a, first_neighbor=b)
        if len(path) >= 2:
            polylines.append((path, cyclic))
        else:
            unused.discard((a, b) if a < b else (b, a))

    return polylines


def _orient_polyline(order, us, cyclic):
    if us is None or len(order) < 2:
        return order
    order = list(order)
    if float(us[order[-1]]) < float(us[order[0]]):
        order.reverse()
    if cyclic:
        min_i = min(range(len(order)), key=lambda i: float(us[order[i]]))
        if min_i:
            order = order[min_i:] + order[:min_i]
    return order


def _add_poly_spline(curve, locs, radii, order, cyclic, gltf):
    spline = curve.splines.new('POLY')
    spline.points.add(len(order) - 1)
    spline.use_cyclic_u = bool(cyclic)
    for i, vertex_index in enumerate(order):
        co = locs[vertex_index]
        point = spline.points[i]
        point.co = (float(co[0]), float(co[1]), float(co[2]), 1.0)
        point.radius = max(_radius_gltf_to_blender(gltf, float(radii[vertex_index])), 0.0)


def _radius_gltf_to_blender(gltf, radius):
    return gltf.loc_gltf_to_blender([radius, 0.0, 0.0]).length
