# Blender Python API Core Patterns

## Module Overview

| Module | Purpose |
|--------|---------|
| `bpy.data` | Access all data blocks (objects, meshes, materials, etc.) |
| `bpy.context` | Current state (active object, selected objects, mode, etc.) |
| `bpy.ops` | Call operators (user-facing actions) |
| `bpy.types` | Class definitions for extending Blender |
| `bpy.props` | Property definitions for addon settings |
| `bpy.utils` | Utility functions (registration, paths, etc.) |
| `bpy.app` | Application info (version, paths, handlers) |
| `bpy.msgbus` | Message bus for property change notifications |

## bpy.context — Current State

```python
# Active object (the one with the orange outline)
obj = bpy.context.active_object
# or equivalently:
obj = bpy.context.object

# All selected objects
selected = bpy.context.selected_objects

# Current scene
scene = bpy.context.scene

# Current view layer
view_layer = bpy.context.view_layer

# Current mode ('OBJECT', 'EDIT', 'SCULPT', 'PAINT_WEIGHT', etc.)
mode = bpy.context.mode

# Current area type
area_type = bpy.context.area.type  # 'VIEW_3D', 'PROPERTIES', etc.

# Preferences
prefs = bpy.context.preferences
addon_prefs = prefs.addons["my_addon"].preferences
```

## bpy.data — Data Access

```python
# All objects in the file
for obj in bpy.data.objects:
    print(obj.name, obj.type)

# Get by name
obj = bpy.data.objects["Cube"]
mat = bpy.data.materials["Material"]
mesh = bpy.data.meshes["Cube"]

# Check existence
if "Cube" in bpy.data.objects:
    obj = bpy.data.objects["Cube"]

# Create new data blocks
mesh = bpy.data.meshes.new("MyMesh")
material = bpy.data.materials.new("MyMaterial")
collection = bpy.data.collections.new("MyCollection")

# Remove data blocks
bpy.data.objects.remove(obj)
bpy.data.meshes.remove(mesh)

# Link object to scene
bpy.context.collection.objects.link(obj)
# or to a specific collection:
collection.objects.link(obj)
```

## bpy.ops — Operator Calls

```python
# Basic operator call
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.object.delete()
bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 1))

# With context override (run in specific context)
# Blender 4.0+ uses context.temp_override():
with bpy.context.temp_override(area=area, region=region):
    bpy.ops.view3d.camera_to_view()

# Check if operator can run
if bpy.ops.object.delete.poll():
    bpy.ops.object.delete()
```

**Important**: Prefer direct data manipulation over `bpy.ops` when possible. Operators have context requirements and are slower.

## Common Object Operations

```python
# Create mesh object from scratch
import bmesh

mesh = bpy.data.meshes.new("MyMesh")
obj = bpy.data.objects.new("MyObject", mesh)
bpy.context.collection.objects.link(obj)

# Build mesh with bmesh
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
bm.to_mesh(mesh)
bm.free()

# Modify object transform
obj.location = (1.0, 2.0, 3.0)
obj.rotation_euler = (0, 0, 3.14159)
obj.scale = (2.0, 2.0, 2.0)

# Parent objects
child.parent = parent_obj

# Apply modifier
bpy.context.view_layer.objects.active = obj
bpy.ops.object.modifier_apply(modifier="MyModifier")

# Set active and selected
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
```

## bpy.app — Application Info

```python
# Blender version
bpy.app.version          # (5, 0, 0)
bpy.app.version_string   # "5.0.0"

# File path
bpy.data.filepath         # Current .blend file path (empty if unsaved)

# Handlers (run code on events)
def on_frame_change(scene):
    print(f"Frame: {scene.frame_current}")

bpy.app.handlers.frame_change_post.append(on_frame_change)

# Available handlers:
# frame_change_pre, frame_change_post
# render_pre, render_post, render_complete, render_cancel
# load_pre, load_post
# save_pre, save_post
# depsgraph_update_pre, depsgraph_update_post
# undo_pre, undo_post
```

## bpy.utils — Utilities

```python
# Register/unregister classes
bpy.utils.register_class(MyOperator)
bpy.utils.unregister_class(MyOperator)

# Addon paths
bpy.utils.user_resource('SCRIPTS', path="addons")  # User addons dir
bpy.utils.resource_path('LOCAL')                     # Blender install dir

# Preview collections (for custom icons)
import bpy.utils.previews
pcoll = bpy.utils.previews.new()
pcoll.load("my_icon", "/path/to/icon.png", 'IMAGE')
icon_id = pcoll["my_icon"].icon_id
# Don't forget to remove in unregister:
bpy.utils.previews.remove(pcoll)
```

## Timer / Deferred Execution

```python
# Run function after delay
def delayed_action():
    print("Executed after 1 second")
    return None  # Return None to stop, or float for next interval

bpy.app.timers.register(delayed_action, first_interval=1.0)

# Unregister
bpy.app.timers.unregister(delayed_action)
```

## Dependency Graph

```python
# Get evaluated (with modifiers applied) object
depsgraph = bpy.context.evaluated_depsgraph_get()
obj_eval = obj.evaluated_get(depsgraph)
mesh_eval = obj_eval.to_mesh()

# Clean up
obj_eval.to_mesh_clear()
```

## Math Utilities

```python
from mathutils import Vector, Matrix, Euler, Quaternion

v = Vector((1, 0, 0))
v_rotated = Matrix.Rotation(1.5708, 4, 'Z') @ v

# World space to local space
local_pos = obj.matrix_world.inverted() @ world_pos
```
