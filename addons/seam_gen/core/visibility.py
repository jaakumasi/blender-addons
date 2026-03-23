"""
Visibility scoring for seam placement via vertex-normal concavity proxy.

Estimates per-vertex "occlusion" by comparing each vertex normal to its
1-ring neighbours.  Vertices whose normal deviates strongly from their
neighbours sit in creases, concavities, or tight areas — exactly the
places where seams should be hidden.

This replaces BVHTree hemisphere raycasting with an O(V+E) algorithm
that produces comparable results for seam placement while using
negligible memory and completing in milliseconds.
"""

import numpy as np


def compute_ao_scores(bm, vert_coords, edge_verts, n_samples=16,
                      max_dist=0.0):
    """Compute per-edge visibility scores via vertex-normal concavity proxy.

    High score = edge sits in a crease / concavity (good for seams).
    Low score  = edge is on a smooth, exposed surface (avoid seams here).

    The ``n_samples`` and ``max_dist`` parameters are accepted for API
    compatibility but are unused by the proxy algorithm.

    Args:
        bm: BMesh object (for vertex normals)
        vert_coords: (V, 3) float64 vertex positions
        edge_verts: (E, 2) int32 edge vertex indices
        n_samples: unused (kept for API compatibility)
        max_dist: unused (kept for API compatibility)

    Returns (E,) float64 array with scores in [0, 1].
    """
    bm.verts.ensure_lookup_table()
    V = len(vert_coords)
    E = len(edge_verts)

    if V == 0 or E == 0:
        return np.zeros(E, dtype=np.float64)

    # Extract all vertex normals into a numpy array.
    vert_normals = np.empty((V, 3), dtype=np.float64)
    for vi in range(V):
        n = bm.verts[vi].normal
        vert_normals[vi] = (n.x, n.y, n.z)

    # Normalise (handle degenerate zero-length normals).
    norms = np.linalg.norm(vert_normals, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    vert_normals /= norms

    # Build 1-ring adjacency from edge_verts and accumulate neighbour
    # normal agreement.  For each vertex we compute
    #   ao[v] = 1 - mean(dot(normal_v, normal_neighbour))
    # so that creased / concave vertices score close to 1 and flat
    # areas score close to 0.
    dot_sum = np.zeros(V, dtype=np.float64)
    degree = np.zeros(V, dtype=np.int32)

    ev0 = edge_verts[:, 0]
    ev1 = edge_verts[:, 1]

    # Vectorised per-edge dot products between endpoint normals.
    edge_dots = np.einsum('ij,ij->i', vert_normals[ev0], vert_normals[ev1])

    # Scatter-add to both endpoints.
    np.add.at(dot_sum, ev0, edge_dots)
    np.add.at(dot_sum, ev1, edge_dots)
    np.add.at(degree, ev0, 1)
    np.add.at(degree, ev1, 1)

    # Avoid division by zero for isolated vertices.
    degree = np.maximum(degree, 1)

    ao = 1.0 - (dot_sum / degree)
    ao = np.clip(ao, 0.0, 1.0)

    # Per-edge: average of endpoint scores.
    edge_ao = (ao[ev0] + ao[ev1]) * 0.5

    return np.clip(edge_ao, 0.0, 1.0)
