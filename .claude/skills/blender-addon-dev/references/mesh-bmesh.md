# Mesh & BMesh Deep Dive

## BMesh Overview

BMesh is Blender's in-memory mesh editing library. It provides full access to
vertices, edges, and faces for procedural mesh creation and modification.

```python
import bpy
import bmesh
from mathutils import Vector, Matrix
```

## Creating Mesh from Scratch

```python
# Create empty mesh and object
mesh = bpy.data.meshes.new("MyMesh")
obj = bpy.data.objects.new("MyObject", mesh)
bpy.context.collection.objects.link(obj)

# Build with bmesh
bm = bmesh.new()

# Add vertices
v1 = bm.verts.new((0, 0, 0))
v2 = bm.verts.new((1, 0, 0))
v3 = bm.verts.new((1, 1, 0))
v4 = bm.verts.new((0, 1, 0))

# Ensure internal index table is valid
bm.verts.ensure_lookup_table()

# Create face from vertices (auto-creates edges)
face = bm.faces.new((v1, v2, v3, v4))

# Create edge without face
edge = bm.edges.new((v1, v3))

# Write to mesh and free
bm.to_mesh(mesh)
bm.free()  # ALWAYS free bmesh when done

# Update mesh (recalculate normals, etc.)
mesh.update()
```

## Editing Existing Mesh

```python
obj = bpy.context.active_object
mesh = obj.data

# From mesh data (object mode)
bm = bmesh.new()
bm.from_mesh(mesh)

# ... modify ...

bm.to_mesh(mesh)
bm.free()
mesh.update()

# From edit mode (if already in edit mode)
# bm = bmesh.from_edit_mesh(mesh)
# ... modify ...
# bmesh.update_edit_mesh(mesh)  # Do NOT call bm.free() in edit mode
```

## Vertex Operations

```python
bm = bmesh.new()
bm.from_mesh(mesh)

# Access all vertices
for vert in bm.verts:
    print(f"Vert {vert.index}: {vert.co}")

# Move vertices
for vert in bm.verts:
    vert.co.z += 0.5  # Move up

# Select vertices
bm.verts.ensure_lookup_table()
bm.verts[0].select = True

# Delete vertices
verts_to_delete = [v for v in bm.verts if v.co.z < 0]
bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')

# Merge vertices by distance
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)

bm.to_mesh(mesh)
bm.free()
```

## Edge Operations

```python
# Iterate edges
for edge in bm.edges:
    v1, v2 = edge.verts
    length = (v2.co - v1.co).length
    print(f"Edge {edge.index}: length={length:.3f}")

# Subdivide edges
edges_to_sub = [e for e in bm.edges if e.calc_length() > 1.0]
bmesh.ops.subdivide_edges(bm, edges=edges_to_sub, cuts=1)

# Dissolve edges
bmesh.ops.dissolve_edges(bm, edges=edges_to_sub)

# Bevel edges
bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.1, segments=2, affect='EDGES')
```

## Face Operations

```python
# Iterate faces
for face in bm.faces:
    print(f"Face {face.index}: normal={face.normal}, area={face.calc_area():.3f}")
    print(f"  Verts: {[v.index for v in face.verts]}")

# Extrude faces
faces_to_extrude = [f for f in bm.faces if f.normal.z > 0.9]
result = bmesh.ops.extrude_face_region(bm, geom=faces_to_extrude)
# Move extruded geometry
extruded_verts = [v for v in result['geom'] if isinstance(v, bmesh.types.BMVert)]
bmesh.ops.translate(bm, verts=extruded_verts, vec=(0, 0, 1.0))

# Inset faces
bmesh.ops.inset_region(bm, faces=faces_to_extrude, thickness=0.1, depth=0.0)

# Triangulate
bmesh.ops.triangulate(bm, faces=bm.faces[:])

# Flip normals
for face in bm.faces:
    face.normal_flip()
```

## BMesh Operators (bmesh.ops)

Common procedural operations:

```python
# Create primitives
bmesh.ops.create_cube(bm, size=2.0)
bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0)
bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
bmesh.ops.create_cone(bm, segments=32, radius1=1.0, radius2=0.0, depth=2.0)
bmesh.ops.create_grid(bm, x_segments=10, y_segments=10, size=2.0)
bmesh.ops.create_circle(bm, segments=32, radius=1.0)

# Transform
bmesh.ops.translate(bm, verts=bm.verts, vec=(1, 0, 0))
bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(0.5, 3, 'Z'))
bmesh.ops.scale(bm, verts=bm.verts, vec=(2, 2, 2))
bmesh.ops.transform(bm, verts=bm.verts, matrix=some_4x4_matrix)

# Duplicate
result = bmesh.ops.duplicate(bm, geom=bm.faces[:])

# Spin (lathe)
bmesh.ops.spin(bm, geom=bm.faces[:], axis=(0, 0, 1), cent=(0, 0, 0),
               angle=3.14159 * 2, steps=32, use_duplicate=False)

# Mirror
bmesh.ops.mirror(bm, geom=bm.faces[:], axis='X', merge_dist=0.001)

# Solidify (add thickness)
bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.1)

# Smooth vertices
bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.5, use_axis_x=True,
                      use_axis_y=True, use_axis_z=True)

# Recalculate normals
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
```

## UV Maps

```python
bm = bmesh.new()
bm.from_mesh(mesh)

# Access UV layer
uv_layer = bm.loops.layers.uv.verify()  # Get or create active UV layer
# uv_layer = bm.loops.layers.uv.new("MyUVMap")  # Create named UV layer

# Read/write UV coordinates
for face in bm.faces:
    for loop in face.loops:
        uv = loop[uv_layer]
        print(f"UV: ({uv.uv.x:.3f}, {uv.uv.y:.3f})")
        # Modify UV
        uv.uv.x *= 2.0
        uv.uv.y *= 2.0

bm.to_mesh(mesh)
bm.free()
```

## Vertex Colors

```python
bm = bmesh.new()
bm.from_mesh(mesh)

# Access color layer
color_layer = bm.loops.layers.color.verify()

for face in bm.faces:
    for loop in face.loops:
        color = loop[color_layer]
        # RGBA (0-1 range)
        loop[color_layer] = (1.0, 0.0, 0.0, 1.0)  # Red

bm.to_mesh(mesh)
bm.free()
```

## Vertex Groups

```python
obj = bpy.context.active_object

# Create vertex group
vg = obj.vertex_groups.new(name="MyGroup")

# Add vertices to group (by index, with weight)
vg.add([0, 1, 2, 3], 1.0, 'REPLACE')  # 'REPLACE', 'ADD', 'SUBTRACT'

# Read weights
for vert in obj.data.vertices:
    for group in vert.groups:
        group_name = obj.vertex_groups[group.group].name
        weight = group.weight
        print(f"Vert {vert.index}: group={group_name}, weight={weight}")

# Remove from group
vg.remove([0, 1])

# Delete vertex group
obj.vertex_groups.remove(vg)
```

## Modifiers

```python
obj = bpy.context.active_object

# Add modifier
mod = obj.modifiers.new(name="MySubsurf", type='SUBSURF')
mod.levels = 2            # Viewport subdivision
mod.render_levels = 3     # Render subdivision

# Common modifier types
# 'SUBSURF', 'MIRROR', 'ARRAY', 'SOLIDIFY', 'BEVEL', 'BOOLEAN',
# 'DECIMATE', 'REMESH', 'SMOOTH', 'SHRINKWRAP', 'ARMATURE',
# 'CURVE', 'LATTICE', 'CLOTH', 'COLLISION', 'PARTICLE_SYSTEM',
# 'NODES' (Geometry Nodes)

# Array modifier example
array = obj.modifiers.new("Array", 'ARRAY')
array.count = 5
array.relative_offset_displace = (1.2, 0, 0)

# Mirror modifier example
mirror = obj.modifiers.new("Mirror", 'MIRROR')
mirror.use_axis = (True, False, False)
mirror.merge_threshold = 0.001

# Boolean modifier example
boolean = obj.modifiers.new("Boolean", 'BOOLEAN')
boolean.operation = 'DIFFERENCE'  # 'INTERSECT', 'UNION', 'DIFFERENCE'
boolean.object = bpy.data.objects["Cutter"]

# Apply modifier (makes it permanent)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.modifier_apply(modifier="MySubsurf")

# Remove modifier
obj.modifiers.remove(mod)

# Reorder modifier
bpy.ops.object.modifier_move_up(modifier="Mirror")
bpy.ops.object.modifier_move_down(modifier="Mirror")
```

## from_pydata — Quick Mesh Creation

```python
# Faster than bmesh for simple cases
mesh = bpy.data.meshes.new("MyMesh")

vertices = [
    (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),  # Bottom
    (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),  # Top
]
edges = []  # Auto-generated from faces
faces = [
    (0, 1, 2, 3),  # Bottom
    (4, 5, 6, 7),  # Top
    (0, 1, 5, 4),  # Front
    (2, 3, 7, 6),  # Back
    (0, 3, 7, 4),  # Left
    (1, 2, 6, 5),  # Right
]

mesh.from_pydata(vertices, edges, faces)
mesh.update()

obj = bpy.data.objects.new("MyCube", mesh)
bpy.context.collection.objects.link(obj)
```
