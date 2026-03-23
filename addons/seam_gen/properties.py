"""
SeamGen settings PropertyGroup attached to Scene.
"""

import bpy
from bpy.props import (
    EnumProperty, FloatProperty, IntProperty, BoolProperty, PointerProperty
)

# Mode preset weights (7 signals)
PRESETS = {
    'HARD_SURFACE': {
        'w_dihedral': 0.30, 'w_curvature': 0.05, 'w_concavity': 0.10,
        'w_edge_loop': 0.10, 'w_visibility': 0.15, 'w_segmentation': 0.10,
        'w_normal_cluster': 0.20,
    },
    'ORGANIC': {
        'w_dihedral': 0.10, 'w_curvature': 0.18, 'w_concavity': 0.14,
        'w_edge_loop': 0.08, 'w_visibility': 0.30, 'w_segmentation': 0.15,
        'w_normal_cluster': 0.05,
    },
    'BALANCED': {
        'w_dihedral': 0.18, 'w_curvature': 0.12, 'w_concavity': 0.12,
        'w_edge_loop': 0.08, 'w_visibility': 0.22, 'w_segmentation': 0.13,
        'w_normal_cluster': 0.15,
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

    # --- Signal weights (7 signals) — defaults match the BALANCED preset ---
    w_dihedral: FloatProperty(
        name="Dihedral Angle",
        description="Weight for sharp angle detection between faces",
        default=0.18, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )
    w_curvature: FloatProperty(
        name="Curvature",
        description="Weight for surface curvature analysis",
        default=0.12, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )
    w_concavity: FloatProperty(
        name="Concavity",
        description="Bonus for seams in concave creases (hidden seams)",
        default=0.12, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )
    w_edge_loop: FloatProperty(
        name="Edge Loop",
        description="Weight for clean edge loop alignment",
        default=0.08, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )
    w_visibility: FloatProperty(
        name="Visibility (AO)",
        description="Weight for ambient occlusion — hides seams in dark/occluded areas",
        default=0.22, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )
    w_segmentation: FloatProperty(
        name="Part Boundaries",
        description="Weight for natural part boundaries (arm/torso, handle/body)",
        default=0.13, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )
    w_normal_cluster: FloatProperty(
        name="Normal Clusters",
        description="Weight for face-normal clustering — detects flat panel transitions "
                    "(recommended high for hard-surface, low for organic)",
        default=0.15, min=0.0, max=1.0, step=1,
        update=_on_weight_changed,
    )

    # --- Settings ---
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
    ao_samples: IntProperty(
        name="AO Quality",
        description="Rays per vertex for occlusion detection (higher = slower, more accurate)",
        default=16, min=4, max=64,
    )
    layout_bias: bpy.props.FloatProperty(
        name="Layout Bias",
        description="How strongly to prefer compact, cross-shaped UV layouts. "
                    "0 = pure score, 1 = strongly favour star/cross shape "
                    "(fixes cube/cylinder unfolding on uniform meshes)",
        default=0.35, min=0.0, max=1.0, step=1,
    )
    normal_cluster_angle: bpy.props.FloatProperty(
        name="Cluster Angle",
        description="Maximum angle (degrees) between adjacent face normals "
                    "for them to belong to the same normal cluster. "
                    "Lower = stricter panel detection",
        default=30.0, min=5.0, max=90.0, step=100,
    )
    use_genus_cuts: bpy.props.BoolProperty(
        name="Topology Cuts",
        description="Detect mesh genus (handles/holes) and add mandatory "
                    "non-contractible loop seams so the mesh can fully unfold. "
                    "Required for tori, knots, and any mesh with handles",
        default=True,
    )
    use_distortion_split: bpy.props.BoolProperty(
        name="Auto-Split Distortion",
        description="After seam placement, identify UV charts that would produce "
                    "high stretch and automatically add extra seams to split them",
        default=True,
    )
    distortion_threshold: bpy.props.FloatProperty(
        name="Distortion Threshold",
        description="Charts with a mean internal edge score above this value are "
                    "split (lower = more aggressive splitting)",
        default=0.55, min=0.20, max=0.90, step=1,
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
