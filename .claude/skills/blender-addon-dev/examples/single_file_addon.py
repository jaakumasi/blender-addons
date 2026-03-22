# Single-file Blender addon example
# This addon adds a custom object to the scene and provides a panel to control it.
#
# To use as an extension, place this file alongside a blender_manifest.toml
# in a directory and install via Edit > Preferences > Extensions.

import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import (
    FloatProperty,
    IntProperty,
    BoolProperty,
    EnumProperty,
    PointerProperty,
)


# ---------------------------------------------------------------------------
# Property Group — stores addon settings on the scene
# ---------------------------------------------------------------------------

class MY_PG_settings(PropertyGroup):
    """Settings for the example addon, stored on bpy.types.Scene."""

    count: IntProperty(
        name="Count",
        description="Number of objects to create",
        default=3,
        min=1,
        max=50,
    )
    size: FloatProperty(
        name="Size",
        description="Size of each object",
        default=1.0,
        min=0.1,
        max=10.0,
    )
    shape: EnumProperty(
        name="Shape",
        description="Choose primitive shape",
        items=[
            ('CUBE', "Cube", "Create cubes"),
            ('SPHERE', "Sphere", "Create UV spheres"),
            ('CYLINDER', "Cylinder", "Create cylinders"),
        ],
        default='CUBE',
    )
    use_random_location: BoolProperty(
        name="Random Location",
        description="Place objects at random locations",
        default=False,
    )


# ---------------------------------------------------------------------------
# Operator — the action the addon performs
# ---------------------------------------------------------------------------

class MY_OT_create_objects(Operator):
    """Create objects based on addon settings"""
    bl_idname = "my_addon.create_objects"
    bl_label = "Create Objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Only allow in object mode
        return context.mode == 'OBJECT'

    def execute(self, context):
        settings = context.scene.my_addon_settings
        import random

        for i in range(settings.count):
            if settings.use_random_location:
                loc = (random.uniform(-5, 5), random.uniform(-5, 5), random.uniform(0, 5))
            else:
                loc = (i * (settings.size + 0.5), 0, 0)

            if settings.shape == 'CUBE':
                bpy.ops.mesh.primitive_cube_add(size=settings.size, location=loc)
            elif settings.shape == 'SPHERE':
                bpy.ops.mesh.primitive_uv_sphere_add(radius=settings.size / 2, location=loc)
            elif settings.shape == 'CYLINDER':
                bpy.ops.mesh.primitive_cylinder_add(radius=settings.size / 2, depth=settings.size, location=loc)

        self.report({'INFO'}, f"Created {settings.count} {settings.shape.lower()}(s)")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Panel — sidebar UI in the 3D viewport (N-panel)
# ---------------------------------------------------------------------------

class MY_PT_main_panel(Panel):
    """Main panel in the 3D Viewport sidebar"""
    bl_label = "My Example Addon"
    bl_idname = "VIEW3D_PT_my_example"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "My Addon"  # Tab name in sidebar

    def draw(self, context):
        layout = self.layout
        settings = context.scene.my_addon_settings

        # Properties
        layout.prop(settings, "shape")
        layout.prop(settings, "count")
        layout.prop(settings, "size")
        layout.prop(settings, "use_random_location")

        layout.separator()

        # Big action button
        row = layout.row()
        row.scale_y = 1.5
        row.operator(MY_OT_create_objects.bl_idname, icon='ADD')


# ---------------------------------------------------------------------------
# Menu integration — add to the Add > Mesh menu
# ---------------------------------------------------------------------------

def menu_func(self, context):
    self.layout.operator(MY_OT_create_objects.bl_idname, icon='PLUGIN')


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    MY_PG_settings,
    MY_OT_create_objects,
    MY_PT_main_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.my_addon_settings = PointerProperty(type=MY_PG_settings)
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
    del bpy.types.Scene.my_addon_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
