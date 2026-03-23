"""
Topological seam extraction via dual graph MST.

The core insight: seams are the COMPLEMENT of a spanning tree on the face
adjacency graph. The MST keeps faces with low geometric scores connected
(smooth regions stay together), while high-score edges get excluded (sharp
creases become seams).

For a mesh with F faces:
- MST has F-1 edges (minimum to keep all faces connected)
- Seam edges = total interior edges - MST edges
- This guarantees the mesh unfolds into a topological disk
"""

import numpy as np


class UnionFind:
    """Disjoint set data structure for Kruskal's MST algorithm."""

    __slots__ = ('parent', 'rank')

    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        return True


def build_face_adjacency(edge_face_map, edge_face_count):
    """Build face-to-face adjacency from edge-face relationships.

    Returns:
        interior_edges: list of (edge_index, face_i, face_j) for edges with 2 faces
        boundary_edges: list of edge_index for edges with 1 face
    """
    interior_edges = []
    boundary_edges = []

    for ei in range(len(edge_face_map)):
        fc = edge_face_count[ei]
        if fc == 2:
            fi, fj = edge_face_map[ei][0], edge_face_map[ei][1]
            interior_edges.append((ei, fi, fj))
        elif fc == 1:
            boundary_edges.append(ei)

    return interior_edges, boundary_edges


def compute_mst_seams(edge_face_map, edge_face_count, edge_weights, n_faces,
                      n_islands=0):
    """Find seams via MST complement on the face adjacency graph.

    Algorithm:
    1. Build face adjacency (interior edges connect two faces)
    2. For each interior edge, MST weight = 1.0 - geometric_score
       - Low geometric score → low MST weight → kept in MST → NOT a seam
       - High geometric score → high MST weight → excluded from MST → IS a seam
    3. Kruskal's MST: sort by weight ascending, greedily add edges
    4. Seam edges = interior edges NOT in MST + all boundary edges
    5. For multi-island: remove heaviest MST edges to split

    Args:
        edge_face_map: list of face index lists per edge
        edge_face_count: (E,) int array
        edge_weights: (E,) float array of geometric scores [0, 1]
                      (high = good seam candidate)
        n_faces: total number of faces
        n_islands: target island count (0 or 1 = single island)

    Returns:
        (E,) boolean seam mask
    """
    E = len(edge_face_map)
    seam_mask = np.zeros(E, dtype=bool)

    interior_edges, boundary_edges = build_face_adjacency(
        edge_face_map, edge_face_count
    )

    # Boundary edges are always seams
    for ei in boundary_edges:
        seam_mask[ei] = True

    if not interior_edges or n_faces < 2:
        return seam_mask

    # Kruskal's MST: sort interior edges by MST weight ascending
    # MST weight = 1.0 - geometric_score (keep smooth edges, cut sharp ones)
    sorted_edges = sorted(
        interior_edges,
        key=lambda x: 1.0 - edge_weights[x[0]]  # ascending MST weight
    )

    uf = UnionFind(n_faces)
    mst_edge_indices = set()
    mst_edges_sorted = []  # Keep insertion order for multi-island splitting

    for ei, fi, fj in sorted_edges:
        if uf.union(fi, fj):
            mst_edge_indices.add(ei)
            mst_edges_sorted.append((ei, edge_weights[ei]))

    # All interior edges NOT in MST are seams
    for ei, fi, fj in interior_edges:
        if ei not in mst_edge_indices:
            seam_mask[ei] = True

    # Multi-island: remove heaviest MST edges to split islands
    if n_islands > 1:
        # Sort MST edges by geometric score descending (heaviest first)
        mst_edges_sorted.sort(key=lambda x: x[1], reverse=True)

        splits_needed = n_islands - 1
        for i in range(min(splits_needed, len(mst_edges_sorted))):
            ei, _ = mst_edges_sorted[i]
            seam_mask[ei] = True

    return seam_mask


def compute_mst_seams_adaptive(edge_face_map, edge_face_count, edge_weights,
                               n_faces, threshold=0.5):
    """Adaptive seam extraction: single island plus extra cuts where distortion is high.

    Starts with MST complement (minimum seams for single island), then adds
    additional seam edges where the geometric score exceeds the threshold.
    Each additional cut is only added if it splits an existing island
    (avoids redundant cuts).

    Args:
        edge_face_map, edge_face_count, edge_weights: as above
        n_faces: total face count
        threshold: geometric score above which extra cuts are considered

    Returns:
        (E,) boolean seam mask
    """
    # Start with base MST seams (single island)
    seam_mask = compute_mst_seams(
        edge_face_map, edge_face_count, edge_weights, n_faces, n_islands=0
    )

    # Find MST edges that have high geometric scores
    # These are places where the MST is "holding together" faces that want to separate
    interior_edges, _ = build_face_adjacency(edge_face_map, edge_face_count)

    # Collect MST edges above threshold, sorted by score descending
    mst_high_score = []
    for ei, fi, fj in interior_edges:
        if not seam_mask[ei] and edge_weights[ei] > threshold:
            mst_high_score.append((ei, edge_weights[ei]))

    mst_high_score.sort(key=lambda x: x[1], reverse=True)

    # Add extra cuts (each one creates an additional island)
    # Limit: don't create more than sqrt(F) extra islands
    max_extra = max(1, int(np.sqrt(n_faces)))
    for i in range(min(max_extra, len(mst_high_score))):
        ei, _ = mst_high_score[i]
        seam_mask[ei] = True

    return seam_mask
