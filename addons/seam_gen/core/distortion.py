"""
UV chart distortion estimation and adaptive seam splitting.

After initial seam placement, this module identifies UV charts (connected
face regions bounded by seams) that are geometrically complex — meaning they
contain many high-scoring interior edges that ideally should have been seams
but were kept for MST connectivity.

The adaptive splitter adds one seam edge at a time to the highest-distortion
chart (the edge with the highest geometric score inside that chart), repeating
until all charts fall below the distortion threshold or the split budget is
exhausted.

All per-chart statistics are computed in a single vectorized pass over edges
per iteration, avoiding the previous O(charts × edges) full-scan.
"""

import numpy as np
from collections import deque


def adaptive_chart_splitting(seam_mask, edge_scores, edge_face_map,
                              edge_face_count, n_faces,
                              max_splits: int = 8,
                              distortion_threshold: float = 0.55,
                              edge_face_pairs=None):
    """Adaptively split high-distortion UV charts by adding seam edges.

    Args:
        seam_mask:            (E,) bool — current seam set (copied, not mutated).
        edge_scores:          (E,) float — combined geometric scores [0, 1].
        edge_face_map:        list[list[int]] — face indices per edge.
        edge_face_count:      (E,) int32.
        n_faces:              total face count.
        max_splits:           upper bound on extra seam edges added.
        distortion_threshold: charts with mean score above this are split.
        edge_face_pairs:      (E, 2) int32 optional — fast face-pair array.

    Returns modified (E,) boolean seam mask.
    """
    mask = seam_mask.copy()
    E = len(mask)
    two_face = edge_face_count == 2

    # Build edge_face_pairs if not provided
    if edge_face_pairs is None:
        efp = np.full((E, 2), -1, dtype=np.int32)
        for ei in range(E):
            if edge_face_count[ei] == 2:
                efp[ei, 0] = edge_face_map[ei][0]
                efp[ei, 1] = edge_face_map[ei][1]
    else:
        efp = edge_face_pairs

    # Compute a relative threshold: only split if the chart's mean score
    # is significantly above the overall mean. This prevents splitting on
    # uniform-score meshes (e.g. a cube where all edges score ~0.5).
    global_mean = float(edge_scores[two_face].mean()) if two_face.any() else 0.5
    # Effective threshold: the higher of the user threshold or
    # (global_mean + 0.15).  On a cube (global ~0.56) this becomes 0.71,
    # which no chart can exceed → no splits.  On organic meshes with
    # varied scores, the user threshold dominates.
    effective_threshold = max(distortion_threshold,
                              global_mean + 0.15)

    for _ in range(max_splits):
        face_chart = _label_charts(mask, efp, two_face, n_faces)
        n_charts = int(face_chart.max()) + 1 if n_faces > 0 else 0
        if n_charts == 0:
            break

        # Non-seam interior edges (candidates for scoring and splitting)
        interior = two_face & (~mask)
        idx = np.where(interior)[0]
        if len(idx) == 0:
            break

        fi = efp[idx, 0]
        fj = efp[idx, 1]
        ci = face_chart[fi]
        same = ci == face_chart[fj]
        idx = idx[same]
        ci = ci[same]
        scores = edge_scores[idx]

        if len(idx) == 0:
            break

        # Per-chart statistics (single vectorized pass)
        chart_total = np.zeros(n_charts, dtype=np.float64)
        chart_count = np.zeros(n_charts, dtype=np.int64)
        np.add.at(chart_total, ci, scores)
        np.add.at(chart_count, ci, 1)

        chart_mean = np.zeros(n_charts, dtype=np.float64)
        valid_charts = chart_count > 0
        chart_mean[valid_charts] = chart_total[valid_charts] / chart_count[valid_charts]
        worst_ci = int(np.argmax(chart_mean))

        # Don't split charts with very few interior edges (already small)
        if chart_count[worst_ci] < 4:
            break

        if chart_mean[worst_ci] <= effective_threshold:
            break

        # Best split edge in worst chart
        worst_mask = ci == worst_ci
        if not np.any(worst_mask):
            break
        worst_idx = idx[worst_mask]
        worst_scores = scores[worst_mask]
        best_local = int(np.argmax(worst_scores))
        mask[worst_idx[best_local]] = True

    return mask


def _label_charts(seam_mask, efp, two_face, n_faces):
    """BFS over non-seam face adjacency. Returns (F,) int32 chart labels."""
    interior = two_face & (~seam_mask)
    idx = np.where(interior)[0]
    fi = efp[idx, 0]
    fj = efp[idx, 1]

    face_adj: list[list[int]] = [[] for _ in range(n_faces)]
    for a, b in zip(fi.tolist(), fj.tolist()):
        face_adj[a].append(b)
        face_adj[b].append(a)

    labels = np.full(n_faces, -1, dtype=np.int32)
    chart_id = 0
    for seed in range(n_faces):
        if labels[seed] >= 0:
            continue
        q: deque[int] = deque([seed])
        labels[seed] = chart_id
        while q:
            f = q.popleft()
            for nb in face_adj[f]:
                if labels[nb] < 0:
                    labels[nb] = chart_id
                    q.append(nb)
        chart_id += 1

    return labels
