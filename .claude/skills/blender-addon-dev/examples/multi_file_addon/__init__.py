# Multi-file addon example: __init__.py
# This is the entry point. It imports submodules and dispatches registration.

bl_info = {
    "name": "My Multi-File Addon",
    "author": "Developer Name",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > My Addon",
    "description": "Example multi-file addon demonstrating package structure",
    "category": "Object",
}

# Import submodules. These must be imported BEFORE registration
# so their classes are available.
from . import operators
from . import panels
from . import preferences


def register():
    preferences.register()   # Preferences first (may be referenced by others)
    operators.register()     # Then operators
    panels.register()        # Then UI last


def unregister():
    panels.unregister()      # Reverse order
    operators.unregister()
    preferences.unregister()
