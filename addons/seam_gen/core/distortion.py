"""
UV chart distortion estimation and adaptive seam splitting.

After initial seam placement, this module identifies UV charts (connected
face regions bounded by seams) that are geometrically complex — meaning they
contain many high-scoring interior edges that ideally should have been seams
but were kept for MST connectivity.  Such charts tend to produce high UV
stretch when unwrapped.

The adaptive splitter adds one seam edge at a time to the highest-distortion
chart (the edge with the highest geometric score inside that chart), repeating
until all charts fall below the distortion threshold or the split budget is
exhausted.

Distortion estimate
-------------------
For each chart we compute the *mean geometric score* of all interior (non-seam)
edges.  A high mean score signals that the chart contains sharp creases or
curved areas that will stretch badly — it is a proven proxy for angle/area
distortion in practice and is very cheap to compute.
"""

import numpy as np
from collections import deque


def adaptive_chart_splitting(seam_mask, edge_scores, edge_face_map,
                              edge_face_count, n_faces,
                              max_splits: int = 8,
                              distortion_threshold: float = 0.55):
    """Adaptively split high-distortion UV charts by adding seam edges.

    Algorithm
    ----------
    1. Identify current UV charts (connected face components via non-seam edges).
    2. Score each chart by its mean interior edge score.
    3. Split the worst chart at its highest-scoring interior unseamed edge.
    4. Repeat up to ``max_splits`` times or until all charts score below
       ``distortion_threshold``.

    Args:
        seam_mask:            (E,) bool — current seam set (modified in-place copy).
        edge_scores:          (E,) float — combined geometric scores [0, 1].
        edge_face_map:        list[list[int]] — face indices per edge.
        edge_face_count:      (E,) int32.
        n_faces:              total face count.
        max_splits:           upper bound on extra seam edges added.
        distortion_threshold: charts with mean score above this are split.
                              Typical range [0.40, 0.70].

    Returns modified (E,) boolean seam mask.
    """
    mask = seam_mask.copy()

    for _ in range(max_splits):
        charts = _identify_charts(mask, edge_face_map, edge_face_count, n_faces)
        if not charts:
            break

        # Find the highest-distortion chart.
        worst_chart = None
        worst_score = -1.0
        for chart_faces in charts:
            d = _chart_distortion(
                chart_faces, mask, edge_face_map, edge_face_count, edge_scores
            )
            if d > worst_score:
                worst_score = d
                worst_chart = chart_faces

        if worst_score <= distortion_threshold:
            break

        # Split at the highest-scoring interior edge of that chart.
        best_ei = _best_split_edge(
            worst_chart, mask, edge_face_map, edge_face_count, edge_scores
        )
        if best_ei is None:
            break

        mask[best_ei] = True

    return mask


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _identify_charts(seam_mask, edge_face_map, edge_face_count, n_faces):
    """BFS over non-seam face adjacency to find connected face components.

    Returns list of frozensets of face indices, one per UV chart.
    """
    face_adj: list[list[int]] = [[] for _ in range(n_faces)]
    for ei in range(len(edge_face_map)):
        if seam_mask[ei] or edge_face_count[ei] != 2:
            continue
        fi, fj = edge_face_map[ei][0], edge_face_map[ei][1]
        face_adj[fi].append(fj)
        face_adj[fj].append(fi)

    visited = np.zeros(n_faces, dtype=bool)
    charts: list[frozenset] = []

    for seed in range(n_faces):
        if visited[seed]:
            continue
        comp: list[int] = []
        q: deque[int] = deque([seed])
        visited[seed] = True
        while q:
            fi = q.popleft()
            comp.append(fi)
            for fj in face_adj[fi]:
                if not visited[fj]:
                    visited[fj] = True
                    q.append(fj)
        charts.append(frozenset(comp))

    return charts


def _chart_distortion(chart_faces, seam_mask, edge_face_map,
                       edge_face_count, edge_scores) -> float:
    """Mean score of unseamed interior edges within a chart.

    Higher mean → more complex geometry → higher distortion potential.
    Returns 0.0 for trivial single-face charts.
    """
    if len(chart_faces) < 2:
        return 0.0

    total = 0.0
    count = 0
    for ei in range(len(edge_face_map)):
        if seam_mask[ei] or edge_face_count[ei] != 2:
            continue
        fi, fj = edge_face_map[ei][0], edge_face_map[ei][1]
        if fi in chart_faces and fj in chart_faces:
            total += edge_scores[ei]
            count += 1

    return total / count if count > 0 else 0.0


def _best_split_edge(chart_faces, seam_mask, edge_face_map,
                      edge_face_count, edge_scores):
    """Find the highest-scoring unseamed interior edge within a chart.

    Returns edge index or None if no candidate exists.
    """
    best_ei = None
    best_score = -1.0

    for ei in range(len(edge_face_map)):
        if seam_mask[ei] or edge_face_count[ei] != 2:
            continue
        fi, fj = edge_face_map[ei][0], edge_face_map[ei][1]
        if fi in chart_faces and fj in chart_faces:
            if edge_scores[ei] > best_score:
                best_score = edge_scores[ei]
                best_ei = ei

    return best_ei
