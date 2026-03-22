# Particles & Physics

## Particle Systems

### Creating a Particle System

```python
import bpy

obj = bpy.context.active_object

# Add particle system
bpy.ops.object.particle_system_add()
ps = obj.particle_systems[-1]       # The particle system
ps.name = "MyParticles"
settings = ps.settings               # Particle settings data block

# Or create via data API
# settings = bpy.data.particles.new("MyParticleSettings")
# mod = obj.modifiers.new("Particles", 'PARTICLE_SYSTEM')
# ps = obj.particle_systems[-1]
# ps.settings = settings
```

### Emitter Particles

```python
settings = ps.settings
settings.type = 'EMITTER'

# Emission
settings.count = 1000              # Total particle count
settings.frame_start = 1           # Emission start frame
settings.frame_end = 50            # Emission end frame
settings.lifetime = 100            # Particle lifetime (frames)
settings.lifetime_random = 0.5     # Randomize lifetime (0-1)

settings.emit_from = 'FACE'        # 'VERT', 'FACE', 'VOLUME'
settings.use_emit_random = True
settings.distribution = 'RAND'     # 'JIT' (jittered), 'RAND' (random)

# Velocity
settings.normal_factor = 1.0       # Velocity along normals
settings.tangent_factor = 0.0
settings.object_align_factor = (0, 0, 0)
settings.factor_random = 0.5       # Random velocity factor

# Physics
settings.physics_type = 'NEWTON'   # 'NEWTON', 'KEYED', 'BOIDS', 'FLUID', 'NO'
settings.mass = 1.0
settings.particle_size = 0.05
settings.size_random = 0.2

# Gravity
settings.effector_weights.gravity = 1.0

# Display
settings.display_method = 'DOT'    # 'NONE', 'DOT', 'CIRC', 'CROSS', 'AXIS'
settings.display_size = 0.01
settings.display_percentage = 100
```

### Hair Particles

```python
settings.type = 'HAIR'

settings.count = 500
settings.hair_length = 0.3
settings.hair_step = 5             # Path segments

# Children
settings.child_type = 'INTERPOLATED'  # 'NONE', 'SIMPLE', 'INTERPOLATED'
settings.child_nbr = 10              # Viewport children per parent
settings.rendered_child_count = 100   # Render children per parent
settings.child_length = 1.0
settings.child_radius = 0.1          # Spread radius

# Roughness
settings.roughness_1 = 0.0
settings.roughness_2 = 0.0
settings.roughness_endpoint = 0.0
```

### Rendering Particles as Objects

```python
settings.render_type = 'OBJECT'      # 'NONE', 'HALO', 'LINE', 'PATH', 'OBJECT', 'COLLECTION'
settings.instance_object = bpy.data.objects["InstanceObject"]
settings.particle_size = 0.1
settings.size_random = 0.3
settings.use_rotation_instance = True
settings.use_scale_instance = True

# Random rotation
settings.rotation_mode = 'OB_X'      # 'NONE', 'NOR', 'VEL', 'OB_X', 'OB_Y', 'OB_Z', 'GLOB_X', 'GLOB_Y', 'GLOB_Z'
settings.phase_factor = 1.0           # Initial rotation phase
settings.phase_factor_random = 1.0    # Random rotation

# Render as collection
settings.render_type = 'COLLECTION'
settings.instance_collection = bpy.data.collections["ScatterObjects"]
settings.use_collection_pick_random = True
```

### Accessing Particle Data at Runtime

```python
# Evaluate depsgraph to get particle positions
depsgraph = bpy.context.evaluated_depsgraph_get()
obj_eval = obj.evaluated_get(depsgraph)
ps_eval = obj_eval.particle_systems[0]

for particle in ps_eval.particles:
    loc = particle.location
    vel = particle.velocity
    size = particle.size
    alive = particle.alive_state  # 'ALIVE', 'DEAD', 'UNBORN'
    print(f"Pos: {loc}, Vel: {vel}, Size: {size}, State: {alive}")
```

## Force Fields (Effectors)

```python
# Create empty with force field
bpy.ops.object.empty_add(location=(0, 0, 2))
empty = bpy.context.active_object
empty.name = "WindForce"

# Add force field
empty.field.type = 'WIND'    # 'FORCE', 'WIND', 'VORTEX', 'MAGNETIC', 'HARMONIC',
                              # 'CHARGE', 'LENNARDJ', 'TEXTURE', 'GUIDE', 'BOID',
                              # 'TURBULENCE', 'DRAG', 'FLUID_FLOW'
empty.field.strength = 5.0
empty.field.flow = 0.5

# Turbulence example
empty.field.type = 'TURBULENCE'
empty.field.strength = 10.0
empty.field.size = 1.0
empty.field.noise = 1.5

# Vortex example
empty.field.type = 'VORTEX'
empty.field.strength = 3.0
```

## Rigid Body Physics

```python
obj = bpy.context.active_object

# Add rigid body
bpy.ops.rigidbody.object_add()
rb = obj.rigid_body

# Active (dynamic, simulated)
rb.type = 'ACTIVE'
rb.mass = 1.0
rb.friction = 0.5
rb.restitution = 0.3               # Bounciness
rb.collision_shape = 'CONVEX_HULL'  # 'BOX', 'SPHERE', 'CAPSULE', 'CYLINDER',
                                     # 'CONE', 'CONVEX_HULL', 'MESH', 'COMPOUND'
rb.use_margin = True
rb.collision_margin = 0.04

# Passive (static, collider)
rb.type = 'PASSIVE'
rb.kinematic = False                # True = animated passive body

# Damping
rb.linear_damping = 0.04
rb.angular_damping = 0.1

# Scene rigid body world settings
scene = bpy.context.scene
if not scene.rigidbody_world:
    bpy.ops.rigidbody.world_add()

rbw = scene.rigidbody_world
rbw.point_cache.frame_start = 1
rbw.point_cache.frame_end = 250
rbw.substeps_per_frame = 10
rbw.solver_iterations = 10
```

## Rigid Body Constraints

```python
# Create empty for constraint
bpy.ops.object.empty_add(location=(0, 0, 2))
constraint_obj = bpy.context.active_object

# Add rigid body constraint
bpy.ops.rigidbody.constraint_add()
rbc = constraint_obj.rigid_body_constraint

rbc.type = 'HINGE'          # 'FIXED', 'POINT', 'HINGE', 'SLIDER', 'PISTON',
                              # 'GENERIC', 'GENERIC_SPRING', 'MOTOR'
rbc.object1 = bpy.data.objects["Object1"]
rbc.object2 = bpy.data.objects["Object2"]

# Hinge limits
rbc.use_limit_ang_z = True
rbc.limit_ang_z_lower = -1.57  # Radians
rbc.limit_ang_z_upper = 1.57
```

## Cloth Simulation

```python
obj = bpy.context.active_object

# Add cloth modifier
cloth_mod = obj.modifiers.new("Cloth", 'CLOTH')
cloth = cloth_mod.settings

# Physical properties
cloth.mass = 0.3               # kg
cloth.air_damping = 1.0

# Stiffness
cloth.tension_stiffness = 15.0
cloth.compression_stiffness = 15.0
cloth.shear_stiffness = 5.0
cloth.bending_stiffness = 0.5

# Quality
cloth.quality = 5              # Simulation steps per frame

# Collision settings
collision = cloth_mod.collision_settings
collision.use_collision = True
collision.distance_min = 0.015
collision.use_self_collision = True
collision.self_distance_min = 0.015

# Pin group (vertex group that stays fixed)
cloth.vertex_group_mass = "Pin"  # Name of vertex group
```

## Collision Objects

```python
obj = bpy.context.active_object

# Add collision modifier (makes object a collider for cloth/particles)
coll_mod = obj.modifiers.new("Collision", 'COLLISION')
coll = coll_mod.settings

coll.thickness_outer = 0.02
coll.thickness_inner = 0.2
coll.cloth_friction = 5.0
coll.damping = 0.1
```

## Soft Body

```python
obj = bpy.context.active_object

# Add soft body modifier
sb_mod = obj.modifiers.new("Softbody", 'SOFT_BODY')
sb = sb_mod.settings

sb.mass = 1.0
sb.friction = 0.5
sb.speed = 1.0

# Springs
sb.pull = 0.5          # Pull stiffness
sb.push = 0.5          # Push stiffness
sb.damping = 0.5
sb.bend = 0.5          # Bending stiffness

# Goal (attraction to original shape)
sb.goal_spring = 0.5
sb.goal_friction = 0.5
sb.goal_default = 0.7
sb.vertex_group_goal = "Goal"  # Vertex group for goal weights
```

## Fluid Simulation

```python
# Blender 5.0 uses Mantaflow for fluids
obj = bpy.context.active_object

# Add fluid modifier
fluid_mod = obj.modifiers.new("Fluid", 'FLUID')

# Domain (the bounding box for simulation)
fluid_mod.fluid_type = 'DOMAIN'
domain = fluid_mod.domain_settings
domain.domain_type = 'LIQUID'    # 'GAS' for smoke/fire, 'LIQUID' for water
domain.resolution_max = 64
domain.use_adaptive_domain = True
domain.cache_frame_start = 1
domain.cache_frame_end = 250

# Flow (emitter)
# On a different object:
flow_obj = bpy.data.objects["FlowEmitter"]
flow_mod = flow_obj.modifiers.new("Fluid", 'FLUID')
flow_mod.fluid_type = 'FLOW'
flow = flow_mod.flow_settings
flow.flow_type = 'LIQUID'       # 'SMOKE', 'FIRE', 'BOTH', 'LIQUID'
flow.flow_behavior = 'INFLOW'   # 'INFLOW', 'OUTFLOW', 'GEOMETRY'

# Effector (obstacle)
# On a different object:
eff_obj = bpy.data.objects["Obstacle"]
eff_mod = eff_obj.modifiers.new("Fluid", 'FLUID')
eff_mod.fluid_type = 'EFFECTOR'
```

## Baking Simulations

```python
# Bake rigid body
scene = bpy.context.scene
# Set frame range
scene.rigidbody_world.point_cache.frame_start = 1
scene.rigidbody_world.point_cache.frame_end = 250
# Bake
bpy.ops.ptcache.bake_all(bake=True)

# Free bake
bpy.ops.ptcache.free_bake_all()

# For cloth/softbody, bake per modifier
# Select the object first, then:
bpy.ops.ptcache.bake(bake=True)
```
