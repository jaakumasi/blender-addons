"""
Builds the PhysicsMachine Geometry Nodes modifier.

Follows the exact pattern from Blender 5.0's official geometry_nodes.py:
  1. Create node tree
  2. Add interface sockets BEFORE creating nodes
  3. Create GroupInput/GroupOutput nodes (they auto-sync with interface)
  4. Set output_node.is_active_output = True
  5. Link everything
"""

import bpy
import traceback

NODE_GROUP_NAME = "PhysicsMachine_Deform"


def get_or_create_node_group(force_rebuild=False):
    if NODE_GROUP_NAME in bpy.data.node_groups:
        if force_rebuild:
            bpy.data.node_groups.remove(bpy.data.node_groups[NODE_GROUP_NAME])
        else:
            return bpy.data.node_groups[NODE_GROUP_NAME]
    return _build_node_group()


def _build_node_group():
    group = bpy.data.node_groups.new(NODE_GROUP_NAME, 'GeometryNodeTree')

    # -------------------------------------------------------
    # Step 1: Define ALL interface sockets BEFORE creating nodes
    # (nodes auto-sync their sockets from the interface)
    # -------------------------------------------------------
    group.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    group.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    group.interface.new_socket("Deform X", in_out='INPUT', socket_type='NodeSocketFloat')
    group.interface.new_socket("Deform Y", in_out='INPUT', socket_type='NodeSocketFloat')
    group.interface.new_socket("Deform Z", in_out='INPUT', socket_type='NodeSocketFloat')
    group.interface.new_socket("Secondary X", in_out='INPUT', socket_type='NodeSocketFloat')
    group.interface.new_socket("Secondary Y", in_out='INPUT', socket_type='NodeSocketFloat')
    group.interface.new_socket("Secondary Z", in_out='INPUT', socket_type='NodeSocketFloat')
    group.interface.new_socket("Gravity Strength", in_out='INPUT', socket_type='NodeSocketFloat')
    group.interface.new_socket("Influence Falloff", in_out='INPUT', socket_type='NodeSocketFloat')

    for item in group.interface.items_tree:
        if hasattr(item, 'default_value'):
            if item.name == "Gravity Strength":
                item.default_value = 1.0
            elif item.name == "Influence Falloff":
                item.default_value = 1.0

    # -------------------------------------------------------
    # Step 2: Create GroupInput and GroupOutput nodes
    # (they auto-populate sockets from the interface above)
    # -------------------------------------------------------
    input_node = group.nodes.new('NodeGroupInput')
    input_node.select = False
    input_node.location = (-1200, 0)

    output_node = group.nodes.new('NodeGroupOutput')
    output_node.is_active_output = True
    output_node.select = False
    output_node.location = (800, 0)

    # -------------------------------------------------------
    # Step 3: Build the node graph
    # -------------------------------------------------------
    try:
        _wire_nodes(group)
    except Exception:
        traceback.print_exc()
        print("PhysicsMachine: Node build failed — creating passthrough")
        # Remove everything except GroupInput/GroupOutput, wire direct passthrough
        for node in list(group.nodes):
            if node.bl_idname not in ('NodeGroupInput', 'NodeGroupOutput'):
                group.nodes.remove(node)
        group.links.clear()
        group.links.new(
            group.nodes["Group Input"].outputs[0],
            group.nodes["Group Output"].inputs[0]
        )

    return group


def _wire_nodes(group):
    """Build all processing nodes and wire them up."""
    nodes = group.nodes
    links = group.links

    gi = nodes["Group Input"]
    go = nodes["Group Output"]

    # === Get vertex position Z ===
    pos = nodes.new('GeometryNodeInputPosition')
    pos.location = (-1000, -300)

    sep_pos = nodes.new('ShaderNodeSeparateXYZ')
    sep_pos.location = (-800, -300)
    links.new(pos.outputs[0], sep_pos.inputs[0])

    # === Bounding box for Z normalization ===
    bbox = nodes.new('GeometryNodeBoundBox')
    bbox.location = (-1000, -550)
    links.new(gi.outputs[0], bbox.inputs[0])  # outputs[0] = Geometry

    sep_min = nodes.new('ShaderNodeSeparateXYZ')
    sep_min.location = (-800, -550)
    links.new(bbox.outputs["Min"], sep_min.inputs[0])

    sep_max = nodes.new('ShaderNodeSeparateXYZ')
    sep_max.location = (-800, -750)
    links.new(bbox.outputs["Max"], sep_max.inputs[0])

    # z_range = max(max_z - min_z, 0.001)
    z_range = nodes.new('ShaderNodeMath')
    z_range.operation = 'SUBTRACT'
    z_range.location = (-600, -650)
    links.new(sep_max.outputs["Z"], z_range.inputs[0])
    links.new(sep_min.outputs["Z"], z_range.inputs[1])

    z_safe = nodes.new('ShaderNodeMath')
    z_safe.operation = 'MAXIMUM'
    z_safe.location = (-400, -650)
    links.new(z_range.outputs[0], z_safe.inputs[0])
    z_safe.inputs[1].default_value = 0.001

    # === Weight = clamp((z - min_z) / z_range, 0, 1) ===
    z_sub = nodes.new('ShaderNodeMath')
    z_sub.operation = 'SUBTRACT'
    z_sub.location = (-600, -300)
    links.new(sep_pos.outputs["Z"], z_sub.inputs[0])
    links.new(sep_min.outputs["Z"], z_sub.inputs[1])

    z_div = nodes.new('ShaderNodeMath')
    z_div.operation = 'DIVIDE'
    z_div.location = (-400, -300)
    links.new(z_sub.outputs[0], z_div.inputs[0])
    links.new(z_safe.outputs[0], z_div.inputs[1])

    clamp = nodes.new('ShaderNodeClamp')
    clamp.location = (-200, -300)
    links.new(z_div.outputs[0], clamp.inputs[0])
    clamp.inputs[1].default_value = 0.0
    clamp.inputs[2].default_value = 1.0

    # weight = pow(weight, falloff)
    power = nodes.new('ShaderNodeMath')
    power.operation = 'POWER'
    power.location = (0, -300)
    links.new(clamp.outputs[0], power.inputs[0])
    links.new(gi.outputs["Influence Falloff"], power.inputs[1])

    # === Primary deformation vector ===
    comb_pri = nodes.new('ShaderNodeCombineXYZ')
    comb_pri.location = (-400, 200)
    links.new(gi.outputs["Deform X"], comb_pri.inputs[0])
    links.new(gi.outputs["Deform Y"], comb_pri.inputs[1])
    links.new(gi.outputs["Deform Z"], comb_pri.inputs[2])

    # === Secondary deformation vector * 0.3 ===
    comb_sec = nodes.new('ShaderNodeCombineXYZ')
    comb_sec.location = (-400, 400)
    links.new(gi.outputs["Secondary X"], comb_sec.inputs[0])
    links.new(gi.outputs["Secondary Y"], comb_sec.inputs[1])
    links.new(gi.outputs["Secondary Z"], comb_sec.inputs[2])

    scale_sec = nodes.new('ShaderNodeVectorMath')
    scale_sec.operation = 'SCALE'
    scale_sec.location = (-200, 400)
    links.new(comb_sec.outputs[0], scale_sec.inputs[0])
    scale_sec.inputs["Scale"].default_value = 0.3

    # primary + secondary
    add_vecs = nodes.new('ShaderNodeVectorMath')
    add_vecs.operation = 'ADD'
    add_vecs.location = (0, 200)
    links.new(comb_pri.outputs[0], add_vecs.inputs[0])
    links.new(scale_sec.outputs[0], add_vecs.inputs[1])

    # === Gravity: (0, 0, -gravity * 0.1) ===
    grav_mul = nodes.new('ShaderNodeMath')
    grav_mul.operation = 'MULTIPLY'
    grav_mul.location = (-200, -100)
    links.new(gi.outputs["Gravity Strength"], grav_mul.inputs[0])
    grav_mul.inputs[1].default_value = -0.1

    grav_vec = nodes.new('ShaderNodeCombineXYZ')
    grav_vec.location = (0, -100)
    grav_vec.inputs[0].default_value = 0.0
    grav_vec.inputs[1].default_value = 0.0
    links.new(grav_mul.outputs[0], grav_vec.inputs[2])

    # deform + gravity
    add_grav = nodes.new('ShaderNodeVectorMath')
    add_grav.operation = 'ADD'
    add_grav.location = (200, 200)
    links.new(add_vecs.outputs[0], add_grav.inputs[0])
    links.new(grav_vec.outputs[0], add_grav.inputs[1])

    # === offset * weight ===
    final = nodes.new('ShaderNodeVectorMath')
    final.operation = 'SCALE'
    final.location = (400, 0)
    links.new(add_grav.outputs[0], final.inputs[0])
    links.new(power.outputs[0], final.inputs["Scale"])

    # === Set Position ===
    set_pos = nodes.new('GeometryNodeSetPosition')
    set_pos.location = (600, 0)
    links.new(gi.outputs[0], set_pos.inputs["Geometry"])
    links.new(final.outputs[0], set_pos.inputs["Offset"])

    # === Wire to output ===
    links.new(set_pos.outputs["Geometry"], go.inputs[0])


# ---------------------------------------------------------------
# Modifier management
# ---------------------------------------------------------------

def apply_modifier(obj):
    node_group = get_or_create_node_group()

    mod = obj.modifiers.get("PhysicsMachine")
    if not mod:
        mod = obj.modifiers.new("PhysicsMachine", 'NODES')

    mod.node_group = node_group

    for prop in ("pm_deform_x", "pm_deform_y", "pm_deform_z",
                 "pm_secondary_x", "pm_secondary_y", "pm_secondary_z"):
        obj[prop] = 0.0

    _setup_drivers(obj, mod)
    return mod


def _setup_drivers(obj, mod):
    socket_map = {
        "Deform X": "pm_deform_x",
        "Deform Y": "pm_deform_y",
        "Deform Z": "pm_deform_z",
        "Secondary X": "pm_secondary_x",
        "Secondary Y": "pm_secondary_y",
        "Secondary Z": "pm_secondary_z",
    }

    for item in mod.node_group.interface.items_tree:
        if not hasattr(item, 'identifier') or not hasattr(item, 'in_out'):
            continue
        if item.in_out != 'INPUT' or item.name == "Geometry":
            continue

        ident = item.identifier
        if item.name in socket_map:
            _add_driver(obj, ident, f'["{socket_map[item.name]}"]')
        elif item.name == "Gravity Strength":
            _add_driver(obj, ident, "physics_machine.gravity_strength")
        elif item.name == "Influence Falloff":
            _add_driver(obj, ident, "physics_machine.influence_falloff")


def _add_driver(obj, socket_identifier, data_path_source):
    dp = f'modifiers["PhysicsMachine"]["{socket_identifier}"]'
    try:
        obj.driver_remove(dp)
    except TypeError:
        pass

    fc = obj.driver_add(dp)
    fc.driver.type = 'AVERAGE'
    var = fc.driver.variables.new()
    var.name = "v"
    var.type = 'SINGLE_PROP'
    var.targets[0].id_type = 'OBJECT'
    var.targets[0].id = obj
    var.targets[0].data_path = data_path_source


def remove_modifier(obj):
    mod = obj.modifiers.get("PhysicsMachine")
    if mod:
        if mod.node_group:
            for item in mod.node_group.interface.items_tree:
                if not hasattr(item, 'identifier'):
                    continue
                if item.name == "Geometry":
                    continue
                dp = f'modifiers["PhysicsMachine"]["{item.identifier}"]'
                try:
                    obj.driver_remove(dp)
                except TypeError:
                    pass
        obj.modifiers.remove(mod)

    for prop in ("pm_deform_x", "pm_deform_y", "pm_deform_z",
                 "pm_secondary_x", "pm_secondary_y", "pm_secondary_z"):
        if prop in obj:
            del obj[prop]
