"""
Discrete curvature estimation on triangle meshes (vectorized).

Gaussian curvature via angle defect method.
Mean curvature via cotangent Laplacian.
All operations use batch numpy — no Python per-face loops.
"""

import numpy as np


def compute_gaussian_curvature(tri_verts, vert_coords, mixed_areas, V):
    """Compute discrete Gaussian curvature at each vertex using angle defect.

    K(v) = (2*pi - sum(face_angles_at_v)) / A_mixed(v)

    Args:
        tri_verts: (T, 3) int32 triangle vertex indices
        vert_coords: (V, 3) vertex positions
        mixed_areas: (V,) mixed Voronoi areas
        V: int number of vertices

    Returns (V,) float64 array of Gaussian curvature values.
    """
    angle_sums = np.zeros(V, dtype=np.float64)

    if len(tri_verts) == 0:
        return (2.0 * np.pi - angle_sums) / mixed_areas

    i0, i1, i2 = tri_verts[:, 0], tri_verts[:, 1], tri_verts[:, 2]
    p0, p1, p2 = vert_coords[i0], vert_coords[i1], vert_coords[i2]

    e01 = p1 - p0
    e02 = p2 - p0
    e12 = p2 - p1

    # 2 * triangle area = |cross(e01, e02)|
    cross_vec = np.cross(e01, e02)
    double_area = np.linalg.norm(cross_vec, axis=1)

    # Dot products at each vertex (unnormalized cosines)
    d0 = np.einsum('ij,ij->i', e01, e02)
    d1 = np.einsum('ij,ij->i', -e01, e12)
    d2 = np.einsum('ij,ij->i', e02, e12)  # = dot(-e02, -e12)

    # Angles via atan2 (numerically stable)
    ang0 = np.arctan2(double_area, d0)
    ang1 = np.arctan2(double_area, d1)
    ang2 = np.arctan2(double_area, d2)

    # Scatter-add angles to vertices
    np.add.at(angle_sums, i0, ang0)
    np.add.at(angle_sums, i1, ang1)
    np.add.at(angle_sums, i2, ang2)

    return (2.0 * np.pi - angle_sums) / mixed_areas


def compute_mean_curvature(tri_verts, vert_coords, mixed_areas, V):
    """Compute discrete mean curvature at each vertex using cotangent Laplacian.

    H(v) = |sum_j w_ij * (x_j - x_i)| / (2 * A_mixed(v))
    where w_ij = (cot(alpha_ij) + cot(beta_ij)) / 2

    Args:
        tri_verts: (T, 3) int32 triangle vertex indices
        vert_coords: (V, 3) vertex positions
        mixed_areas: (V,) mixed Voronoi areas
        V: int number of vertices

    Returns (V,) float64 array of mean curvature magnitudes.
    """
    laplacian = np.zeros((V, 3), dtype=np.float64)

    if len(tri_verts) == 0:
        return np.zeros(V, dtype=np.float64)

    i0, i1, i2 = tri_verts[:, 0], tri_verts[:, 1], tri_verts[:, 2]
    p0, p1, p2 = vert_coords[i0], vert_coords[i1], vert_coords[i2]

    e01 = p1 - p0
    e02 = p2 - p0
    e12 = p2 - p1

    # 2 * triangle area
    cross_vec = np.cross(e01, e02)
    double_area = np.linalg.norm(cross_vec, axis=1)
    inv_4a = np.where(double_area > 1e-12, 1.0 / (2.0 * double_area), 0.0)

    # Dot products at each vertex
    d0 = np.einsum('ij,ij->i', e01, e02)
    d1 = np.einsum('ij,ij->i', -e01, e12)
    d2 = np.einsum('ij,ij->i', e02, e12)

    # Cotangent weights: cot(angle_i)/2 = d_i / (4 * tri_area) = d_i / (2 * double_area)
    # Contributions per vertex per triangle:
    # lap[v0] += cot(a1)/2 * e02 + cot(a2)/2 * e01
    # lap[v1] += cot(a0)/2 * e12 + cot(a2)/2 * (-e01)
    # lap[v2] += cot(a0)/2 * (-e12) + cot(a1)/2 * (-e02)
    w_d0 = (d0 * inv_4a)[:, None]
    w_d1 = (d1 * inv_4a)[:, None]
    w_d2 = (d2 * inv_4a)[:, None]

    contrib0 = w_d1 * e02 + w_d2 * e01
    contrib1 = w_d0 * e12 - w_d2 * e01
    contrib2 = -w_d0 * e12 - w_d1 * e02

    np.add.at(laplacian, i0, contrib0)
    np.add.at(laplacian, i1, contrib1)
    np.add.at(laplacian, i2, contrib2)

    laplacian_norm = np.linalg.norm(laplacian, axis=1)
    return laplacian_norm / (2.0 * mixed_areas)


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
