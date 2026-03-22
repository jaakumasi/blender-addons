# Camera & Render Settings

## Creating & Configuring Cameras

```python
import bpy
from mathutils import Vector, Euler
import math

# Create camera
cam_data = bpy.data.cameras.new(name="MyCamera")
cam_obj = bpy.data.objects.new("MyCamera", cam_data)
bpy.context.collection.objects.link(cam_obj)

# Set as active scene camera
bpy.context.scene.camera = cam_obj

# Position and aim
cam_obj.location = (7.0, -6.0, 5.0)
cam_obj.rotation_euler = Euler((math.radians(63), 0, math.radians(47)), 'XYZ')
```

## Camera Properties

```python
cam = bpy.data.cameras["MyCamera"]

# Lens type
cam.type = 'PERSP'          # 'PERSP', 'ORTHO', 'PANO'

# Perspective settings
cam.lens = 50               # Focal length (mm)
cam.sensor_width = 36       # Sensor width (mm)
cam.sensor_height = 24      # Sensor height (mm)
cam.sensor_fit = 'AUTO'     # 'AUTO', 'HORIZONTAL', 'VERTICAL'

# Orthographic settings
cam.ortho_scale = 6.0       # Orthographic scale

# Clipping
cam.clip_start = 0.1
cam.clip_end = 1000.0

# Depth of Field
cam.dof.use_dof = True
cam.dof.focus_distance = 5.0
cam.dof.aperture_fstop = 2.8
cam.dof.focus_object = bpy.data.objects.get("FocusTarget")  # Or None

# Shift (lens shift)
cam.shift_x = 0.0
cam.shift_y = 0.0

# Background images
cam.show_background_images = True
# bg = cam.background_images.new()
# bg.image = bpy.data.images.load("/path/to/reference.jpg")
```

## Camera Utilities

```python
# Point camera at a target
def look_at(camera_obj, target_point):
    """Point camera at a world-space location."""
    direction = target_point - camera_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera_obj.rotation_euler = rot_quat.to_euler()

look_at(cam_obj, Vector((0, 0, 0)))

# Track-to constraint (auto-aim at object)
constraint = cam_obj.constraints.new(type='TRACK_TO')
constraint.target = bpy.data.objects["Cube"]
constraint.track_axis = 'TRACK_NEGATIVE_Z'
constraint.up_axis = 'UP_Y'
```

## Render Settings

```python
scene = bpy.context.scene
render = scene.render

# Resolution
render.resolution_x = 1920
render.resolution_y = 1080
render.resolution_percentage = 100   # Scale percentage

# Frame range
scene.frame_start = 1
scene.frame_end = 250

# Output
render.filepath = "//renders/output_"   # // = relative to .blend file
render.image_settings.file_format = 'PNG'    # 'PNG', 'JPEG', 'OPEN_EXR', 'TIFF', 'BMP', 'FFMPEG'
render.image_settings.color_mode = 'RGBA'    # 'BW', 'RGB', 'RGBA'
render.image_settings.color_depth = '16'     # '8', '16', '32' (format-dependent)
render.image_settings.compression = 15       # PNG compression (0-100)

# For JPEG
# render.image_settings.quality = 90

# For EXR
# render.image_settings.exr_codec = 'ZIP'

# For video (FFMPEG)
# render.image_settings.file_format = 'FFMPEG'
# render.ffmpeg.format = 'MPEG4'
# render.ffmpeg.codec = 'H264'
# render.ffmpeg.constant_rate_factor = 'HIGH'
# render.ffmpeg.audio_codec = 'AAC'

# Film
render.film_transparent = True   # Transparent background

# Performance
render.threads_mode = 'AUTO'     # 'AUTO' or 'FIXED'
render.use_persistent_data = True  # Keep render data between frames
```

## Render Engine Selection

```python
scene = bpy.context.scene

# Switch render engine
scene.render.engine = 'BLENDER_EEVEE_NEXT'   # EEVEE (Blender 4.0+)
# scene.render.engine = 'BLENDER_EEVEE'      # EEVEE (legacy)
# scene.render.engine = 'CYCLES'              # Cycles
# scene.render.engine = 'BLENDER_WORKBENCH'   # Workbench
```

## Cycles Settings

```python
scene.render.engine = 'CYCLES'
cycles = scene.cycles

# Device
cycles.device = 'GPU'               # 'CPU' or 'GPU'

# Sampling
cycles.samples = 256                 # Render samples
cycles.preview_samples = 32          # Viewport samples
cycles.use_adaptive_sampling = True
cycles.adaptive_threshold = 0.01

# Denoising
cycles.use_denoising = True
cycles.denoiser = 'OPENIMAGEDENOISE'  # 'OPENIMAGEDENOISE' or 'OPTIX'

# Light paths (bounces)
cycles.max_bounces = 12
cycles.diffuse_bounces = 4
cycles.glossy_bounces = 4
cycles.transmission_bounces = 12
cycles.volume_bounces = 0
cycles.transparent_max_bounces = 8

# Performance
cycles.use_auto_tile = True
cycles.tile_size = 2048

# Set GPU compute device type
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'CUDA'  # 'CUDA', 'OPTIX', 'HIP', 'ONEAPI', 'METAL'
prefs.get_devices()  # Refresh device list
for device in prefs.devices:
    device.use = True  # Enable all devices
```

## EEVEE Settings

```python
scene.render.engine = 'BLENDER_EEVEE_NEXT'
eevee = scene.eevee

# Sampling
eevee.taa_render_samples = 64
eevee.taa_samples = 16  # Viewport

# Shadows
eevee.shadow_cube_size = '1024'
eevee.shadow_cascade_size = '2048'
eevee.use_shadow_high_bitdepth = True

# Screen Space Reflections
eevee.use_ssr = True
eevee.use_ssr_refraction = True

# Ambient Occlusion
eevee.use_gtao = True
eevee.gtao_distance = 0.2

# Bloom
eevee.use_bloom = True
eevee.bloom_threshold = 0.8
eevee.bloom_intensity = 0.05
```

## Rendering from Script

```python
# Render still image
bpy.ops.render.render(write_still=True)

# Render animation
bpy.ops.render.render(animation=True)

# Render specific frame
scene.frame_set(42)
bpy.ops.render.render(write_still=True)

# Render to specific path (override)
scene.render.filepath = "/tmp/my_render.png"
bpy.ops.render.render(write_still=True)

# OpenGL viewport render (preview quality)
bpy.ops.render.opengl(write_still=True)
```

## Render Slots & Compositing

```python
# Switch render slot (for comparing renders)
bpy.data.images['Render Result'].render_slots.active_index = 0

# View Layer settings
view_layer = bpy.context.view_layer
view_layer.use_pass_combined = True
view_layer.use_pass_z = True              # Depth pass
view_layer.use_pass_normal = True          # Normal pass
view_layer.use_pass_diffuse_color = True   # Diffuse color pass
view_layer.use_pass_emit = True            # Emission pass
view_layer.use_pass_ao = True              # Ambient Occlusion pass

# Enable compositing
scene.use_nodes = True  # Enable compositor
compositor = scene.node_tree
# Access compositor nodes similar to shader nodes
```

## Multi-Camera Setup

```python
cameras = {}

def create_camera(name, location, target, lens=50):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_obj = bpy.data.objects.new(name, cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = location

    # Aim at target
    direction = Vector(target) - Vector(location)
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    cameras[name] = cam_obj
    return cam_obj

# Create multiple cameras
create_camera("Front", (0, -10, 2), (0, 0, 1), lens=35)
create_camera("Top", (0, 0, 15), (0, 0, 0), lens=50)
create_camera("Close", (3, -3, 2), (0, 0, 1), lens=85)

# Switch active camera via markers
scene = bpy.context.scene
scene.timeline_markers.new("Front_Cam", frame=1)
scene.timeline_markers["Front_Cam"].camera = cameras["Front"]
scene.timeline_markers.new("Top_Cam", frame=60)
scene.timeline_markers["Top_Cam"].camera = cameras["Top"]
scene.timeline_markers.new("Close_Cam", frame=120)
scene.timeline_markers["Close_Cam"].camera = cameras["Close"]
```
