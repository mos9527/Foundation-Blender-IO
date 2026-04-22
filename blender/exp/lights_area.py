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
from typing import Optional, List, Dict, Any

from ...io.com import lights_area as gltf2_io_lights_area
from ..com.extras import generate_extras
from .cache import cached
from .lights import gather_lamp_color
from .material import search_node_tree


@cached
def gather_lights_area(blender_lamp, blender_lamp_world_matrix, export_settings) -> Optional[Dict[str, Any]]:
    """Gather EXT_lights_area definition for a Blender AREA lamp.

    Returns the light-as-dict that callers attach to the document-root
    extension array. Returns None for non-AREA lamps.
    """

    export_settings['current_paths'] = {}  # For KHR_animation_pointer

    if not __filter_lights_area(blender_lamp, export_settings):
        return None

    light_type, size, rect = __gather_shape(blender_lamp, export_settings)
    if light_type is None:
        return None

    light = gltf2_io_lights_area.LightArea(
        color=__gather_color(blender_lamp, export_settings),
        intensity=__gather_intensity(blender_lamp, export_settings),
        type=light_type,
        size=size,
        rect=rect,
        name=__gather_name(blender_lamp, export_settings),
        extensions=__gather_extensions(blender_lamp, export_settings),
        extras=__gather_extras(blender_lamp, export_settings),
    )

    return light.to_dict()


def __filter_lights_area(blender_lamp, _) -> bool:
    return blender_lamp.type == "AREA"


def __gather_color(blender_lamp, export_settings) -> Optional[List[float]]:
    return gather_lamp_color(
        blender_lamp,
        "/extensions/EXT_lights_area/lights/XXX/color",
        export_settings,
    )


def __gather_intensity(blender_lamp, export_settings) -> Optional[float]:
    """Pass-through of Blender's energy value (in Blender units).

    The EXT_lights_area spec defines `intensity` as surface luminance in nits
    (cd/m²). Blender Area lights store `energy` in watts (Cycles) or a
    viewport-tuned unit (EEVEE), which can't be converted to nits without
    knowing the render engine's exact normalization. Per addon design
    decision we write the raw Blender value (post emission/exposure) and
    leave normalization to the consumer. Downstream tooling that needs
    physically accurate nits should multiply/divide accordingly.
    """

    emission_strength = blender_lamp.energy

    path_ = {}
    path_['length'] = 1
    path_['path'] = "/extensions/EXT_lights_area/lights/XXX/intensity"
    path_['lamp_type'] = blender_lamp.type
    export_settings['current_paths']['energy'] = path_

    # Apply exposure, like the punctual path does. No nit/lumen conversion.
    return emission_strength * 2 ** blender_lamp.exposure


def __gather_shape(blender_lamp, export_settings):
    """Map Blender AreaLight shape to (type, size, rect).

    - SQUARE  -> ("rect", size,   LightAreaRect(aspect=1.0))
    - RECTANGLE -> ("rect", size_y, LightAreaRect(aspect=size_x/size_y))
    - DISK    -> ("disk", size,   None)
    - ELLIPSE -> ("rect", size_y, LightAreaRect(...)) with a warning
    """
    shape = getattr(blender_lamp, "shape", "SQUARE")

    if shape == "SQUARE":
        size = float(blender_lamp.size)
        if size <= 0.0:
            size = 1.0
        return "rect", size, gltf2_io_lights_area.LightAreaRect(aspect=1.0)

    if shape == "RECTANGLE":
        size_x = float(blender_lamp.size)
        size_y = float(blender_lamp.size_y)
        if size_y <= 0.0:
            size_y = 1.0
        aspect = size_x / size_y if size_y > 0.0 else 1.0
        return "rect", size_y, gltf2_io_lights_area.LightAreaRect(aspect=aspect)

    if shape == "DISK":
        size = float(blender_lamp.size)  # Blender semantics: diameter
        if size <= 0.0:
            size = 1.0
        return "disk", size, None

    if shape == "ELLIPSE":
        export_settings['log'].warning(
            "EXT_lights_area does not support elliptical lights; "
            "exporting '{}' as a rectangle (bounding-box approximation).".format(blender_lamp.name)
        )
        size_x = float(blender_lamp.size)
        size_y = float(blender_lamp.size_y)
        if size_y <= 0.0:
            size_y = 1.0
        aspect = size_x / size_y if size_y > 0.0 else 1.0
        return "rect", size_y, gltf2_io_lights_area.LightAreaRect(aspect=aspect)

    export_settings['log'].warning(
        "Unknown Blender area light shape '{}'; skipping.".format(shape)
    )
    return None, None, None


def __gather_name(blender_lamp, export_settings) -> Optional[str]:
    return blender_lamp.name


def __gather_extensions(blender_lamp, export_settings) -> Optional[dict]:
    return None


def __gather_extras(blender_lamp, export_settings) -> Optional[Any]:
    if export_settings['gltf_extras']:
        return generate_extras(blender_lamp)
    return None
