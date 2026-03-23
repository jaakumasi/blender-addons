import bpy
from bpy.types import Panel


class VIEW3D_PT_physics_machine(Panel):
    """PhysicsMachine settings panel in the 3D Viewport sidebar"""
    bl_label = "PhysicsMachine"
    bl_idname = "VIEW3D_PT_physics_machine"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Physics"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        pm = obj.physics_machine

        # Enable/Disable + Reset row
        row = layout.row(align=True)
        if pm.enabled:
            row.operator("physics_machine.disable", text="Disable Physics", icon='CANCEL')
            row.operator("physics_machine.reset", text="", icon='FILE_REFRESH')
        else:
            row.operator("physics_machine.enable", text="Enable Physics", icon='PLAY')

        if not pm.enabled:
            return

        layout.separator()

        # Spring Settings
        box = layout.box()
        box.label(text="Spring Settings", icon='FORCE_HARMONIC')
        col = box.column(align=True)
        col.prop(pm, "stiffness")
        col.prop(pm, "damping")
        col.prop(pm, "mass")

        layout.separator()

        # Gravity
        box = layout.box()
        box.label(text="Gravity", icon='FORCE_FORCE')
        box.prop(pm, "gravity_strength")

        layout.separator()

        # Pin Settings
        box = layout.box()
        box.label(text="Pin Settings", icon='PINNED')
        box.prop(pm, "pin_method")
        if pm.pin_method == 'VERTEX_GROUP':
            row = box.row()
            row.prop_search(pm, "pin_group_name", obj, "vertex_groups", text="Group")
        box.prop(pm, "influence_falloff")

        layout.separator()

        # Advanced
        box = layout.box()
        box.label(text="Advanced", icon='PREFERENCES')
        box.prop(pm, "max_displacement")
        box.prop(pm, "secondary_enabled")
        if pm.secondary_enabled:
            col = box.column(align=True)
            col.prop(pm, "secondary_stiffness")
            col.prop(pm, "secondary_damping")

        layout.separator()

        # Apply button
        layout.operator("physics_machine.apply", text="Apply Deformation", icon='CHECKMARK')


classes = (VIEW3D_PT_physics_machine,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
