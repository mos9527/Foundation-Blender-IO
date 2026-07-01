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
import tempfile

from .node import BlenderNode
from .animation import BlenderAnimation
from .vnode import VNode, compute_vnodes
from ..com.extras import set_extras
from ...io.com.path import uri_to_path
from ...io.imp.user_extensions import import_user_extensions

EXT_FOUNDATION_ENVIRONMENT = "EXT_foundation_environment"


def _foundation_environment_buffer_view_bytes(gltf, buffer_view_index):
    if buffer_view_index is None:
        return None
    if buffer_view_index < 0 or buffer_view_index >= len(gltf.data.buffer_views):
        gltf.log.warning("Skipping Foundation environment image with invalid bufferView: %s" % buffer_view_index)
        return None

    view = gltf.data.buffer_views[buffer_view_index]
    buffer_data = gltf.buffers[view.buffer]
    offset = view.byte_offset or 0
    end = offset + view.byte_length
    return bytes(buffer_data[offset:end])


def _foundation_apply_environment(gltf, pyscene, scene):
    if pyscene.extensions is None or EXT_FOUNDATION_ENVIRONMENT not in pyscene.extensions:
        return

    extension = pyscene.extensions[EXT_FOUNDATION_ENVIRONMENT]
    env_type = extension.get("type")
    strength = extension.get("strength", 1.0)

    world = scene.world
    if world is None:
        world = bpy.data.worlds.new(scene.name + " World")
        scene.world = world
    world.use_nodes = True

    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputWorld")
    background = nodes.new("ShaderNodeBackground")
    links.new(background.outputs["Background"], output.inputs["Surface"])
    background.inputs["Strength"].default_value = strength

    if env_type == "color":
        color = extension.get("color", [1.0, 1.0, 1.0])
        background.inputs["Color"].default_value = (color[0], color[1], color[2], 1.0)
        return

    if env_type in {"hdri", "envMap"}:
        uri = extension.get("uri")
        buffer_view = extension.get("bufferView")
        temp_path = None
        if buffer_view is not None:
            data = _foundation_environment_buffer_view_bytes(gltf, buffer_view)
            if data is None:
                return
            with tempfile.NamedTemporaryFile(delete=False, suffix=".hdr") as f:
                f.write(data)
                temp_path = f.name
            path = temp_path
        elif uri is not None:
            path = os.path.abspath(os.path.join(os.path.dirname(gltf.filename), uri_to_path(uri)))
        else:
            return
        ext = os.path.splitext(path)[1].lower()
        if ext not in {".hdr", ".hdri"}:
            gltf.log.warning("Skipping unsupported Foundation environment image: %s" % path)
            return

        env = nodes.new("ShaderNodeTexEnvironment")
        try:
            env.image = bpy.data.images.load(path, check_existing=True)
            if temp_path is not None:
                env.image.name = "Foundation Environment"
                env.image.pack()
        except RuntimeError:
            gltf.log.error("Missing Foundation environment image: %s" % path)
            return
        finally:
            if temp_path is not None:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
        links.new(env.outputs["Color"], background.inputs["Color"])


class BlenderScene():
    """Blender Scene."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf):
        """Scene creation."""
        scene = bpy.context.scene
        gltf.blender_scene = scene.name
        if bpy.context.collection.name in bpy.data.collections:  # avoid master collection
            gltf.blender_active_collection = bpy.context.collection.name

        if gltf.data.scene is not None:
            import_user_extensions('gather_import_scene_before_hook', gltf, gltf.data.scenes[gltf.data.scene], scene)
            pyscene = gltf.data.scenes[gltf.data.scene]
            # Special case for scene extras:
            # As the scene may already exists in Blender, custom properties can be overwritten
            # So, there is an option to know if the user want to set extras or not
            if gltf.import_settings['import_scene_extras']:
                set_extras(scene, pyscene.extras)
            _foundation_apply_environment(gltf, pyscene, scene)

        compute_vnodes(gltf)

        gltf.display_current_node = 0  # for debugging
        BlenderNode.create_vnode(gltf, 'root')

        # User extensions before scene creation
        gltf_scene = None
        if gltf.data.scene is not None:
            gltf_scene = gltf.data.scenes[gltf.data.scene]
        import_user_extensions('gather_import_scene_after_nodes_hook', gltf, gltf_scene, scene)

        BlenderScene.create_animations(gltf)

        # User extensions after scene creation
        gltf_scene = None
        if gltf.data.scene is not None:
            gltf_scene = gltf.data.scenes[gltf.data.scene]
        import_user_extensions('gather_import_scene_after_animation_hook', gltf, gltf_scene, scene)

        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        if gltf.import_settings['import_select_created_objects'] and gltf.import_settings['import_scene_as_collection'] is True:
            BlenderScene.select_imported_objects(gltf)
            BlenderScene.set_active_object(gltf)

        # Exclude not default scene(s) collection(s), if we are in collection
        if gltf.import_settings['import_scene_as_collection'] is True:
            if gltf.data.scene is not None:
                for scene_idx, coll in gltf.blender_collections.items():
                    if scene_idx != gltf.data.scene:
                        bpy.context.layer_collection.children[coll.name].exclude = True

    @staticmethod
    def create_animations(gltf):
        """Create animations."""

        # Use a class here, to be able to pass data by reference to hook (to be able to change them inside hook)
        class IMPORT_animation_options:
            def __init__(self, restore_first_anim: bool = True):
                self.restore_first_anim = restore_first_anim

        animation_options = IMPORT_animation_options()
        import_user_extensions('gather_import_animations', gltf, gltf.data.animations, animation_options)

        if gltf.data.animations:
            # NLA tracks are added bottom to top, so create animations in
            # reverse so the first winds up on top
            for anim_idx in reversed(range(len(gltf.data.animations))):
                BlenderAnimation.anim(gltf, anim_idx)

            # Restore first animation
            if animation_options.restore_first_anim:
                anim_name = gltf.data.animations[0].track_name
                BlenderAnimation.restore_animation(gltf, anim_name)

                if hasattr(bpy.data.scenes[0], "gltf2_animation_applied"):
                    bpy.data.scenes[0].gltf2_animation_applied = bpy.data.scenes[0].gltf2_animation_tracks.find(
                        gltf.data.animations[0].track_name)

    @staticmethod
    def select_imported_objects(gltf):
        """Select all (and only) the imported objects."""
        if bpy.ops.object.select_all.poll():
            bpy.ops.object.select_all(action='DESELECT')

        for vnode in gltf.vnodes.values():
            if vnode.type == VNode.Object:
                vnode.blender_object.select_set(state=True)

    @staticmethod
    def set_active_object(gltf):
        """Make the first root object from the default glTF scene active.
        If no default scene, use the first scene, or just any root object.
        """
        vnode = None

        if gltf.data.scene is not None:
            pyscene = gltf.data.scenes[gltf.data.scene]
            if pyscene.nodes:
                vnode = gltf.vnodes[pyscene.nodes[0]]

        if not vnode:
            for pyscene in gltf.data.scenes or []:
                if pyscene.nodes:
                    vnode = gltf.vnodes[pyscene.nodes[0]]
                    break

        if not vnode:
            vnode = gltf.vnodes['root']
            if vnode.type == VNode.DummyRoot:
                if not vnode.children:
                    return  # no nodes
                vnode = gltf.vnodes[vnode.children[0]]

        if vnode.type == VNode.Bone:
            vnode = gltf.vnodes[vnode.bone_arma]

        bpy.context.view_layer.objects.active = vnode.blender_object
