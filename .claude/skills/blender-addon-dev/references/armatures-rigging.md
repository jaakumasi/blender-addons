# Armatures & Rigging

## Creating an Armature

```python
import bpy
from mathutils import Vector, Matrix
import math

# Create armature data and object
armature_data = bpy.data.armatures.new("MyArmature")
armature_obj = bpy.data.objects.new("MyArmature", armature_data)
bpy.context.collection.objects.link(armature_obj)

# Must be in edit mode to add bones
bpy.context.view_layer.objects.active = armature_obj
bpy.ops.object.mode_set(mode='EDIT')

edit_bones = armature_data.edit_bones
```

## Adding Bones

```python
# Bones must be created in EDIT mode

# Create a bone
bone = edit_bones.new("Root")
bone.head = (0, 0, 0)       # Base position
bone.tail = (0, 0, 1)       # Tip position (determines bone length and direction)

# Create child bone (connected)
bone_upper = edit_bones.new("Upper")
bone_upper.head = (0, 0, 1)
bone_upper.tail = (0, 0, 2)
bone_upper.parent = bone
bone_upper.use_connect = True  # Connected to parent's tail

# Create child bone (not connected — offset from parent)
bone_side = edit_bones.new("Side")
bone_side.head = (0.5, 0, 1)
bone_side.tail = (1.0, 0, 1)
bone_side.parent = bone
bone_side.use_connect = False  # Free-floating child

# Bone properties in edit mode
bone.roll = 0.0                     # Bone roll angle
bone.use_deform = True              # Whether bone deforms mesh
bone.envelope_distance = 0.25       # Envelope influence radius
bone.head_radius = 0.1              # Head envelope radius
bone.tail_radius = 0.1              # Tail envelope radius

# Exit edit mode when done
bpy.ops.object.mode_set(mode='OBJECT')
```

## Simple Skeleton Example

```python
def create_simple_skeleton():
    armature_data = bpy.data.armatures.new("Skeleton")
    armature_obj = bpy.data.objects.new("Skeleton", armature_data)
    bpy.context.collection.objects.link(armature_obj)

    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = armature_data.edit_bones

    # Spine chain
    root = edit_bones.new("Root")
    root.head = (0, 0, 0)
    root.tail = (0, 0, 0.3)

    spine = edit_bones.new("Spine")
    spine.head = (0, 0, 0.3)
    spine.tail = (0, 0, 0.8)
    spine.parent = root
    spine.use_connect = True

    chest = edit_bones.new("Chest")
    chest.head = (0, 0, 0.8)
    chest.tail = (0, 0, 1.2)
    chest.parent = spine
    chest.use_connect = True

    head = edit_bones.new("Head")
    head.head = (0, 0, 1.2)
    head.tail = (0, 0, 1.5)
    head.parent = chest
    head.use_connect = True

    # Left arm
    upper_arm_l = edit_bones.new("UpperArm.L")
    upper_arm_l.head = (0.2, 0, 1.1)
    upper_arm_l.tail = (0.6, 0, 1.1)
    upper_arm_l.parent = chest

    forearm_l = edit_bones.new("Forearm.L")
    forearm_l.head = (0.6, 0, 1.1)
    forearm_l.tail = (1.0, 0, 1.1)
    forearm_l.parent = upper_arm_l
    forearm_l.use_connect = True

    # Right arm (mirror)
    upper_arm_r = edit_bones.new("UpperArm.R")
    upper_arm_r.head = (-0.2, 0, 1.1)
    upper_arm_r.tail = (-0.6, 0, 1.1)
    upper_arm_r.parent = chest

    forearm_r = edit_bones.new("Forearm.R")
    forearm_r.head = (-0.6, 0, 1.1)
    forearm_r.tail = (-1.0, 0, 1.1)
    forearm_r.parent = upper_arm_r
    forearm_r.use_connect = True

    # Left leg
    upper_leg_l = edit_bones.new("UpperLeg.L")
    upper_leg_l.head = (0.15, 0, 0)
    upper_leg_l.tail = (0.15, 0, -0.5)
    upper_leg_l.parent = root

    lower_leg_l = edit_bones.new("LowerLeg.L")
    lower_leg_l.head = (0.15, 0, -0.5)
    lower_leg_l.tail = (0.15, 0, -1.0)
    lower_leg_l.parent = upper_leg_l
    lower_leg_l.use_connect = True

    # Right leg (mirror)
    upper_leg_r = edit_bones.new("UpperLeg.R")
    upper_leg_r.head = (-0.15, 0, 0)
    upper_leg_r.tail = (-0.15, 0, -0.5)
    upper_leg_r.parent = root

    lower_leg_r = edit_bones.new("LowerLeg.R")
    lower_leg_r.head = (-0.15, 0, -0.5)
    lower_leg_r.tail = (-0.15, 0, -1.0)
    lower_leg_r.parent = upper_leg_r
    lower_leg_r.use_connect = True

    bpy.ops.object.mode_set(mode='OBJECT')
    return armature_obj
```

## Bone Layers & Collections (Blender 4.0+)

```python
# Blender 4.0+ uses bone collections instead of layers
armature = armature_obj.data

# Create bone collection
col = armature.collections.new("Deform")
ik_col = armature.collections.new("IK Controls")

# Assign bones to collections (in edit mode)
bpy.ops.object.mode_set(mode='EDIT')
for bone in armature.edit_bones:
    if bone.use_deform:
        col.assign(bone)
    else:
        ik_col.assign(bone)
bpy.ops.object.mode_set(mode='OBJECT')

# Toggle collection visibility
col.is_visible = True
ik_col.is_visible = False
```

## Parenting Mesh to Armature

```python
mesh_obj = bpy.data.objects["MyMesh"]
armature_obj = bpy.data.objects["MyArmature"]

# Parent with automatic weights
mesh_obj.parent = armature_obj
mod = mesh_obj.modifiers.new("Armature", 'ARMATURE')
mod.object = armature_obj

# Or use operator (sets up automatic weights)
bpy.context.view_layer.objects.active = armature_obj
mesh_obj.select_set(True)
armature_obj.select_set(True)
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
```

## Pose Mode & Bone Transforms

```python
# Switch to pose mode
bpy.context.view_layer.objects.active = armature_obj
bpy.ops.object.mode_set(mode='POSE')

# Access pose bones
pose_bones = armature_obj.pose.bones

# Transform a pose bone
pb = pose_bones["UpperArm.L"]
pb.location = (0, 0, 0.1)                          # Local offset
pb.rotation_euler = (0, 0, math.radians(45))        # Euler rotation
pb.rotation_quaternion = (1, 0, 0, 0)               # Quaternion
pb.rotation_mode = 'XYZ'                             # 'XYZ', 'QUATERNION', 'AXIS_ANGLE'
pb.scale = (1, 1, 1)

# Keyframe pose
pb.keyframe_insert(data_path="rotation_euler", frame=1)
pb.rotation_euler = (0, 0, math.radians(90))
pb.keyframe_insert(data_path="rotation_euler", frame=30)

bpy.ops.object.mode_set(mode='OBJECT')
```

## Bone Constraints

```python
bpy.ops.object.mode_set(mode='POSE')
pb = armature_obj.pose.bones["Forearm.L"]

# Inverse Kinematics
ik = pb.constraints.new('IK')
ik.target = bpy.data.objects.get("IK_Target")  # Empty or bone
ik.chain_count = 2                               # Number of bones in chain (0 = all)
ik.use_tail = True
ik.influence = 1.0

# Copy Rotation
copy_rot = pb.constraints.new('COPY_ROTATION')
copy_rot.target = armature_obj
copy_rot.subtarget = "Root"         # Target bone name
copy_rot.use_x = True
copy_rot.use_y = True
copy_rot.use_z = True
copy_rot.influence = 0.5

# Limit Rotation
limit = pb.constraints.new('LIMIT_ROTATION')
limit.use_limit_x = True
limit.min_x = math.radians(-10)
limit.max_x = math.radians(160)
limit.owner_space = 'LOCAL'

# Damped Track (aim at target)
track = pb.constraints.new('DAMPED_TRACK')
track.target = bpy.data.objects.get("LookTarget")
track.track_axis = 'TRACK_Y'

# Stretch To
stretch = pb.constraints.new('STRETCH_TO')
stretch.target = armature_obj
stretch.subtarget = "StretchTarget"
stretch.rest_length = 0  # 0 = auto
stretch.volume = 'VOLUME_XZX'

# Common constraint types:
# 'COPY_LOCATION', 'COPY_ROTATION', 'COPY_SCALE', 'COPY_TRANSFORMS'
# 'LIMIT_LOCATION', 'LIMIT_ROTATION', 'LIMIT_SCALE'
# 'TRANSFORM', 'CLAMP_TO', 'DAMPED_TRACK', 'IK', 'LOCKED_TRACK'
# 'STRETCH_TO', 'TRACK_TO', 'FLOOR', 'FOLLOW_PATH'
# 'ACTION', 'ARMATURE', 'CHILD_OF', 'PIVOT'

bpy.ops.object.mode_set(mode='OBJECT')
```

## Weight Painting (Programmatic)

```python
mesh_obj = bpy.data.objects["MyMesh"]

# Create vertex group matching a bone name
vg = mesh_obj.vertex_groups.new(name="UpperArm.L")

# Assign weights by vertex index
# add(vertex_indices, weight, mode)
# mode: 'REPLACE', 'ADD', 'SUBTRACT'
vg.add([0, 1, 2, 3, 4], 1.0, 'REPLACE')       # Full weight
vg.add([5, 6, 7], 0.5, 'REPLACE')              # Half weight
vg.add([8, 9, 10], 0.25, 'REPLACE')            # Quarter weight

# Gradient weight by distance from bone
import bmesh
armature = bpy.data.objects["MyArmature"]

def auto_weight_by_distance(mesh_obj, armature_obj, bone_name, max_distance=2.0):
    """Assign weights based on distance from bone."""
    bone = armature_obj.data.bones[bone_name]
    bone_head_world = armature_obj.matrix_world @ bone.head_local
    bone_tail_world = armature_obj.matrix_world @ bone.tail_local

    vg = mesh_obj.vertex_groups.get(bone_name)
    if not vg:
        vg = mesh_obj.vertex_groups.new(name=bone_name)

    for vert in mesh_obj.data.vertices:
        vert_world = mesh_obj.matrix_world @ vert.co
        # Distance to bone center
        bone_center = (bone_head_world + bone_tail_world) / 2
        dist = (vert_world - bone_center).length
        weight = max(0.0, 1.0 - (dist / max_distance))
        if weight > 0.001:
            vg.add([vert.index], weight, 'REPLACE')
```

## Bone Custom Properties

```python
# In pose mode, add custom properties to bones
bpy.ops.object.mode_set(mode='POSE')
pb = armature_obj.pose.bones["Root"]

# Add custom property
pb["ik_fk_switch"] = 0.0

# Configure property UI (min, max, description)
ui = pb.id_properties_ui("ik_fk_switch")
ui.update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, description="IK/FK Switch")

# Use in driver
# data_path: pose.bones["Root"]["ik_fk_switch"]
```
