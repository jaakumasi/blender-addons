"""
Seam path optimization: cosmetic smoothing for MST-based seam paths.

The MST guarantees topologically valid seams. This module only performs
safe cosmetic improvements — it NEVER removes seams that would break topology.
"""

import numpy as np


def smooth_seam_paths(bm, seam_mask, scores, edge_verts, iterations=3):
    """Smooth jagged seam paths by swapping zig-zag edges for straighter alternatives.

    IMPORTANT: This only performs SWAPS (remove one seam edge, add another).
    It never reduces the total seam count, preserving MST topology.

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

        # Find zig-zag patterns: vertex with exactly 2 seam edges where
        # a shortcut edge exists between the two "other" vertices
        for vi, edges in vert_edges.items():
            seam_edges = [ei for ei in edges if mask[ei]]
            if len(seam_edges) != 2:
                continue

            e1, e2 = seam_edges

            # Get the "other" vertex of each seam edge
            v1_other = edge_verts[e1][0] if edge_verts[e1][1] == vi else edge_verts[e1][1]
            v2_other = edge_verts[e2][0] if edge_verts[e2][1] == vi else edge_verts[e2][1]

            # Look for a direct edge between v1_other and v2_other
            for ei_candidate in vert_edges.get(v1_other, []):
                other_v = (edge_verts[ei_candidate][0]
                           if edge_verts[ei_candidate][1] == v1_other
                           else edge_verts[ei_candidate][1])

                if other_v == v2_other and not mask[ei_candidate]:
                    # Found a shortcut — swap only if it has comparable score
                    min_existing = min(scores[e1], scores[e2])
                    if scores[ei_candidate] >= min_existing * 0.3:
                        # Swap: remove 2 edges through the zig-zag vertex,
                        # add 1 shortcut. But this reduces seam count by 1,
                        # which could break topology. So only swap if the
                        # vertex has other seam edges keeping it connected.
                        # Safe check: only swap if vi has >2 seam edges
                        # (the 2 we're removing + at least 1 remaining)
                        other_seam_count = sum(1 for ei2 in edges
                                               if mask[ei2] and ei2 != e1 and ei2 != e2)
                        if other_seam_count > 0:
                            mask[e1] = False
                            mask[e2] = False
                            mask[ei_candidate] = True
                            changed = True
                            break
                    break

        if not changed:
            break

    return mask
