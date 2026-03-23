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

        # Threshold & Smoothing
        box = layout.box()
        box.label(text="Threshold & Smoothing", icon='MODIFIER')
        col = box.column(align=True)
        col.prop(sg, "seam_threshold")
        col.prop(sg, "smoothing_iterations")
        col.prop(sg, "segment_count")

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
        col.prop(sg, "w_dihedral")
        col.prop(sg, "w_curvature")
        col.prop(sg, "w_segmentation")
        col.prop(sg, "w_concavity")
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
        col.label(text="Too many seams: raise Threshold")
        col.label(text="Too few seams: lower Threshold")
        col.label(text="Seams ignore creases: raise Dihedral")
        col.label(text="Seams on flat areas: lower Segmentation")
        col.label(text="Jagged seams: raise Edge Loop + Smoothing")
        col.label(text="Seams on ridges: raise Concavity")
        col.label(text="Mechanical mesh: use Hard Surface mode")
        col.label(text="Character mesh: use Organic mode")


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
