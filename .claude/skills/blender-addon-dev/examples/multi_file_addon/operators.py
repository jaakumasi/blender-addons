# Multi-file addon example: operators.py
# All operator classes live here.

import bpy
from bpy.types import Operator
from bpy.props import FloatProperty, StringProperty


class MYADDON_OT_simple_action(Operator):
    """Perform a simple action on the active object"""
    bl_idname = "my_addon.simple_action"
    bl_label = "Simple Action"
    bl_options = {'REGISTER', 'UNDO'}

    scale_factor: FloatProperty(
        name="Scale Factor",
        default=2.0,
        min=0.1,
        max=10.0,
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.active_object
        obj.scale *= self.scale_factor
        self.report({'INFO'}, f"Scaled {obj.name} by {self.scale_factor}")
        return {'FINISHED'}


class MYADDON_OT_rename_selected(Operator):
    """Batch rename selected objects with a prefix"""
    bl_idname = "my_addon.rename_selected"
    bl_label = "Rename Selected"
    bl_options = {'REGISTER', 'UNDO'}

    prefix: StringProperty(
        name="Prefix",
        default="MyObj_",
    )

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        for i, obj in enumerate(context.selected_objects):
            obj.name = f"{self.prefix}{i:03d}"
        self.report({'INFO'}, f"Renamed {len(context.selected_objects)} objects")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Menu draw function — appended in register()
# ---------------------------------------------------------------------------

def menu_func(self, context):
    self.layout.separator()
    self.layout.operator(MYADDON_OT_simple_action.bl_idname)
    self.layout.operator(MYADDON_OT_rename_selected.bl_idname)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    MYADDON_OT_simple_action,
    MYADDON_OT_rename_selected,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
