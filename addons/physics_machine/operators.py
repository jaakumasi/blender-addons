import bpy
from bpy.types import Operator

from . import node_setup
from . import physics_engine
from . import handlers


class PHYSICS_MACHINE_OT_enable(Operator):
    """Enable PhysicsMachine on selected objects"""
    bl_idname = "physics_machine.enable"
    bl_label = "Enable Physics"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH'
                and not context.active_object.physics_machine.enabled)

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            if obj.physics_machine.enabled:
                continue

            # Initialize physics state
            state = physics_engine.get_or_create_state(obj)
            state.initialize(obj)

            # Apply the GN modifier (force rebuild node group on first enable)
            node_setup.get_or_create_node_group(force_rebuild=True)
            node_setup.apply_modifier(obj)

            # Enable
            obj.physics_machine.enabled = True

        # Ensure handlers are active
        handlers.register_handlers()

        self.report({'INFO'}, "PhysicsMachine enabled")
        return {'FINISHED'}


class PHYSICS_MACHINE_OT_disable(Operator):
    """Disable PhysicsMachine and remove deformation"""
    bl_idname = "physics_machine.disable"
    bl_label = "Disable Physics"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH'
                and context.active_object.physics_machine.enabled)

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            if not obj.physics_machine.enabled:
                continue

            # Remove modifier and drivers
            node_setup.remove_modifier(obj)

            # Clean up physics state
            physics_engine.remove_state(obj)

            # Disable
            obj.physics_machine.enabled = False

        self.report({'INFO'}, "PhysicsMachine disabled")
        return {'FINISHED'}


class PHYSICS_MACHINE_OT_reset(Operator):
    """Reset deformation to rest state"""
    bl_idname = "physics_machine.reset"
    bl_label = "Reset"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH'
                and context.active_object.physics_machine.enabled)

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            if not obj.physics_machine.enabled:
                continue

            physics_engine.reset_state(obj)

        self.report({'INFO'}, "PhysicsMachine reset")
        return {'FINISHED'}


class PHYSICS_MACHINE_OT_apply(Operator):
    """Apply current deformation permanently and remove PhysicsMachine"""
    bl_idname = "physics_machine.apply"
    bl_label = "Apply Deformation"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return False
        if not obj.physics_machine.enabled:
            return False
        # Must have the modifier to apply
        return obj.modifiers.get("PhysicsMachine") is not None

    def execute(self, context):
        obj = context.active_object
        mod = obj.modifiers.get("PhysicsMachine")

        if not mod:
            self.report({'WARNING'}, "No PhysicsMachine modifier found")
            return {'CANCELLED'}

        # Remove drivers first (applying modifier fails with active drivers)
        if mod.node_group:
            for item in mod.node_group.interface.items_tree:
                if item.item_type == 'SOCKET' and item.in_out == 'INPUT':
                    if getattr(item, 'socket_type', '') == 'NodeSocketGeometry':
                        continue
                    data_path = f'modifiers["PhysicsMachine"]["{item.identifier}"]'
                    obj.driver_remove(data_path)

        # Apply the modifier
        bpy.context.view_layer.objects.active = obj
        try:
            bpy.ops.object.modifier_apply(modifier="PhysicsMachine")
        except RuntimeError as e:
            self.report({'ERROR'}, f"Failed to apply: {e}")
            return {'CANCELLED'}

        # Clean up
        physics_engine.remove_state(obj)
        obj.physics_machine.enabled = False

        for prop in ("pm_deform_x", "pm_deform_y", "pm_deform_z",
                     "pm_secondary_x", "pm_secondary_y", "pm_secondary_z"):
            if prop in obj:
                del obj[prop]

        self.report({'INFO'}, "Deformation applied")
        return {'FINISHED'}


classes = (
    PHYSICS_MACHINE_OT_enable,
    PHYSICS_MACHINE_OT_disable,
    PHYSICS_MACHINE_OT_reset,
    PHYSICS_MACHINE_OT_apply,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
