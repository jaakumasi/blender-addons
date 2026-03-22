# Multi-file addon example: panels.py
# All panel/UI classes live here.

import bpy
from bpy.types import Panel

from . import operators


class MYADDON_PT_main_panel(Panel):
    """Main panel in the 3D Viewport sidebar"""
    bl_label = "My Addon"
    bl_idname = "VIEW3D_PT_my_addon_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "My Addon"

    def draw(self, context):
        layout = self.layout

        if context.active_object:
            layout.label(text=f"Active: {context.active_object.name}", icon='OBJECT_DATA')
        else:
            layout.label(text="No active object", icon='ERROR')

        layout.separator()

        # Operator buttons
        col = layout.column(align=True)
        col.operator(operators.MYADDON_OT_simple_action.bl_idname, icon='FULLSCREEN_ENTER')
        col.operator(operators.MYADDON_OT_rename_selected.bl_idname, icon='SORTALPHA')


class MYADDON_PT_info_subpanel(Panel):
    """Sub-panel showing object info"""
    bl_label = "Object Info"
    bl_idname = "VIEW3D_PT_my_addon_info"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "My Addon"
    bl_parent_id = "VIEW3D_PT_my_addon_main"  # Makes this a sub-panel
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        col = layout.column()
        col.prop(obj, "name")
        col.prop(obj, "location")
        col.prop(obj, "rotation_euler")
        col.prop(obj, "scale")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    MYADDON_PT_main_panel,
    MYADDON_PT_info_subpanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
