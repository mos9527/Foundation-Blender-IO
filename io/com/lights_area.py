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

from ...io.com.gltf2_io import from_dict, from_union, from_none, from_float, from_str, from_list
from ...io.com.gltf2_io import to_float, to_class


class LightAreaRect:
    """light/rect (EXT_lights_area rectangle-specific properties)."""

    def __init__(self, aspect):
        self.aspect = aspect

    @staticmethod
    def from_dict(obj):
        if obj is None:
            return None
        assert isinstance(obj, dict)
        aspect = from_union([from_float, from_none], obj.get("aspect"))
        return LightAreaRect(aspect)

    def to_dict(self):
        result = {}
        if self.aspect is not None:
            result["aspect"] = to_float(self.aspect)
        return result


class LightArea:
    """EXT_lights_area area light (rectangle or disk)."""

    def __init__(self, color, intensity, type, size, rect, name, extensions, extras):
        self.color = color
        self.intensity = intensity
        self.type = type
        self.size = size
        self.rect = rect
        self.name = name
        self.extensions = extensions
        self.extras = extras

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        color = from_union([lambda x: from_list(from_float, x), from_none], obj.get("color"))
        intensity = from_union([from_float, from_none], obj.get("intensity"))
        type = from_str(obj.get("type"))
        size = from_union([from_float, from_none], obj.get("size"))
        rect = LightAreaRect.from_dict(obj.get("rect")) if obj.get("rect") is not None else None
        name = from_union([from_str, from_none], obj.get("name"))
        extensions = from_union(
            [lambda x: from_dict(lambda x: from_dict(lambda x: x, x), x), from_none],
            obj.get("extensions"),
        )
        extras = obj.get("extras")
        return LightArea(color, intensity, type, size, rect, name, extensions, extras)

    def to_dict(self):
        result = {}
        if self.color is not None:
            result["color"] = from_list(to_float, self.color)
        if self.intensity is not None:
            result["intensity"] = to_float(self.intensity)
        # `type` is required by the extension spec.
        result["type"] = from_str(self.type)
        if self.size is not None:
            result["size"] = to_float(self.size)
        # `rect` sub-object only makes sense for rect lights.
        if self.type == "rect" and self.rect is not None:
            rect_dict = to_class(LightAreaRect, self.rect)
            if rect_dict:
                result["rect"] = rect_dict
        if self.name is not None:
            result["name"] = from_str(self.name)
        if self.extensions is not None:
            result["extensions"] = from_dict(
                lambda x: from_dict(lambda x: x, x), self.extensions
            )
        if self.extras is not None:
            result["extras"] = self.extras
        return result
