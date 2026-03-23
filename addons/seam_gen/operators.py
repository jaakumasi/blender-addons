"""
SeamGen operators: Analyze, Accept, Accept & Unwrap, Clear.
"""

import bpy
import bmesh
from bpy.types import Operator

from .core.analyzer import get_analyzer
from .drawing import overlay


class MESH_OT_seam_gen_analyze(Operator):
    """Analyze mesh geometry and suggest optimal seam placements"""
    bl_idname = "mesh.seam_gen_analyze"
    bl_label = "Analyze Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and obj.type == 'MESH'
                and context.mode == 'EDIT_MESH')

    def execute(self, context):
        obj = context.active_object
        sg = context.scene.seam_gen

        bm = bmesh.from_edit_mesh(obj.data)

        if len(bm.edges) == 0:
            self.report({'WARNING'}, "Mesh has no edges")
            return {'CANCELLED'}

        weights = {
            'dihedral': sg.w_dihedral,
            'curvature': sg.w_curvature,
            'concavity': sg.w_concavity,
            'edge_loop': sg.w_edge_loop,
        }

        wm = context.window_manager
        wm.progress_begin(0, 100)

        def progress_cb(name, frac):
            wm.progress_update(int(frac * 100))

        analyzer = get_analyzer()
        try:
            scores, seam_mask = analyzer.analyze(
                bm, obj, weights,
                smoothing_iters=sg.smoothing_iterations,
                island_count=sg.island_count,
                progress_callback=progress_cb,
            )
        except Exception as e:
            wm.progress_end()
            self.report({'ERROR'}, f"Analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

        wm.progress_end()

        # Show overlay
        overlay.enable_overlay(obj, bm, scores)
        sg.is_analyzed = True
        sg.overlay_visible = True

        n_seams = int(seam_mask.sum())
        self.report({'INFO'}, f"Analysis complete: {n_seams} seam edges suggested")
        return {'FINISHED'}


class MESH_OT_seam_gen_accept(Operator):
    """Mark suggested edges as UV seams"""
    bl_idname = "mesh.seam_gen_accept"
    bl_label = "Accept Seams"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH' or context.mode != 'EDIT_MESH':
            return False
        return context.scene.seam_gen.is_analyzed

    def execute(self, context):
        obj = context.active_object
        sg = context.scene.seam_gen

        analyzer = get_analyzer()
        scores, seam_mask = analyzer.get_cached_results()

        if seam_mask is None:
            self.report({'WARNING'}, "No analysis results — run Analyze first")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()

        n_marked = 0
        for edge in bm.edges:
            if edge.index < len(seam_mask) and seam_mask[edge.index]:
                edge.seam = True
                n_marked += 1

        bmesh.update_edit_mesh(obj.data)

        # Clean up overlay
        overlay.disable_overlay()
        sg.is_analyzed = False
        sg.overlay_visible = False

        self.report({'INFO'}, f"{n_marked} seam edges marked")
        return {'FINISHED'}


class MESH_OT_seam_gen_accept_unwrap(Operator):
    """Mark suggested seams and unwrap the mesh"""
    bl_idname = "mesh.seam_gen_accept_unwrap"
    bl_label = "Accept & Unwrap"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH' or context.mode != 'EDIT_MESH':
            return False
        return context.scene.seam_gen.is_analyzed

    def execute(self, context):
        obj = context.active_object
        sg = context.scene.seam_gen

        analyzer = get_analyzer()
        scores, seam_mask = analyzer.get_cached_results()

        if seam_mask is None:
            self.report({'WARNING'}, "No analysis results — run Analyze first")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()

        n_marked = 0
        for edge in bm.edges:
            if edge.index < len(seam_mask) and seam_mask[edge.index]:
                edge.seam = True
                n_marked += 1

        bmesh.update_edit_mesh(obj.data)

        # Select all faces for unwrap
        bpy.ops.mesh.select_all(action='SELECT')

        # Unwrap
        try:
            bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
        except RuntimeError as e:
            self.report({'WARNING'}, f"Unwrap issue: {e}")

        # Clean up overlay
        overlay.disable_overlay()
        sg.is_analyzed = False
        sg.overlay_visible = False

        self.report({'INFO'}, f"{n_marked} seams marked and mesh unwrapped")
        return {'FINISHED'}


class MESH_OT_seam_gen_clear(Operator):
    """Clear seam suggestions and remove overlay"""
    bl_idname = "mesh.seam_gen_clear"
    bl_label = "Clear Suggestions"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return False
        sg = context.scene.seam_gen
        return sg.is_analyzed or sg.overlay_visible

    def execute(self, context):
        sg = context.scene.seam_gen

        overlay.disable_overlay()
        get_analyzer().invalidate()

        sg.is_analyzed = False
        sg.overlay_visible = False

        self.report({'INFO'}, "Suggestions cleared")
        return {'FINISHED'}


classes = (
    MESH_OT_seam_gen_analyze,
    MESH_OT_seam_gen_accept,
    MESH_OT_seam_gen_accept_unwrap,
    MESH_OT_seam_gen_clear,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
