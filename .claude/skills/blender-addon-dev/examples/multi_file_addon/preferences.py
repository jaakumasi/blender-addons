# Multi-file addon example: preferences.py
# AddonPreferences class — appears in Edit > Preferences > Add-ons

import bpy
from bpy.types import AddonPreferences
from bpy.props import BoolProperty, StringProperty, EnumProperty


class MyAddonPreferences(AddonPreferences):
    # bl_idname must match the addon package name
    bl_idname = __package__

    debug_mode: BoolProperty(
        name="Debug Mode",
        description="Enable verbose console output",
        default=False,
    )

    default_prefix: StringProperty(
        name="Default Prefix",
        description="Default prefix for rename operations",
        default="Obj_",
    )

    theme: EnumProperty(
        name="Theme",
        description="UI theme for addon panels",
        items=[
            ('DEFAULT', "Default", "Standard appearance"),
            ('COMPACT', "Compact", "Reduced spacing"),
        ],
        default='DEFAULT',
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "debug_mode")
        layout.prop(self, "default_prefix")
        layout.prop(self, "theme")


# Helper function to get preferences from anywhere in the addon
def get_preferences():
    return bpy.context.preferences.addons[__package__].preferences


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    MyAddonPreferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
