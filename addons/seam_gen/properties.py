"""
SeamGen settings PropertyGroup attached to Scene.
"""

import bpy
from bpy.props import (
    EnumProperty, FloatProperty, IntProperty, BoolProperty, PointerProperty
)

# Mode preset weights (4 signals — no segmentation)
PRESETS = {
    'HARD_SURFACE': {
        'w_dihedral': 0.5, 'w_curvature': 0.1,
        'w_concavity': 0.2, 'w_edge_loop': 0.2,
    },
    'ORGANIC': {
        'w_dihedral': 0.2, 'w_curvature': 0.4,
        'w_concavity': 0.2, 'w_edge_loop': 0.2,
    },
    'BALANCED': {
        'w_dihedral': 0.35, 'w_curvature': 0.25,
        'w_concavity': 0.2, 'w_edge_loop': 0.2,
    },
}

# Guard flag to prevent recursion between mode and weight callbacks
_updating = False


def _on_mode_changed(self, context):
    global _updating
    if _updating:
        return
    _updating = True
    try:
        preset = PRESETS.get(self.mode)
        if preset:
            for key, value in preset.items():
                setattr(self, key, value)
    finally:
        _updating = False


def _on_weight_changed(self, context):
    global _updating
    if _updating:
        return
    _updating = True
    try:
        # Check if current weights match any preset
        for mode_name, preset in PRESETS.items():
            match = all(
                abs(getattr(self, k) - v) < 0.001
                for k, v in preset.items()
            )
            if match:
                if self.mode != mode_name:
                    self.mode = mode_name
                _updating = False
                return

        # No preset match — switch to CUSTOM
        if self.mode != 'CUSTOM':
            self.mode = 'CUSTOM'
    finally:
        _updating = False


class SeamGenSettings(bpy.types.PropertyGroup):
    mode: EnumProperty(
        name="Mode",
        items=[
            ('HARD_SURFACE', "Hard Surface", "Optimized for mechanical/architectural models"),
            ('ORGANIC', "Organic", "Optimized for characters, creatures, organic shapes"),
            ('BALANCED', "Balanced", "General purpose, works well on most meshes"),
            ('CUSTOM', "Custom", "Manual weight adjustment"),
        ],
        default='BALANCED',
        update=_on_mode_changed,
    )

    w_dihedral: FloatProperty(
        name="Dihedral Angle",
        description="Weight for sharp angle detection between faces",
        default=0.35, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )
    w_curvature: FloatProperty(
        name="Curvature",
        description="Weight for surface curvature analysis",
        default=0.25, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )
    w_concavity: FloatProperty(
        name="Concavity",
        description="Bonus for seams in concave creases (hidden seams)",
        default=0.2, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )
    w_edge_loop: FloatProperty(
        name="Edge Loop",
        description="Weight for clean edge loop alignment",
        default=0.2, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )

    smoothing_iterations: IntProperty(
        name="Smoothing",
        description="Path smoothing passes to reduce jagged seams",
        default=3, min=0, max=10,
    )
    island_count: IntProperty(
        name="UV Islands",
        description="Target UV island count (0 = single island, more = less distortion)",
        default=0, min=0, max=20,
    )

    # Hidden state flags
    is_analyzed: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})
    overlay_visible: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})


classes = (SeamGenSettings,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.seam_gen = PointerProperty(type=SeamGenSettings)


def unregister():
    del bpy.types.Scene.seam_gen
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
