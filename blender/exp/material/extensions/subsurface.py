# Copyright 2018-2022 The glTF-Blender-IO authors.
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
from .....io.com.gltf2_io_extensions import Extension
from ..search_node_tree import get_socket


def _get_first_socket(node_tree, names):
    for name in names:
        socket = get_socket(node_tree, name)
        if socket.socket is not None:
            return socket
    return None


def _get_unlinked_value(socket):
    if socket is None or socket.socket is None:
        return None
    if not isinstance(socket.socket, bpy.types.NodeSocket) or socket.socket.is_linked:
        return None
    return socket.socket.default_value


def _socket_path(socket):
    return "node_tree." + socket.socket.path_from_id() + ".default_value"


def _get_subsurface_method(bmat):
    material = bmat.get_used_material()
    node_tree = material.node_tree
    method = getattr(material, "subsurface_method", None)

    if node_tree:
        nodes = [node for node in node_tree.nodes if isinstance(node, bpy.types.ShaderNodeBsdfPrincipled)]
        for node in nodes:
            method = getattr(node, "subsurface_method", method)

    if method is None:
        return "christensenBurley"

    normalized = str(method).lower().replace("_", "")
    if normalized in {"christensenburley", "burley"}:
        return "christensenBurley"
    if normalized == "randomwalk":
        return "randomWalk"
    if normalized == "randomwalkskin":
        return "randomWalkSkin"
    return str(method)


def export_subsurface(bmat, export_settings):
    node_tree = bmat.get_used_material().node_tree
    if node_tree is None:
        return None, {}, {}

    weight_socket = _get_first_socket(node_tree, ("Subsurface Weight", "Subsurface"))
    radius_socket = _get_first_socket(node_tree, ("Subsurface Radius",))
    scale_socket = _get_first_socket(node_tree, ("Subsurface Scale",))

    weight = _get_unlinked_value(weight_socket)
    if weight is None or weight == 0.0:
        return None, {}, {}

    subsurface_extension = {
        "subsurfaceMethod": _get_subsurface_method(bmat),
        "subsurfaceWeight": weight,
    }

    path_ = {}
    path_["length"] = 1
    path_["path"] = "/materials/XXX/extensions/EXT_materials_subsurface/subsurfaceWeight"
    export_settings["current_paths"][_socket_path(weight_socket)] = path_

    radius = _get_unlinked_value(radius_socket)
    if radius is not None:
        subsurface_extension["subsurfaceRadius"] = list(radius[:3])

        path_ = {}
        path_["length"] = 3
        path_["path"] = "/materials/XXX/extensions/EXT_materials_subsurface/subsurfaceRadius"
        export_settings["current_paths"][_socket_path(radius_socket)] = path_

    scale = _get_unlinked_value(scale_socket)
    if scale is not None:
        subsurface_extension["subsurfaceScale"] = scale

        path_ = {}
        path_["length"] = 1
        path_["path"] = "/materials/XXX/extensions/EXT_materials_subsurface/subsurfaceScale"
        export_settings["current_paths"][_socket_path(scale_socket)] = path_

    return Extension("EXT_materials_subsurface", subsurface_extension, False), {}, {}
