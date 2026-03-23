bl_info = {
    "name": "SeamGen",
    "author": "SeamGen Team",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > UV",
    "description": "Automatic UV seam suggestion using curvature and angle analysis",
    "category": "UV",
}

from . import properties
from . import operators
from . import panels


def register():
    properties.register()
    operators.register()
    panels.register()


def unregister():
    # Clean up GPU overlay before unregistering
    from .drawing import overlay
    overlay.disable_overlay()

    panels.unregister()
    operators.unregister()
    properties.unregister()
