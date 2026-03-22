# Modal operator example
# A modal operator stays active and processes events (mouse, keyboard) until
# the user confirms or cancels. Common uses: interactive tools, drawing, measuring.

import bpy
from bpy.types import Operator
from bpy.props import IntProperty, FloatProperty


class MY_OT_interactive_scale(Operator):
    """Interactively scale an object by moving the mouse"""
    bl_idname = "my_addon.interactive_scale"
    bl_label = "Interactive Scale"
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR'}

    # Internal properties (not shown in UI, used to track state)
    first_mouse_x: IntProperty()
    initial_scale: FloatProperty()

    # Undo value — stored so we can revert on cancel
    sensitivity: FloatProperty(
        name="Sensitivity",
        default=0.01,
        min=0.001,
        max=0.1,
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def modal(self, context, event):
        """Called for every event while the operator is running.

        Must return one of:
          {'RUNNING_MODAL'} — keep running, consume the event
          {'PASS_THROUGH'}  — keep running, let other handlers see the event
          {'FINISHED'}      — done, commit changes
          {'CANCELLED'}     — done, revert changes
        """
        if event.type == 'MOUSEMOVE':
            # Calculate scale delta from mouse movement
            delta = event.mouse_x - self.first_mouse_x
            scale_factor = 1.0 + delta * self.sensitivity
            scale_factor = max(0.01, scale_factor)  # Clamp to avoid zero/negative

            context.active_object.scale = (
                self.initial_scale * scale_factor,
                self.initial_scale * scale_factor,
                self.initial_scale * scale_factor,
            )

            # Update header text to show current value
            context.area.header_text_set(f"Scale: {scale_factor:.3f}  |  LMB: Confirm  |  RMB/Esc: Cancel")

        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # Confirm — accept the current scale
            context.area.header_text_set(None)  # Reset header
            self.report({'INFO'}, f"Scaled to {context.active_object.scale[0]:.3f}")
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            # Cancel — revert to original scale
            context.active_object.scale = (
                self.initial_scale,
                self.initial_scale,
                self.initial_scale,
            )
            context.area.header_text_set(None)
            self.report({'INFO'}, "Scale cancelled")
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        """Called when the operator is first triggered (e.g., from a button or shortcut).

        This is where you set up the modal state and register the modal handler.
        For modal operators, invoke() should NOT call execute() — it returns
        {'RUNNING_MODAL'} to start the modal loop.
        """
        if context.active_object:
            # Store initial state for cancel/undo
            self.first_mouse_x = event.mouse_x
            self.initial_scale = context.active_object.scale[0]

            # Register this operator as a modal handler
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}


# ---------------------------------------------------------------------------
# Menu & Registration
# ---------------------------------------------------------------------------

def menu_func(self, context):
    self.layout.operator(MY_OT_interactive_scale.bl_idname)


def register():
    bpy.utils.register_class(MY_OT_interactive_scale)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    bpy.utils.unregister_class(MY_OT_interactive_scale)


if __name__ == "__main__":
    register()
