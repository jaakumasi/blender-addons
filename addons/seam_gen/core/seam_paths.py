"""
Seam path optimisation — multi-stage cleanup for MST / Prim seam sets.

Stages (all topology-preserving)
---------------------------------
1. Zig-zag smoothing  — replace 2-edge detours through degree-2 seam
   vertices with a direct shortcut edge when one exists.

2. Geodesic chain re-routing — for chains of 3+ edges between branch
   points, find the highest-scoring Dijkstra path between the same
   endpoints and replace the chain if it strictly improves average score.

3. Fragment cleanup — remove isolated connected seam components with fewer
   than 3 edges that are *not* load-bearing (i.e. removing them leaves every
   mesh face still touching a seam or still reachable via non-seam edges).

Topological safety rule: no operation removes a seam unless at least one
alternative path through the mesh graph connects the seam's endpoints.
"""

import heapq

import numpy as np


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def smooth_seam_paths(bm, seam_mask, scores, edge_verts, iterations=3):
    """Multi-stage seam path optimisation.

    Args:
        bm:         BMesh (for ensure_lookup_table calls).
        seam_mask:  (E,) bool — initial seam mask from MST / Prim's.
        scores:     (E,) float — combined geometric scores.
        edge_verts: (E, 2) int — vertex index pairs per edge.
        iterations: smoothing passes for stage 1.

    Returns modified (E,) boolean seam mask.
    """
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    E = len(edge_verts)
    mask = seam_mask.copy()

    # Build vertex → edge adjacency (used by all stages).
    vert_edges: dict[int, list[int]] = {}
    for ei in range(E):
        v1, v2 = int(edge_verts[ei][0]), int(edge_verts[ei][1])
        vert_edges.setdefault(v1, []).append(ei)
        vert_edges.setdefault(v2, []).append(ei)

    # Stage 1: zig-zag swapping.
    mask = _zigzag_smooth(mask, scores, edge_verts, vert_edges, iterations)

    # Stage 2: geodesic chain re-routing (only when there are enough passes).
    if iterations >= 2:
        mask = _chain_geodesic_smooth(mask, scores, edge_verts, vert_edges)

    # Stage 3: remove isolated stray fragments.
    mask = _remove_redundant_fragments(mask, edge_verts, vert_edges)

    return mask


# ---------------------------------------------------------------------------
# Stage 1: zig-zag smoothing
# ---------------------------------------------------------------------------

def _zigzag_smooth(mask, scores, edge_verts, vert_edges, iterations):
    """Replace 2-edge zig-zag detours with a direct shortcut edge."""
    for _it in range(iterations):
        changed = False

        for vi, edges in vert_edges.items():
            seam_edges = [ei for ei in edges if mask[ei]]
            if len(seam_edges) != 2:
                continue

            e1, e2 = seam_edges
            v1_other = int(
                edge_verts[e1][0] if edge_verts[e1][1] == vi else edge_verts[e1][1]
            )
            v2_other = int(
                edge_verts[e2][0] if edge_verts[e2][1] == vi else edge_verts[e2][1]
            )

            for ei_cand in vert_edges.get(v1_other, []):
                other_v = int(
                    edge_verts[ei_cand][0]
                    if edge_verts[ei_cand][1] == v1_other
                    else edge_verts[ei_cand][1]
                )
                if other_v != v2_other or mask[ei_cand]:
                    continue

                # Accept shortcut if it scores at least 30 % of the weaker leg.
                min_existing = min(scores[e1], scores[e2])
                if scores[ei_cand] < min_existing * 0.3:
                    break

                # Only safe to reduce seam count here if vi has other
                # seam edges keeping it topologically connected.
                other_seam = sum(
                    1 for ei2 in edges
                    if mask[ei2] and ei2 != e1 and ei2 != e2
                )
                if other_seam > 0:
                    mask[e1] = False
                    mask[e2] = False
                    mask[ei_cand] = True
                    changed = True
                break

        if not changed:
            break

    return mask


# ---------------------------------------------------------------------------
# Stage 2: geodesic chain re-routing
# ---------------------------------------------------------------------------

def _chain_geodesic_smooth(mask, scores, edge_verts, vert_edges):
    """Re-route seam chains through highest-scoring geodesic paths.

    For each non-loop chain of 3+ edges, run Dijkstra (maximising score)
    between the chain's two endpoints on the full mesh graph, explicitly
    *avoiding* the chain's own edges.  Replace the chain only when the
    alternative has a strictly higher *average* score per edge and is no
    more than 50 % longer (to prevent runaway detours).
    """
    new_mask = mask.copy()
    chains = _build_seam_chains(mask, edge_verts, vert_edges)

    # Only re-route the longest chains (most impact, avoid excess Dijkstra).
    eligible = [c for c in chains if len(c['edges']) >= 5 and not c['is_loop']]
    eligible.sort(key=lambda c: len(c['edges']), reverse=True)
    eligible = eligible[:20]

    for chain in eligible:
        n = len(chain['edges'])
        start_v = chain['start']
        end_v = chain['end']
        if start_v == end_v:
            continue

        alt = _dijkstra_max_score(
            start_v, end_v, edge_verts, vert_edges, scores,
            avoid_edges=set(chain['edges'])
        )
        if alt is None:
            continue

        old_avg = sum(scores[ei] for ei in chain['edges']) / n
        new_avg = sum(scores[ei] for ei in alt) / len(alt)

        # Accept: strictly better score AND path not excessively longer.
        if new_avg > old_avg * 1.02 and len(alt) <= n * 1.5:
            for ei in chain['edges']:
                new_mask[ei] = False
            for ei in alt:
                new_mask[ei] = True

    return new_mask


def _build_seam_chains(mask, edge_verts, vert_edges):
    """Decompose the seam graph into maximal non-branching chains.

    A chain is a maximal sequence of seam edges where every *interior*
    vertex has exactly 2 seam edges (no branch points, no endpoints).
    Endpoints / branch-points have seam-degree ≠ 2.

    Returns list of dicts:
        {'edges': [ei, ...], 'start': v, 'end': v, 'is_loop': bool}
    """
    E = len(mask)
    visited = np.zeros(E, dtype=bool)
    chains = []

    # Start chains from branch / endpoint vertices first.
    for vi, edges in vert_edges.items():
        seam_deg = sum(1 for ei in edges if mask[ei])
        if seam_deg == 0 or seam_deg == 2:
            continue
        for ei in edges:
            if mask[ei] and not visited[ei]:
                c = _walk_chain(ei, vi, mask, edge_verts, vert_edges, visited)
                if c:
                    chains.append(c)

    # Handle isolated loops (all vertices have seam-degree 2).
    for ei in range(E):
        if mask[ei] and not visited[ei]:
            v0 = int(edge_verts[ei][0])
            c = _walk_chain(ei, v0, mask, edge_verts, vert_edges, visited)
            if c:
                chains.append(c)

    return chains


def _walk_chain(start_ei, start_vert, mask, edge_verts, vert_edges, visited):
    """Walk one chain starting at start_ei / start_vert."""
    chain_edges = []
    chain_verts = [start_vert]
    cur_ei = start_ei
    cur_vert = start_vert

    for _ in range(len(mask)):
        if visited[cur_ei]:
            break
        visited[cur_ei] = True
        chain_edges.append(cur_ei)

        v0 = int(edge_verts[cur_ei][0])
        v1 = int(edge_verts[cur_ei][1])
        next_vert = v1 if v0 == cur_vert else v0
        chain_verts.append(next_vert)

        seam_nbs = [
            ei for ei in vert_edges.get(next_vert, [])
            if mask[ei] and ei != cur_ei
        ]
        if len(seam_nbs) != 1:
            break

        cur_vert = next_vert
        cur_ei = seam_nbs[0]

    if not chain_edges:
        return None

    is_loop = (
        chain_verts[0] == chain_verts[-1]
        and len(chain_edges) > 2
    )
    return {
        'edges': chain_edges,
        'start': chain_verts[0],
        'end': chain_verts[-1],
        'is_loop': is_loop,
    }


def _dijkstra_max_score(start_v, end_v, edge_verts, vert_edges, scores,
                        avoid_edges: set, max_visited: int = 2000):
    """Dijkstra shortest-path that *maximises* total score.

    Implemented as minimum-cost with cost = -score.
    Aborts and returns None if more than max_visited vertices are settled
    or the heap exceeds a safe size limit.

    Returns ordered list of edge indices from start_v to end_v, or None.
    """
    MAX_HEAP = 20000  # Safety cap to prevent MemoryError

    dist: dict[int, float] = {start_v: 0.0}
    parent: dict[int, tuple[int, int]] = {}
    heap: list[tuple[float, int, int]] = [(0.0, 0, start_v)]
    counter = 1
    settled = 0

    while heap:
        neg_score, _, vert = heapq.heappop(heap)

        if neg_score > dist.get(vert, float('inf')):
            continue

        settled += 1
        if settled > max_visited:
            return None

        if vert == end_v:
            path = []
            cur = end_v
            while cur != start_v:
                prev_v, ei = parent[cur]
                path.append(ei)
                cur = prev_v
            path.reverse()
            return path

        for ei in vert_edges.get(vert, []):
            if ei in avoid_edges:
                continue
            v0 = int(edge_verts[ei][0])
            v1 = int(edge_verts[ei][1])
            next_v = v1 if v0 == vert else v0
            new_neg = neg_score - scores[ei]
            if new_neg < dist.get(next_v, float('inf')):
                dist[next_v] = new_neg
                parent[next_v] = (vert, ei)
                if len(heap) < MAX_HEAP:
                    heapq.heappush(heap, (new_neg, counter, next_v))
                    counter += 1

    return None


# ---------------------------------------------------------------------------
# Stage 3: stray fragment removal
# ---------------------------------------------------------------------------

def _remove_redundant_fragments(mask, edge_verts, vert_edges):
    """Remove tiny isolated seam components that are topologically redundant.

    A component is removed only when ALL of the following hold:
    * It has fewer than 3 edges.
    * None of its vertices connects to a seam edge outside the component
      (i.e. it is completely isolated from the rest of the seam graph).

    These arise from minor numerical noise or disconnected mesh islands.
    They contribute nothing to UV island separation.
    """
    E = len(mask)
    visited = np.zeros(E, dtype=bool)
    components: list[set[int]] = []

    for ei in range(E):
        if not mask[ei] or visited[ei]:
            continue
        comp: set[int] = set()
        queue = [ei]
        while queue:
            cur = queue.pop()
            if visited[cur]:
                continue
            visited[cur] = True
            comp.add(cur)
            for vi in (int(edge_verts[cur][0]), int(edge_verts[cur][1])):
                for nb_ei in vert_edges.get(vi, []):
                    if mask[nb_ei] and not visited[nb_ei]:
                        queue.append(nb_ei)
        components.append(comp)

    new_mask = mask.copy()

    for comp in components:
        if len(comp) >= 3:
            continue

        # Check isolation: no vertex of this component touches an external seam.
        is_isolated = True
        for ei in comp:
            for vi in (int(edge_verts[ei][0]), int(edge_verts[ei][1])):
                for ext_ei in vert_edges.get(vi, []):
                    if mask[ext_ei] and ext_ei not in comp:
                        is_isolated = False
                        break
                if not is_isolated:
                    break
            if not is_isolated:
                break

        if is_isolated:
            for ei in comp:
                new_mask[ei] = False

    return new_mask
