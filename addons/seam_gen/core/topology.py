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

import heapq

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
    2. Sort interior edges by geometric score ascending (smooth edges first)
       - Low geometric score (smooth) → added to MST first → NOT a seam
       - High geometric score (sharp) → excluded from MST → IS a seam
    3. Kruskal's MST: greedily add edges via union-find
    4. Seam edges = interior edges NOT in MST + all boundary edges
    5. For multi-island: remove the highest-scored MST edges to split islands

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

    # Kruskal's MST: sort interior edges by score ascending.
    # Low score (smooth) → added to MST first → kept connected → NOT a seam.
    # High score (sharp) → added last / excluded → IS a seam.
    sorted_edges = sorted(
        interior_edges,
        key=lambda x: edge_weights[x[0]]  # ascending: smooth edges enter tree first
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


def compute_prim_seams(edge_face_map, edge_face_count, edge_weights, n_faces,
                       face_centroids=None, n_islands=1, layout_bias=0.3,
                       forced_seam_edges=None):
    """Layout-aware seam extraction via a depth-penalised Prim's spanning tree.

    Unlike Kruskal's global sort, Prim's grows a tree from a single *root*
    face outward.  A small depth penalty steers the tree into a compact
    star / cross shape, which on uniform meshes (cube, cylinder, sphere)
    produces the professional cross-unfolding layout an artist would choose.

    Priority of each candidate edge:
        p = score(e) + layout_bias * (depth(parent) / (1 + sqrt(n_faces)))

    Lower priority → added to the tree first → NOT a seam.
    Higher priority → excluded from the tree → IS a seam.

    Args:
        face_centroids:      (F, 3) float array used to pick the root face.
                             If None, face 0 is used.
        layout_bias:         0.0 = pure score-based (like fixed Kruskal's)
                             1.0 = strongly prefer compact / cross layout.
        forced_seam_edges:   Optional set/list of edge indices that are
                             pre-marked as seams (e.g. genus cuts). They are
                             excluded from tree candidacy.

    Returns (E,) boolean seam mask.
    """
    E = len(edge_face_map)
    seam_mask = np.zeros(E, dtype=bool)

    interior_edges, boundary_edges = build_face_adjacency(edge_face_map, edge_face_count)

    for ei in boundary_edges:
        seam_mask[ei] = True

    forced = set(forced_seam_edges) if forced_seam_edges else set()
    for ei in forced:
        seam_mask[ei] = True

    if not interior_edges or n_faces < 2:
        return seam_mask

    # Build face → [(neighbour_face, edge_index)] adjacency
    face_adj = [[] for _ in range(n_faces)]
    for ei, fi, fj in interior_edges:
        face_adj[fi].append((fj, ei))
        face_adj[fj].append((fi, ei))

    # Root = face whose centroid is closest to the mesh centroid (hub face).
    if face_centroids is not None and len(face_centroids) >= n_faces:
        mesh_center = face_centroids[:n_faces].mean(axis=0)
        dists = np.linalg.norm(face_centroids[:n_faces] - mesh_center, axis=1)
        root_face = int(np.argmin(dists))
    else:
        root_face = 0

    # Depth divisor — keeps the penalty bounded in [0, layout_bias] regardless
    # of mesh size (typical BFS depth ≈ sqrt(n_faces) for a 2D surface).
    depth_divisor = 1.0 + float(n_faces) ** 0.5

    # Prim's with lazy deletion.
    # Heap: (priority, edge_index, source_face, dest_face)
    in_tree = np.zeros(n_faces, dtype=bool)
    face_depth = np.zeros(n_faces, dtype=np.float64)
    tree_edge_set = set()

    in_tree[root_face] = True
    heap = []
    for neighbour, ei in face_adj[root_face]:
        if ei in forced:
            continue
        p = edge_weights[ei]  # root depth = 0 → no depth penalty
        heapq.heappush(heap, (p, ei, root_face, neighbour))

    while heap:
        p, ei, src, dst = heapq.heappop(heap)

        if in_tree[dst]:
            continue

        in_tree[dst] = True
        face_depth[dst] = face_depth[src] + 1.0
        tree_edge_set.add(ei)

        for neighbour, next_ei in face_adj[dst]:
            if in_tree[neighbour] or next_ei in forced:
                continue
            depth_penalty = layout_bias * (face_depth[dst] / depth_divisor)
            next_p = edge_weights[next_ei] + depth_penalty
            heapq.heappush(heap, (next_p, next_ei, dst, neighbour))

    # Interior edges not in the tree → seams.
    for ei, fi, fj in interior_edges:
        if ei not in tree_edge_set:
            seam_mask[ei] = True

    # Multi-island: break the highest-scored tree edges to create extra islands.
    if n_islands > 1:
        tree_sorted = sorted(tree_edge_set, key=lambda e: edge_weights[e], reverse=True)
        for i in range(min(n_islands - 1, len(tree_sorted))):
            seam_mask[tree_sorted[i]] = True

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
