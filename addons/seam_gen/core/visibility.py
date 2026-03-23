"""
Ambient Occlusion visibility scoring for seam placement.

Uses BVHTree hemisphere raycasting to estimate per-vertex occlusion.
Edges in occluded (dark) areas score HIGH → preferred as seams.
Edges on exposed surfaces score LOW → avoided as seams.

This is the most impactful signal for professional seam hiding — it
ensures seams route through armpits, under chins, behind ears, and
inside creases rather than across visible surfaces.
"""

import math
import random
import numpy as np

# Seed for reproducible AO results across re-analyses
_RNG = random.Random(42)


def _build_hemisphere_samples(n_samples):
    """Pre-compute stratified hemisphere sample directions.

    Uses stratified sampling (jittered grid) for better coverage
    than pure random, especially at low sample counts.

    Returns list of (x, y, z) unit vectors in the +Z hemisphere.
    """
    samples = []
    sqrt_n = max(1, int(math.sqrt(n_samples)))
    actual_n = sqrt_n * sqrt_n  # Round to perfect square for stratification

    for i in range(sqrt_n):
        for j in range(sqrt_n):
            # Stratified jitter within each cell
            u = (i + _RNG.random()) / sqrt_n
            v = (j + _RNG.random()) / sqrt_n

            # Cosine-weighted hemisphere sampling
            # This biases toward the normal direction (more relevant for visibility)
            phi = 2.0 * math.pi * u
            cos_theta = math.sqrt(1.0 - v)  # cosine-weighted
            sin_theta = math.sqrt(v)

            x = sin_theta * math.cos(phi)
            y = sin_theta * math.sin(phi)
            z = cos_theta

            samples.append((x, y, z))

    # Fill remaining samples if n_samples != perfect square
    while len(samples) < n_samples:
        u = _RNG.random()
        v = _RNG.random()
        phi = 2.0 * math.pi * u
        cos_theta = math.sqrt(1.0 - v)
        sin_theta = math.sqrt(v)
        samples.append((sin_theta * math.cos(phi),
                         sin_theta * math.sin(phi),
                         cos_theta))

    return samples[:n_samples]


def _orient_to_normal(sample_dirs, normal):
    """Rotate pre-computed +Z hemisphere samples to align with given normal.

    Constructs a tangent-space basis from the normal and transforms
    each sample direction.

    Args:
        sample_dirs: list of (x, y, z) tuples in +Z hemisphere
        normal: (3,) numpy array, unit normal

    Returns list of (3,) numpy arrays in world space.
    """
    n = normal
    # Build orthonormal basis (tangent, bitangent, normal)
    if abs(n[2]) < 0.999:
        up = np.array([0.0, 0.0, 1.0])
    else:
        up = np.array([1.0, 0.0, 0.0])

    tangent = np.cross(up, n)
    t_len = np.linalg.norm(tangent)
    if t_len < 1e-8:
        return [n for _ in sample_dirs]  # Degenerate — all rays along normal
    tangent /= t_len
    bitangent = np.cross(n, tangent)

    # Transform each sample: world_dir = x*tangent + y*bitangent + z*normal
    oriented = []
    for sx, sy, sz in sample_dirs:
        d = sx * tangent + sy * bitangent + sz * n
        length = np.linalg.norm(d)
        if length > 1e-8:
            d /= length
        oriented.append(d)

    return oriented


def compute_ao_scores(bm, vert_coords, edge_verts, n_samples=16,
                      max_dist=0.0):
    """Compute per-edge AO visibility scores via BVHTree hemisphere raycasting.

    High score = edge is in occluded area (good for seams).
    Low score = edge is exposed (avoid placing seams here).

    Args:
        bm: BMesh object (for BVHTree construction + vertex normals)
        vert_coords: (V, 3) float64 vertex positions
        edge_verts: (E, 2) int32 edge vertex indices
        n_samples: rays per vertex (4-64, default 16)
        max_dist: max ray distance (0 = auto from mesh bounds)

    Returns (E,) float64 array with scores in [0, 1].
    """
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector

    bm.verts.ensure_lookup_table()
    V = len(vert_coords)
    E = len(edge_verts)

    if V == 0 or E == 0:
        return np.zeros(E, dtype=np.float64)

    # Auto-compute max ray distance from mesh bounding box
    if max_dist <= 0.0:
        bbox_min = vert_coords.min(axis=0)
        bbox_max = vert_coords.max(axis=0)
        diagonal = np.linalg.norm(bbox_max - bbox_min)
        max_dist = diagonal * 2.0  # 2x bounding diagonal

    # Build BVH tree
    tree = BVHTree.FromBMesh(bm, epsilon=0.0)

    # Pre-compute hemisphere sample directions (+Z hemisphere)
    sample_dirs = _build_hemisphere_samples(n_samples)

    # Self-intersection offset (small fraction of mesh size)
    offset_dist = max_dist * 0.0001

    # Per-vertex AO
    ao = np.zeros(V, dtype=np.float64)

    for vi in range(V):
        vert = bm.verts[vi]
        normal = vert.normal
        n_len = normal.length

        if n_len < 0.01:
            # Degenerate vertex (wire edge, isolated) — treat as fully visible
            ao[vi] = 0.0
            continue

        n_arr = np.array([normal.x, normal.y, normal.z]) / n_len
        origin = Vector(vert_coords[vi]) + normal.normalized() * offset_dist

        # Orient samples to vertex normal
        oriented = _orient_to_normal(sample_dirs, n_arr)

        hits = 0
        for d in oriented:
            direction = Vector((d[0], d[1], d[2]))
            result = tree.ray_cast(origin, direction, max_dist)
            if result[0] is not None:
                hits += 1

        ao[vi] = hits / n_samples

    # Per-edge: average of endpoint AO values
    v1 = edge_verts[:, 0]
    v2 = edge_verts[:, 1]
    edge_ao = (ao[v1] + ao[v2]) * 0.5

    return np.clip(edge_ao, 0.0, 1.0)
