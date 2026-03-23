import bpy
from .physics_engine import get_or_create_state

_updating = False
_handlers_registered = False


@bpy.app.handlers.persistent
def on_depsgraph_update(scene, depsgraph):
    """Called after every dependency graph update.

    Detects object movement and advances the spring simulation.
    The recursion guard prevents infinite loops since writing custom
    properties triggers another depsgraph update.
    """
    global _updating
    if _updating:
        return

    _updating = True
    try:
        dt = 1.0 / max(scene.render.fps, 1)

        for update in depsgraph.updates:
            obj_id = update.id
            if not isinstance(obj_id, bpy.types.Object):
                continue
            if obj_id.type != 'MESH':
                continue

            # Get the original object (not the evaluated copy)
            obj = bpy.data.objects.get(obj_id.name)
            if obj is None:
                continue

            pm = obj.physics_machine
            if not pm.enabled:
                continue

            state = get_or_create_state(obj)
            state.step(obj, dt)
    finally:
        _updating = False


@bpy.app.handlers.persistent
def on_load_post(dummy):
    """Re-register handlers after file load."""
    register_handlers()


def register_handlers():
    """Add handlers to Blender's handler lists."""
    global _handlers_registered

    if _handlers_registered:
        return

    if on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(on_depsgraph_update)

    if on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(on_load_post)

    _handlers_registered = True


def unregister_handlers():
    """Remove handlers from Blender's handler lists."""
    global _handlers_registered

    if on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(on_depsgraph_update)

    if on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_load_post)

    _handlers_registered = False
