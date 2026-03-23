"""
Main mesh analysis orchestrator.

Runs the full analysis pipeline, combines signals, and caches results
for fast parameter tuning.
"""

import hashlib
import numpy as np
import bmesh

from ..utils.mesh_utils import bmesh_to_arrays, compute_mixed_voronoi_areas
from . import edge_scoring
from . import curvature
from . import segmentation
from . import seam_paths


class MeshAnalyzer:
    """Orchestrates the seam suggestion pipeline with result caching."""

    def __init__(self):
        self._cache_key = None

        # Cached per-signal scores (reusable across weight changes)
        self._dihedral = None
        self._curvature_scores = None
        self._segmentation_scores = None
        self._concavity = None
        self._edge_loop = None

        # Cached final results
        self._combined_scores = None
        self._seam_mask = None
        self._arrays = None

    def analyze(self, bm, obj, weights, threshold, smoothing_iters,
                segment_count, progress_callback=None):
        """Run full analysis pipeline.

        Args:
            bm: BMesh in edit mode
            obj: Blender object (for matrix_world in overlay)
            weights: dict with keys 'dihedral', 'curvature', 'segmentation',
                     'concavity', 'edge_loop'
            threshold: float seam threshold [0, 1]
            smoothing_iters: int path smoothing iterations
            segment_count: int target segments (0=auto)
            progress_callback: optional callable(stage_name, fraction)

        Returns (edge_scores, seam_mask) tuple of numpy arrays.
        """
        def progress(name, frac):
            if progress_callback:
                progress_callback(name, frac)

        # Check cache — if mesh unchanged, skip signal computation
        cache_key = self._compute_cache_key(bm)
        signals_cached = (cache_key == self._cache_key and self._dihedral is not None)

        if not signals_cached:
            self._cache_key = cache_key

            # Step 1: Extract numpy arrays
            progress("Extracting mesh data", 0.05)
            arrays = bmesh_to_arrays(bm)
            self._arrays = arrays

            vert_coords = arrays['vert_coords']
            edge_verts = arrays['edge_verts']
            face_normals = arrays['face_normals']
            face_centroids = arrays['face_centroids']
            edge_face_map = arrays['edge_face_map']
            edge_face_count = arrays['edge_face_count']
            vert_valence = arrays['vert_valence']

            # Step 2: Dihedral angle scores
            progress("Computing dihedral angles", 0.10)
            self._dihedral = edge_scoring.compute_dihedral_scores(
                edge_face_map, edge_face_count, face_normals
            )

            # Step 3: Curvature scores
            progress("Computing curvature", 0.25)
            mixed_areas = compute_mixed_voronoi_areas(bm, vert_coords)
            gaussian = curvature.compute_gaussian_curvature(bm, vert_coords, mixed_areas)
            mean_curv = curvature.compute_mean_curvature(bm, vert_coords, mixed_areas)
            self._curvature_scores = curvature.compute_edge_curvature_scores(
                vert_coords, edge_verts, gaussian, mean_curv
            )

            # Step 4: Segmentation
            progress("Segmenting mesh", 0.45)
            self._segmentation_scores = segmentation.compute_segmentation_scores(
                bm, vert_coords, edge_verts, edge_face_map,
                edge_face_count, face_normals, n_segments=segment_count
            )

            # Step 5: Concavity + edge loop alignment
            progress("Analyzing concavity and edge flow", 0.70)
            self._concavity = edge_scoring.compute_concavity_scores(
                edge_face_map, edge_face_count, edge_verts,
                vert_coords, face_normals, face_centroids
            )
            self._edge_loop = edge_scoring.compute_edge_loop_alignment(
                vert_valence, edge_verts
            )
        else:
            progress("Using cached signals", 0.70)

        # Step 6: Combined scoring (always recomputed — fast)
        progress("Combining scores", 0.80)
        self._combined_scores = edge_scoring.compute_combined_scores(
            self._dihedral,
            self._curvature_scores,
            self._segmentation_scores,
            self._concavity,
            self._edge_loop,
            weights,
        )

        # Step 7: Threshold + path optimization
        progress("Optimizing seam paths", 0.90)
        arrays = self._arrays
        mask = seam_paths.threshold_edges(self._combined_scores, threshold)

        mask = seam_paths.smooth_seam_paths(
            bm, mask, self._combined_scores,
            arrays['edge_verts'], iterations=smoothing_iters
        )

        mask = seam_paths.follow_edge_loops(
            bm, mask, self._combined_scores,
            arrays['edge_verts'], arrays['vert_valence']
        )

        mask = seam_paths.ensure_connected_islands(
            bm, mask, arrays['edge_verts'], self._combined_scores
        )

        self._seam_mask = mask

        progress("Done", 1.0)
        return self._combined_scores, self._seam_mask

    def get_cached_results(self):
        """Return cached (scores, seam_mask) or (None, None)."""
        if self._combined_scores is not None and self._seam_mask is not None:
            return self._combined_scores, self._seam_mask
        return None, None

    def get_cached_arrays(self):
        """Return cached mesh arrays or None."""
        return self._arrays

    def invalidate(self):
        """Clear all caches."""
        self._cache_key = None
        self._dihedral = None
        self._curvature_scores = None
        self._segmentation_scores = None
        self._concavity = None
        self._edge_loop = None
        self._combined_scores = None
        self._seam_mask = None
        self._arrays = None

    def _compute_cache_key(self, bm):
        """Compute a hash of the mesh topology + positions for cache invalidation."""
        bm.verts.ensure_lookup_table()
        # Hash vertex count + edge count + a sample of vertex positions
        V = len(bm.verts)
        E = len(bm.edges)
        F = len(bm.faces)

        hasher = hashlib.md5()
        hasher.update(f"{V}:{E}:{F}".encode())

        # Sample some vertex positions for change detection
        step = max(1, V // 100)
        for i in range(0, V, step):
            co = bm.verts[i].co
            hasher.update(f"{co.x:.6f},{co.y:.6f},{co.z:.6f}".encode())

        return hasher.hexdigest()


# Module-level singleton
_analyzer = MeshAnalyzer()


def get_analyzer():
    """Get the module-level analyzer singleton."""
    return _analyzer
