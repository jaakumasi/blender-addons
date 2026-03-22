# Animation, Keyframes & Drivers

## Inserting Keyframes

```python
import bpy

obj = bpy.context.active_object

# Keyframe a single property at current frame
obj.location = (1.0, 2.0, 3.0)
obj.keyframe_insert(data_path="location", frame=1)

# Keyframe at specific frame
obj.location = (5.0, 2.0, 3.0)
obj.keyframe_insert(data_path="location", frame=60)

# Keyframe individual axis (index)
obj.keyframe_insert(data_path="location", index=0, frame=1)  # X only
obj.keyframe_insert(data_path="location", index=1, frame=1)  # Y only
obj.keyframe_insert(data_path="location", index=2, frame=1)  # Z only

# Keyframe rotation
obj.rotation_euler = (0, 0, 3.14159)
obj.keyframe_insert(data_path="rotation_euler", frame=30)

# Keyframe scale
obj.scale = (2.0, 2.0, 2.0)
obj.keyframe_insert(data_path="scale", frame=30)

# Keyframe custom properties
obj["my_value"] = 5.0
obj.keyframe_insert(data_path='["my_value"]', frame=1)
obj["my_value"] = 10.0
obj.keyframe_insert(data_path='["my_value"]', frame=60)

# Keyframe material values
mat = obj.active_material
if mat and mat.use_nodes:
    principled = mat.node_tree.nodes.get("Principled BSDF")
    if principled:
        principled.inputs['Alpha'].default_value = 1.0
        principled.inputs['Alpha'].keyframe_insert(data_path="default_value", frame=1)
        principled.inputs['Alpha'].default_value = 0.0
        principled.inputs['Alpha'].keyframe_insert(data_path="default_value", frame=60)
```

## Deleting Keyframes

```python
obj.keyframe_delete(data_path="location", frame=30)
obj.keyframe_delete(data_path="location", index=0, frame=30)  # X only

# Clear all animation from object
obj.animation_data_clear()
```

## Working with Actions

Actions are reusable animation clips stored as data blocks.

```python
# Get or create animation data
if not obj.animation_data:
    obj.animation_data_create()

# Get current action
action = obj.animation_data.action
print(f"Action: {action.name if action else 'None'}")

# Create new action
action = bpy.data.actions.new(name="MyAction")
obj.animation_data.action = action

# List all actions
for action in bpy.data.actions:
    print(f"Action: {action.name}, fcurves: {len(action.fcurves)}")

# Duplicate action (make single-user)
new_action = action.copy()
new_action.name = "MyAction.copy"
obj.animation_data.action = new_action
```

## F-Curves

F-Curves define the animation curves for individual properties.

```python
action = obj.animation_data.action

# Iterate all fcurves
for fcurve in action.fcurves:
    print(f"  data_path: {fcurve.data_path}, index: {fcurve.array_index}")
    print(f"  keyframes: {len(fcurve.keyframe_points)}")

# Find specific fcurve
fcurve = action.fcurves.find("location", index=0)  # X location

# Read keyframe data
if fcurve:
    for kp in fcurve.keyframe_points:
        print(f"  frame={kp.co[0]}, value={kp.co[1]}, interp={kp.interpolation}")

# Create fcurve and add keyframes programmatically
fcurve = action.fcurves.new(data_path="location", index=2)  # Z location
fcurve.keyframe_points.add(count=3)
fcurve.keyframe_points[0].co = (1.0, 0.0)
fcurve.keyframe_points[1].co = (30.0, 5.0)
fcurve.keyframe_points[2].co = (60.0, 0.0)

# Set interpolation for all keyframes
for kp in fcurve.keyframe_points:
    kp.interpolation = 'BEZIER'  # 'CONSTANT', 'LINEAR', 'BEZIER'

# Update fcurve (recalculate handles)
fcurve.update()
```

## Keyframe Interpolation Types

```python
# Per-keyframe interpolation
kp.interpolation = 'CONSTANT'  # Stepped / hold
kp.interpolation = 'LINEAR'    # Straight line
kp.interpolation = 'BEZIER'    # Smooth curve (default)

# Bezier handle types
kp.handle_left_type = 'AUTO'        # Automatic
kp.handle_left_type = 'AUTO_CLAMPED' # Auto, clamped to not overshoot
kp.handle_left_type = 'VECTOR'      # Straight toward next key
kp.handle_left_type = 'ALIGNED'     # Aligned handles
kp.handle_left_type = 'FREE'        # Independent handles

# Easing (for non-Bezier)
kp.easing = 'AUTO'        # Automatic
kp.easing = 'EASE_IN'     # Accelerate
kp.easing = 'EASE_OUT'    # Decelerate
kp.easing = 'EASE_IN_OUT' # Both
```

## Drivers

Drivers link one property's value to an expression or another property.

```python
# Add a driver to a property
# Returns the driver fcurve
driver_fcurve = obj.driver_add("location", 2)  # Z location
driver = driver_fcurve.driver

# Simple expression driver
driver.type = 'SCRIPTED'
driver.expression = "frame * 0.1"  # Move up over time

# Driver with variables
driver.expression = "var * 2.0"
var = driver.variables.new()
var.name = "var"
var.type = 'TRANSFORMS'  # 'SINGLE_PROP', 'TRANSFORMS', 'ROTATION_DIFF', 'LOC_DIFF'
var.targets[0].id = bpy.data.objects["Empty"]
var.targets[0].transform_type = 'LOC_X'
var.targets[0].transform_space = 'WORLD_SPACE'

# Single property driver variable
var = driver.variables.new()
var.name = "slider"
var.type = 'SINGLE_PROP'
var.targets[0].id_type = 'SCENE'
var.targets[0].id = bpy.context.scene
var.targets[0].data_path = 'my_custom_prop'

# Remove a driver
obj.driver_remove("location", 2)

# Remove all drivers from property
obj.driver_remove("location")
```

## NLA (Non-Linear Animation)

NLA allows stacking, blending, and sequencing multiple actions.

```python
# Access NLA tracks
if obj.animation_data:
    nla_tracks = obj.animation_data.nla_tracks

    # Create NLA track
    track = nla_tracks.new()
    track.name = "MyTrack"

    # Add action strip to track
    action = bpy.data.actions["MyAction"]
    strip = track.strips.new("MyStrip", start=1, action=action)

    # Configure strip
    strip.frame_start = 1
    strip.frame_end = 60
    strip.repeat = 2.0           # Repeat the action
    strip.scale = 1.0            # Time scale
    strip.blend_type = 'REPLACE'  # 'REPLACE', 'COMBINE', 'ADD', 'SUBTRACT', 'MULTIPLY'
    strip.influence = 1.0         # Blend influence (0-1)
    strip.mute = False

    # Stash current action as NLA strip (common workflow)
    track = nla_tracks.new()
    track.strips.new(action.name, start=1, action=action)
    obj.animation_data.action = None  # Clear active action
```

## Scene Timeline

```python
scene = bpy.context.scene

# Frame range
scene.frame_start = 1
scene.frame_end = 250
scene.frame_current = 1

# FPS
scene.render.fps = 24
scene.render.fps_base = 1.0  # Actual FPS = fps / fps_base

# Set current frame (triggers depsgraph update)
scene.frame_set(30)

# Step through frames
for frame in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(frame)
    # Read animated values at this frame
    loc = obj.matrix_world.translation.copy()
```

## Frame Change Handlers

```python
@bpy.app.handlers.persistent
def on_frame_change(scene, depsgraph):
    """Called every time the frame changes."""
    frame = scene.frame_current
    for obj in scene.objects:
        if obj.get("auto_rotate"):
            obj.rotation_euler.z = frame * 0.05

bpy.app.handlers.frame_change_post.append(on_frame_change)

# Remove handler
# bpy.app.handlers.frame_change_post.remove(on_frame_change)
```

## Shape Keys (Blend Shapes)

```python
obj = bpy.context.active_object
mesh = obj.data

# Create basis shape key (required first)
if not mesh.shape_keys:
    obj.shape_key_add(name="Basis", from_mix=False)

# Add shape key
sk = obj.shape_key_add(name="Smile", from_mix=False)

# Modify shape key vertices
for i, vert in enumerate(sk.data):
    vert.co.z += 0.1  # Move all verts up in this shape

# Animate shape key value
sk.value = 0.0
sk.keyframe_insert(data_path="value", frame=1)
sk.value = 1.0
sk.keyframe_insert(data_path="value", frame=30)

# Access shape keys
shape_keys = mesh.shape_keys
for key_block in shape_keys.key_blocks:
    print(f"{key_block.name}: value={key_block.value}")
```
