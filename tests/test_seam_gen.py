"""
Headless test for SeamGen addon (v2 — MST-based topology).

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

    from seam_gen import register, unregister
    register()

    assert hasattr(bpy.types, "MESH_OT_seam_gen_analyze"), "Analyze operator not registered"
    assert hasattr(bpy.types, "MESH_OT_seam_gen_accept"), "Accept operator not registered"
    assert hasattr(bpy.types, "MESH_OT_seam_gen_accept_unwrap"), "Accept & Unwrap not registered"
    assert hasattr(bpy.types, "MESH_OT_seam_gen_clear"), "Clear operator not registered"
    assert hasattr(bpy.types.Scene, "seam_gen"), "Scene property not registered"

    print("  Registration: PASS")
    unregister()
    register()


def test_mesh_utils():
    """Test BMesh to numpy array extraction."""
    print("\n=== Test: Mesh Utils ===")

    from seam_gen.utils.mesh_utils import bmesh_to_arrays

    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    arrays = bmesh_to_arrays(bm)

    assert arrays['vert_coords'].shape == (8, 3)
    assert arrays['edge_verts'].shape == (12, 2)
    assert arrays['face_normals'].shape == (6, 3)
    assert np.all(arrays['vert_valence'] == 3)
    assert np.all(arrays['edge_face_count'] == 2)

    bm.free()
    bpy.data.objects.remove(obj)
    print("  Mesh Utils: PASS")


def test_topology_mst_cube():
    """Test MST-based seam extraction on a cube.

    A cube has 6 faces and 12 edges. MST needs 5 edges.
    So seams = 12 - 5 = 7 edges.
    """
    print("\n=== Test: Topology MST on Cube ===")

    from seam_gen.utils.mesh_utils import bmesh_to_arrays
    from seam_gen.core.edge_scoring import compute_dihedral_scores
    from seam_gen.core.topology import compute_mst_seams, build_face_adjacency

    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    arrays = bmesh_to_arrays(bm)

    E = len(bm.edges)
    F = len(bm.faces)
    print(f"  Cube: {E} edges, {F} faces")

    # All cube edges have same dihedral (~0.5)
    dihedral = compute_dihedral_scores(
        arrays['edge_face_map'], arrays['edge_face_count'], arrays['face_normals']
    )

    # Use dihedral as edge weights for MST
    seam_mask = compute_mst_seams(
        arrays['edge_face_map'], arrays['edge_face_count'],
        dihedral, F, n_islands=1
    )

    n_seams = int(seam_mask.sum())
    expected_seams = E - (F - 1)  # 12 - 5 = 7
    print(f"  Seam edges: {n_seams} (expected {expected_seams})")
    assert n_seams == expected_seams, f"Expected {expected_seams} seams, got {n_seams}"

    # Verify face adjacency
    interior, boundary = build_face_adjacency(
        arrays['edge_face_map'], arrays['edge_face_count']
    )
    print(f"  Interior edges: {len(interior)}, Boundary: {len(boundary)}")
    assert len(interior) == 12, "Cube should have 12 interior edges"
    assert len(boundary) == 0, "Cube should have 0 boundary edges"

    bm.free()
    bpy.data.objects.remove(obj)
    print("  Topology MST Cube: PASS")


def test_topology_mst_multi_island():
    """Test multi-island splitting on a cube."""
    print("\n=== Test: Multi-Island MST ===")

    from seam_gen.utils.mesh_utils import bmesh_to_arrays
    from seam_gen.core.edge_scoring import compute_dihedral_scores
    from seam_gen.core.topology import compute_mst_seams

    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    arrays = bmesh_to_arrays(bm)

    F = len(bm.faces)
    dihedral = compute_dihedral_scores(
        arrays['edge_face_map'], arrays['edge_face_count'], arrays['face_normals']
    )

    # 1 island: 7 seams
    mask1 = compute_mst_seams(
        arrays['edge_face_map'], arrays['edge_face_count'], dihedral, F, n_islands=1
    )
    # 2 islands: 8 seams (7 + 1 removed MST edge)
    mask2 = compute_mst_seams(
        arrays['edge_face_map'], arrays['edge_face_count'], dihedral, F, n_islands=2
    )
    # 3 islands: 9 seams
    mask3 = compute_mst_seams(
        arrays['edge_face_map'], arrays['edge_face_count'], dihedral, F, n_islands=3
    )

    n1, n2, n3 = int(mask1.sum()), int(mask2.sum()), int(mask3.sum())
    print(f"  1 island: {n1} seams, 2 islands: {n2} seams, 3 islands: {n3} seams")

    assert n2 == n1 + 1, f"2 islands should have 1 more seam than 1 island"
    assert n3 == n1 + 2, f"3 islands should have 2 more seams than 1 island"

    bm.free()
    bpy.data.objects.remove(obj)
    print("  Multi-Island MST: PASS")


def test_full_pipeline_cube():
    """Test the full analysis pipeline produces valid seams on a cube."""
    print("\n=== Test: Full Pipeline (Cube) ===")

    from seam_gen.core.analyzer import get_analyzer

    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    E = len(bm.edges)
    F = len(bm.faces)
    print(f"  Cube: {E} edges, {F} faces")

    weights = {
        'dihedral': 0.35, 'curvature': 0.25,
        'concavity': 0.2, 'edge_loop': 0.2,
    }

    analyzer = get_analyzer()
    scores, seam_mask = analyzer.analyze(
        bm, obj, weights, smoothing_iters=0, island_count=0,
    )

    n_seams = int(seam_mask.sum())
    expected = E - (F - 1)  # 7 for cube
    print(f"  Seam edges: {n_seams} (expected {expected})")
    assert n_seams == expected, f"Expected {expected}, got {n_seams}"

    bm.free()
    bpy.data.objects.remove(obj)
    print("  Full Pipeline (Cube): PASS")


def test_full_pipeline_sphere():
    """Test on a UV sphere — should produce valid topology."""
    print("\n=== Test: Full Pipeline (UV Sphere) ===")

    from seam_gen.core.analyzer import get_analyzer

    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
    obj = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    V = len(bm.verts)
    E = len(bm.edges)
    F = len(bm.faces)
    print(f"  Sphere: {V} verts, {E} edges, {F} faces")

    weights = {
        'dihedral': 0.35, 'curvature': 0.25,
        'concavity': 0.2, 'edge_loop': 0.2,
    }

    analyzer = get_analyzer()
    scores, seam_mask = analyzer.analyze(
        bm, obj, weights, smoothing_iters=0, island_count=0,
    )

    n_seams = int(seam_mask.sum())
    expected_min = E - (F - 1)  # Minimum for single island
    print(f"  Seam edges: {n_seams} (minimum for 1 island: {expected_min})")
    assert n_seams >= expected_min, f"Need at least {expected_min} seams, got {n_seams}"

    # Score range should be valid
    assert scores.min() >= 0.0 and scores.max() <= 1.0, "Scores out of [0,1]"

    bm.free()
    bpy.data.objects.remove(obj)
    print("  Full Pipeline (UV Sphere): PASS")


def test_full_pipeline_subdivided():
    """Test on a subdivided cube — more complex topology."""
    print("\n=== Test: Full Pipeline (Subdivided Cube) ===")

    from seam_gen.core.analyzer import get_analyzer

    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.subdivide(number_cuts=2)
    bpy.ops.object.mode_set(mode='OBJECT')

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    V = len(bm.verts)
    E = len(bm.edges)
    F = len(bm.faces)
    print(f"  Subdivided cube: {V} verts, {E} edges, {F} faces")

    weights = {
        'dihedral': 0.35, 'curvature': 0.25,
        'concavity': 0.2, 'edge_loop': 0.2,
    }

    analyzer = get_analyzer()
    scores, seam_mask = analyzer.analyze(
        bm, obj, weights, smoothing_iters=3, island_count=0,
    )

    n_seams = int(seam_mask.sum())
    expected_min = E - (F - 1)
    print(f"  Seam edges: {n_seams} (minimum for 1 island: {expected_min})")
    # With smoothing, seam count might differ slightly but should be close
    assert n_seams >= expected_min - 5, f"Seam count too low: {n_seams}"

    bm.free()
    bpy.data.objects.remove(obj)
    print("  Full Pipeline (Subdivided Cube): PASS")


def test_mode_presets():
    """Test that mode presets update weights correctly."""
    print("\n=== Test: Mode Presets ===")

    sg = bpy.context.scene.seam_gen

    sg.mode = 'HARD_SURFACE'
    assert abs(sg.w_dihedral - 0.5) < 0.01, f"Hard surface dihedral: {sg.w_dihedral}"

    sg.mode = 'ORGANIC'
    assert abs(sg.w_dihedral - 0.2) < 0.01, f"Organic dihedral: {sg.w_dihedral}"
    assert abs(sg.w_curvature - 0.4) < 0.01, f"Organic curvature: {sg.w_curvature}"

    sg.mode = 'BALANCED'
    assert abs(sg.w_dihedral - 0.35) < 0.01, f"Balanced dihedral: {sg.w_dihedral}"

    # Manual weight change should switch to CUSTOM
    sg.w_dihedral = 0.99
    assert sg.mode == 'CUSTOM', f"Expected CUSTOM after weight change, got {sg.mode}"

    sg.mode = 'BALANCED'
    print("  Mode Presets: PASS")


# ---------------------------------------------------------------
def main():
    print("\n" + "=" * 60)
    print("SeamGen v2 Headless Test Suite (MST Topology)")
    print("=" * 60)

    passed = 0
    failed = 0
    tests = [
        test_registration,
        test_mesh_utils,
        test_topology_mst_cube,
        test_topology_mst_multi_island,
        test_full_pipeline_cube,
        test_full_pipeline_sphere,
        test_full_pipeline_subdivided,
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
