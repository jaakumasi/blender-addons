"""
Discrete curvature estimation on triangle meshes.

Gaussian curvature via angle defect method.
Mean curvature via cotangent Laplacian.
"""

import math
import numpy as np


def compute_gaussian_curvature(bm, vert_coords, mixed_areas):
    """Compute discrete Gaussian curvature at each vertex using angle defect.

    K(v) = (2*pi - sum(face_angles_at_v)) / A_mixed(v)

    Args:
        bm: BMesh object
        vert_coords: (V, 3) array
        mixed_areas: (V,) array of mixed Voronoi areas

    Returns (V,) float64 array of Gaussian curvature values.
    """
    V = len(bm.verts)
    angle_sums = np.zeros(V, dtype=np.float64)

    for face in bm.faces:
        fv = face.verts
        n = len(fv)
        for i in range(n):
            v = fv[i]
            prev_v = fv[(i - 1) % n]
            next_v = fv[(i + 1) % n]

            vec_a = vert_coords[prev_v.index] - vert_coords[v.index]
            vec_b = vert_coords[next_v.index] - vert_coords[v.index]

            len_a = np.linalg.norm(vec_a)
            len_b = np.linalg.norm(vec_b)

            if len_a < 1e-10 or len_b < 1e-10:
                continue

            cos_angle = np.dot(vec_a, vec_b) / (len_a * len_b)
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            angle_sums[v.index] += math.acos(cos_angle)

    gaussian = (2.0 * np.pi - angle_sums) / mixed_areas
    return gaussian


def compute_mean_curvature(bm, vert_coords, mixed_areas):
    """Compute discrete mean curvature at each vertex using cotangent Laplacian.

    H(v) = |sum_j w_ij * (x_j - x_i)| / (2 * A_mixed(v))
    where w_ij = (cot(alpha_ij) + cot(beta_ij)) / 2

    For non-triangle faces, fan-triangulates from the first vertex.

    Args:
        bm: BMesh object
        vert_coords: (V, 3) array
        mixed_areas: (V,) array of mixed Voronoi areas

    Returns (V,) float64 array of mean curvature magnitudes.
    """
    V = len(bm.verts)
    laplacian = np.zeros((V, 3), dtype=np.float64)

    for face in bm.faces:
        fv = face.verts
        n = len(fv)

        # Fan-triangulate for n-gons
        for ti in range(1, n - 1):
            tri = [fv[0], fv[ti], fv[ti + 1]]
            _accumulate_cotangent_weights(tri, vert_coords, laplacian)

    # Mean curvature magnitude
    laplacian_norm = np.linalg.norm(laplacian, axis=1)
    mean_curv = laplacian_norm / (2.0 * mixed_areas)

    return mean_curv


def _accumulate_cotangent_weights(tri_verts, vert_coords, laplacian):
    """Add cotangent Laplacian contributions from one triangle.

    For triangle with vertices (a, b, c):
    - Edge (a, b): opposite angle at c, weight = cot(angle_c)
    - Edge (b, c): opposite angle at a, weight = cot(angle_a)
    - Edge (a, c): opposite angle at b, weight = cot(angle_b)
    """
    idx = [v.index for v in tri_verts]
    p = np.array([vert_coords[i] for i in idx])  # (3, 3)

    # Edge vectors
    edges = [
        p[1] - p[0],  # edge a→b
        p[2] - p[1],  # edge b→c
        p[0] - p[2],  # edge c→a
    ]

    # Angles at each vertex
    for i in range(3):
        j = (i + 1) % 3
        k = (i + 2) % 3

        # Angle at vertex i (between edges to j and k)
        vec_to_j = p[j] - p[i]
        vec_to_k = p[k] - p[i]
        len_j = np.linalg.norm(vec_to_j)
        len_k = np.linalg.norm(vec_to_k)

        if len_j < 1e-10 or len_k < 1e-10:
            continue

        cos_a = np.dot(vec_to_j, vec_to_k) / (len_j * len_k)
        cos_a = np.clip(cos_a, -0.999, 0.999)
        sin_a = math.sqrt(1.0 - cos_a * cos_a)
        cot_a = cos_a / max(sin_a, 1e-10)

        # This angle is opposite to edge (j, k)
        # Weight for edge (j, k) += cot(angle_at_i) / 2
        w = cot_a * 0.5
        diff_jk = vert_coords[idx[k]] - vert_coords[idx[j]]
        laplacian[idx[j]] += w * diff_jk
        laplacian[idx[k]] -= w * diff_jk


def compute_edge_curvature_scores(vert_coords, edge_verts, gaussian, mean_curv):
    """Convert per-vertex curvature to per-edge scores.

    For each edge, average the curvature magnitudes of its two endpoints,
    then normalize to [0, 1].

    Returns (E,) float64 array.
    """
    v1 = edge_verts[:, 0]
    v2 = edge_verts[:, 1]

    # Combine Gaussian and mean curvature magnitudes
    vert_scores = np.abs(gaussian) + np.abs(mean_curv)

    edge_scores = (vert_scores[v1] + vert_scores[v2]) * 0.5

    # Normalize to [0, 1]
    max_score = edge_scores.max()
    if max_score > 1e-10:
        edge_scores /= max_score

    return edge_scores
