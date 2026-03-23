"""
Main mesh analysis orchestrator.

Pipeline (v4):
1. Extract numpy arrays from BMesh (cached per mesh topology).
2. Compute 7 geometric/visibility signals (all cached):
   - Dihedral angles, curvature, concavity, edge loops
   - AO visibility (BVHTree raycasting)
   - Segmentation boundaries (spectral / region growing)
   - Face-normal clustering (new — hard-surface panel detection)
3. Combine into a weighted "seam desirability" score per edge.
4. Genus detection + tree-cotree homology loop cutting (new — fixes torus etc.).
5. Layout-aware Prim's spanning tree seam extraction (replaces Kruskal's —
   fixes cube / cylinder unfolding on uniform meshes).
6. Optional distortion feedback: adaptively split high-distortion charts.
7. Multi-stage seam path smoothing (zig-zag, geodesic re-routing, fragment cleanup).
"""

import hashlib
import numpy as np

from ..utils.mesh_utils import bmesh_to_arrays, compute_mixed_voronoi_areas
from . import edge_scoring
from . import curvature
from . import visibility
from . import segmentation
from . import topology
from . import seam_paths
from . import genus as genus_mod
from . import normal_clustering
from . import distortion as distortion_mod


class MeshAnalyzer:
    """Orchestrates the seam suggestion pipeline with result caching."""

    def __init__(self):
        self._cache_key = None

        # Cached per-signal scores (reusable across weight changes)
        self._dihedral = None
        self._curvature_scores = None
        self._concavity = None
        self._edge_loop = None
        self._visibility = None
        self._segmentation = None
        self._normal_cluster = None   # new signal

        # Cached final results
        self._combined_scores = None
        self._seam_mask = None
        self._arrays = None
        self._n_faces = 0

    def analyze(self, bm, obj, weights, smoothing_iters,
                island_count=0, ao_samples=16,
                layout_bias=0.35,
                normal_cluster_angle=30.0,
                use_genus_cuts=True,
                use_distortion_split=True,
                distortion_threshold=0.55,
                progress_callback=None):
        """Run the full analysis pipeline.

        Args:
            bm:                    BMesh in Edit Mode.
            obj:                   Active Blender object.
            weights:               dict — keys for all 7 signal weights.
            smoothing_iters:       int — seam path smoothing passes.
            island_count:          int — target UV islands (0 = automatic).
            ao_samples:            int — AO rays per vertex (4–64).
            layout_bias:           float — Prim's depth penalty (0–1).
            normal_cluster_angle:  float — normal-cluster angle threshold (°).
            use_genus_cuts:        bool — detect genus and add homology seams.
            use_distortion_split:  bool — adaptively split high-distortion charts.
            distortion_threshold:  float — mean-score threshold for splitting.
            progress_callback:     optional callable(stage_name, fraction).

        Returns (edge_scores, seam_mask) tuple of numpy arrays.
        """
        def progress(name, frac):
            if progress_callback:
                progress_callback(name, frac)

        # --- Signal computation (cached per mesh topology) -------------------
        cache_key = self._compute_cache_key(bm)
        signals_cached = (cache_key == self._cache_key
                          and self._dihedral is not None)

        if not signals_cached:
            self._cache_key = cache_key

            # Phase 1: Extract numpy arrays.
            progress("Extracting mesh data", 0.04)
            arrays = bmesh_to_arrays(bm)
            self._arrays = arrays
            self._n_faces = len(bm.faces)

            vert_coords = arrays['vert_coords']
            edge_verts = arrays['edge_verts']
            face_normals = arrays['face_normals']
            face_centroids = arrays['face_centroids']
            edge_face_map = arrays['edge_face_map']
            edge_face_count = arrays['edge_face_count']
            vert_valence = arrays['vert_valence']

            # Phase 2: Dihedral angles.
            progress("Computing dihedral angles", 0.08)
            self._dihedral = edge_scoring.compute_dihedral_scores(
                edge_face_map, edge_face_count, face_normals
            )

            # Phase 3: Curvature.
            progress("Computing curvature", 0.14)
            mixed_areas = compute_mixed_voronoi_areas(bm, vert_coords)
            gaussian = curvature.compute_gaussian_curvature(
                bm, vert_coords, mixed_areas
            )
            mean_curv = curvature.compute_mean_curvature(
                bm, vert_coords, mixed_areas
            )
            self._curvature_scores = curvature.compute_edge_curvature_scores(
                vert_coords, edge_verts, gaussian, mean_curv
            )

            # Phase 4: Concavity + edge loop alignment.
            progress("Analysing concavity and edge flow", 0.22)
            self._concavity = edge_scoring.compute_concavity_scores(
                edge_face_map, edge_face_count, edge_verts,
                vert_coords, face_normals, face_centroids
            )
            self._edge_loop = edge_scoring.compute_edge_loop_alignment(
                vert_valence, edge_verts
            )

            # Phase 5: AO Visibility (most expensive signal).
            progress("Computing visibility (AO raycasting)", 0.32)
            self._visibility = visibility.compute_ao_scores(
                bm, vert_coords, edge_verts, n_samples=ao_samples
            )

            # Phase 6: Segmentation boundaries.
            progress("Computing part boundaries", 0.52)
            self._segmentation = segmentation.compute_segmentation_scores(
                bm, vert_coords, edge_verts, edge_face_map,
                edge_face_count, face_normals
            )

            # Phase 7: Normal clustering (hard-surface panel detection).
            progress("Computing normal clusters", 0.60)
            self._normal_cluster = normal_clustering.compute_normal_cluster_scores(
                face_normals, edge_face_map, edge_face_count,
                angle_threshold_deg=normal_cluster_angle
            )

        else:
            progress("Using cached signals", 0.60)

        arrays = self._arrays

        # --- Combined scoring (always recomputed — fast) ---------------------
        progress("Combining scores", 0.63)
        self._combined_scores = edge_scoring.compute_combined_scores(
            self._dihedral,
            self._curvature_scores,
            self._concavity,
            self._edge_loop,
            self._visibility,
            self._segmentation,
            weights,
            normal_cluster=self._normal_cluster,
        )

        # --- Genus detection + homology cuts ---------------------------------
        forced_seam_edges: set[int] = set()

        if use_genus_cuts:
            progress("Detecting mesh topology (genus)", 0.67)
            try:
                loops = genus_mod.find_homology_generators(
                    bm,
                    arrays['edge_verts'],
                    arrays['edge_face_map'],
                    arrays['edge_face_count'],
                    self._combined_scores,
                )
                for loop in loops:
                    forced_seam_edges.update(loop)
            except Exception:
                pass  # Genus detection is best-effort; never abort analysis.

        # --- Layout-aware Prim's spanning tree seam extraction ---------------
        progress("Computing seams (Prim's spanning tree)", 0.75)
        n_islands = max(1, island_count) if island_count > 0 else 1

        mask = topology.compute_prim_seams(
            arrays['edge_face_map'],
            arrays['edge_face_count'],
            self._combined_scores,
            self._n_faces,
            face_centroids=arrays['face_centroids'],
            n_islands=n_islands,
            layout_bias=layout_bias,
            forced_seam_edges=forced_seam_edges if forced_seam_edges else None,
        )

        # --- Distortion feedback: adaptively split high-distortion charts ----
        if use_distortion_split:
            progress("Splitting high-distortion charts", 0.84)
            mask = distortion_mod.adaptive_chart_splitting(
                mask,
                self._combined_scores,
                arrays['edge_face_map'],
                arrays['edge_face_count'],
                self._n_faces,
                max_splits=8,
                distortion_threshold=distortion_threshold,
            )

        # --- Multi-stage seam path smoothing ---------------------------------
        progress("Smoothing seam paths", 0.93)
        mask = seam_paths.smooth_seam_paths(
            bm, mask, self._combined_scores,
            arrays['edge_verts'], iterations=smoothing_iters
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
        self._concavity = None
        self._edge_loop = None
        self._visibility = None
        self._segmentation = None
        self._normal_cluster = None
        self._combined_scores = None
        self._seam_mask = None
        self._arrays = None
        self._n_faces = 0

    def _compute_cache_key(self, bm):
        """Compute a hash of the mesh topology + positions for cache invalidation."""
        bm.verts.ensure_lookup_table()
        V = len(bm.verts)
        E = len(bm.edges)
        F = len(bm.faces)

        hasher = hashlib.md5()
        hasher.update(f"{V}:{E}:{F}".encode())

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
