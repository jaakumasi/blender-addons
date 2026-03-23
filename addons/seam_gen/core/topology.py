"""
Loop-first seam extraction with topological validation.

Algorithm:
1. Take scored edge loops (closed rings, partial chains)
2. Greedily add the highest-scoring loops as seams
3. After each addition, check if all face charts are topological disks
4. When all charts are disks → DONE (minimal, artist-quality seams)
5. If no more loops available but charts aren't disks yet, add single
   high-scoring edges to complete the cuts

This produces the same seam patterns an artist would choose:
- Cylinder: ring cuts around caps + one vertical seam
- Torus: one ring cut + one tube cut = flat rectangle
- Cube: edge loops along axes = cross-shaped unfolding
- Cone: base ring + one side edge = fan + circle
"""

import numpy as np
from collections import deque


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_loop_seams(edge_face_map, edge_face_count, edge_weights,
                       n_faces, scored_loops, edge_verts, n_verts,
                       n_islands=1):
    """Loop-first seam extraction.

    Args:
        edge_face_map:  list[list[int]] per edge
        edge_face_count: (E,) int32
        edge_weights:   (E,) float64 combined geometric scores
        n_faces:        total face count
        scored_loops:   list of loop dicts from loop_detection, sorted best-first
        edge_verts:     (E, 2) int32
        n_verts:        total vertex count
        n_islands:      target island count (1 = single island or natural islands)

    Returns (E,) boolean seam mask.
    """
    E = len(edge_face_count)
    seam_mask = np.zeros(E, dtype=bool)

    # Boundary edges are always seams
    for ei in range(E):
        if edge_face_count[ei] == 1:
            seam_mask[ei] = True

    if n_faces < 2:
        return seam_mask

    # Build face adjacency for chart validation
    face_adj_edges = _build_face_adj(edge_face_map, edge_face_count, E, n_faces)

    # Count how many closed loops we have
    closed_loops = [lp for lp in scored_loops
                    if lp.get('is_closed') and len(lp.get('edges', [])) >= 3]

    if closed_loops:
        # Phase 1: Loop-first approach — greedily add closed loops as seams
        for lp in closed_loops:
            edges = lp['edges']

            # Add this loop's edges as seams
            for ei in edges:
                seam_mask[ei] = True

            # Check if all charts are now topological disks
            charts = _label_charts(seam_mask, edge_face_map, edge_face_count, n_faces)
            all_valid = _all_charts_are_disks(
                charts, seam_mask, edge_face_map, edge_face_count,
                edge_verts, n_verts, n_faces
            )

            if all_valid:
                break
    else:
        # Phase 1b: No loops available — use MST fallback for simple meshes
        # (cube, cone, cylinder with no quad loops)
        seam_mask = _mst_fallback(
            seam_mask, edge_face_map, edge_face_count,
            edge_weights, n_faces
        )

    # Phase 2: If charts still aren't valid, add single high-scoring edges
    charts = _label_charts(seam_mask, edge_face_map, edge_face_count, n_faces)
    if not _all_charts_are_disks(
        charts, seam_mask, edge_face_map, edge_face_count,
        edge_verts, n_verts, n_faces
    ):
        seam_mask = _complete_with_singles(
            seam_mask, edge_weights, edge_face_map, edge_face_count,
            edge_verts, n_verts, n_faces
        )

    # Phase 3: Multi-island splitting (if requested)
    if n_islands > 1:
        charts = _label_charts(seam_mask, edge_face_map, edge_face_count, n_faces)
        current_islands = int(charts.max()) + 1
        if current_islands < n_islands and scored_loops:
            # Add more loops to create additional islands
            for lp in scored_loops:
                if current_islands >= n_islands:
                    break
                edges = lp['edges']
                # Only add loops that would actually split an existing chart
                already_seam = all(seam_mask[ei] for ei in edges)
                if already_seam:
                    continue
                for ei in edges:
                    seam_mask[ei] = True
                new_charts = _label_charts(seam_mask, edge_face_map, edge_face_count, n_faces)
                new_islands = int(new_charts.max()) + 1
                if new_islands > current_islands:
                    current_islands = new_islands

    return seam_mask


# ---------------------------------------------------------------------------
# Chart labeling
# ---------------------------------------------------------------------------

def _build_face_adj(edge_face_map, edge_face_count, E, n_faces):
    """Build face adjacency: face_adj[f] = [(neighbor_face, edge_index), ...]"""
    face_adj = [[] for _ in range(n_faces)]
    for ei in range(E):
        if edge_face_count[ei] == 2:
            fi, fj = edge_face_map[ei][0], edge_face_map[ei][1]
            face_adj[fi].append((fj, ei))
            face_adj[fj].append((fi, ei))
    return face_adj


def _label_charts(seam_mask, edge_face_map, edge_face_count, n_faces):
    """BFS over non-seam face adjacency. Returns (F,) int32 chart labels."""
    labels = np.full(n_faces, -1, dtype=np.int32)
    chart_id = 0

    # Build non-seam face adjacency
    non_seam_adj = [[] for _ in range(n_faces)]
    for ei in range(len(seam_mask)):
        if edge_face_count[ei] == 2 and not seam_mask[ei]:
            fi, fj = edge_face_map[ei][0], edge_face_map[ei][1]
            non_seam_adj[fi].append(fj)
            non_seam_adj[fj].append(fi)

    for seed in range(n_faces):
        if labels[seed] >= 0:
            continue
        q = deque([seed])
        labels[seed] = chart_id
        while q:
            f = q.popleft()
            for nb in non_seam_adj[f]:
                if labels[nb] < 0:
                    labels[nb] = chart_id
                    q.append(nb)
        chart_id += 1

    return labels


# ---------------------------------------------------------------------------
# Topological disk validation
# ---------------------------------------------------------------------------

def _all_charts_are_disks(charts, seam_mask, edge_face_map, edge_face_count,
                          edge_verts, n_verts, n_faces):
    """Check if every chart is a topological disk.

    A chart is a valid UV island (topological disk) if:
    1. It's connected (guaranteed by chart labeling)
    2. It has at least one boundary edge (seam or mesh boundary)
    3. It has no interior "handles" (genus = 0 within the chart)

    We check condition 3 via Euler characteristic:
    For a chart treated as a surface with boundary:
      chi = V_chart - E_interior - E_boundary + F_chart
    where E_boundary counts seam/boundary edges of this chart.
    For a disk: chi = 1. For a cylinder: chi = 0. For genus-g: chi = 1-2g.

    But for UV unwrapping, the key practical check is simpler:
    does this chart have a CONNECTED boundary? If the boundary forms
    one connected loop, the chart is a disk. If it forms multiple
    disconnected loops, it has holes.
    """
    n_charts = int(charts.max()) + 1 if n_faces > 0 else 0
    E = len(seam_mask)

    for ci in range(n_charts):
        chart_faces = set(np.where(charts == ci)[0].tolist())
        if len(chart_faces) <= 1:
            continue  # Single face is always a disk

        # Find boundary edges of this chart: seam edges or mesh boundary
        # edges that touch this chart
        boundary_edges = []
        has_boundary = False

        for ei in range(E):
            fc = edge_face_count[ei]
            chart_face_count = 0
            for fi in edge_face_map[ei][:fc]:
                if fi in chart_faces:
                    chart_face_count += 1

            if chart_face_count == 0:
                continue

            # Boundary edge: either a seam edge touching this chart,
            # or a mesh boundary (1-face edge) in this chart
            is_boundary = False
            if seam_mask[ei] and chart_face_count >= 1:
                is_boundary = True
            elif fc == 1 and chart_face_count == 1:
                is_boundary = True

            if is_boundary:
                boundary_edges.append(ei)
                has_boundary = True

        # A chart with no boundary can't be a disk (it's a closed surface)
        if not has_boundary:
            return False

        # Check boundary connectivity: all boundary edges should form
        # one connected component (one boundary loop = disk,
        # multiple loops = has holes = not a disk)
        if len(boundary_edges) > 0:
            # Build boundary vertex adjacency
            boundary_verts = {}
            for ei in boundary_edges:
                v0, v1 = int(edge_verts[ei][0]), int(edge_verts[ei][1])
                boundary_verts.setdefault(v0, []).append(ei)
                boundary_verts.setdefault(v1, []).append(ei)

            # BFS on boundary edges
            visited_be = set()
            start = boundary_edges[0]
            queue = deque([start])
            visited_be.add(start)
            while queue:
                cur = queue.popleft()
                v0, v1 = int(edge_verts[cur][0]), int(edge_verts[cur][1])
                for v in (v0, v1):
                    for nb_ei in boundary_verts.get(v, []):
                        if nb_ei not in visited_be:
                            visited_be.add(nb_ei)
                            queue.append(nb_ei)

            # If not all boundary edges are connected, multiple boundary loops
            if len(visited_be) < len(boundary_edges):
                return False

    return True


# ---------------------------------------------------------------------------
# Single-edge fallback for incomplete charts
# ---------------------------------------------------------------------------

def _mst_fallback(seam_mask, edge_face_map, edge_face_count,
                   edge_weights, n_faces):
    """MST complement fallback for meshes with no detected edge loops.

    Used for simple meshes like cubes, cones, and cylinders where the
    loop detector can't find quad-traversal loops.
    """
    mask = seam_mask.copy()
    interior_edges, _ = build_face_adjacency(edge_face_map, edge_face_count)

    if not interior_edges or n_faces < 2:
        return mask

    # Kruskal's MST: sort by score ascending (smooth edges enter tree first)
    sorted_edges = sorted(interior_edges, key=lambda x: edge_weights[x[0]])

    uf = UnionFind(n_faces)
    mst_edges = set()

    for ei, fi, fj in sorted_edges:
        if mask[ei]:  # Skip already-marked seam edges
            continue
        if uf.union(fi, fj):
            mst_edges.add(ei)

    # Interior edges NOT in MST = seams
    for ei, fi, fj in interior_edges:
        if ei not in mst_edges and not mask[ei]:
            mask[ei] = True

    return mask


def _complete_with_singles(seam_mask, edge_weights, edge_face_map,
                           edge_face_count, edge_verts, n_verts, n_faces,
                           max_iterations=200):
    """Add single high-scoring edges to make all charts into disks.

    This is the fallback when loops alone aren't sufficient (e.g., the
    mesh has no clean loops, or the topology requires additional cuts).
    """
    mask = seam_mask.copy()

    # Sort non-seam interior edges by score descending
    candidates = []
    for ei in range(len(mask)):
        if not mask[ei] and edge_face_count[ei] == 2:
            candidates.append((edge_weights[ei], ei))
    candidates.sort(reverse=True)

    for iteration in range(min(max_iterations, len(candidates))):
        charts = _label_charts(mask, edge_face_map, edge_face_count, n_faces)
        if _all_charts_are_disks(charts, mask, edge_face_map, edge_face_count,
                                  edge_verts, n_verts, n_faces):
            break

        # Find the highest-scoring non-seam edge and add it
        if iteration < len(candidates):
            _, ei = candidates[iteration]
            mask[ei] = True

    return mask


# ---------------------------------------------------------------------------
# Legacy API (kept for backwards compatibility)
# ---------------------------------------------------------------------------

class UnionFind:
    """Disjoint set data structure."""
    __slots__ = ('parent', 'rank')

    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        return True


def build_face_adjacency(edge_face_map, edge_face_count):
    """Build face adjacency from edge-face relationships."""
    interior_edges = []
    boundary_edges = []
    for ei in range(len(edge_face_map)):
        fc = edge_face_count[ei]
        if fc == 2:
            fi, fj = edge_face_map[ei][0], edge_face_map[ei][1]
            interior_edges.append((ei, fi, fj))
        elif fc == 1:
            boundary_edges.append(ei)
    return interior_edges, boundary_edges
