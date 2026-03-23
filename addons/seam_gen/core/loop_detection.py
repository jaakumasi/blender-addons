"""
Edge loop detection and scoring for seam placement.

Detects continuous edge loops on the mesh using the standard "opposite edge
across quad" traversal.  Each loop is scored by how well it would serve as a
seam: completeness (closed loops score higher), normal-cluster separation
across the loop, and mean dihedral angle of loop edges.

The scored loops feed into the seam pipeline in two ways:
1. Per-edge "loop coherence" signal — edges on high-quality loops get high
   scores, making entire loops light up as coherent seam candidates.
2. Structural loop selection — the top loops are forced as seams before the
   spanning tree runs, ensuring clean continuous cuts.
"""

import numpy as np


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_edge_loops(edge_verts, vert_edge_map, edge_face_map,
                      edge_face_count):
    """Detect edge loops via opposite-edge-across-quad traversal.

    For each unvisited edge, walks in both directions following the "opposite
    edge" rule: at a valence-4 vertex in a quad face, the opposite edge is
    the one that doesn't share a face with the current edge.

    Args:
        edge_verts:      (E, 2) int32 — vertex pairs per edge.
        vert_edge_map:   list[list[int]] — edge indices per vertex.
        edge_face_map:   list[list[int]] — face indices per edge.
        edge_face_count: (E,) int32 — face count per edge.

    Returns list of dicts, each with:
        'edges':     list[int] — ordered edge indices in the loop
        'verts':     list[int] — ordered vertex indices
        'is_closed': bool — True if the loop forms a complete ring
    """
    E = len(edge_verts)
    visited = np.zeros(E, dtype=bool)

    # Precompute face → edge sets for fast opposite-edge lookup.
    max_face = 0
    for faces in edge_face_map:
        for fi in faces:
            if fi > max_face:
                max_face = fi
    face_edges: list[list[int]] = [[] for _ in range(max_face + 1)]
    for ei in range(E):
        for fi in edge_face_map[ei]:
            face_edges[fi].append(ei)

    loops = []

    for start_ei in range(E):
        if visited[start_ei]:
            continue
        # Only start from interior edges (2 faces).
        if edge_face_count[start_ei] != 2:
            visited[start_ei] = True
            continue

        # Walk in both directions from start_ei.
        fwd_edges, fwd_verts, fwd_closed = _walk_loop_direction(
            start_ei, 0, edge_verts, vert_edge_map, edge_face_map,
            edge_face_count, face_edges, visited
        )
        if fwd_closed:
            # Closed loop found in forward direction alone.
            for ei in fwd_edges:
                visited[ei] = True
            loops.append({
                'edges': fwd_edges,
                'verts': fwd_verts,
                'is_closed': True,
            })
            continue

        bwd_edges, bwd_verts, bwd_closed = _walk_loop_direction(
            start_ei, 1, edge_verts, vert_edge_map, edge_face_map,
            edge_face_count, face_edges, visited
        )

        # Combine: reverse backward + forward.
        if bwd_edges:
            combined_edges = list(reversed(bwd_edges)) + fwd_edges
            combined_verts = list(reversed(bwd_verts)) + fwd_verts
        else:
            combined_edges = fwd_edges
            combined_verts = fwd_verts

        is_closed = (len(combined_verts) >= 3
                     and combined_verts[0] == combined_verts[-1])

        for ei in combined_edges:
            visited[ei] = True

        if len(combined_edges) >= 3:
            loops.append({
                'edges': combined_edges,
                'verts': combined_verts,
                'is_closed': is_closed,
            })

    return loops


def score_loops(loops, face_normals, edge_face_pairs, edge_face_count,
                dihedral_scores):
    """Score each loop by structural importance for seam placement.

    Scoring factors:
    1. Completeness: closed loops get a 1.5x bonus.
    2. Normal separation: fraction of loop edges where the two adjacent faces
       have normals diverging by more than 30°. High separation → natural
       seam location.
    3. Mean dihedral: average dihedral score of loop edges. Higher → sharper
       → better seam.
    4. Length bonus: longer loops score higher (they produce more meaningful
       cuts than short loops).

    Adds 'score' key to each loop dict. Returns sorted list (best first).
    """
    if not loops:
        return loops

    cos_30 = float(np.cos(np.radians(30.0)))

    # Maximum possible loop length for normalization.
    max_len = max(len(lp['edges']) for lp in loops)

    for lp in loops:
        edges = lp['edges']
        n = len(edges)
        if n == 0:
            lp['score'] = 0.0
            continue

        edge_arr = np.array(edges, dtype=np.int32)

        # Mean dihedral score of loop edges.
        mean_dih = float(np.mean(dihedral_scores[edge_arr]))

        # Normal separation: how many loop edges straddle different-facing regions.
        two_face = edge_face_count[edge_arr] == 2
        n_two = int(np.sum(two_face))
        separation = 0.0
        if n_two > 0:
            tf_idx = edge_arr[two_face]
            f1 = edge_face_pairs[tf_idx, 0]
            f2 = edge_face_pairs[tf_idx, 1]
            dots = np.einsum('ij,ij->i', face_normals[f1], face_normals[f2])
            # Count edges where normals diverge more than 30°.
            separation = float(np.mean(dots < cos_30))

        # Completeness bonus.
        closed_bonus = 1.5 if lp['is_closed'] else 1.0

        # Length factor: longer loops are proportionally more valuable.
        length_factor = min(1.0, n / max(max_len * 0.5, 1.0))

        # Combined score.
        score = closed_bonus * (
            0.35 * mean_dih
            + 0.35 * separation
            + 0.30 * length_factor
        )

        lp['score'] = float(score)

    loops.sort(key=lambda lp: lp['score'], reverse=True)
    return loops


def compute_loop_coherence_scores(E, scored_loops):
    """Convert scored loops into per-edge coherence scores.

    Each edge gets the maximum loop score across all loops it belongs to.
    Edges not in any loop get 0.0.

    Returns (E,) float64 array in [0, 1].
    """
    scores = np.zeros(E, dtype=np.float64)

    for lp in scored_loops:
        s = lp.get('score', 0.0)
        for ei in lp['edges']:
            if s > scores[ei]:
                scores[ei] = s

    # Normalize to [0, 1].
    mx = scores.max() if E > 0 else 0.0
    if mx > 1e-10:
        scores /= mx

    return scores


# ---------------------------------------------------------------------------
# Structural loop selection
# ---------------------------------------------------------------------------

def select_structural_loops(scored_loops, genus, n_faces):
    """Select the best loops to force as seams.

    Strategy:
    - For genus > 0: need at least 2*genus loops for homology cuts.
    - Additional loops are selected greedily if they meaningfully partition
      the mesh (score above threshold).
    - Budget: at most sqrt(n_faces)/4 loops total (prevents over-cutting).

    Args:
        scored_loops: list of loop dicts with 'score' and 'edges' keys,
                      pre-sorted best-first.
        genus:        topological genus of the mesh.
        n_faces:      number of faces.

    Returns set of edge indices to force as seams.
    """
    if not scored_loops:
        return set()

    # Budget: minimum loops needed + a few extra for structure.
    min_loops = max(2 * genus, 0)
    max_budget = max(min_loops + 2, int(n_faces ** 0.5 / 4))
    max_budget = min(max_budget, 20)

    forced = set()
    selected = 0
    used_edges = set()

    for lp in scored_loops:
        if selected >= max_budget:
            break

        edges = lp['edges']
        score = lp.get('score', 0.0)

        # After satisfying minimum, only add loops that score well.
        if selected >= min_loops and score < 0.15:
            break

        # Skip loops that heavily overlap with already-selected loops.
        overlap = sum(1 for ei in edges if ei in used_edges)
        if len(edges) > 0 and overlap / len(edges) > 0.5:
            continue

        for ei in edges:
            forced.add(ei)
            used_edges.add(ei)
        selected += 1

    return forced


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _walk_loop_direction(start_ei, vert_side, edge_verts, vert_edge_map,
                         edge_face_map, edge_face_count, face_edges, visited):
    """Walk in one direction from start_ei following opposite-edge-across-quad.

    Args:
        start_ei:   starting edge index.
        vert_side:  0 = walk from edge_verts[start_ei][0] side,
                    1 = walk from edge_verts[start_ei][1] side.
        visited:    (E,) bool — edges already claimed by other loops.

    Returns (edges, verts, is_closed):
        edges:     list of edge indices in walk order (includes start_ei).
        verts:     list of vertex indices in walk order.
        is_closed: True if walk returned to start edge (complete ring).
    """
    walked_edges = [start_ei]
    start_v = int(edge_verts[start_ei][vert_side])
    other_v = int(edge_verts[start_ei][1 - vert_side])
    walked_verts = [other_v, start_v]

    cur_ei = start_ei
    cur_v = start_v

    max_steps = len(edge_verts) + 1  # Safety bound.

    for _ in range(max_steps):
        next_ei = _find_opposite_edge(cur_ei, cur_v, edge_verts, vert_edge_map,
                                      edge_face_map, edge_face_count, face_edges)
        if next_ei is None:
            break

        if next_ei == start_ei:
            # Closed loop!
            return walked_edges, walked_verts, True

        if visited[next_ei]:
            break

        walked_edges.append(next_ei)
        v0, v1 = int(edge_verts[next_ei][0]), int(edge_verts[next_ei][1])
        next_v = v1 if v0 == cur_v else v0
        walked_verts.append(next_v)

        cur_ei = next_ei
        cur_v = next_v

    return walked_edges, walked_verts, False


def _find_opposite_edge(edge_idx, vertex, edge_verts, vert_edge_map,
                        edge_face_map, edge_face_count, face_edges):
    """Find the opposite edge across a quad at the given vertex.

    At a vertex with valence 4 in a quad mesh, there are 4 edges meeting.
    Two of them share a face with edge_idx. The "opposite" edge is the one
    among the remaining two that also has 2 adjacent faces (interior edge)
    and does NOT share any face with edge_idx.

    For non-quad vertices (valence != 4) or triangle-only regions, returns
    None (loop terminates).
    """
    v_edges = vert_edge_map[vertex]
    if len(v_edges) != 4:
        return None

    # Faces of current edge.
    cur_faces = set(edge_face_map[edge_idx])
    if len(cur_faces) < 2:
        return None

    # Find edges at this vertex that don't share a face with current edge.
    candidates = []
    for ei in v_edges:
        if ei == edge_idx:
            continue
        if edge_face_count[ei] != 2:
            continue
        ei_faces = set(edge_face_map[ei])
        if not ei_faces.intersection(cur_faces):
            candidates.append(ei)

    if len(candidates) == 1:
        return candidates[0]

    return None
