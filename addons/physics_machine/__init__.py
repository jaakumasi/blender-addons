bl_info = {
    "name": "PhysicsMachine",
    "author": "PhysicsMachine Team",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > Physics",
    "description": "Realistic jiggle and flex deformation for any mesh using spring physics and Geometry Nodes",
    "category": "Physics",
}

from . import properties
from . import operators
from . import panels
from . import handlers
from .physics_engine import clear_all_states


def register():
    properties.register()
    operators.register()
    panels.register()
    handlers.register_handlers()


def unregister():
    handlers.unregister_handlers()
    panels.unregister()
    operators.unregister()
    properties.unregister()
    clear_all_states()
