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
        vert_coords:    (V, 3) float64 — vertex positions
        edge_verts:     (E, 2) int32   — vertex index pairs per edge
        face_normals:   (F, 3) float64 — unit face normals
        face_centroids: (F, 3) float64 — face center positions
        edge_face_map:  list[list[int]] length E — face indices per edge
        vert_face_map:  list[list[int]] length V — face indices per vertex
        vert_edge_map:  list[list[int]] length V — edge indices per vertex
        edge_face_count: (E,) int32    — number of faces per edge
        vert_valence:   (V,) int32     — number of edges per vertex
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

    vert_face_map = [[] for _ in range(V)]
    for v in bm.verts:
        vert_face_map[v.index] = [f.index for f in v.link_faces]

    vert_edge_map = [[] for _ in range(V)]
    for v in bm.verts:
        vert_edge_map[v.index] = [e.index for e in v.link_edges]

    # Convenience arrays
    edge_face_count = np.array([len(ef) for ef in edge_face_map], dtype=np.int32)
    vert_valence = np.array([len(ve) for ve in vert_edge_map], dtype=np.int32)

    return {
        'vert_coords': vert_coords,
        'edge_verts': edge_verts,
        'face_normals': face_normals,
        'face_centroids': face_centroids,
        'edge_face_map': edge_face_map,
        'vert_face_map': vert_face_map,
        'vert_edge_map': vert_edge_map,
        'edge_face_count': edge_face_count,
        'vert_valence': vert_valence,
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


def compute_mixed_voronoi_areas(bm, vert_coords):
    """Compute mixed Voronoi area around each vertex.

    Uses the Voronoi-safe formula: for obtuse triangles, use area/2 or area/4
    instead of Voronoi area to avoid negative contributions.

    Returns (V,) float64 array.
    """
    V = len(bm.verts)
    areas = np.zeros(V, dtype=np.float64)

    for face in bm.faces:
        fv = face.verts
        n = len(fv)
        if n < 3:
            continue

        # Fan-triangulate for n-gons
        for i in range(1, n - 1):
            v0 = fv[0]
            v1 = fv[i]
            v2 = fv[i + 1]

            p0 = vert_coords[v0.index]
            p1 = vert_coords[v1.index]
            p2 = vert_coords[v2.index]

            # Triangle area
            e1 = p1 - p0
            e2 = p2 - p0
            tri_area = 0.5 * np.linalg.norm(np.cross(e1, e2))

            if tri_area < 1e-12:
                continue

            # Check for obtuse angles
            d01 = np.dot(p1 - p0, p2 - p0)
            d10 = np.dot(p0 - p1, p2 - p1)
            d20 = np.dot(p0 - p2, p1 - p2)

            if d01 < 0:
                # Obtuse at v0
                areas[v0.index] += tri_area / 2.0
                areas[v1.index] += tri_area / 4.0
                areas[v2.index] += tri_area / 4.0
            elif d10 < 0:
                # Obtuse at v1
                areas[v0.index] += tri_area / 4.0
                areas[v1.index] += tri_area / 2.0
                areas[v2.index] += tri_area / 4.0
            elif d20 < 0:
                # Obtuse at v2
                areas[v0.index] += tri_area / 4.0
                areas[v1.index] += tri_area / 4.0
                areas[v2.index] += tri_area / 2.0
            else:
                # Non-obtuse: use Voronoi area (cotangent formula)
                # Area at v0 = (|e01|^2 * cot(angle_at_v2) + |e02|^2 * cot(angle_at_v1)) / 8
                e01 = p1 - p0
                e02 = p2 - p0
                e12 = p2 - p1

                len_e01_sq = np.dot(e01, e01)
                len_e02_sq = np.dot(e02, e02)
                len_e12_sq = np.dot(e12, e12)

                # Cotangent of angle at v2
                cos2 = d20
                sin2_sq = len_e02_sq * len_e12_sq - cos2 * cos2
                sin2 = math.sqrt(max(sin2_sq, 1e-20))
                cot2 = cos2 / sin2

                # Cotangent of angle at v1
                cos1 = d10
                sin1_sq = len_e01_sq * len_e12_sq - cos1 * cos1
                sin1 = math.sqrt(max(sin1_sq, 1e-20))
                cot1 = cos1 / sin1

                # Cotangent of angle at v0
                cos0 = d01
                sin0_sq = len_e01_sq * len_e02_sq - cos0 * cos0
                sin0 = math.sqrt(max(sin0_sq, 1e-20))
                cot0 = cos0 / sin0

                areas[v0.index] += (len_e01_sq * cot2 + len_e02_sq * cot1) / 8.0
                areas[v1.index] += (len_e01_sq * cot2 + len_e12_sq * cot0) / 8.0
                areas[v2.index] += (len_e02_sq * cot1 + len_e12_sq * cot0) / 8.0

    # Clamp to avoid division by zero
    areas = np.maximum(areas, 1e-10)
    return areas
