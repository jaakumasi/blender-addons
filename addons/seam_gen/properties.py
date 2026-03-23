"""
SeamGen settings PropertyGroup attached to Scene.
"""

import bpy
from bpy.props import (
    EnumProperty, FloatProperty, IntProperty, BoolProperty, PointerProperty
)

# Mode preset weights
PRESETS = {
    'HARD_SURFACE': {
        'w_dihedral': 0.5, 'w_curvature': 0.1, 'w_segmentation': 0.2,
        'w_concavity': 0.1, 'w_edge_loop': 0.1,
    },
    'ORGANIC': {
        'w_dihedral': 0.2, 'w_curvature': 0.3, 'w_segmentation': 0.3,
        'w_concavity': 0.1, 'w_edge_loop': 0.1,
    },
    'BALANCED': {
        'w_dihedral': 0.3, 'w_curvature': 0.2, 'w_segmentation': 0.25,
        'w_concavity': 0.1, 'w_edge_loop': 0.15,
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
        default=0.3, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )
    w_curvature: FloatProperty(
        name="Curvature",
        description="Weight for surface curvature analysis",
        default=0.2, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )
    w_segmentation: FloatProperty(
        name="Segmentation",
        description="Weight for natural region boundary detection",
        default=0.25, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )
    w_concavity: FloatProperty(
        name="Concavity",
        description="Bonus for seams in concave creases (hidden seams)",
        default=0.1, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )
    w_edge_loop: FloatProperty(
        name="Edge Loop",
        description="Weight for clean edge loop alignment",
        default=0.15, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )

    seam_threshold: FloatProperty(
        name="Seam Threshold",
        description="Minimum score to suggest an edge as a seam (lower = more seams)",
        default=0.5, min=0.0, max=1.0, step=1,
    )
    smoothing_iterations: IntProperty(
        name="Smoothing",
        description="Path smoothing passes to reduce jagged seams",
        default=3, min=0, max=10,
    )
    segment_count: IntProperty(
        name="Segments",
        description="Target chart segments (0 = auto-detect from mesh complexity)",
        default=0, min=0, max=50,
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
