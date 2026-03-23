"""
Headless test for SeamGen addon.

Run with:
  blender.exe -b --python tests/test_seam_gen.py
"""

import sys
import os
import traceback

# Add addons directory to path
addon_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "addons")
if addon_dir not in sys.path:
    sys.path.insert(0, addon_dir)

import bpy
import bmesh
import numpy as np


def test_registration():
    """Test that addon registers correctly."""
    print("\n=== Test: Registration ===")

    # Register manually
    from seam_gen import register, unregister
    register()

    # Check operators
    assert hasattr(bpy.types, "MESH_OT_seam_gen_analyze"), "Analyze operator not registered"
    assert hasattr(bpy.types, "MESH_OT_seam_gen_accept"), "Accept operator not registered"
    assert hasattr(bpy.types, "MESH_OT_seam_gen_accept_unwrap"), "Accept & Unwrap not registered"
    assert hasattr(bpy.types, "MESH_OT_seam_gen_clear"), "Clear operator not registered"

    # Check properties
    assert hasattr(bpy.types.Scene, "seam_gen"), "Scene property not registered"

    print("  Registration: PASS")

    # Clean up
    unregister()
    register()  # Re-register for further tests


def test_mesh_utils():
    """Test BMesh to numpy array extraction."""
    print("\n=== Test: Mesh Utils ===")

    from seam_gen.utils.mesh_utils import bmesh_to_arrays, compute_mixed_voronoi_areas

    # Create a cube
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    arrays = bmesh_to_arrays(bm)

    assert arrays['vert_coords'].shape == (8, 3), f"Expected (8,3), got {arrays['vert_coords'].shape}"
    assert arrays['edge_verts'].shape == (12, 2), f"Expected (12,2), got {arrays['edge_verts'].shape}"
    assert arrays['face_normals'].shape == (6, 3), f"Expected (6,3), got {arrays['face_normals'].shape}"
    assert arrays['face_centroids'].shape == (6, 3), f"Expected (6,3), got {arrays['face_centroids'].shape}"
    assert len(arrays['edge_face_map']) == 12, f"Expected 12 edge_face entries"
    assert arrays['edge_face_count'].shape == (12,), f"Expected (12,)"
    assert arrays['vert_valence'].shape == (8,), f"Expected (8,)"

    # All cube vertices should have valence 3
    assert np.all(arrays['vert_valence'] == 3), f"Cube valence: {arrays['vert_valence']}"

    # All cube edges should have 2 adjacent faces
    assert np.all(arrays['edge_face_count'] == 2), f"Edge face count: {arrays['edge_face_count']}"

    # Mixed Voronoi areas should all be positive
    areas = compute_mixed_voronoi_areas(bm, arrays['vert_coords'])
    assert np.all(areas > 0), f"Some areas are non-positive"

    bm.free()
    bpy.data.objects.remove(obj)
    print("  Mesh Utils: PASS")


def test_dihedral_scoring():
    """Test dihedral angle scoring on a cube (all 90-degree angles)."""
    print("\n=== Test: Dihedral Scoring ===")

    from seam_gen.utils.mesh_utils import bmesh_to_arrays
    from seam_gen.core.edge_scoring import compute_dihedral_scores

    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    arrays = bmesh_to_arrays(bm)

    scores = compute_dihedral_scores(
        arrays['edge_face_map'],
        arrays['edge_face_count'],
        arrays['face_normals']
    )

    # Cube edges are 90 degrees = pi/2, so score should be ~0.5
    assert scores.shape == (12,), f"Expected (12,), got {scores.shape}"
    expected = 0.5  # 90 degrees / 180 degrees
    for i, s in enumerate(scores):
        assert abs(s - expected) < 0.05, f"Edge {i}: expected ~{expected}, got {s}"

    bm.free()
    bpy.data.objects.remove(obj)
    print(f"  Dihedral Scoring: PASS (all scores ~{expected})")


def test_curvature():
    """Test curvature computation on a UV sphere."""
    print("\n=== Test: Curvature ===")

    from seam_gen.utils.mesh_utils import bmesh_to_arrays, compute_mixed_voronoi_areas
    from seam_gen.core.curvature import (
        compute_gaussian_curvature,
        compute_mean_curvature,
        compute_edge_curvature_scores,
    )

    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
    obj = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    arrays = bmesh_to_arrays(bm)

    mixed_areas = compute_mixed_voronoi_areas(bm, arrays['vert_coords'])
    gaussian = compute_gaussian_curvature(bm, arrays['vert_coords'], mixed_areas)
    mean_curv = compute_mean_curvature(bm, arrays['vert_coords'], mixed_areas)

    V = len(bm.verts)
    assert gaussian.shape == (V,), f"Expected ({V},), got {gaussian.shape}"
    assert mean_curv.shape == (V,), f"Expected ({V},), got {mean_curv.shape}"

    # Gaussian curvature should be positive on a sphere (convex everywhere)
    # Poles might have extreme values, but most vertices should be positive
    positive_ratio = np.mean(gaussian > 0)
    print(f"  Gaussian K > 0: {positive_ratio*100:.0f}% of vertices")
    assert positive_ratio > 0.7, f"Expected most vertices to have K>0 on sphere"

    # Mean curvature should be positive on a sphere
    positive_H_ratio = np.mean(mean_curv > 0)
    print(f"  Mean H > 0: {positive_H_ratio*100:.0f}% of vertices")

    edge_scores = compute_edge_curvature_scores(
        arrays['vert_coords'], arrays['edge_verts'], gaussian, mean_curv
    )
    assert edge_scores.min() >= 0 and edge_scores.max() <= 1.0, "Scores out of [0,1]"

    bm.free()
    bpy.data.objects.remove(obj)
    print("  Curvature: PASS")


def test_segmentation():
    """Test mesh segmentation on a cube."""
    print("\n=== Test: Segmentation ===")

    from seam_gen.utils.mesh_utils import bmesh_to_arrays
    from seam_gen.core.segmentation import compute_segmentation_scores

    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    arrays = bmesh_to_arrays(bm)

    scores = compute_segmentation_scores(
        bm, arrays['vert_coords'], arrays['edge_verts'],
        arrays['edge_face_map'], arrays['edge_face_count'],
        arrays['face_normals'], n_segments=2,
    )

    assert scores.shape == (12,), f"Expected (12,), got {scores.shape}"
    # Some edges should be boundary (score=1.0)
    boundary_count = np.sum(scores > 0.5)
    print(f"  Boundary edges: {boundary_count} out of 12")
    assert boundary_count > 0, "Expected some boundary edges"

    bm.free()
    bpy.data.objects.remove(obj)
    print("  Segmentation: PASS")


def test_full_pipeline():
    """Test the full analysis pipeline on a subdivided cube."""
    print("\n=== Test: Full Pipeline ===")

    from seam_gen.core.analyzer import get_analyzer

    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object

    # Subdivide for more interesting topology
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.subdivide(number_cuts=2)
    bpy.ops.object.mode_set(mode='OBJECT')

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    V = len(bm.verts)
    E = len(bm.edges)
    F = len(bm.faces)
    print(f"  Mesh: {V} verts, {E} edges, {F} faces")

    weights = {
        'dihedral': 0.3,
        'curvature': 0.2,
        'segmentation': 0.25,
        'concavity': 0.1,
        'edge_loop': 0.15,
    }

    analyzer = get_analyzer()
    scores, seam_mask = analyzer.analyze(
        bm, obj, weights,
        threshold=0.5,
        smoothing_iters=3,
        segment_count=0,
    )

    assert scores.shape == (E,), f"Scores shape: {scores.shape}"
    assert seam_mask.shape == (E,), f"Mask shape: {seam_mask.shape}"
    assert scores.min() >= 0.0 and scores.max() <= 1.0, "Scores out of range"

    n_seams = int(seam_mask.sum())
    print(f"  Suggested seams: {n_seams} out of {E} edges")
    print(f"  Score range: [{scores.min():.3f}, {scores.max():.3f}]")
    print(f"  Score mean: {scores.mean():.3f}")

    assert n_seams > 0, "Expected at least some seam suggestions"
    assert n_seams < E, "Expected fewer seams than total edges"

    # Test threshold sensitivity
    _, mask_low = analyzer.analyze(bm, obj, weights, threshold=0.1, smoothing_iters=3, segment_count=0)
    _, mask_high = analyzer.analyze(bm, obj, weights, threshold=0.9, smoothing_iters=3, segment_count=0)

    low_count = int(mask_low.sum())
    high_count = int(mask_high.sum())
    print(f"  Threshold 0.1: {low_count} seams")
    print(f"  Threshold 0.5: {n_seams} seams")
    print(f"  Threshold 0.9: {high_count} seams")
    assert low_count >= n_seams >= high_count, "Seam count should decrease with higher threshold"

    bm.free()
    bpy.data.objects.remove(obj)
    print("  Full Pipeline: PASS")


def test_mode_presets():
    """Test that mode presets update weights correctly."""
    print("\n=== Test: Mode Presets ===")

    sg = bpy.context.scene.seam_gen

    sg.mode = 'HARD_SURFACE'
    assert abs(sg.w_dihedral - 0.5) < 0.01, f"Hard surface dihedral: {sg.w_dihedral}"
    assert abs(sg.w_curvature - 0.1) < 0.01, f"Hard surface curvature: {sg.w_curvature}"

    sg.mode = 'ORGANIC'
    assert abs(sg.w_dihedral - 0.2) < 0.01, f"Organic dihedral: {sg.w_dihedral}"
    assert abs(sg.w_curvature - 0.3) < 0.01, f"Organic curvature: {sg.w_curvature}"

    sg.mode = 'BALANCED'
    assert abs(sg.w_dihedral - 0.3) < 0.01, f"Balanced dihedral: {sg.w_dihedral}"

    # Manually changing a weight should switch to CUSTOM
    sg.w_dihedral = 0.99
    assert sg.mode == 'CUSTOM', f"Expected CUSTOM mode after weight change, got {sg.mode}"

    # Reset
    sg.mode = 'BALANCED'
    print("  Mode Presets: PASS")


# ---------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------

def main():
    print("\n" + "=" * 60)
    print("SeamGen Headless Test Suite")
    print("=" * 60)

    passed = 0
    failed = 0
    tests = [
        test_registration,
        test_mesh_utils,
        test_dihedral_scoring,
        test_curvature,
        test_segmentation,
        test_full_pipeline,
        test_mode_presets,
    ]

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


main()
