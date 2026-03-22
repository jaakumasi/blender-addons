# Blender Addon Registration Patterns

## Single-file Addon

```python
import bpy

classes = (
    MyPropertyGroup,
    MY_OT_my_operator,
    MY_PT_my_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # Register scene properties AFTER their PropertyGroup classes
    bpy.types.Scene.my_settings = bpy.props.PointerProperty(type=MyPropertyGroup)

def unregister():
    # Delete scene properties BEFORE unregistering their classes
    del bpy.types.Scene.my_settings
    for cls in reversed(classes):  # REVERSE order
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
```

**Key rules:**
- Register PropertyGroups BEFORE classes that use them
- Register properties on types AFTER their PropertyGroup class is registered
- Unregister in REVERSE order
- The `if __name__` block allows running from Blender's text editor

## Multi-file Addon

### __init__.py
```python
bl_info = {
    "name": "My Addon",
    "author": "Your Name",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > My Tab",
    "description": "Description here",
    "category": "Object",
}

from . import operators
from . import panels
from . import preferences
from . import properties

def register():
    properties.register()    # PropertyGroups first
    preferences.register()   # Then preferences
    operators.register()     # Then operators
    panels.register()        # Then UI last

def unregister():
    panels.unregister()      # Reverse order
    operators.unregister()
    preferences.unregister()
    properties.unregister()
```

### Each submodule pattern (e.g., operators.py)
```python
import bpy

classes = (
    MY_OT_operator_one,
    MY_OT_operator_two,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

## AddonPreferences

Addon preferences appear in Edit > Preferences > Add-ons when the addon is selected.

```python
class MyAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__  # MUST match the addon module name

    api_key: bpy.props.StringProperty(
        name="API Key",
        subtype='PASSWORD',
    )
    debug_mode: bpy.props.BoolProperty(
        name="Debug Mode",
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "api_key")
        layout.prop(self, "debug_mode")

# Access preferences at runtime:
def get_prefs():
    return bpy.context.preferences.addons[__package__].preferences
```

## Keymap Registration

```python
addon_keymaps = []

def register():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(
            MY_OT_my_operator.bl_idname,
            type='Q',           # Key
            value='PRESS',
            ctrl=True,          # Modifier keys
            shift=False,
            alt=False,
        )
        # Set operator properties if needed
        # kmi.properties.some_prop = "value"
        addon_keymaps.append((km, kmi))

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
```

## Menu Registration

```python
def draw_menu_func(self, context):
    self.layout.operator(MY_OT_my_operator.bl_idname)

def register():
    bpy.types.VIEW3D_MT_object.append(draw_menu_func)

def unregister():
    bpy.types.VIEW3D_MT_object.remove(draw_menu_func)
```

## Scene Property Registration

```python
def register():
    bpy.utils.register_class(MyPropertyGroup)
    bpy.types.Scene.my_tool = bpy.props.PointerProperty(type=MyPropertyGroup)
    # Can also attach to Object, Material, etc.:
    # bpy.types.Object.my_data = bpy.props.PointerProperty(type=MyObjectData)

def unregister():
    del bpy.types.Scene.my_tool
    # del bpy.types.Object.my_data
    bpy.utils.unregister_class(MyPropertyGroup)
```

## Handler Registration

```python
@bpy.app.handlers.persistent  # Survive file load
def on_load(dummy):
    print("File loaded!")

def register():
    bpy.app.handlers.load_post.append(on_load)

def unregister():
    bpy.app.handlers.load_post.remove(on_load)
```

## Custom Icon Registration

```python
import bpy.utils.previews

preview_collections = {}

def register():
    pcoll = bpy.utils.previews.new()
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    pcoll.load("my_icon", os.path.join(icons_dir, "icon.png"), 'IMAGE')
    preview_collections["main"] = pcoll

def unregister():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

# Usage in draw():
# icon_id = preview_collections["main"]["my_icon"].icon_id
# layout.operator("my.op", icon_value=icon_id)
```
