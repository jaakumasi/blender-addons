# Testing & Debugging Blender Addons

## CLI Flags

```bash
BLENDER="C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"

# Run script headlessly (no GUI)
"$BLENDER" -b --python my_script.py

# Set exit code on Python error (useful for CI)
"$BLENDER" -b --python-exit-code 1 --python my_script.py

# Enable addon before running script
"$BLENDER" -b --addons my_addon --python test_script.py

# Open a specific .blend file, then run script
"$BLENDER" -b scene.blend --python my_script.py

# Run Python expression directly
"$BLENDER" -b --python-expr "import bpy; print(bpy.app.version_string)"

# Factory settings (ignore user preferences)
"$BLENDER" -b --factory-startup --python my_script.py

# Debug Python (verbose errors)
"$BLENDER" --debug-python
```

## Development Workflow with Symlinks

Instead of copying your addon to Blender's addon directory every time, create a symlink:

```bash
# Run Command Prompt as Administrator
mklink /D "%APPDATA%\Blender Foundation\Blender\5.0\scripts\addons\my_addon" "C:\Users\JeromeAwonnisebaAkum\Documents\projects\blender\addons\my_addon"
```

Now editing files in your project directory immediately affects the addon in Blender.

To reload the addon after code changes (in Blender's Python console or script):
```python
import importlib
import my_addon
importlib.reload(my_addon)
```

For multi-file addons, you need to reload each module:
```python
import importlib
from my_addon import operators, panels, preferences
importlib.reload(operators)
importlib.reload(panels)
importlib.reload(preferences)
importlib.reload(my_addon)
```

Or simply press F3 in Blender, search "Reload Scripts" (or use `bpy.ops.script.reload()`).

## Debug Printing

```python
# Print to console (visible in terminal that launched Blender)
print("Debug:", some_value)

# Report to user (shows in status bar / info editor)
self.report({'INFO'}, "Operation completed")
self.report({'WARNING'}, "Something might be wrong")
self.report({'ERROR'}, "Something failed")

# Log with Python logging module
import logging
log = logging.getLogger(__name__)
log.info("Addon initialized")
log.warning("Missing optional dependency")
log.error("Failed to process data")
```

## Writing Test Scripts

```python
# test_my_addon.py - run with: blender -b --python-exit-code 1 --addons my_addon --python test_my_addon.py

import bpy
import sys

def test_operator_creates_object():
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Run addon operator
    result = bpy.ops.my_addon.create_thing()
    assert result == {'FINISHED'}, f"Expected FINISHED, got {result}"

    # Check results
    assert len(bpy.data.objects) == 1, f"Expected 1 object, got {len(bpy.data.objects)}"
    obj = bpy.data.objects[0]
    assert obj.name.startswith("MyThing"), f"Unexpected name: {obj.name}"

    print("PASS: test_operator_creates_object")

def test_panel_exists():
    # Verify panel is registered
    assert hasattr(bpy.types, 'VIEW3D_PT_my_panel'), "Panel not registered"
    print("PASS: test_panel_exists")

# Run tests
try:
    test_operator_creates_object()
    test_panel_exists()
    print("\nAll tests passed!")
except Exception as e:
    print(f"\nTEST FAILED: {e}")
    sys.exit(1)
```

## Common Debugging Techniques

### Inspect object properties
```python
# In Blender's Python console:
obj = bpy.context.active_object
print(dir(obj))                    # List all attributes
print(obj.bl_rna.properties.keys())  # List RNA properties
```

### Trace operator execution
```python
# Enable operator logging
bpy.app.debug_wm = True
```

### Check if addon is enabled
```python
addon_name = "my_addon"
is_enabled = addon_name in bpy.context.preferences.addons
print(f"Addon enabled: {is_enabled}")
```

### Profile performance
```python
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()

    # Your code here
    my_expensive_operation()

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
```

## Troubleshooting Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Addon not showing in menu | `register()` not appending to menu | Add `bpy.types.MENU_TYPE.append(draw_func)` |
| `AttributeError: 'NoneType'` | Wrong context (e.g., no active object) | Add `poll()` classmethod to check context |
| Properties not saving | Using `=` instead of `:` for props | Use annotation syntax: `prop: Type(...)` |
| Changes not visible after edit | Module not reloaded | Press F3 > "Reload Scripts" or restart Blender |
| `RuntimeError: Operator bpy.ops...` | Calling operator from wrong context | Use `context.temp_override()` or restructure code |
| Panel not in expected location | Wrong `bl_space_type`/`bl_region_type` | Check values match target editor area |
