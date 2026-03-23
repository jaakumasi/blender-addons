"""
GPU shader-based edge heatmap overlay in the 3D viewport.

Draws colored edges (green→yellow→red) to visualize seam suggestion scores.
"""

import numpy as np

import bpy
import gpu
from gpu_extras.batch import batch_for_shader

# Module-level state
_draw_handler = None
_cached_batch = None
_cached_shader = None


def _score_to_color(score):
    """Map a score [0, 1] to an RGBA color.

    0.0 = green (good seam location, low priority)
    0.5 = yellow (moderate)
    1.0 = red (strong seam candidate)
    """
    if score < 0.5:
        t = score * 2.0
        r = t * 0.9
        g = 0.8
        b = 0.0
    else:
        t = (score - 0.5) * 2.0
        r = 0.9
        g = 0.8 * (1.0 - t)
        b = 0.0

    a = 0.4 + score * 0.6  # More opaque for higher scores
    return (r, g, b, a)


def build_heatmap_data(obj, bm, edge_scores, min_score=0.1):
    """Build vertex positions and colors for the heatmap overlay.

    Args:
        obj: Blender object (for matrix_world transform)
        bm: BMesh object
        edge_scores: (E,) float64 array of scores
        min_score: minimum score to include (skip low-score edges)

    Returns (positions, colors) tuple of lists, or (None, None) if no edges.
    """
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    matrix = obj.matrix_world
    positions = []
    colors = []

    for edge in bm.edges:
        score = edge_scores[edge.index]
        if score < min_score:
            continue

        v1_world = matrix @ edge.verts[0].co
        v2_world = matrix @ edge.verts[1].co

        color = _score_to_color(score)

        positions.append((v1_world.x, v1_world.y, v1_world.z))
        positions.append((v2_world.x, v2_world.y, v2_world.z))
        colors.append(color)
        colors.append(color)

    if not positions:
        return None, None

    return positions, colors


def _draw_callback():
    """Draw function registered with SpaceView3D."""
    global _cached_batch, _cached_shader

    if _cached_batch is None or _cached_shader is None:
        return

    # Save GPU state
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.line_width_set(3.0)

    _cached_shader.bind()
    _cached_batch.draw(_cached_shader)

    # Restore GPU state
    gpu.state.line_width_set(1.0)
    gpu.state.depth_test_set('NONE')
    gpu.state.blend_set('NONE')


def enable_overlay(obj, bm, edge_scores, min_score=0.1):
    """Build batch and register draw handler.

    Args:
        obj: Blender object
        bm: BMesh object
        edge_scores: (E,) float64 array
        min_score: minimum score threshold for display
    """
    global _draw_handler, _cached_batch, _cached_shader

    # Remove existing handler if any
    disable_overlay()

    positions, colors = build_heatmap_data(obj, bm, edge_scores, min_score)
    if positions is None:
        return

    _cached_shader = gpu.shader.from_builtin('SMOOTH_COLOR')
    _cached_batch = batch_for_shader(
        _cached_shader, 'LINES',
        {"pos": positions, "color": colors}
    )

    _draw_handler = bpy.types.SpaceView3D.draw_handler_add(
        _draw_callback, (), 'WINDOW', 'POST_VIEW'
    )

    # Force viewport redraw
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


def update_overlay(obj, bm, edge_scores, min_score=0.1):
    """Rebuild batch without removing/re-adding the draw handler."""
    global _cached_batch, _cached_shader

    if _draw_handler is None:
        enable_overlay(obj, bm, edge_scores, min_score)
        return

    positions, colors = build_heatmap_data(obj, bm, edge_scores, min_score)
    if positions is None:
        disable_overlay()
        return

    if _cached_shader is None:
        _cached_shader = gpu.shader.from_builtin('SMOOTH_COLOR')

    _cached_batch = batch_for_shader(
        _cached_shader, 'LINES',
        {"pos": positions, "color": colors}
    )

    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


def disable_overlay():
    """Remove draw handler and free resources."""
    global _draw_handler, _cached_batch, _cached_shader

    if _draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
        _draw_handler = None

    _cached_batch = None
    _cached_shader = None

    # Force viewport redraw
    try:
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    except (AttributeError, RuntimeError):
        pass


def is_overlay_active():
    """Check if the overlay draw handler is currently registered."""
    return _draw_handler is not None
