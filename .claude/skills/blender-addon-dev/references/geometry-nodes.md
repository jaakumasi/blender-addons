# Geometry Nodes

## Overview

Geometry Nodes is Blender's node-based system for procedural geometry generation
and modification. Addons interact with it by creating/modifying node groups and
applying them as modifiers.

## Applying a Geometry Nodes Modifier

```python
import bpy

obj = bpy.context.active_object

# Add Geometry Nodes modifier
mod = obj.modifiers.new(name="GeometryNodes", type='NODES')

# The modifier auto-creates an empty node group
# Access it:
node_group = mod.node_group
print(f"Node group: {node_group.name}")
```

## Creating a Node Group from Scratch

```python
# Create new geometry node group
node_group = bpy.data.node_groups.new(name="MyGeoNodes", type='GeometryNodeTree')

# Every geometry node group needs Group Input and Group Output
input_node = node_group.nodes.new('NodeGroupInput')
input_node.location = (-400, 0)

output_node = node_group.nodes.new('NodeGroupOutput')
output_node.location = (400, 0)

# The group starts with a Geometry input and output socket by default
# Connect input geometry → output geometry (passthrough)
node_group.links.new(
    input_node.outputs['Geometry'],
    output_node.inputs['Geometry']
)

# Assign to a modifier
mod = obj.modifiers.new("MyGeoNodes", type='NODES')
mod.node_group = node_group
```

## Adding Nodes

```python
# Add a Transform Geometry node
transform = node_group.nodes.new('GeometryNodeTransform')
transform.location = (0, 0)

# Wire it between input and output
node_group.links.new(input_node.outputs['Geometry'], transform.inputs['Geometry'])
node_group.links.new(transform.outputs['Geometry'], output_node.inputs['Geometry'])

# Set default values on the node
transform.inputs['Translation'].default_value = (0, 0, 1.0)
transform.inputs['Scale'].default_value = (2, 2, 2)
```

## Common Geometry Node Types

### Geometry Operations
| Node Type | Description |
|-----------|-------------|
| `GeometryNodeTransform` | Transform Geometry |
| `GeometryNodeJoinGeometry` | Join Geometry |
| `GeometryNodeSetPosition` | Set Position |
| `GeometryNodeSetShadeSmooth` | Set Shade Smooth |
| `GeometryNodeBoundBox` | Bounding Box |
| `GeometryNodeConvexHull` | Convex Hull |
| `GeometryNodeDeleteGeometry` | Delete Geometry |
| `GeometryNodeDuplicateElements` | Duplicate Elements |
| `GeometryNodeMergeByDistance` | Merge by Distance |
| `GeometryNodeSeparateGeometry` | Separate Geometry |

### Mesh Primitives
| Node Type | Description |
|-----------|-------------|
| `GeometryNodeMeshCube` | Cube |
| `GeometryNodeMeshCylinder` | Cylinder |
| `GeometryNodeMeshCone` | Cone |
| `GeometryNodeMeshUVSphere` | UV Sphere |
| `GeometryNodeMeshIcoSphere` | Ico Sphere |
| `GeometryNodeMeshCircle` | Circle |
| `GeometryNodeMeshGrid` | Grid |
| `GeometryNodeMeshLine` | Line |

### Curves
| Node Type | Description |
|-----------|-------------|
| `GeometryNodeCurvePrimitiveLine` | Curve Line |
| `GeometryNodeCurvePrimitiveCircle` | Curve Circle |
| `GeometryNodeCurveToMesh` | Curve to Mesh |
| `GeometryNodeFillCurve` | Fill Curve |
| `GeometryNodeResampleCurve` | Resample Curve |
| `GeometryNodeTrimCurve` | Trim Curve |
| `GeometryNodeSetCurveRadius` | Set Curve Radius |
| `GeometryNodeCurveLength` | Curve Length |
| `GeometryNodeSampleCurve` | Sample Curve |

### Instances
| Node Type | Description |
|-----------|-------------|
| `GeometryNodeInstanceOnPoints` | Instance on Points |
| `GeometryNodeRealizeInstances` | Realize Instances |
| `GeometryNodeRotateInstances` | Rotate Instances |
| `GeometryNodeScaleInstances` | Scale Instances |
| `GeometryNodeTranslateInstances` | Translate Instances |

### Input / Attribute
| Node Type | Description |
|-----------|-------------|
| `GeometryNodeInputPosition` | Position |
| `GeometryNodeInputNormal` | Normal |
| `GeometryNodeInputIndex` | Index |
| `GeometryNodeInputID` | ID |
| `GeometryNodeInputNamedAttribute` | Named Attribute |
| `GeometryNodeStoreNamedAttribute` | Store Named Attribute |
| `GeometryNodeInputMeshEdgeAngle` | Edge Angle |
| `GeometryNodeInputMeshFaceArea` | Face Area |

### Math & Utility
| Node Type | Description |
|-----------|-------------|
| `ShaderNodeMath` | Math (shared with shaders) |
| `ShaderNodeVectorMath` | Vector Math |
| `FunctionNodeCompare` | Compare |
| `ShaderNodeMapRange` | Map Range |
| `ShaderNodeClamp` | Clamp |
| `FunctionNodeRandomValue` | Random Value |
| `GeometryNodeSwitch` | Switch |
| `FunctionNodeBooleanMath` | Boolean Math |

### Distribution
| Node Type | Description |
|-----------|-------------|
| `GeometryNodeDistributePointsOnFaces` | Distribute Points on Faces |
| `GeometryNodeDistributePointsInVolume` | Distribute Points in Volume |
| `GeometryNodePoints` | Points |

## Group Inputs (Modifier Parameters)

Add custom inputs that appear as modifier properties:

```python
# Add custom inputs to the node group
# In Blender 4.0+, use the tree interface:
items = node_group.interface.items_tree

# Add a float input
node_group.interface.new_socket(
    name="Scale Factor",
    in_out='INPUT',
    socket_type='NodeSocketFloat',
)

# Add an integer input
node_group.interface.new_socket(
    name="Count",
    in_out='INPUT',
    socket_type='NodeSocketInt',
)

# Add an object input (for referencing other objects)
node_group.interface.new_socket(
    name="Target Object",
    in_out='INPUT',
    socket_type='NodeSocketObject',
)

# Add a boolean input
node_group.interface.new_socket(
    name="Enable Feature",
    in_out='INPUT',
    socket_type='NodeSocketBool',
)

# Common socket types:
# 'NodeSocketFloat', 'NodeSocketInt', 'NodeSocketBool',
# 'NodeSocketVector', 'NodeSocketColor', 'NodeSocketString',
# 'NodeSocketObject', 'NodeSocketCollection', 'NodeSocketMaterial',
# 'NodeSocketImage', 'NodeSocketGeometry'
```

## Setting Modifier Input Values

```python
mod = obj.modifiers["GeometryNodes"]

# Set input values by identifier
# Inputs are indexed as: mod[identifier]
# The identifier comes from the socket

# For newer Blender (4.0+), inputs are accessed by socket identifier:
for item in mod.node_group.interface.items_tree:
    if item.item_type == 'SOCKET' and item.in_out == 'INPUT':
        print(f"Input: {item.name}, identifier: {item.identifier}")

# Set values using the modifier's __setitem__
# The key is the socket identifier string
mod["Socket_2"] = 5.0  # Set a float input
mod["Socket_3"] = 10    # Set an int input
```

## Complete Example: Scatter Objects

```python
def create_scatter_node_group():
    """Create a geometry node group that scatters instances on a surface."""
    ng = bpy.data.node_groups.new("ScatterObjects", 'GeometryNodeTree')
    nodes = ng.nodes
    links = ng.links

    # Group I/O
    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-800, 0)
    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (600, 0)

    # Add custom inputs
    ng.interface.new_socket("Density", in_out='INPUT', socket_type='NodeSocketFloat')
    ng.interface.new_socket("Scale", in_out='INPUT', socket_type='NodeSocketFloat')
    ng.interface.new_socket("Seed", in_out='INPUT', socket_type='NodeSocketInt')

    # Distribute Points on Faces
    distribute = nodes.new('GeometryNodeDistributePointsOnFaces')
    distribute.location = (-200, 0)
    distribute.distribute_method = 'POISSON'

    # Instance on Points
    instance = nodes.new('GeometryNodeInstanceOnPoints')
    instance.location = (200, 0)

    # Mesh Ico Sphere (the thing to scatter)
    ico = nodes.new('GeometryNodeMeshIcoSphere')
    ico.location = (0, -200)
    ico.inputs['Radius'].default_value = 0.1

    # Links
    links.new(group_in.outputs['Geometry'], distribute.inputs['Mesh'])
    links.new(group_in.outputs['Density'], distribute.inputs['Density Max'])
    links.new(group_in.outputs['Seed'], distribute.inputs['Seed'])
    links.new(distribute.outputs['Points'], instance.inputs['Points'])
    links.new(ico.outputs['Mesh'], instance.inputs['Instance'])
    links.new(instance.outputs['Instances'], group_out.inputs['Geometry'])

    return ng
```

## Using Existing Node Groups

```python
# Reference an existing node group
existing_group = bpy.data.node_groups.get("MyExistingGeoNodes")
if existing_group:
    mod = obj.modifiers.new("GN", type='NODES')
    mod.node_group = existing_group

# List all geometry node groups
for ng in bpy.data.node_groups:
    if ng.type == 'GEOMETRY':
        print(f"Geo Nodes: {ng.name}")
```
