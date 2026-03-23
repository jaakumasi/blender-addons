"""
Face-normal clustering signal for seam placement.

Clusters mesh faces by surface-normal direction using a BFS flood-fill with
an angle threshold.  Edges that sit on the boundary between two different
clusters score 1.0 — strong seam candidates.

This is the most discriminating signal for hard-surface models: sharp panel
transitions (e.g. hood-to-body, top cap-to-side) are detected cleanly even
when geometry is chamfered or beveled rather than perfectly sharp.

For organic models the threshold is raised (softer groupings), so the signal
adds mild guidance without over-segmenting smooth skin.
"""

import numpy as np
from collections import deque


def compute_normal_cluster_scores(face_normals, edge_face_map, edge_face_count,
                                  angle_threshold_deg: float = 30.0,
                                  edge_face_pairs=None):
    """Cluster faces by normal direction and score edges at cluster boundaries.

    Algorithm
    ---------
    BFS flood-fill starting from each unvisited face.  A neighbour face is
    added to the current cluster if the angle between *its* normal and the
    *current face's* normal is less than ``angle_threshold_deg``.  This gives
    smooth clusters that can follow gentle curvature without fragmenting.

    Args:
        face_normals:        (F, 3) normalised face normals.
        edge_face_map:       list[list[int]] — face indices per edge.
        edge_face_count:     (E,) int array.
        angle_threshold_deg: Maximum normal-angle difference (degrees) for
                             faces to belong to the same cluster.
                             Typical values:
                               15° → hard-surface (strict panel detection)
                               30° → balanced
                               45° → organic (loose orientation grouping)

    Returns
        (E,) float64 array — 1.0 at cluster boundary edges, 0.0 within.
    """
    F = len(face_normals)
    E = len(edge_face_map)

    if F == 0:
        return np.zeros(E, dtype=np.float64)

    cos_thresh = float(np.cos(np.radians(max(1.0, float(angle_threshold_deg)))))

    # Build face adjacency: face → [(neighbour_face, edge_index)]
    face_adj: list[list[tuple[int, int]]] = [[] for _ in range(F)]
    for ei in range(E):
        if edge_face_count[ei] == 2:
            fi, fj = edge_face_map[ei][0], edge_face_map[ei][1]
            face_adj[fi].append((fj, ei))
            face_adj[fj].append((fi, ei))

    labels = np.full(F, -1, dtype=np.int32)
    cluster_id = 0

    for seed in range(F):
        if labels[seed] != -1:
            continue

        labels[seed] = cluster_id
        queue: deque[int] = deque([seed])

        while queue:
            fi = queue.popleft()
            fi_normal = face_normals[fi]

            for fj, _ei in face_adj[fi]:
                if labels[fj] != -1:
                    continue

                # Compare the current face's normal to the candidate — this
                # gives smoother cluster shapes than comparing to seed normal.
                dot = float(np.dot(fi_normal, face_normals[fj]))
                dot = max(-1.0, min(1.0, dot))

                if dot >= cos_thresh:
                    labels[fj] = cluster_id
                    queue.append(fj)

        cluster_id += 1

    # Vectorised boundary scoring.
    scores = np.zeros(E, dtype=np.float64)
    two_face_idx = np.where(edge_face_count == 2)[0]

    if len(two_face_idx) > 0:
        if edge_face_pairs is not None:
            f1 = edge_face_pairs[two_face_idx, 0]
            f2 = edge_face_pairs[two_face_idx, 1]
        else:
            f1 = np.array([edge_face_map[i][0] for i in two_face_idx], dtype=np.int32)
            f2 = np.array([edge_face_map[i][1] for i in two_face_idx], dtype=np.int32)
        boundary = labels[f1] != labels[f2]
        scores[two_face_idx[boundary]] = 1.0

    return scores
