"""
Edge scoring: dihedral angles, concavity detection, edge loop alignment, and combined scoring.

All functions operate on numpy arrays extracted by mesh_utils.bmesh_to_arrays().
"""

import numpy as np


def compute_dihedral_scores(edge_face_map, edge_face_count, face_normals):
    """Score each edge by dihedral angle between adjacent faces.

    Returns (E,) float64 array with scores in [0, 1].
    - 2-face edges: arccos(dot(n1, n2)) / pi
    - 1-face edges (boundary): 0.8 (strong seam candidates)
    - 0 or >2 face edges: 0.0
    """
    E = len(edge_face_map)
    scores = np.zeros(E, dtype=np.float64)

    # Vectorize the 2-face case
    two_face_mask = edge_face_count == 2
    two_face_indices = np.where(two_face_mask)[0]

    if len(two_face_indices) > 0:
        f1_indices = np.array([edge_face_map[i][0] for i in two_face_indices], dtype=np.int32)
        f2_indices = np.array([edge_face_map[i][1] for i in two_face_indices], dtype=np.int32)

        n1 = face_normals[f1_indices]  # (K, 3)
        n2 = face_normals[f2_indices]  # (K, 3)

        dots = np.einsum('ij,ij->i', n1, n2)
        dots = np.clip(dots, -1.0, 1.0)
        angles = np.arccos(dots)
        scores[two_face_indices] = angles / np.pi

    # Boundary edges
    boundary_mask = edge_face_count == 1
    scores[boundary_mask] = 0.8

    return scores


def compute_concavity_scores(edge_face_map, edge_face_count, edge_verts,
                             vert_coords, face_normals, face_centroids):
    """Score edges by concavity — concave (valley) edges get bonus, convex don't.

    A concave edge is one where the face centroids are "below" the edge
    relative to the face normals (the faces fold inward).

    Returns (E,) float64 array with scores in [0, 1].
    """
    E = len(edge_face_map)
    scores = np.zeros(E, dtype=np.float64)

    two_face_mask = edge_face_count == 2
    two_face_indices = np.where(two_face_mask)[0]

    if len(two_face_indices) == 0:
        return scores

    # Edge midpoints
    v1_idx = edge_verts[two_face_indices, 0]
    v2_idx = edge_verts[two_face_indices, 1]
    midpoints = (vert_coords[v1_idx] + vert_coords[v2_idx]) * 0.5  # (K, 3)

    f1_indices = np.array([edge_face_map[i][0] for i in two_face_indices], dtype=np.int32)
    f2_indices = np.array([edge_face_map[i][1] for i in two_face_indices], dtype=np.int32)

    c1 = face_centroids[f1_indices]  # (K, 3)
    c2 = face_centroids[f2_indices]  # (K, 3)
    n1 = face_normals[f1_indices]    # (K, 3)
    n2 = face_normals[f2_indices]    # (K, 3)

    # Vector from midpoint to each centroid
    v_to_c1 = c1 - midpoints  # (K, 3)
    v_to_c2 = c2 - midpoints  # (K, 3)

    # Dot with opposite face normal to detect concavity
    # Concave: centroids are on the "wrong" side of the edge
    dot1 = np.einsum('ij,ij->i', v_to_c1, n2)
    dot2 = np.einsum('ij,ij->i', v_to_c2, n1)

    # Both negative = concave (valley)
    concave = (dot1 < 0) & (dot2 < 0)

    # Score based on dihedral angle magnitude for concave edges
    dots = np.einsum('ij,ij->i', n1, n2)
    dots = np.clip(dots, -1.0, 1.0)
    angles = np.arccos(dots)

    # Concave edges get a score proportional to their sharpness
    scores[two_face_indices[concave]] = angles[concave] / np.pi

    return scores


def compute_edge_loop_alignment(vert_valence, edge_verts):
    """Score edges by how well they sit on clean quad edge loops.

    Edges where both endpoints have valence 4 (regular quad mesh) score highest.
    Score decays with increasing valence deviation from 4.

    Returns (E,) float64 array with scores in [0, 1].
    """
    E = len(edge_verts)

    v1_val = vert_valence[edge_verts[:, 0]]
    v2_val = vert_valence[edge_verts[:, 1]]

    # Deviation from ideal valence 4
    dev1 = np.abs(v1_val - 4).astype(np.float64)
    dev2 = np.abs(v2_val - 4).astype(np.float64)

    # Average deviation, mapped to [0, 1] where 0 deviation = score 1.0
    avg_dev = (dev1 + dev2) / 2.0
    scores = np.exp(-avg_dev * 0.5)  # Gaussian-like decay

    return scores


def compute_combined_scores(dihedral, curvature, concavity, edge_loop, weights):
    """Combine geometric signal scores with given weights.

    These scores feed into the MST as edge weights — higher score means
    the edge is a better seam candidate (more likely to be cut).

    Args:
        dihedral:  (E,) dihedral angle scores
        curvature: (E,) curvature scores
        concavity: (E,) concavity scores
        edge_loop: (E,) edge loop alignment scores
        weights:   dict with keys 'dihedral', 'curvature', 'concavity', 'edge_loop'

    Returns (E,) float64 array with scores in [0, 1].
    """
    combined = (
        weights['dihedral'] * dihedral
        + weights['curvature'] * curvature
        + weights['concavity'] * concavity
        + weights['edge_loop'] * edge_loop
    )

    # Normalize by total weight to keep in [0, 1] range
    total_weight = sum(weights.values())
    if total_weight > 0:
        combined /= total_weight

    return np.clip(combined, 0.0, 1.0)
