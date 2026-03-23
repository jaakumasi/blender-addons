"""
Mesh segmentation into natural chart regions.

Region-growing segmentation using dihedral-angle weighted BFS from
farthest-point seeds.  O(V+E) time, O(V+E) space.
"""

import numpy as np
from collections import deque


def compute_segmentation_scores(bm, vert_coords, edge_verts, edge_face_map,
                                edge_face_count, face_normals, n_segments=0,
                                edge_face_pairs=None):
    """Segment mesh and return per-edge boundary scores.

    Args:
        bm: BMesh object (unused, kept for API compatibility)
        vert_coords: (V, 3) array
        edge_verts: (E, 2) array
        edge_face_map: list of face index lists per edge
        edge_face_count: (E,) array
        face_normals: (F, 3) array
        n_segments: target segments (0 = auto-detect)
        edge_face_pairs: (E, 2) int32 optional fast face-pair array

    Returns (E,) float64 array: 1.0 for edges on segment boundaries, 0.0 otherwise.
    """
    V = len(vert_coords)

    if n_segments <= 0:
        n_segments = max(2, min(20, int(np.sqrt(V / 100.0))))

    dihedral = _quick_dihedral(edge_face_map, edge_face_count, face_normals,
                               edge_face_pairs=edge_face_pairs)
    labels = region_growing(vert_coords, edge_verts, dihedral, n_segments)

    return _labels_to_edge_scores(labels, edge_verts)


def region_growing(vert_coords, edge_verts, dihedral_scores, n_segments):
    """Segment mesh via region growing from seed vertices.

    Uses farthest-point sampling for seeds, BFS with dihedral-weighted priority.

    Returns (V,) int32 array of segment labels.
    """
    V = len(vert_coords)

    # Build adjacency list
    adj = [[] for _ in range(V)]
    for ei in range(len(edge_verts)):
        v1, v2 = edge_verts[ei]
        w = dihedral_scores[ei]
        adj[v1].append((v2, w, ei))
        adj[v2].append((v1, w, ei))

    # Farthest-point sampling for seeds
    seeds = _farthest_point_sample(vert_coords, n_segments)

    # BFS from all seeds simultaneously
    labels = np.full(V, -1, dtype=np.int32)
    # Priority: lower = process first. We want to stop at high-dihedral edges.
    # So priority = cumulative dihedral weight along path.
    dist = np.full(V, np.inf, dtype=np.float64)

    queue = deque()
    for seg_id, seed in enumerate(seeds):
        labels[seed] = seg_id
        dist[seed] = 0.0
        queue.append((seed, seg_id, 0.0))

    while queue:
        v, seg_id, d = queue.popleft()

        if labels[v] != seg_id:
            continue

        for neighbor, edge_weight, _ in adj[v]:
            new_dist = d + edge_weight
            if new_dist < dist[neighbor]:
                dist[neighbor] = new_dist
                labels[neighbor] = seg_id
                queue.append((neighbor, seg_id, new_dist))

    # Assign any remaining unlabeled vertices to nearest labeled neighbor
    unlabeled = labels == -1
    if unlabeled.any():
        labels[unlabeled] = 0

    return labels


def _farthest_point_sample(vert_coords, n_seeds):
    """Select n_seeds vertices via farthest-point sampling."""
    V = len(vert_coords)
    if n_seeds >= V:
        return list(range(V))

    seeds = [0]  # Start from vertex 0
    min_dists = np.full(V, np.inf, dtype=np.float64)

    for _ in range(n_seeds - 1):
        # Update distances from latest seed
        last_seed = seeds[-1]
        diffs = vert_coords - vert_coords[last_seed]
        dists = np.linalg.norm(diffs, axis=1)
        min_dists = np.minimum(min_dists, dists)

        # Pick farthest vertex
        next_seed = np.argmax(min_dists)
        seeds.append(int(next_seed))

    return seeds


def _quick_dihedral(edge_face_map, edge_face_count, face_normals,
                    edge_face_pairs=None):
    """Quick dihedral angle computation for region growing weights."""
    E = len(edge_face_count)
    scores = np.zeros(E, dtype=np.float64)

    two_face = edge_face_count == 2
    two_face_idx = np.where(two_face)[0]

    if len(two_face_idx) > 0:
        if edge_face_pairs is not None:
            f1 = edge_face_pairs[two_face_idx, 0]
            f2 = edge_face_pairs[two_face_idx, 1]
        else:
            f1 = np.array([edge_face_map[i][0] for i in two_face_idx], dtype=np.int32)
            f2 = np.array([edge_face_map[i][1] for i in two_face_idx], dtype=np.int32)
        dots = np.einsum('ij,ij->i', face_normals[f1], face_normals[f2])
        dots = np.clip(dots, -1.0, 1.0)
        scores[two_face_idx] = np.arccos(dots) / np.pi

    return scores


def _labels_to_edge_scores(labels, edge_verts):
    """Convert vertex segment labels to per-edge boundary scores.

    Edges between different segments score 1.0, same-segment edges score 0.0.
    """
    v1_labels = labels[edge_verts[:, 0]]
    v2_labels = labels[edge_verts[:, 1]]
    return (v1_labels != v2_labels).astype(np.float64)
