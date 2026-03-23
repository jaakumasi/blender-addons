import bpy
from bpy.props import (
    BoolProperty,
    FloatProperty,
    EnumProperty,
    StringProperty,
)


class PhysicsMachineSettings(bpy.types.PropertyGroup):
    """Per-object PhysicsMachine settings."""

    enabled: BoolProperty(
        name="Enabled",
        description="Enable PhysicsMachine on this object",
        default=False,
    )

    stiffness: FloatProperty(
        name="Stiffness",
        description="Spring stiffness — higher values return to rest faster",
        default=5.0,
        min=0.1,
        max=50.0,
        soft_min=1.0,
        soft_max=20.0,
    )

    damping: FloatProperty(
        name="Damping",
        description="How quickly wobble dies out",
        default=0.3,
        min=0.01,
        max=1.0,
    )

    mass: FloatProperty(
        name="Mass",
        description="Inertia multiplier — heavier objects deform more on sudden movement",
        default=1.0,
        min=0.1,
        max=10.0,
    )

    gravity_strength: FloatProperty(
        name="Gravity",
        description="Gravity influence — objects sag under their weight",
        default=1.0,
        min=0.0,
        max=2.0,
    )

    pin_method: EnumProperty(
        name="Pin Method",
        description="Which part of the mesh stays fixed",
        items=[
            ('BOTTOM', "Bottom", "Pin the lowest vertices (good for standing objects)"),
            ('TOP', "Top", "Pin the highest vertices (good for hanging objects)"),
            ('CENTER', "Center", "Pin the center (deforms outward in all directions)"),
            ('VERTEX_GROUP', "Vertex Group", "Use a vertex group to define pinned vertices"),
        ],
        default='BOTTOM',
    )

    pin_group_name: StringProperty(
        name="Pin Group",
        description="Vertex group where weight=1 means fully pinned",
        default="",
    )

    influence_falloff: FloatProperty(
        name="Falloff",
        description="How quickly influence ramps from pinned to free (exponent)",
        default=1.0,
        min=0.1,
        max=5.0,
    )

    max_displacement: FloatProperty(
        name="Max Displacement",
        description="Maximum deformation distance to prevent physics explosion",
        default=2.0,
        min=0.1,
        max=10.0,
    )

    secondary_enabled: BoolProperty(
        name="Secondary Wobble",
        description="Enable a secondary higher-frequency wobble for more realism",
        default=True,
    )

    secondary_stiffness: FloatProperty(
        name="Sec. Stiffness",
        description="Secondary spring stiffness (higher = faster wobble)",
        default=15.0,
        min=1.0,
        max=80.0,
    )

    secondary_damping: FloatProperty(
        name="Sec. Damping",
        description="Secondary spring damping",
        default=0.5,
        min=0.01,
        max=1.0,
    )


classes = (PhysicsMachineSettings,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.physics_machine = bpy.props.PointerProperty(type=PhysicsMachineSettings)


def unregister():
    del bpy.types.Object.physics_machine
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
