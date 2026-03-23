"""
Headless test for SeamGen addon (v3 — MST + AO visibility + segmentation).

Run with:
  blender.exe -b --python tests/test_seam_gen.py
"""

import sys
import os
import traceback
import time

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
    assert hasattr(bpy.types.Scene, "seam_gen"), "Scene property not registered"

    # Verify new v3 properties exist
    sg = bpy.context.scene.seam_gen
    assert hasattr(sg, "w_visibility"), "Missing w_visibility property"
    assert hasattr(sg, "w_segmentation"), "Missing w_segmentation property"
    assert hasattr(sg, "ao_samples"), "Missing ao_samples property"

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

    bm.free()
    bpy.data.objects.remove(obj)
    print("  Mesh Utils: PASS")


def test_ao_visibility_cube():
    """Test AO visibility on a cube — should be roughly uniform."""
    print("\n=== Test: AO Visibility (Cube) ===")

    from seam_gen.utils.mesh_utils import bmesh_to_arrays
    from seam_gen.core.visibility import compute_ao_scores

    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    arrays = bmesh_to_arrays(bm)

    t0 = time.time()
    ao = compute_ao_scores(bm, arrays['vert_coords'], arrays['edge_verts'], n_samples=16)
    elapsed = time.time() - t0

    print(f"  AO range: [{ao.min():.3f}, {ao.max():.3f}], mean: {ao.mean():.3f}")
    print(f"  AO computation: {elapsed:.3f}s")

    assert ao.shape == (12,), f"Expected (12,), got {ao.shape}"
    assert ao.min() >= 0.0, "AO scores below 0"
    assert ao.max() <= 1.0, "AO scores above 1"

    bm.free()
    bpy.data.objects.remove(obj)
    print("  AO Visibility (Cube): PASS")


def test_ao_visibility_sphere():
    """Test AO on a UV sphere — bottom/interior should be more occluded."""
    print("\n=== Test: AO Visibility (Sphere) ===")

    from seam_gen.utils.mesh_utils import bmesh_to_arrays
    from seam_gen.core.visibility import compute_ao_scores

    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
    obj = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    arrays = bmesh_to_arrays(bm)

    t0 = time.time()
    ao = compute_ao_scores(bm, arrays['vert_coords'], arrays['edge_verts'], n_samples=16)
    elapsed = time.time() - t0

    print(f"  Sphere AO range: [{ao.min():.3f}, {ao.max():.3f}], mean: {ao.mean():.3f}")
    print(f"  AO computation ({len(arrays['vert_coords'])} verts): {elapsed:.3f}s")

    assert ao.shape[0] == len(arrays['edge_verts']), "AO shape mismatch"
    assert ao.min() >= 0.0 and ao.max() <= 1.0, "AO out of range"

    bm.free()
    bpy.data.objects.remove(obj)
    print("  AO Visibility (Sphere): PASS")


def test_topology_mst_cube():
    """Test MST seam extraction on a cube — 7 seams expected."""
    print("\n=== Test: Topology MST on Cube ===")

    from seam_gen.utils.mesh_utils import bmesh_to_arrays
    from seam_gen.core.edge_scoring import compute_dihedral_scores
    from seam_gen.core.topology import compute_mst_seams

    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    arrays = bmesh_to_arrays(bm)

    E = len(bm.edges)
    F = len(bm.faces)

    dihedral = compute_dihedral_scores(
        arrays['edge_face_map'], arrays['edge_face_count'], arrays['face_normals']
    )
    seam_mask = compute_mst_seams(
        arrays['edge_face_map'], arrays['edge_face_count'],
        dihedral, F, n_islands=1
    )

    n_seams = int(seam_mask.sum())
    expected = E - (F - 1)
    print(f"  Seam edges: {n_seams} (expected {expected})")
    assert n_seams == expected

    bm.free()
    bpy.data.objects.remove(obj)
    print("  Topology MST Cube: PASS")


def test_full_pipeline_cube():
    """Test full v3 pipeline on a cube."""
    print("\n=== Test: Full Pipeline v3 (Cube) ===")

    from seam_gen.core.analyzer import get_analyzer

    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    E = len(bm.edges)
    F = len(bm.faces)

    weights = {
        'dihedral': 0.2, 'curvature': 0.15, 'concavity': 0.15,
        'edge_loop': 0.1, 'visibility': 0.25, 'segmentation': 0.15,
    }

    analyzer = get_analyzer()
    scores, seam_mask = analyzer.analyze(
        bm, obj, weights, smoothing_iters=0, island_count=0, ao_samples=8,
    )

    n_seams = int(seam_mask.sum())
    expected = E - (F - 1)
    print(f"  Cube: {E} edges, {F} faces, {n_seams} seams (expected {expected})")
    assert n_seams == expected

    bm.free()
    bpy.data.objects.remove(obj)
    print("  Full Pipeline v3 (Cube): PASS")


def test_full_pipeline_suzanne():
    """Test on Suzanne (monkey head) — the real organic test."""
    print("\n=== Test: Full Pipeline v3 (Suzanne) ===")

    from seam_gen.core.analyzer import get_analyzer

    bpy.ops.mesh.primitive_monkey_add()
    obj = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    V = len(bm.verts)
    E = len(bm.edges)
    F = len(bm.faces)
    print(f"  Suzanne: {V} verts, {E} edges, {F} faces")

    weights = {
        'dihedral': 0.2, 'curvature': 0.15, 'concavity': 0.15,
        'edge_loop': 0.1, 'visibility': 0.25, 'segmentation': 0.15,
    }

    t0 = time.time()
    analyzer = get_analyzer()
    scores, seam_mask = analyzer.analyze(
        bm, obj, weights, smoothing_iters=3, island_count=0, ao_samples=8,
    )
    elapsed = time.time() - t0

    n_seams = int(seam_mask.sum())
    expected_min = E - (F - 1)
    print(f"  Seam edges: {n_seams} (minimum: {expected_min})")
    print(f"  Total analysis time: {elapsed:.2f}s")

    assert n_seams >= expected_min, f"Too few seams: {n_seams} < {expected_min}"
    assert scores.min() >= 0.0 and scores.max() <= 1.0

    bm.free()
    bpy.data.objects.remove(obj)
    print("  Full Pipeline v3 (Suzanne): PASS")


def test_mode_presets():
    """Test that mode presets update all 6 weights correctly."""
    print("\n=== Test: Mode Presets (v3) ===")

    sg = bpy.context.scene.seam_gen

    sg.mode = 'ORGANIC'
    assert abs(sg.w_visibility - 0.3) < 0.01, f"Organic visibility: {sg.w_visibility}"
    assert abs(sg.w_dihedral - 0.1) < 0.01, f"Organic dihedral: {sg.w_dihedral}"

    sg.mode = 'HARD_SURFACE'
    assert abs(sg.w_dihedral - 0.35) < 0.01, f"Hard surface dihedral: {sg.w_dihedral}"

    sg.mode = 'BALANCED'
    assert abs(sg.w_visibility - 0.25) < 0.01, f"Balanced visibility: {sg.w_visibility}"
    assert abs(sg.w_segmentation - 0.15) < 0.01, f"Balanced segmentation: {sg.w_segmentation}"

    # Custom detection
    sg.w_visibility = 0.99
    assert sg.mode == 'CUSTOM', f"Expected CUSTOM, got {sg.mode}"

    sg.mode = 'BALANCED'
    print("  Mode Presets (v3): PASS")


# ---------------------------------------------------------------
def main():
    print("\n" + "=" * 60)
    print("SeamGen v3 Headless Test Suite (MST + AO Visibility)")
    print("=" * 60)

    passed = 0
    failed = 0
    tests = [
        test_registration,
        test_mesh_utils,
        test_ao_visibility_cube,
        test_ao_visibility_sphere,
        test_topology_mst_cube,
        test_full_pipeline_cube,
        test_full_pipeline_suzanne,
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
