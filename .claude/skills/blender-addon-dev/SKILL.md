---
name: blender-addon-dev
description: >
  Use this skill when developing Blender add-ons (extensions). Triggers when user asks to
  create, modify, debug, or package a Blender addon/extension, or asks about Blender's
  Python API (bpy), operators, panels, properties, menus, or preferences. Targets Blender 5.0
  with Python 3.11.
version: 1.0.0
---

# Blender Add-on Development Guide

## Target Environment

- **Blender**: 5.0
- **Bundled Python**: 3.11.13 (addon code runs inside this, NOT the system Python)
- **Blender path**: `C:\Program Files\Blender Foundation\Blender 5.0\`
- **User addons**: `%APPDATA%\Blender Foundation\Blender\5.0\scripts\addons\`
- **Extensions**: `%APPDATA%\Blender Foundation\Blender\5.0\extensions\`
- **Blender templates** (read for patterns): `C:\Program Files\Blender Foundation\Blender 5.0\5.0\scripts\templates_py\`
- **Core addons** (read for patterns): `C:\Program Files\Blender Foundation\Blender 5.0\5.0\scripts\addons_core\`
- **API docs**: https://docs.blender.org/api/5.0/

## Critical Rules

### 1. Python version constraint
Target Python 3.11 only. Do NOT use Python 3.12+ features like:
- `type` keyword for type aliases
- Exception groups with `except*`
- `tomllib` (use `tomli` backport if needed)
- f-string improvements from 3.12

### 2. Class naming convention (bl_idname)
Blender enforces strict naming for `bl_idname`:
```
CATEGORY_OT_name    # Operators
CATEGORY_PT_name    # Panels
CATEGORY_MT_name    # Menus
CATEGORY_HT_name    # Headers
CATEGORY_UL_name    # UILists
```
Common categories: `OBJECT`, `VIEW3D`, `SCENE`, `RENDER`, `MATERIAL`, `NODE`, `MESH`, `CURVE`

See @references/naming-conventions.md for full details.

### 3. Property annotation syntax (CRITICAL)
Properties MUST use **annotation** syntax (colon `:`) NOT assignment (`=`):
```python
# CORRECT
my_prop: bpy.props.FloatProperty(name="Value", default=1.0)

# WRONG - will fail silently or raise error
my_prop = bpy.props.FloatProperty(name="Value", default=1.0)
```

### 4. Operator return values
Operators must return a **set** (not a dict or string):
- `{'FINISHED'}` - operation completed
- `{'CANCELLED'}` - operation cancelled
- `{'RUNNING_MODAL'}` - modal operation started/continuing
- `{'PASS_THROUGH'}` - pass event to other handlers

### 5. Registration order
Always unregister in **reverse order** of registration. For multi-file addons, each module should have its own `register()`/`unregister()`.

### 6. Extension manifest (Blender 4.2+)
New addons should use `blender_manifest.toml` instead of legacy `bl_info` dict.
See @references/extension-manifest.md for the full format.

## Addon Structure

### Single-file addon
For simple addons, one `.py` file with everything:
```
my_addon.py          # bl_info + operators + panels + register/unregister
blender_manifest.toml  # extension manifest
```
See @examples/single_file_addon.py

### Multi-file addon (package)
For complex addons:
```
my_addon/
  __init__.py           # bl_info, imports, register(), unregister()
  operators.py          # Operator classes
  panels.py             # Panel/UI classes
  preferences.py        # AddonPreferences class
  properties.py         # PropertyGroup classes
  utils.py              # Shared utilities
  blender_manifest.toml # Extension manifest
```
See @examples/multi_file_addon/

## Common Patterns

### Adding operators to menus
```python
def menu_func(self, context):
    self.layout.operator(MyOperator.bl_idname, text="My Action", icon='PLUGIN')

def register():
    bpy.utils.register_class(MyOperator)
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)

def unregister():
    bpy.utils.unregister_class(MyOperator)
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
```

Common menus — see @references/common-menus.md

### Scene-level custom properties
```python
def register():
    bpy.types.Scene.my_tool_settings = bpy.props.PointerProperty(type=MyPropertyGroup)

def unregister():
    del bpy.types.Scene.my_tool_settings
```

### Operator poll method
```python
@classmethod
def poll(cls, context):
    return context.active_object is not None and context.active_object.type == 'MESH'
```

### Property types
See @references/property-types.md for all `bpy.props` types with full parameter reference.

### Layout API
See @references/ui-layout.md for `layout.row()`, `layout.column()`, `layout.split()`, `layout.box()`, etc.

### API patterns
See @references/api-patterns.md for `bpy.data`, `bpy.context`, `bpy.ops`, `bpy.types`, `bpy.utils` usage.

## Testing & Debugging

### Run addon headlessly (no GUI)
```bash
"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" -b --python-exit-code 1 --python test_script.py
```

### Enable addon and run test
```bash
"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" -b --addons my_addon --python test_script.py
```

### Symlink for live development
Create a symlink from your dev directory to Blender's addon folder so changes are picked up without copying:
```bash
# Run as administrator
mklink /D "%APPDATA%\Blender Foundation\Blender\5.0\scripts\addons\my_addon" "C:\path\to\your\dev\my_addon"
```

See @references/testing-and-debugging.md for full workflow.

## Version Management

When a new Blender major version (e.g. 6.0) ships with API changes:
1. Create a version branch in your addon repo (e.g. `blender-5x`, `blender-6x`)
2. Update `blender_version_min` / `blender_version_max` in `blender_manifest.toml`
3. Package each version separately as a `.zip` for distribution
4. The skill itself should be updated with new API patterns

See @references/version-management.md for details.

## Registration Reference
See @references/registration.md for single-file, multi-file, AddonPreferences, and keymap registration patterns.

## Domain-Specific References

### Materials & Shader Nodes
See @references/materials-and-shaders.md for creating materials, shader node trees, linking nodes,
loading textures, PBR setup, world/HDRI configuration, and the full shader node type table.

### Animation & Keyframes
See @references/animation-keyframes.md for keyframe insertion, F-Curves, Actions, NLA tracks,
drivers, shape keys, frame change handlers, and timeline control.

### Mesh & BMesh
See @references/mesh-bmesh.md for procedural mesh creation, vertex/edge/face manipulation,
bmesh operators, UV maps, vertex colors, vertex groups, modifiers, and `from_pydata`.

### Geometry Nodes
See @references/geometry-nodes.md for creating geometry node groups, adding nodes programmatically,
group inputs (modifier parameters), instancing, and the full geometry node type table.

### Camera & Render Settings
See @references/camera-render.md for camera creation, lens configuration, depth of field,
render resolution, Cycles/EEVEE settings, render engine selection, and multi-camera setups.

### Armatures & Rigging
See @references/armatures-rigging.md for armature/bone creation, pose mode, bone constraints (IK, copy rotation,
limits), weight painting, bone collections, and skeleton building patterns.

### Custom Node Trees
See @references/custom-node-trees.md for defining custom node tree types, custom sockets,
custom nodes, node categories, tree evaluation, and dynamic sockets.

### Particles & Physics
See @references/particles-physics.md for particle systems (emitter/hair), force fields,
rigid body physics, cloth simulation, soft body, fluid simulation, and baking.
