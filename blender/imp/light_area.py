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

from ...io.imp.user_extensions import import_user_extensions
from ..com.extras import set_extras


class BlenderLightArea:
    """Blender-side importer for EXT_lights_area."""

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, vnode, light_id):
        """Create a Blender AREA lamp from an EXT_lights_area light definition."""
        pylight = gltf.data.extensions['EXT_lights_area']['lights'][light_id]

        import_user_extensions('gather_import_light_before_hook', gltf, vnode, pylight)

        light_type = pylight.get('type', 'rect')
        name = pylight.get('name')
        if not name:
            name = "AreaRect" if light_type == "rect" else "AreaDisk"
            pylight['name'] = name

        light = bpy.data.lights.new(name=name, type='AREA')

        # Shape and size
        size = float(pylight.get('size', 1.0))
        if light_type == "disk":
            light.shape = 'DISK'
            light.size = size
        else:  # "rect" (default)
            rect = pylight.get('rect') or {}
            aspect = float(rect.get('aspect', 1.0))
            if abs(aspect - 1.0) < 1e-6:
                light.shape = 'SQUARE'
                light.size = size
            else:
                light.shape = 'RECTANGLE'
                # Spec: width = size * aspect (X), height = size (Y).
                # Blender: size = X, size_y = Y.
                light.size_y = size
                light.size = size * aspect

        # Color
        if 'color' in pylight:
            light.color = pylight['color']

        # Intensity — pass-through (see export side for the inverse decision).
        if 'intensity' in pylight:
            light.energy = float(pylight['intensity'])

        set_extras(light, pylight.get('extras'))

        # Needed in case of KHR_animation_pointer
        pylight['blender_object_data'] = light

        return light
