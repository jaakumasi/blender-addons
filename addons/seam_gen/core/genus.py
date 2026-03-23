"""
Genus-aware topology for UV seam generation.

Detects the topological genus of the mesh and computes non-contractible loop
seams (homology generators) that MUST be cut for the mesh to unfold into a
disk.

Examples
--------
* Torus (genus 1)       → 2 generator loops
* Double torus (genus 2)→ 4 generator loops
* Sphere / cube (genus 0)→ 0 loops (standard MST is sufficient)

Algorithm: Tree-Cotree Decomposition
--------------------------------------
1. Build a spanning tree T on the vertex graph (prefer low-score / smooth
   edges so that generators land on high-score / sharp areas).
2. Build a dual spanning cotree T* on the face adjacency graph, using only
   dual edges whose primal is *not* in T.
3. Remaining interior edges (not in T, not dual-in-T*) = exactly 2g
   generator edges.
4. Each generator edge (u, v) is completed into a closed loop by appending
   the tree path from u to v (via their lowest common ancestor in T).
5. All edges in every loop are returned as forced seam candidates.
"""

import heapq

import numpy as np
from collections import deque


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_genus(n_verts: int, n_edges: int, n_faces: int,
                  n_boundary_loops: int = 0) -> int:
    """Return topological genus from Euler characteristic.

    For a closed orientable surface: χ = V - E + F,  g = (2 - χ) / 2.
    For a surface with *b* boundary loops: g = (2 - χ - b) / 2.

    Returns max(0, g) — negative results are clamped to 0.
    """
    chi = n_verts - n_edges + n_faces
    g = (2 - chi - n_boundary_loops) // 2
    return max(0, int(g))


def find_homology_generators(bm, edge_verts, edge_face_map,
                             edge_face_count, edge_scores):
    """Find non-contractible edge loops via tree-cotree decomposition.

    These loops *must* be marked as seams for the mesh to unfold into a
    topological disk.  The function is a no-op (returns []) for genus-0
    meshes (sphere, cube, cylinder with open caps, …).

    Args:
        bm:             BMesh in Edit Mode.
        edge_verts:     (E, 2) int32 — vertex index pairs per edge.
        edge_face_map:  list[list[int]] — face indices per edge.
        edge_face_count:(E,) int32 — faces per edge.
        edge_scores:    (E,) float64 — combined geometric scores [0, 1].

    Returns
        list[list[int]]: Each inner list is a set of edge indices that
        together form one non-contractible loop.  May be empty.
    """
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    V = len(bm.verts)
    E = len(bm.edges)
    F = len(bm.faces)

    if V == 0 or E == 0 or F == 0:
        return []

    n_boundary_loops = _count_boundary_loops(bm, edge_face_count)
    g = compute_genus(V, E, F, n_boundary_loops)

    if g == 0:
        return []

    # --- Step 1: primal spanning tree on vertices ----------------------------
    # Low-score edges enter the tree first; high-score edges are candidates
    # for generators (they tend to be at natural seam locations).
    primal_tree_edges, parent_edge, vert_depth = _build_primal_tree(
        V, edge_verts, edge_scores
    )

    # --- Step 2: dual spanning cotree on faces --------------------------------
    dual_cotree_edges = _build_dual_cotree(
        F, edge_face_map, edge_face_count, primal_tree_edges
    )

    # --- Step 3: generator edges (interior, not in T, not dual-in-T*) --------
    generator_edges = []
    for ei in range(E):
        if edge_face_count[ei] != 2:
            continue
        if ei in primal_tree_edges:
            continue
        if ei in dual_cotree_edges:
            continue
        generator_edges.append(ei)

    # Clamp to expected 2g generators; prefer high-scoring ones.
    expected = 2 * g
    if len(generator_edges) > expected:
        generator_edges.sort(key=lambda ei: edge_scores[ei], reverse=True)
        generator_edges = generator_edges[:expected]

    # --- Step 4: trace each generator into a closed loop ---------------------
    loops = []
    for gen_ei in generator_edges:
        loop = _trace_generator_loop(
            gen_ei, edge_verts, parent_edge, vert_depth
        )
        if loop:
            loops.append(loop)

    return loops


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _count_boundary_loops(bm, edge_face_count) -> int:
    """Count connected components of boundary edges (boundary loops)."""
    boundary_adj: dict[int, list[int]] = {}

    for edge in bm.edges:
        if edge_face_count[edge.index] == 1:
            v0 = edge.verts[0].index
            v1 = edge.verts[1].index
            boundary_adj.setdefault(v0, []).append(v1)
            boundary_adj.setdefault(v1, []).append(v0)

    if not boundary_adj:
        return 0

    visited: set[int] = set()
    components = 0
    for start in boundary_adj:
        if start in visited:
            continue
        components += 1
        stack = [start]
        while stack:
            v = stack.pop()
            if v in visited:
                continue
            visited.add(v)
            for nb in boundary_adj.get(v, []):
                if nb not in visited:
                    stack.append(nb)
    return components


def _build_primal_tree(n_verts: int, edge_verts, edge_scores):
    """Build a spanning tree on the vertex graph via greedy BFS (min-heap).

    Edges with *low* score are preferred in the tree, so that high-score
    (sharp / occluded) edges remain as generator candidates.

    Returns:
        tree_edges:  set of edge indices in the primal spanning tree.
        parent_edge: (V,) int32 — index of the edge connecting vertex i
                      to its parent (-1 for the root).
        vert_depth:  (V,) int32 — BFS depth from root.
    """
    # Build vertex adjacency: v → [(neighbour, edge_index)]
    adj: list[list[tuple[int, int]]] = [[] for _ in range(n_verts)]
    for ei in range(len(edge_verts)):
        v1, v2 = int(edge_verts[ei][0]), int(edge_verts[ei][1])
        adj[v1].append((v2, ei))
        adj[v2].append((v1, ei))

    parent_edge = np.full(n_verts, -1, dtype=np.int32)
    vert_depth = np.zeros(n_verts, dtype=np.int32)
    visited = np.zeros(n_verts, dtype=bool)
    tree_edges: set[int] = set()

    # heap: (score, edge_index, src_vertex, dst_vertex)
    heap: list[tuple[float, int, int, int]] = []
    visited[0] = True
    for nb, ei in adj[0]:
        heapq.heappush(heap, (float(edge_scores[ei]), ei, 0, nb))

    while heap:
        _, ei, src, dst = heapq.heappop(heap)
        if visited[dst]:
            continue
        visited[dst] = True
        parent_edge[dst] = ei
        vert_depth[dst] = vert_depth[src] + 1
        tree_edges.add(ei)
        for nb, next_ei in adj[dst]:
            if not visited[nb]:
                heapq.heappush(heap, (float(edge_scores[next_ei]), next_ei, dst, nb))

    return tree_edges, parent_edge, vert_depth


def _build_dual_cotree(n_faces: int, edge_face_map, edge_face_count,
                       primal_tree_edges: set) -> set:
    """Build a spanning cotree on the face adjacency graph.

    Only dual edges whose primal is *not* in the primal spanning tree are
    eligible (the others are "used up" by the primal tree).

    Returns set of edge indices whose dual is in the cotree.
    """
    # Face adjacency restricted to non-primal-tree interior edges.
    face_adj: list[list[tuple[int, int]]] = [[] for _ in range(n_faces)]
    for ei in range(len(edge_face_map)):
        if edge_face_count[ei] != 2:
            continue
        if ei in primal_tree_edges:
            continue
        fi, fj = edge_face_map[ei][0], edge_face_map[ei][1]
        face_adj[fi].append((fj, ei))
        face_adj[fj].append((fi, ei))

    visited = np.zeros(n_faces, dtype=bool)
    cotree_edges: set[int] = set()

    queue: deque[int] = deque([0])
    visited[0] = True
    while queue:
        fi = queue.popleft()
        for fj, ei in face_adj[fi]:
            if not visited[fj]:
                visited[fj] = True
                cotree_edges.add(ei)
                queue.append(fj)

    return cotree_edges


def _trace_generator_loop(gen_ei: int, edge_verts, parent_edge,
                           vert_depth) -> list[int]:
    """Trace a generator edge into a closed non-contractible loop.

    Loop = generator_edge  +  tree-path(v_start → LCA)
                           +  tree-path(v_end   → LCA)

    Uses depth-based LCA walking (O(depth)).

    Returns list of edge indices forming the loop, or [gen_ei] as fallback.
    """
    v_start = int(edge_verts[gen_ei][0])
    v_end = int(edge_verts[gen_ei][1])

    path_start: list[int] = []
    path_end: list[int] = []
    cur_s = v_start
    cur_e = v_end

    # Walk both vertices up to the same depth, collecting edge indices.
    for _ in range(len(vert_depth) + 1):
        if cur_s == cur_e:
            break

        d_s = int(vert_depth[cur_s])
        d_e = int(vert_depth[cur_e])

        if d_s >= d_e:
            pe = int(parent_edge[cur_s])
            if pe == -1:
                break
            path_start.append(pe)
            v0, v1 = int(edge_verts[pe][0]), int(edge_verts[pe][1])
            cur_s = v0 if v1 == cur_s else v1

        if cur_s == cur_e:
            break

        d_s = int(vert_depth[cur_s])
        d_e = int(vert_depth[cur_e])

        if d_e >= d_s:
            pe = int(parent_edge[cur_e])
            if pe == -1:
                break
            path_end.append(pe)
            v0, v1 = int(edge_verts[pe][0]), int(edge_verts[pe][1])
            cur_e = v0 if v1 == cur_e else v1

    if cur_s != cur_e:
        # LCA not found — return the generator edge alone as a minimal cut.
        return [gen_ei]

    return [gen_ei] + path_start + path_end
