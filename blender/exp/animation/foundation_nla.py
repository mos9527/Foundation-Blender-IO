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

EXT_FOUNDATION_ANIMATION = "EXT_foundation_animation"

_DEBUG_PREFIX = "[EXT_foundation_animation]"


def _debug(msg):
    print("{} {}".format(_DEBUG_PREFIX, msg))


def gather_foundation_animation_tracks(gltf, export_settings):
    """Build EXT_foundation_animation.tracks[], purely as a read-only mirror of the NLA
    arrangement already authored in Blender (what the NLA editor shows with every exported
    object selected). This never changes how glTF animations[] themselves are baked; it only
    records how the strips referencing them are laid out, by matching each strip's action to
    an already-exported animation by name.

    That name match is only reliable in 'ACTIONS' animation mode, where each single-strip NLA
    track is already baked to its own animation named after the action. In other modes, baked
    animation names don't correspond 1:1 to actions, so the extension is omitted; the plain
    animations still export and play, just without NLA arrangement metadata.
    """
    _debug("gltf_animation_mode = {!r}".format(export_settings['gltf_animation_mode']))
    if export_settings['gltf_animation_mode'] != "ACTIONS":
        _debug("skipping: EXT_foundation_animation only supported with Animation Mode = 'Actions'")
        return None

    name_to_index = {}
    for idx, animation in enumerate(gltf.animations):
        name_to_index[animation.name] = idx
    _debug("exported glTF animations: {}".format(list(name_to_index.keys())))

    fps = bpy.context.scene.render.fps * bpy.context.scene.render.fps_base
    if fps <= 0.0:
        fps = 24.0

    vtree = export_settings['vtree']
    seen_tracks = set()
    tracks_json = []
    objects_with_nla = 0
    for obj_uuid in vtree.get_all_objects():
        blender_object = vtree.nodes[obj_uuid].blender_object
        if blender_object is None or blender_object.animation_data is None:
            continue
        nla_tracks = blender_object.animation_data.nla_tracks
        if len(nla_tracks) == 0:
            continue
        objects_with_nla += 1
        _debug("object '{}': {} NLA track(s)".format(blender_object.name, len(nla_tracks)))

        for track in nla_tracks:
            # Dedupe by (object, track) name, not id(track): each access to the nla_tracks
            # collection returns a fresh transient RNA wrapper, so id() can alias between
            # unrelated tracks once a prior wrapper is garbage-collected.
            track_key = (blender_object.name, track.name)
            if track_key in seen_tracks:
                continue
            seen_tracks.add(track_key)

            _debug("  track '{}': mute={}, {} strip(s)".format(track.name, track.mute, len(track.strips)))

            strips_json = []
            for strip in track.strips:
                action = getattr(strip, 'action', None)
                action_name = action.name if action is not None else None
                _debug("    strip '{}': type={}, mute={}, action={!r}".format(
                    strip.name, strip.type, strip.mute, action_name))

                if strip.mute:
                    _debug("    -> skipped (strip is muted)")
                    continue
                if action is None:
                    _debug("    -> skipped (strip has no action, e.g. sound/meta/transition strip)")
                    continue
                anim_index = name_to_index.get(action.name)
                if anim_index is None:
                    _debug("    -> skipped: action '{}' was not exported as its own glTF animation "
                           "(not baked individually in this configuration)".format(action.name))
                    export_settings['log'].warning(
                        "EXT_foundation_animation: strip '{}' on track '{}' references action '{}', which "
                        "was not exported as its own glTF animation; skipping.".format(
                            strip.name, track.name, action.name))
                    continue

                _debug("    -> matched glTF animation index {}".format(anim_index))
                strips_json.append({
                    "animation": anim_index,
                    "stripStart": strip.frame_start / fps,
                    "stripEnd": strip.frame_end / fps,
                    "clipStart": strip.action_frame_start / fps,
                    "clipEnd": strip.action_frame_end / fps,
                    "timeScale": 1.0 / strip.scale if strip.scale != 0.0 else 1.0,
                    "influence": strip.influence,
                    "cyclic": strip.repeat > 1.0,
                })

            if len(strips_json) == 0:
                _debug("  -> track '{}' has no exportable strips, omitting".format(track.name))
                continue

            tracks_json.append({
                "name": track.name,
                "mute": track.mute,
                "strips": strips_json,
            })

    if objects_with_nla == 0:
        _debug("no exported object has any NLA tracks; nothing to write")

    if len(tracks_json) == 0:
        _debug("result: no tracks written, omitting EXT_foundation_animation")
        return None

    _debug("result: writing {} track(s)".format(len(tracks_json)))
    return {"tracks": tracks_json}
