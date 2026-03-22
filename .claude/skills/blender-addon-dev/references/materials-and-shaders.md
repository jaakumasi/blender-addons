# Materials & Shader Nodes

## Creating Materials

```python
import bpy

# Create a new material
mat = bpy.data.materials.new(name="MyMaterial")
mat.use_nodes = True  # Enable node-based shading (required for Cycles/EEVEE)

# Assign material to active object
obj = bpy.context.active_object
if obj.data.materials:
    obj.data.materials[0] = mat  # Replace first slot
else:
    obj.data.materials.append(mat)  # Add new slot

# Assign material to specific slot index
obj.active_material_index = 0
obj.active_material = mat
```

## Accessing the Node Tree

```python
mat = bpy.data.materials["MyMaterial"]
node_tree = mat.node_tree      # bpy.types.ShaderNodeTree
nodes = node_tree.nodes         # All nodes
links = node_tree.links         # All connections between nodes

# Get the Principled BSDF (default shader node)
principled = nodes.get("Principled BSDF")
# or find by type:
principled = None
for node in nodes:
    if node.type == 'BSDF_PRINCIPLED':
        principled = node
        break

# Get the Material Output node
output = nodes.get("Material Output")
```

## Creating Nodes

```python
node_tree = mat.node_tree

# Clear all existing nodes
node_tree.nodes.clear()

# Create Material Output
output_node = node_tree.nodes.new(type='ShaderNodeOutputMaterial')
output_node.location = (400, 0)

# Create Principled BSDF
principled = node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
principled.location = (0, 0)

# Create Image Texture
tex_node = node_tree.nodes.new(type='ShaderNodeTexImage')
tex_node.location = (-400, 0)

# Create Texture Coordinate
texcoord = node_tree.nodes.new(type='ShaderNodeTexCoord')
texcoord.location = (-800, 0)

# Create Mapping node
mapping = node_tree.nodes.new(type='ShaderNodeMapping')
mapping.location = (-600, 0)
```

## Linking Nodes

```python
links = node_tree.links

# Connect Principled BSDF → Material Output
links.new(principled.outputs['BSDF'], output_node.inputs['Surface'])

# Connect Image Texture → Principled Base Color
links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])

# Connect Texture Coordinate → Mapping → Image Texture
links.new(texcoord.outputs['UV'], mapping.inputs['Vector'])
links.new(mapping.outputs['Vector'], tex_node.inputs['Vector'])
```

## Setting Node Values

```python
# Principled BSDF inputs (by name)
principled.inputs['Base Color'].default_value = (0.8, 0.2, 0.1, 1.0)  # RGBA
principled.inputs['Metallic'].default_value = 1.0
principled.inputs['Roughness'].default_value = 0.3
principled.inputs['IOR'].default_value = 1.45
principled.inputs['Alpha'].default_value = 1.0
principled.inputs['Emission Color'].default_value = (1.0, 1.0, 1.0, 1.0)
principled.inputs['Emission Strength'].default_value = 0.0

# Mapping node values
mapping.inputs['Location'].default_value = (0.0, 0.0, 0.0)
mapping.inputs['Rotation'].default_value = (0.0, 0.0, 0.0)
mapping.inputs['Scale'].default_value = (1.0, 1.0, 1.0)
```

## Loading Images / Textures

```python
# Load image from file
image = bpy.data.images.load(filepath="/path/to/texture.png")
tex_node.image = image

# Create a new blank image
image = bpy.data.images.new(name="Generated", width=1024, height=1024)
tex_node.image = image

# Use an existing image
if "MyTexture.png" in bpy.data.images:
    tex_node.image = bpy.data.images["MyTexture.png"]

# Set image color space
image.colorspace_settings.name = 'sRGB'       # For color textures
image.colorspace_settings.name = 'Non-Color'   # For normal/roughness maps
```

## Common Shader Node Types

| Node Type String | Node Name |
|-----------------|-----------|
| `ShaderNodeBsdfPrincipled` | Principled BSDF |
| `ShaderNodeBsdfDiffuse` | Diffuse BSDF |
| `ShaderNodeBsdfGlossy` | Glossy BSDF |
| `ShaderNodeBsdfGlass` | Glass BSDF |
| `ShaderNodeBsdfTransparent` | Transparent BSDF |
| `ShaderNodeEmission` | Emission |
| `ShaderNodeMixShader` | Mix Shader |
| `ShaderNodeAddShader` | Add Shader |
| `ShaderNodeOutputMaterial` | Material Output |
| `ShaderNodeTexImage` | Image Texture |
| `ShaderNodeTexNoise` | Noise Texture |
| `ShaderNodeTexVoronoi` | Voronoi Texture |
| `ShaderNodeTexMusgrave` | Musgrave Texture |
| `ShaderNodeTexGradient` | Gradient Texture |
| `ShaderNodeTexWave` | Wave Texture |
| `ShaderNodeTexChecker` | Checker Texture |
| `ShaderNodeTexBrick` | Brick Texture |
| `ShaderNodeTexEnvironment` | Environment Texture |
| `ShaderNodeTexCoord` | Texture Coordinate |
| `ShaderNodeMapping` | Mapping |
| `ShaderNodeNormalMap` | Normal Map |
| `ShaderNodeBump` | Bump |
| `ShaderNodeDisplacement` | Displacement |
| `ShaderNodeMath` | Math |
| `ShaderNodeVectorMath` | Vector Math |
| `ShaderNodeMixRGB` | Mix (legacy) / MixRGB |
| `ShaderNodeMix` | Mix (Blender 3.4+) |
| `ShaderNodeColorRamp` | Color Ramp |
| `ShaderNodeValToRGB` | Color Ramp (alternate) |
| `ShaderNodeRGBCurve` | RGB Curves |
| `ShaderNodeSeparateXYZ` | Separate XYZ |
| `ShaderNodeCombineXYZ` | Combine XYZ |
| `ShaderNodeSeparateColor` | Separate Color |
| `ShaderNodeCombineColor` | Combine Color |
| `ShaderNodeClamp` | Clamp |
| `ShaderNodeMapRange` | Map Range |
| `ShaderNodeFresnel` | Fresnel |
| `ShaderNodeLayerWeight` | Layer Weight |
| `ShaderNodeObjectInfo` | Object Info |
| `ShaderNodeValue` | Value |
| `ShaderNodeRGB` | RGB |

## Material Settings (Non-Node)

```python
mat = bpy.data.materials["MyMaterial"]

# Blend mode (for transparency in EEVEE)
mat.blend_method = 'OPAQUE'     # 'OPAQUE', 'CLIP', 'HASHED', 'BLEND'
mat.shadow_method = 'CLIP'      # Shadow mode for transparent materials

# Backface culling
mat.use_backface_culling = True

# Pass index (for compositing)
mat.pass_index = 1

# Viewport display color
mat.diffuse_color = (0.8, 0.2, 0.1, 1.0)  # RGBA
```

## Full Example: PBR Material Setup

```python
def create_pbr_material(name, color_path=None, normal_path=None, roughness_path=None):
    """Create a PBR material with optional texture maps."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear defaults
    nodes.clear()

    # Create nodes
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (600, 0)

    principled = nodes.new('ShaderNodeBsdfPrincipled')
    principled.location = (200, 0)
    links.new(principled.outputs['BSDF'], output.inputs['Surface'])

    x_offset = -300

    if color_path:
        tex_color = nodes.new('ShaderNodeTexImage')
        tex_color.location = (x_offset, 300)
        tex_color.image = bpy.data.images.load(color_path)
        links.new(tex_color.outputs['Color'], principled.inputs['Base Color'])

    if normal_path:
        tex_normal = nodes.new('ShaderNodeTexImage')
        tex_normal.location = (x_offset, 0)
        tex_normal.image = bpy.data.images.load(normal_path)
        tex_normal.image.colorspace_settings.name = 'Non-Color'

        normal_map = nodes.new('ShaderNodeNormalMap')
        normal_map.location = (x_offset + 300, 0)
        links.new(tex_normal.outputs['Color'], normal_map.inputs['Color'])
        links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])

    if roughness_path:
        tex_rough = nodes.new('ShaderNodeTexImage')
        tex_rough.location = (x_offset, -300)
        tex_rough.image = bpy.data.images.load(roughness_path)
        tex_rough.image.colorspace_settings.name = 'Non-Color'
        links.new(tex_rough.outputs['Color'], principled.inputs['Roughness'])

    return mat
```

## Iterating Material Slots on an Object

```python
obj = bpy.context.active_object

for i, slot in enumerate(obj.material_slots):
    mat = slot.material
    if mat:
        print(f"Slot {i}: {mat.name}")
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                print(f"  Node: {node.name} ({node.type})")
```

## World Shader (Environment/HDRI)

```python
world = bpy.context.scene.world
if not world:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world

world.use_nodes = True
nodes = world.node_tree.nodes
links = world.node_tree.links

nodes.clear()

output = nodes.new('ShaderNodeOutputWorld')
output.location = (400, 0)

background = nodes.new('ShaderNodeBackground')
background.location = (200, 0)
background.inputs['Strength'].default_value = 1.0
links.new(background.outputs['Background'], output.inputs['Surface'])

# HDRI environment
env_tex = nodes.new('ShaderNodeTexEnvironment')
env_tex.location = (-200, 0)
env_tex.image = bpy.data.images.load("/path/to/hdri.exr")
links.new(env_tex.outputs['Color'], background.inputs['Color'])

# Or solid color
background.inputs['Color'].default_value = (0.05, 0.05, 0.05, 1.0)
```
