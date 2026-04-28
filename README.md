Foundation-Blender-IO
===
glTF Asset IO for use with the [Foundation](https://github.com/mos9527/Foundation) rendering engine.

Extensions
---
Some extensions non-exsistent in the [offical implementation](https://github.com/KhronosGroup/glTF-Blender-IO) are implemented here for authoring scenes to be used by Foundation.

- `EXT_lights_area` (https://github.com/KhronosGroup/glTF/pull/2525)
- `EXT_materials_subsurface` (Foundation private extension; see [draft](EXT_materials_subsurface.md))

Installation
---
Download as ZIP then install via drag&drop.

This addon can co-exisit with the offical offering. It registers itself as
package `io_scene_foundation` and exposes operators `export_scene.gltf_foundation`
/ `import_scene.gltf_foundation`, plus a menu entry `glTF 2.0 (.glb/.gltf) (Foundation)`,
to avoid any clash with the official `io_scene_gltf2`.
