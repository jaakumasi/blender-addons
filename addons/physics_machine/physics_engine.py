from mathutils import Vector

# Global state store, keyed by object name
_states = {}


class PhysicsState:
    """Tracks spring simulation state for one object."""

    def __init__(self):
        self.prev_location = Vector((0, 0, 0))
        self.prev_velocity = Vector((0, 0, 0))
        self.initialized = False

        # Primary spring (slow wobble)
        self.deform_offset = Vector((0, 0, 0))
        self.deform_velocity = Vector((0, 0, 0))

        # Secondary spring (fast wobble)
        self.secondary_offset = Vector((0, 0, 0))
        self.secondary_velocity = Vector((0, 0, 0))

    def initialize(self, obj):
        """Capture initial position. Call when physics is first enabled."""
        self.prev_location = obj.matrix_world.translation.copy()
        self.prev_velocity = Vector((0, 0, 0))
        self.deform_offset = Vector((0, 0, 0))
        self.deform_velocity = Vector((0, 0, 0))
        self.secondary_offset = Vector((0, 0, 0))
        self.secondary_velocity = Vector((0, 0, 0))
        self.initialized = True

    def step(self, obj, dt):
        """Advance the spring simulation by one timestep.

        Computes object acceleration, applies spring forces, and writes
        the resulting deformation vectors to the object's custom properties
        so the Geometry Nodes modifier can read them.
        """
        if not self.initialized:
            self.initialize(obj)
            return

        settings = obj.physics_machine
        dt = max(dt, 1.0 / 120.0)  # Clamp dt to avoid instability

        # --- Object-level motion ---
        current_location = obj.matrix_world.translation.copy()
        current_velocity = current_location - self.prev_location
        acceleration = current_velocity - self.prev_velocity

        # Convert acceleration to local space so deformation follows object orientation
        inv_rot = obj.matrix_world.to_3x3().inverted_safe()
        local_acceleration = inv_rot @ acceleration

        self.prev_location = current_location
        self.prev_velocity = current_velocity

        # --- Primary spring ---
        stiffness = settings.stiffness
        damping_coeff = settings.damping * 2.0 * (stiffness ** 0.5)  # Critical damping ratio
        mass = settings.mass

        # Inertia force: object accelerated, so mesh "lags behind"
        inertia_force = -local_acceleration * mass * 50.0  # Scale factor for visible effect

        # Spring + damping + inertia
        spring_force = -stiffness * self.deform_offset
        damp_force = -damping_coeff * self.deform_velocity

        total_force = spring_force + damp_force + inertia_force
        self.deform_velocity += total_force * dt
        self.deform_offset += self.deform_velocity * dt

        # Clamp to prevent explosion
        max_disp = settings.max_displacement
        if self.deform_offset.length > max_disp:
            self.deform_offset = self.deform_offset.normalized() * max_disp
            # Also reduce velocity to prevent bouncing off clamp
            self.deform_velocity *= 0.5

        # --- Secondary spring (higher frequency wobble) ---
        if settings.secondary_enabled:
            sec_stiffness = settings.secondary_stiffness
            sec_damping = settings.secondary_damping * 2.0 * (sec_stiffness ** 0.5)

            sec_inertia = -local_acceleration * mass * 20.0
            sec_spring = -sec_stiffness * self.secondary_offset
            sec_damp = -sec_damping * self.secondary_velocity

            sec_total = sec_spring + sec_damp + sec_inertia
            self.secondary_velocity += sec_total * dt
            self.secondary_offset += self.secondary_velocity * dt

            sec_max = max_disp * 0.3
            if self.secondary_offset.length > sec_max:
                self.secondary_offset = self.secondary_offset.normalized() * sec_max
                self.secondary_velocity *= 0.5
        else:
            self.secondary_offset = Vector((0, 0, 0))

        # --- Write to custom properties (read by GN modifier) ---
        obj["pm_deform_x"] = self.deform_offset.x
        obj["pm_deform_y"] = self.deform_offset.y
        obj["pm_deform_z"] = self.deform_offset.z
        obj["pm_secondary_x"] = self.secondary_offset.x
        obj["pm_secondary_y"] = self.secondary_offset.y
        obj["pm_secondary_z"] = self.secondary_offset.z

    def reset(self):
        """Zero out all spring state."""
        self.deform_offset = Vector((0, 0, 0))
        self.deform_velocity = Vector((0, 0, 0))
        self.secondary_offset = Vector((0, 0, 0))
        self.secondary_velocity = Vector((0, 0, 0))


def get_or_create_state(obj):
    """Get or create a PhysicsState for the given object."""
    key = obj.name
    if key not in _states:
        state = PhysicsState()
        state.initialize(obj)
        _states[key] = state
    return _states[key]


def remove_state(obj):
    """Remove physics state for an object."""
    key = obj.name
    if key in _states:
        del _states[key]


def reset_state(obj):
    """Reset physics state for an object."""
    key = obj.name
    if key in _states:
        _states[key].reset()
    # Also zero the custom properties
    obj["pm_deform_x"] = 0.0
    obj["pm_deform_y"] = 0.0
    obj["pm_deform_z"] = 0.0
    obj["pm_secondary_x"] = 0.0
    obj["pm_secondary_y"] = 0.0
    obj["pm_secondary_z"] = 0.0


def clear_all_states():
    """Clear all physics states (called on unregister)."""
    _states.clear()
