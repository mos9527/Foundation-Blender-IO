# Copyright 2018-2021 The glTF-Blender-IO authors.
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
import os
import shutil

from ...io.com import gltf2_io
from ...io.com.gltf2_io_extensions import Extension
from ...io.com.path import path_to_uri
from ...io.exp.user_extensions import export_user_extensions
from ..com.extras import generate_extras
from .cache import cached
from . import nodes as gltf2_blender_gather_nodes
from . import joints as gltf2_blender_gather_joints
from . import tree as gltf2_blender_gather_tree
from .animation.sampled.object.keyframes import get_cache_data
from .animation.animations import gather_animations

EXT_FOUNDATION_ENVIRONMENT = "EXT_foundation_environment"


def gather_gltf2(export_settings):
    """
    Gather glTF properties from the current state of blender.

    :return: list of scene graphs to be added to the glTF export
    """
    scenes = []
    animations = []  # unfortunately animations in gltf2 are just as 'root' as scenes.
    active_scene = None
    store_user_scene = bpy.context.scene
    if export_settings['gltf_collection'] == "" and export_settings['gltf_active_scene'] is False:
        # If no collection export and no active scene export, we need to export all scenes
        scenes_to_export = bpy.data.scenes
    elif export_settings['gltf_collection'] == "" and export_settings['gltf_active_scene'] is True:
        # If no collection export and active scene export, we need to export only the active scene
        scenes_to_export = [
            scene for scene in bpy.data.scenes if scene.name == store_user_scene.name]
    elif export_settings['gltf_collection'] != "":
        # If collection export, we need to export only the collection, so keeping only the active scene
        scenes_to_export = [
            scene for scene in bpy.data.scenes if scene.name == store_user_scene.name]
    else:
        # This should never happen
        raise Exception("Unknown export settings")

    for blender_scene in scenes_to_export:
        scenes.append(__gather_scene(blender_scene, export_settings))
        if export_settings['gltf_animations']:
            # resetting object cache
            get_cache_data.reset_cache()
            animations += gather_animations(export_settings)
        if bpy.context.scene.name == store_user_scene.name:
            active_scene = len(scenes) - 1

    # restore user scene
    bpy.context.window.scene = store_user_scene
    return active_scene, scenes, animations


@cached
def __gather_scene(blender_scene, export_settings):
    scene = gltf2_io.Scene(
        extensions=__gather_extensions(blender_scene, export_settings),
        extras=__gather_extras(blender_scene, export_settings),
        name=__gather_name(blender_scene, export_settings),
        nodes=[]
    )

    # Initialize some data needed for animation pointer
    export_settings['KHR_animation_pointer'] = {}
    export_settings['KHR_animation_pointer']['materials'] = {}
    export_settings['KHR_animation_pointer']['lights'] = {}
    export_settings['KHR_animation_pointer']['cameras'] = {}

    vtree = gltf2_blender_gather_tree.VExportTree(export_settings)
    vtree.construct(blender_scene)
    vtree.search_missing_armature()  # In case armature are no parented correctly
    if export_settings['gltf_armature_object_remove'] is True:
        vtree.check_if_we_can_remove_armature()  # Check if we can remove the armatures objects

    export_user_extensions('vtree_before_filter_hook', export_settings, vtree)

    # Now, we can filter tree if needed
    vtree.filter()

    if export_settings['gltf_flatten_bones_hierarchy'] is True:
        vtree.break_bone_hierarchy()

    vtree.bake_armature_bone_list()  # Used in case we remove the armature. Doing it after filter, as filter can remove some bones
    # And ater breaking bone hierarchy, as this changed the root list

    if export_settings['gltf_flatten_obj_hierarchy'] is True:
        vtree.break_obj_hierarchy()

    # Now we filtered the tree, in case of Collection Export,
    # We need to calculate the collection center,
    # In order to set the scene center to the collection center
    # Using object center barycenter for now (another option could be to use bounding box center)
    if export_settings['gltf_collection'] and export_settings['gltf_at_collection_center']:
        vtree.calculate_collection_center()

    vtree.variants_reset_to_original()

    export_user_extensions('vtree_after_filter_hook', export_settings, vtree)

    export_settings['vtree'] = vtree

    # If we don't remove armature object, we can't have bones directly at root of scene
    # So looping only on root nodes, as they are all nodes, not bones
    if export_settings['gltf_armature_object_remove'] is False:
        for r in [vtree.nodes[r] for r in vtree.roots]:
            node = gltf2_blender_gather_nodes.gather_node(
                r, export_settings)
            if node is not None:
                scene.nodes.append(node)
    else:
        # If we remove armature objects, we can have bone at root of scene
        armature_root_joints = {}
        for r in [vtree.nodes[r] for r in vtree.roots]:
            # Classic Object/node case
            if r.blender_type != gltf2_blender_gather_tree.VExportNode.BONE:
                node = gltf2_blender_gather_nodes.gather_node(
                    r, export_settings)
                if node is not None:
                    scene.nodes.append(node)
            else:
                # We can have bone are root of scene because we remove the armature object
                # and the armature was at root of scene
                node = gltf2_blender_gather_joints.gather_joint_vnode(
                    r.uuid, export_settings)
                if node is not None:
                    scene.nodes.append(node)
                    if r.armature not in armature_root_joints.keys():
                        armature_root_joints[r.armature] = []
                    armature_root_joints[r.armature].append(node)

        # Manage objects parented to bones, now we go through all root objects
        for k, v in armature_root_joints.items():
            gltf2_blender_gather_nodes.get_objects_parented_to_bones(k, v, export_settings)

    vtree.add_neutral_bones()

    export_user_extensions('gather_scene_hook', export_settings, scene, blender_scene)

    return scene


def __gather_extensions(blender_scene, export_settings):
    extension = __foundation_gather_environment(blender_scene, export_settings)
    if extension is None:
        return None
    return {EXT_FOUNDATION_ENVIRONMENT: Extension(EXT_FOUNDATION_ENVIRONMENT, extension, False)}


def __foundation_gather_environment(blender_scene, export_settings):
    world = blender_scene.world
    if world is None:
        return {
            "type": "color",
            "color": [1.0, 1.0, 1.0],
            "strength": 0.25,
        }

    if world.use_nodes and world.node_tree is not None:
        background = next((node for node in world.node_tree.nodes if node.bl_idname == "ShaderNodeBackground"), None)
        if background is not None:
            strength_socket = background.inputs.get("Strength")
            strength = strength_socket.default_value if strength_socket is not None else 1.0
            color_socket = background.inputs.get("Color")
            if color_socket is not None and color_socket.is_linked:
                link = color_socket.links[0]
                if link.from_node.bl_idname == "ShaderNodeTexEnvironment":
                    image = link.from_node.image
                    uri = __foundation_environment_image_uri(image, export_settings)
                    if uri is not None:
                        return {
                            "type": "hdri",
                            "uri": uri,
                            "projection": "longlat",
                            "strength": strength,
                        }

            if color_socket is not None:
                color = color_socket.default_value
                return {
                    "type": "color",
                    "color": [color[0], color[1], color[2]],
                    "strength": strength,
                }

    color = world.color
    return {
        "type": "color",
        "color": [color[0], color[1], color[2]],
        "strength": 1.0,
    }


def __foundation_environment_image_uri(image, export_settings):
    if image is None or image.filepath in {None, ""}:
        return None

    src_path = bpy.path.abspath(image.filepath, library=image.library)
    ext = os.path.splitext(src_path)[1].lower()
    if ext not in {".hdr", ".hdri"}:
        export_settings['log'].warning("Skipping unsupported world environment; Foundation editor supports only .hdr/.hdri")
        return None

    if not os.path.isfile(src_path):
        export_settings['log'].warning(
            "Skipping world environment HDRI; file not found on disk: %s" % src_path)
        return None

    # Resolve a stable filename for the copied HDR sidecar.
    filename = bpy.path.basename(image.filepath) or os.path.basename(src_path)
    if not filename:
        return None

    gltf_dir = export_settings['gltf_filedirectory']

    # Decide where to place the HDR file relative to the exported glTF/GLB.
    # If a separate texture directory is configured (and not GLB), put it there;
    # otherwise drop the HDR next to the glTF/GLB file.
    texture_dir = export_settings.get('gltf_texturedirectory')
    use_texture_subdir = (
        texture_dir is not None
        and export_settings.get('gltf_format') != 'GLB'
        and os.path.normpath(texture_dir) != os.path.normpath(gltf_dir)
    )
    dst_dir = texture_dir if use_texture_subdir else gltf_dir

    try:
        src_abs = os.path.abspath(src_path)
    except (OSError, ValueError):
        src_abs = src_path

    # If the source file already lives at the destination, just reference it.
    try:
        dst_path = os.path.join(dst_dir, filename)
        if not (os.path.exists(dst_path) and os.path.samefile(src_abs, dst_path)):
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copyfile(src_abs, dst_path)
    except OSError as e:
        export_settings['log'].warning(
            "Failed to copy world environment HDRI %s next to exported file: %s" % (src_abs, e))
        return None

    try:
        rel_path = os.path.relpath(dst_path, start=gltf_dir)
    except ValueError:
        return None
    return path_to_uri(rel_path)


def __gather_extras(blender_object, export_settings):
    if export_settings['gltf_extras']:
        # If case of collection export, use custom properties of the collection instead of the scene
        # So Collection custom properties are exported as glTF Scene extras
        if export_settings['gltf_collection']:
            return generate_extras(bpy.data.collections[export_settings['gltf_collection']])
        return generate_extras(blender_object)
    return None


def __gather_name(blender_scene, export_settings):
    if export_settings['gltf_collection']:
        return export_settings['gltf_collection']
    return blender_scene.name
