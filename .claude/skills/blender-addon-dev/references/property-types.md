# Blender Property Types (bpy.props)

All properties use **annotation syntax** (colon `:`), never assignment (`=`).

## BoolProperty

```python
my_bool: bpy.props.BoolProperty(
    name="Enable",              # Display name
    description="Toggle on/off", # Tooltip
    default=False,
    options={'ANIMATABLE'},      # Options set
    subtype='NONE',             # 'NONE'
    update=None,                # Callback: update(self, context)
    get=None,                   # Getter: get(self)
    set=None,                   # Setter: set(self, value)
)
```

## IntProperty

```python
my_int: bpy.props.IntProperty(
    name="Count",
    description="Number of items",
    default=0,
    min=-100,                   # Hard minimum
    max=100,                    # Hard maximum
    soft_min=-10,               # Soft minimum (UI slider range)
    soft_max=10,                # Soft maximum (UI slider range)
    step=1,                     # Step for UI buttons
    options={'ANIMATABLE'},
    subtype='NONE',             # 'NONE', 'PIXEL', 'UNSIGNED', 'PERCENTAGE', 'FACTOR', 'ANGLE', 'TIME', 'DISTANCE'
    update=None,
    get=None,
    set=None,
)
```

## FloatProperty

```python
my_float: bpy.props.FloatProperty(
    name="Value",
    description="A floating point value",
    default=0.0,
    min=-1000.0,
    max=1000.0,
    soft_min=0.0,
    soft_max=1.0,
    step=3,                     # Step in 1/100ths (step=3 means 0.03 increments)
    precision=2,                # Decimal digits displayed
    options={'ANIMATABLE'},
    subtype='NONE',             # 'NONE', 'PIXEL', 'UNSIGNED', 'PERCENTAGE', 'FACTOR', 'ANGLE', 'TIME', 'DISTANCE', 'POWER', 'TEMPERATURE'
    unit='NONE',                # 'NONE', 'LENGTH', 'AREA', 'VOLUME', 'ROTATION', 'TIME', 'VELOCITY', 'ACCELERATION', 'MASS', 'CAMERA', 'POWER', 'TEMPERATURE'
    update=None,
    get=None,
    set=None,
)
```

## StringProperty

```python
my_string: bpy.props.StringProperty(
    name="Name",
    description="Enter a name",
    default="",
    maxlen=0,                   # 0 = unlimited
    options={'ANIMATABLE'},
    subtype='NONE',             # 'NONE', 'FILE_PATH', 'DIR_PATH', 'FILE_NAME', 'BYTE_STRING', 'PASSWORD'
    update=None,
    get=None,
    set=None,
)
```

## EnumProperty

```python
# Static items (tuple of tuples)
my_enum: bpy.props.EnumProperty(
    name="Mode",
    description="Select mode",
    items=[
        ('OPT_A', "Option A", "First option description", 'ICON_NAME', 0),
        ('OPT_B', "Option B", "Second option description", 'NONE', 1),
        ('OPT_C', "Option C", "Third option description"),  # Short form OK
    ],
    default='OPT_A',
    options={'ANIMATABLE'},
    update=None,
    get=None,
    set=None,
)

# Dynamic items (callback function)
def get_items(self, context):
    items = []
    for i, obj in enumerate(context.scene.objects):
        items.append((obj.name, obj.name, f"Select {obj.name}", 'OBJECT_DATA', i))
    return items

my_dynamic_enum: bpy.props.EnumProperty(
    name="Object",
    items=get_items,  # Function reference, called each time menu opens
)

# Multi-select (flag enum)
my_flags: bpy.props.EnumProperty(
    name="Layers",
    items=[
        ('LAYER_1', "Layer 1", ""),
        ('LAYER_2', "Layer 2", ""),
        ('LAYER_3', "Layer 3", ""),
    ],
    default={'LAYER_1'},        # Set for flags
    options={'ENUM_FLAG'},       # CRITICAL: enables multi-select
)
```

**EnumProperty items tuple format**: `(identifier, name, description[, icon[, number]])`

## FloatVectorProperty

```python
my_color: bpy.props.FloatVectorProperty(
    name="Color",
    description="Pick a color",
    default=(1.0, 1.0, 1.0),
    min=0.0,
    max=1.0,
    size=3,                     # Vector size (2, 3, or 4)
    subtype='COLOR',            # 'NONE', 'COLOR', 'TRANSLATION', 'DIRECTION', 'VELOCITY', 'ACCELERATION', 'MATRIX', 'EULER', 'QUATERNION', 'AXISANGLE', 'XYZ', 'COLOR_GAMMA', 'COORDINATES', 'LAYER', 'LAYER_MEMBER'
    update=None,
)

my_location: bpy.props.FloatVectorProperty(
    name="Location",
    subtype='TRANSLATION',
    default=(0.0, 0.0, 0.0),
)
```

## IntVectorProperty

```python
my_ivec: bpy.props.IntVectorProperty(
    name="Resolution",
    default=(1920, 1080),
    size=2,
    min=1,
    subtype='NONE',             # 'NONE', 'COLOR', 'TRANSLATION', 'DIRECTION', 'VELOCITY', 'ACCELERATION', 'MATRIX', 'EULER', 'QUATERNION', 'AXISANGLE', 'XYZ', 'COLOR_GAMMA', 'COORDINATES', 'LAYER', 'LAYER_MEMBER'
)
```

## BoolVectorProperty

```python
my_bvec: bpy.props.BoolVectorProperty(
    name="Axes",
    default=(True, True, False),
    size=3,
    subtype='NONE',
)
```

## PointerProperty

```python
# Points to a PropertyGroup
my_settings: bpy.props.PointerProperty(type=MyPropertyGroup)

# Points to an ID type (Object, Material, etc.)
target_object: bpy.props.PointerProperty(
    name="Target",
    type=bpy.types.Object,
    description="Select target object",
    poll=lambda self, obj: obj.type == 'MESH',  # Optional filter
)
```

## CollectionProperty

```python
# Collection of PropertyGroups
my_items: bpy.props.CollectionProperty(type=MyItemPropertyGroup)

# Usage:
# item = self.my_items.add()
# item.name = "New Item"
# self.my_items.remove(index)
# self.my_items.clear()
# self.my_items.move(from_index, to_index)
```

## Common Options Set Values

- `'HIDDEN'` — hide from UI
- `'SKIP_SAVE'` — don't save in presets
- `'ANIMATABLE'` — can be keyframed (default for most)
- `'LIBRARY_EDITABLE'` — editable in linked libraries
- `'PROPORTIONAL'` — not used in addon props
- `'ENUM_FLAG'` — multi-select enum (EnumProperty only)

## PropertyGroup Pattern

```python
class MySettings(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(name="Enabled", default=True)
    count: bpy.props.IntProperty(name="Count", default=5, min=1, max=100)
    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[('A', "Auto", ""), ('M', "Manual", "")],
        default='A',
    )

def register():
    bpy.utils.register_class(MySettings)
    bpy.types.Scene.my_tool = bpy.props.PointerProperty(type=MySettings)

def unregister():
    del bpy.types.Scene.my_tool
    bpy.utils.unregister_class(MySettings)
```

## Update Callbacks

```python
def on_value_changed(self, context):
    # 'self' is the class instance containing the property
    # 'context' is bpy.context
    print(f"Value changed to: {self.my_value}")
    # WARNING: Do not set the property that triggered this callback
    # inside the callback - it will cause infinite recursion

my_value: bpy.props.IntProperty(
    name="Value",
    update=on_value_changed,
)
```
