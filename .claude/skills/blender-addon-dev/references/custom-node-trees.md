# Custom Node Trees

Addons can define entirely custom node editors with their own node types,
sockets, and trees. This is useful for visual scripting, material systems,
or any graph-based workflow.

## Defining a Custom Node Tree

```python
import bpy
from bpy.types import NodeTree, Node, NodeSocket
from bpy.props import FloatProperty, StringProperty, EnumProperty


class MyCustomTree(NodeTree):
    """A custom node tree type for my addon."""
    bl_idname = 'MyCustomTreeType'
    bl_label = "My Custom Node Tree"
    bl_icon = 'NODETREE'  # Icon in the editor header dropdown
```

## Defining Custom Sockets

```python
class MyFloatSocket(NodeSocket):
    """Custom float socket with a color."""
    bl_idname = 'MyFloatSocketType'
    bl_label = "My Float Socket"

    # Socket property (shown when no link is connected)
    default_value: FloatProperty(
        name="Value",
        default=0.0,
        min=0.0,
        max=1.0,
    )

    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text=text)
        else:
            layout.prop(self, "default_value", text=text)

    def draw_color(self, context, node):
        return (0.5, 0.7, 1.0, 1.0)  # RGBA — socket color


class MyStringSocket(NodeSocket):
    """Custom string socket."""
    bl_idname = 'MyStringSocketType'
    bl_label = "My String Socket"

    default_value: StringProperty(name="Value", default="")

    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text=text)
        else:
            layout.prop(self, "default_value", text=text)

    def draw_color(self, context, node):
        return (0.9, 0.9, 0.3, 1.0)
```

## Defining Custom Nodes

```python
class MyCustomNodeBase:
    """Base class for nodes in this tree type."""

    @classmethod
    def poll(cls, ntree):
        # Only show in our custom tree
        return ntree.bl_idname == 'MyCustomTreeType'


class MyInputNode(MyCustomNodeBase, Node):
    """A node that provides an input value."""
    bl_idname = 'MyInputNodeType'
    bl_label = "Input Value"
    bl_icon = 'IMPORT'

    # Node properties (shown in the node body)
    value: FloatProperty(name="Value", default=1.0, min=0.0, max=100.0)

    def init(self, context):
        """Called when node is created. Set up sockets here."""
        self.outputs.new('MyFloatSocketType', "Value")

    def draw_buttons(self, context, layout):
        """Draw node UI (inside the node body)."""
        layout.prop(self, "value")

    def draw_buttons_ext(self, context, layout):
        """Draw extended UI (in the sidebar when node is selected)."""
        layout.prop(self, "value")

    # Optional: label shown on the node
    def draw_label(self):
        return f"Input: {self.value:.1f}"


class MyProcessNode(MyCustomNodeBase, Node):
    """A node that processes input values."""
    bl_idname = 'MyProcessNodeType'
    bl_label = "Process"
    bl_icon = 'MODIFIER'

    operation: EnumProperty(
        name="Operation",
        items=[
            ('ADD', "Add", "Add values"),
            ('MULTIPLY', "Multiply", "Multiply values"),
            ('POWER', "Power", "Raise to power"),
        ],
        default='ADD',
    )

    def init(self, context):
        self.inputs.new('MyFloatSocketType', "A")
        self.inputs.new('MyFloatSocketType', "B")
        self.outputs.new('MyFloatSocketType', "Result")

    def draw_buttons(self, context, layout):
        layout.prop(self, "operation", text="")


class MyOutputNode(MyCustomNodeBase, Node):
    """A node that displays/uses the final result."""
    bl_idname = 'MyOutputNodeType'
    bl_label = "Output"
    bl_icon = 'EXPORT'

    def init(self, context):
        self.inputs.new('MyFloatSocketType', "Value")

    def draw_buttons(self, context, layout):
        layout.label(text="Final Output")
```

## Node Categories (Add Menu)

```python
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories


class MyNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'MyCustomTreeType'


node_categories = [
    MyNodeCategory("INPUT_NODES", "Input", items=[
        NodeItem("MyInputNodeType"),
    ]),
    MyNodeCategory("PROCESS_NODES", "Processing", items=[
        NodeItem("MyProcessNodeType"),
    ]),
    MyNodeCategory("OUTPUT_NODES", "Output", items=[
        NodeItem("MyOutputNodeType"),
    ]),
]
```

## Evaluating the Node Tree

```python
def evaluate_tree(node_tree):
    """Walk the node tree and compute values.

    Custom node trees don't auto-evaluate like shader nodes.
    Your addon must implement the evaluation logic.
    """
    # Find output nodes
    output_nodes = [n for n in node_tree.nodes if n.bl_idname == 'MyOutputNodeType']

    for output_node in output_nodes:
        result = evaluate_node(output_node)
        print(f"Output: {result}")

    return result


def evaluate_node(node):
    """Recursively evaluate a node by following input links."""
    if node.bl_idname == 'MyInputNodeType':
        return node.value

    elif node.bl_idname == 'MyProcessNodeType':
        a = get_input_value(node, "A")
        b = get_input_value(node, "B")

        if node.operation == 'ADD':
            return a + b
        elif node.operation == 'MULTIPLY':
            return a * b
        elif node.operation == 'POWER':
            return a ** b

    elif node.bl_idname == 'MyOutputNodeType':
        return get_input_value(node, "Value")

    return 0.0


def get_input_value(node, input_name):
    """Get the value from an input socket, following links if connected."""
    socket = node.inputs.get(input_name)
    if socket is None:
        return 0.0

    if socket.is_linked:
        # Follow the link to the connected output socket
        link = socket.links[0]
        connected_node = link.from_node
        return evaluate_node(connected_node)
    else:
        return socket.default_value
```

## Registration

```python
classes = (
    MyCustomTree,
    MyFloatSocket,
    MyStringSocket,
    MyInputNode,
    MyProcessNode,
    MyOutputNode,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_node_categories("MY_CUSTOM_NODES", node_categories)


def unregister():
    unregister_node_categories("MY_CUSTOM_NODES")
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

## Tips for Custom Node Trees

### Socket Compatibility
Only sockets of the same `bl_idname` can be linked by default. To allow
cross-type linking, override `NodeTree.valid_socket_type()`.

### Node Colors
```python
class MyNode(Node):
    def init(self, context):
        self.use_custom_color = True
        self.color = (0.2, 0.4, 0.6)  # RGB
```

### Dynamic Sockets
```python
class MyDynamicNode(MyCustomNodeBase, Node):
    bl_idname = 'MyDynamicNodeType'
    bl_label = "Dynamic Inputs"

    input_count: bpy.props.IntProperty(name="Inputs", default=2, min=1, max=10,
                                        update=lambda self, ctx: self.update_sockets())

    def init(self, context):
        self.update_sockets()
        self.outputs.new('MyFloatSocketType', "Result")

    def update_sockets(self):
        # Remove extra inputs
        while len(self.inputs) > self.input_count:
            self.inputs.remove(self.inputs[-1])
        # Add missing inputs
        while len(self.inputs) < self.input_count:
            self.inputs.new('MyFloatSocketType', f"Input {len(self.inputs)}")

    def draw_buttons(self, context, layout):
        layout.prop(self, "input_count")
```

### Updating on Connection Changes
```python
class MyCustomTree(NodeTree):
    bl_idname = 'MyCustomTreeType'
    bl_label = "My Custom Node Tree"

    def update(self):
        """Called when links change. Use for auto-evaluation or validation."""
        # Re-evaluate tree when connections change
        pass
```

### Using with Shader/Compositor Nodes
If you want to add custom nodes to the EXISTING shader or compositor tree
(instead of creating a whole new tree type), set the poll to match:

```python
class MyShaderNode(Node):
    bl_idname = 'MyCustomShaderNode'
    bl_label = "My Custom Shader"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == 'ShaderNodeTree'
```

Note: Custom shader nodes won't be evaluated by Cycles/EEVEE automatically.
They are UI-only unless you translate them to actual shader nodes via a handler.
