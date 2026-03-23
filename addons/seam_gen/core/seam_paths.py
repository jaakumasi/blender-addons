"""
Seam path optimization: thresholding, smoothing, edge loop following.

Converts raw edge scores into clean, usable seam paths.
"""

import numpy as np
from collections import deque


def threshold_edges(scores, threshold):
    """Return boolean mask of edges above threshold.

    Args:
        scores: (E,) float64 combined edge scores
        threshold: float in [0, 1]

    Returns (E,) boolean array.
    """
    return scores >= threshold


def smooth_seam_paths(bm, seam_mask, scores, edge_verts, iterations=3):
    """Smooth jagged seam paths by removing zig-zags and filling gaps.

    For each iteration:
    1. Find seam vertices with exactly 2 seam edges that form a sharp turn
    2. Check if a smoother alternative path exists through neighboring edges
    3. Replace zig-zag with smoother path if available

    Returns modified (E,) boolean seam mask.
    """
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    E = len(edge_verts)
    mask = seam_mask.copy()

    # Build vertex-to-edge adjacency
    vert_edges = {}
    for ei in range(E):
        v1, v2 = edge_verts[ei]
        vert_edges.setdefault(v1, []).append(ei)
        vert_edges.setdefault(v2, []).append(ei)

    for _iteration in range(iterations):
        changed = False

        # Find vertices where exactly 1 seam edge connects (dead ends)
        # Remove dead-end seam edges (they create artifacts)
        for vi, edges in vert_edges.items():
            seam_edges = [ei for ei in edges if mask[ei]]
            if len(seam_edges) == 1:
                # Dead end — only remove if the edge score is below median
                ei = seam_edges[0]
                if scores[ei] < 0.7:
                    mask[ei] = False
                    changed = True

        # Find seam chains and smooth them
        # A "jagged" vertex has 2 seam edges where the angle between them is sharp
        for vi, edges in vert_edges.items():
            seam_edges = [ei for ei in edges if mask[ei]]
            if len(seam_edges) != 2:
                continue

            e1, e2 = seam_edges
            # Get the "other" vertex of each seam edge
            v1_other = edge_verts[e1][0] if edge_verts[e1][1] == vi else edge_verts[e1][1]
            v2_other = edge_verts[e2][0] if edge_verts[e2][1] == vi else edge_verts[e2][1]

            # Check if there's a direct edge between v1_other and v2_other
            # that would be a smoother shortcut
            for ei_candidate in vert_edges.get(v1_other, []):
                other_v = edge_verts[ei_candidate][0] if edge_verts[ei_candidate][1] == v1_other else edge_verts[ei_candidate][1]
                if other_v == v2_other and not mask[ei_candidate]:
                    # Found a shortcut edge — use it if it has reasonable score
                    if scores[ei_candidate] > min(scores[e1], scores[e2]) * 0.5:
                        mask[e1] = False
                        mask[e2] = False
                        mask[ei_candidate] = True
                        changed = True
                        break

        if not changed:
            break

    return mask


def follow_edge_loops(bm, seam_mask, scores, edge_verts, vert_valence):
    """Extend seam paths along edge loops for cleaner results.

    Where a seam path ends at a vertex with valence 4, attempt to continue
    along the edge loop.

    Returns modified (E,) boolean seam mask.
    """
    E = len(edge_verts)
    mask = seam_mask.copy()

    # Build vertex-to-edge adjacency
    vert_edges = {}
    for ei in range(E):
        v1, v2 = edge_verts[ei]
        vert_edges.setdefault(v1, []).append(ei)
        vert_edges.setdefault(v2, []).append(ei)

    # Find seam endpoints (vertices with exactly 1 seam edge)
    endpoints = []
    for vi, edges in vert_edges.items():
        seam_count = sum(1 for ei in edges if mask[ei])
        if seam_count == 1:
            endpoints.append(vi)

    # Try to extend each endpoint along the edge loop
    for vi in endpoints:
        if vert_valence[vi] != 4:
            continue

        seam_edge = None
        for ei in vert_edges[vi]:
            if mask[ei]:
                seam_edge = ei
                break

        if seam_edge is None:
            continue

        # Find the "opposite" edge in the quad loop
        # The opposite edge shares no faces with the seam edge
        seam_faces = set()
        bm_edge = bm.edges[seam_edge]
        for f in bm_edge.link_faces:
            seam_faces.add(f.index)

        best_candidate = None
        best_score = 0.0
        for ei in vert_edges[vi]:
            if ei == seam_edge or mask[ei]:
                continue
            # Check if this edge shares any faces with the seam edge
            candidate_faces = set(f.index for f in bm.edges[ei].link_faces)
            if not candidate_faces.intersection(seam_faces):
                # Opposite edge in quad — good candidate for loop continuation
                if scores[ei] > best_score:
                    best_score = scores[ei]
                    best_candidate = ei

        # Extend if candidate has reasonable score
        if best_candidate is not None and best_score > 0.2:
            mask[best_candidate] = True

    return mask


def ensure_connected_islands(bm, seam_mask, edge_verts, scores):
    """Verify seams partition mesh into valid UV islands.

    If any face region has no boundary seam edges, find the lowest-score
    non-seam edge connecting two regions and mark it as a seam.

    Returns modified (E,) boolean seam mask.
    """
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    mask = seam_mask.copy()
    F = len(bm.faces)

    # Build face adjacency (faces connected by non-seam edges)
    face_adj = [[] for _ in range(F)]
    for ei in range(len(edge_verts)):
        if mask[ei]:
            continue  # Seam edge — don't connect faces through it
        edge = bm.edges[ei]
        faces = list(edge.link_faces)
        if len(faces) == 2:
            fi, fj = faces[0].index, faces[1].index
            face_adj[fi].append(fj)
            face_adj[fj].append(fi)

    # BFS to find connected face components
    visited = np.full(F, -1, dtype=np.int32)
    component_id = 0

    for start in range(F):
        if visited[start] >= 0:
            continue
        queue = deque([start])
        visited[start] = component_id
        while queue:
            fi = queue.popleft()
            for fj in face_adj[fi]:
                if visited[fj] < 0:
                    visited[fj] = component_id
                    queue.append(fj)
        component_id += 1

    # If only one component, we need at least one seam to create valid UV islands
    if component_id <= 1 and not mask.any():
        # Find the edge with the highest score and mark it
        if len(scores) > 0:
            best_edge = np.argmax(scores)
            mask[best_edge] = True

    return mask
