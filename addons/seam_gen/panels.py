"""
SeamGen sidebar panel in 3D Viewport, UV tab, Edit Mode only.
"""

import bpy
from bpy.types import Panel


class VIEW3D_PT_seam_gen(Panel):
    """SeamGen automatic seam suggestion panel"""
    bl_label = "SeamGen"
    bl_idname = "VIEW3D_PT_seam_gen"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "UV"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and obj.type == 'MESH'
                and context.mode == 'EDIT_MESH')

    def draw(self, context):
        layout = self.layout
        sg = context.scene.seam_gen

        # Analyze button
        row = layout.row()
        row.scale_y = 1.5
        row.operator("mesh.seam_gen_analyze", text="Analyze Mesh", icon='VIEWZOOM')

        layout.separator()

        # Mode selector
        layout.prop(sg, "mode", expand=True)

        layout.separator()

        # Settings
        box = layout.box()
        box.label(text="Settings", icon='MODIFIER')
        col = box.column(align=True)
        col.prop(sg, "smoothing_iterations")
        col.prop(sg, "island_count")
        col.prop(sg, "ao_samples")
        col.prop(sg, "layout_bias")
        col.prop(sg, "normal_cluster_angle")
        col.separator()
        row = col.row(align=True)
        row.prop(sg, "use_genus_cuts")
        row.prop(sg, "use_distortion_split")
        if sg.use_distortion_split:
            col.prop(sg, "distortion_threshold")

        # Actions (only when analyzed)
        if sg.is_analyzed:
            layout.separator()
            box = layout.box()
            box.label(text="Actions", icon='CHECKMARK')
            row = box.row(align=True)
            row.operator("mesh.seam_gen_accept", text="Accept Seams", icon='CHECKMARK')
            row.operator("mesh.seam_gen_accept_unwrap", text="Accept & Unwrap", icon='UV')
            box.operator("mesh.seam_gen_clear", text="Clear Suggestions", icon='X')


class VIEW3D_PT_seam_gen_weights(Panel):
    """Weight settings sub-panel"""
    bl_label = "Weight Settings"
    bl_idname = "VIEW3D_PT_seam_gen_weights"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "UV"
    bl_parent_id = "VIEW3D_PT_seam_gen"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        sg = context.scene.seam_gen

        col = layout.column(align=True)
        col.prop(sg, "w_visibility")
        col.prop(sg, "w_dihedral")
        col.prop(sg, "w_curvature")
        col.prop(sg, "w_concavity")
        col.prop(sg, "w_normal_cluster")
        col.prop(sg, "w_segmentation")
        col.prop(sg, "w_edge_loop")

        if sg.mode != 'CUSTOM':
            layout.label(text="Adjust any weight to enter Custom mode", icon='INFO')


class VIEW3D_PT_seam_gen_tips(Panel):
    """Tuning guide sub-panel"""
    bl_label = "Tuning Guide"
    bl_idname = "VIEW3D_PT_seam_gen_tips"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "UV"
    bl_parent_id = "VIEW3D_PT_seam_gen"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.scale_y = 0.8
        col.label(text="Seams too visible: raise Visibility (AO)")
        col.label(text="Seams ignore creases: raise Dihedral")
        col.label(text="Seams on smooth areas: raise Curvature")
        col.label(text="Seams on ridges: raise Concavity")
        col.label(text="Seams bisect flat panels: raise Normal Clusters")
        col.label(text="Seams cross parts: raise Part Boundaries")
        col.label(text="Jagged seams: raise Edge Loop + Smoothing")
        col.label(text="Cube/cylinder looks wrong: raise Layout Bias")
        col.label(text="Torus not unfolding: enable Topology Cuts")
        col.label(text="AO too slow: lower AO Quality")
        col.label(text="Too much stretch: enable Auto-Split Distortion")


classes = (
    VIEW3D_PT_seam_gen,
    VIEW3D_PT_seam_gen_weights,
    VIEW3D_PT_seam_gen_tips,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
