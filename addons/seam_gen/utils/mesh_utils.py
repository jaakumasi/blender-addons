"""
BMesh → numpy array extraction utilities.

Converts BMesh topology into numpy arrays for vectorized computation.
All core modules depend on this interface.
"""

import math
import numpy as np


def bmesh_to_arrays(bm):
    """Extract mesh data into numpy arrays for vectorized processing.

    Returns dict with:
        vert_coords:     (V, 3) float64 — vertex positions
        edge_verts:      (E, 2) int32   — vertex index pairs per edge
        face_normals:    (F, 3) float64 — unit face normals
        face_centroids:  (F, 3) float64 — face center positions
        edge_face_map:   list[list[int]] length E — face indices per edge
        edge_face_pairs: (E, 2) int32   — face pair per edge (-1 for boundary)
        vert_face_map:   list[list[int]] length V — face indices per vertex
        vert_edge_map:   list[list[int]] length V — edge indices per vertex
        edge_face_count: (E,) int32     — number of faces per edge
        vert_valence:    (V,) int32     — number of edges per vertex
        tri_verts:       (T, 3) int32   — triangle vertex indices (fan-triangulated)
    """
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    V = len(bm.verts)
    E = len(bm.edges)
    F = len(bm.faces)

    # Vertex positions
    vert_coords = np.empty((V, 3), dtype=np.float64)
    for v in bm.verts:
        vert_coords[v.index] = v.co[:]

    # Edge vertex pairs
    edge_verts = np.empty((E, 2), dtype=np.int32)
    for e in bm.edges:
        edge_verts[e.index] = (e.verts[0].index, e.verts[1].index)

    # Face normals and centroids
    face_normals = np.empty((F, 3), dtype=np.float64)
    face_centroids = np.empty((F, 3), dtype=np.float64)
    for f in bm.faces:
        face_normals[f.index] = f.normal[:]
        face_centroids[f.index] = f.calc_center_median()[:]

    # Adjacency maps
    edge_face_map = [[] for _ in range(E)]
    for e in bm.edges:
        edge_face_map[e.index] = [f.index for f in e.link_faces]

    # Fast numpy array for the common 2-face case (interior edges).
    # Boundary / wire edges get -1.
    edge_face_pairs = np.full((E, 2), -1, dtype=np.int32)
    for ei in range(E):
        faces = edge_face_map[ei]
        if len(faces) >= 2:
            edge_face_pairs[ei, 0] = faces[0]
            edge_face_pairs[ei, 1] = faces[1]
        elif len(faces) == 1:
            edge_face_pairs[ei, 0] = faces[0]

    vert_face_map = [[] for _ in range(V)]
    for v in bm.verts:
        vert_face_map[v.index] = [f.index for f in v.link_faces]

    vert_edge_map = [[] for _ in range(V)]
    for v in bm.verts:
        vert_edge_map[v.index] = [e.index for e in v.link_edges]

    # Convenience arrays
    edge_face_count = np.array([len(ef) for ef in edge_face_map], dtype=np.int32)
    vert_valence = np.array([len(ve) for ve in vert_edge_map], dtype=np.int32)

    # Fan-triangulated triangle vertex indices
    tri_list = []
    for f in bm.faces:
        fv = [v.index for v in f.verts]
        for i in range(1, len(fv) - 1):
            tri_list.append((fv[0], fv[i], fv[i + 1]))
    tri_verts = np.array(tri_list, dtype=np.int32) if tri_list else np.empty((0, 3), dtype=np.int32)

    return {
        'vert_coords': vert_coords,
        'edge_verts': edge_verts,
        'face_normals': face_normals,
        'face_centroids': face_centroids,
        'edge_face_map': edge_face_map,
        'edge_face_pairs': edge_face_pairs,
        'vert_face_map': vert_face_map,
        'vert_edge_map': vert_edge_map,
        'edge_face_count': edge_face_count,
        'vert_valence': vert_valence,
        'tri_verts': tri_verts,
    }


def get_face_angles_at_vertex(bm, vert):
    """Return list of angles (radians) at a vertex in each adjacent face."""
    angles = []
    for face in vert.link_faces:
        verts = face.verts
        n = len(verts)
        # Find position of vert in the face loop
        idx = None
        for i, v in enumerate(verts):
            if v.index == vert.index:
                idx = i
                break
        if idx is None:
            continue
        prev_v = verts[(idx - 1) % n]
        next_v = verts[(idx + 1) % n]
        vec_a = prev_v.co - vert.co
        vec_b = next_v.co - vert.co
        len_a = vec_a.length
        len_b = vec_b.length
        if len_a < 1e-10 or len_b < 1e-10:
            angles.append(0.0)
            continue
        cos_angle = vec_a.dot(vec_b) / (len_a * len_b)
        cos_angle = max(-1.0, min(1.0, cos_angle))
        angles.append(math.acos(cos_angle))
    return angles


def compute_face_vertex_angles(bm):
    """Compute angles at each vertex in each adjacent face.

    Returns dict: {vert_index: [angle_in_face0, angle_in_face1, ...]}
    """
    bm.verts.ensure_lookup_table()
    result = {}
    for v in bm.verts:
        result[v.index] = get_face_angles_at_vertex(bm, v)
    return result


def compute_mixed_voronoi_areas(tri_verts, vert_coords, V):
    """Compute mixed Voronoi area around each vertex (vectorized).

    Uses the Voronoi-safe formula: for obtuse triangles, use area/2 or area/4
    instead of Voronoi area to avoid negative contributions.

    Args:
        tri_verts: (T, 3) int32 triangle vertex indices
        vert_coords: (V, 3) float64 vertex positions
        V: int number of vertices

    Returns (V,) float64 array.
    """
    areas = np.zeros(V, dtype=np.float64)

    if len(tri_verts) == 0:
        return np.maximum(areas, 1e-10)

    i0, i1, i2 = tri_verts[:, 0], tri_verts[:, 1], tri_verts[:, 2]
    p0, p1, p2 = vert_coords[i0], vert_coords[i1], vert_coords[i2]

    e01 = p1 - p0
    e02 = p2 - p0
    e12 = p2 - p1

    # Triangle areas
    cross = np.cross(e01, e02)
    tri_area = 0.5 * np.linalg.norm(cross, axis=1)
    valid = tri_area > 1e-12

    # Dot products at each vertex (unnormalized cosines)
    d0 = np.einsum('ij,ij->i', e01, e02)
    d1 = np.einsum('ij,ij->i', -e01, e12)
    d2 = np.einsum('ij,ij->i', e02, e12)  # dot(-e02, -e12)

    # Edge lengths squared
    len01_sq = np.einsum('ij,ij->i', e01, e01)
    len02_sq = np.einsum('ij,ij->i', e02, e02)
    len12_sq = np.einsum('ij,ij->i', e12, e12)

    # Obtuse angle detection
    obtuse0 = valid & (d0 < 0)
    obtuse1 = valid & (~obtuse0) & (d1 < 0)
    obtuse2 = valid & (~obtuse0) & (~obtuse1) & (d2 < 0)
    non_obtuse = valid & (d0 >= 0) & (d1 >= 0) & (d2 >= 0)

    # Per-triangle per-vertex area contributions
    a0 = np.zeros(len(tri_verts), dtype=np.float64)
    a1 = np.zeros(len(tri_verts), dtype=np.float64)
    a2 = np.zeros(len(tri_verts), dtype=np.float64)

    # Obtuse cases
    for mask, half_idx in [(obtuse0, 0), (obtuse1, 1), (obtuse2, 2)]:
        if not np.any(mask):
            continue
        ta = tri_area[mask]
        targets = [a0, a1, a2]
        for j in range(3):
            targets[j][mask] = ta / 4.0
        targets[half_idx][mask] = ta / 2.0

    # Non-obtuse: Voronoi formula
    if np.any(non_obtuse):
        m = non_obtuse
        inv_16a = 1.0 / (16.0 * tri_area[m])
        a0[m] = (len01_sq[m] * d2[m] + len02_sq[m] * d1[m]) * inv_16a
        a1[m] = (len01_sq[m] * d2[m] + len12_sq[m] * d0[m]) * inv_16a
        a2[m] = (len02_sq[m] * d1[m] + len12_sq[m] * d0[m]) * inv_16a

    # Scatter-add to per-vertex areas
    np.add.at(areas, i0, a0)
    np.add.at(areas, i1, a1)
    np.add.at(areas, i2, a2)

    return np.maximum(areas, 1e-10)
