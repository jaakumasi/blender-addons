# Blender UI Layout API

## Panel Setup

```python
class MY_PT_panel(bpy.types.Panel):
    bl_label = "My Panel"
    bl_idname = "VIEW3D_PT_my_panel"
    bl_space_type = 'VIEW_3D'       # Where the panel lives
    bl_region_type = 'UI'           # 'UI' = sidebar (N-panel), 'TOOLS' = tool shelf
    bl_category = "My Tab"          # Tab name in sidebar
    bl_context = ""                 # Optional: limit to mode ("objectmode", "mesh_edit", etc.)
    bl_options = {'DEFAULT_CLOSED'} # Optional: collapsed by default

    def draw(self, context):
        layout = self.layout
        # ... build UI here
```

### Common bl_space_type Values
- `'VIEW_3D'` — 3D Viewport
- `'PROPERTIES'` — Properties editor
- `'NODE_EDITOR'` — Node editor
- `'IMAGE_EDITOR'` — Image/UV editor
- `'SEQUENCE_EDITOR'` — Video sequencer
- `'CLIP_EDITOR'` — Movie clip editor
- `'TEXT_EDITOR'` — Text editor
- `'GRAPH_EDITOR'` — Graph editor
- `'DOPESHEET_EDITOR'` — Dope sheet
- `'NLA_EDITOR'` — NLA editor
- `'PREFERENCES'` — Preferences window

### Common bl_region_type Values
- `'UI'` — Sidebar (N-panel in 3D view)
- `'TOOLS'` — Tool shelf (T-panel)
- `'WINDOW'` — Main window area (for Properties editor panels)
- `'HEADER'` — Header area
- `'TOOL_HEADER'` — Tool header

### bl_context for Properties Editor
When `bl_space_type = 'PROPERTIES'`, use `bl_context` to pick the tab:
- `"scene"`, `"render"`, `"output"`, `"view_layer"`, `"world"`, `"object"`, `"modifier"`, `"particle"`, `"physics"`, `"constraint"`, `"data"`, `"material"`, `"texture"`

## Layout Methods

### Containers

```python
# Row - horizontal layout
row = layout.row(align=False)

# Column - vertical layout
col = layout.column(align=False)

# Split - side by side columns with factor
split = layout.split(factor=0.5)
left = split.column()
right = split.column()

# Box - bordered container
box = layout.box()
box.label(text="Inside a box")

# Grid flow - automatic grid layout
grid = layout.grid_flow(row_major=True, columns=3, even_columns=True, even_rows=False, align=False)
```

### Display Elements

```python
# Label
layout.label(text="Hello World", icon='INFO')

# Separator (empty space)
layout.separator()
layout.separator(factor=2.0)  # Double space

# Property (auto-creates appropriate widget)
layout.prop(data, "property_name")
layout.prop(data, "property_name", text="Custom Label")
layout.prop(data, "property_name", text="", icon='CAMERA_DATA')  # Icon only
layout.prop(data, "property_name", toggle=True)   # Toggle button
layout.prop(data, "property_name", slider=True)   # Slider
layout.prop(data, "property_name", expand=True)    # Expanded enum buttons

# Operator button
layout.operator("mesh.add_object", text="Add Object", icon='MESH_CUBE')
op = layout.operator("mesh.add_object")
op.scale = (2.0, 2.0, 2.0)  # Set operator properties

# Menu
layout.menu("VIEW3D_MT_my_menu", text="My Menu", icon='DOWNARROW_HLT')

# Template for selecting ID blocks
layout.template_ID(context.object, "data")
layout.template_list("UI_UL_list", "", data, "collection", data, "active_index")
```

### Layout Properties

```python
row = layout.row()
row.scale_x = 2.0      # Horizontal scale
row.scale_y = 3.0      # Vertical scale (make big button)
row.enabled = False     # Grey out (disabled)
row.active = False      # Dim (inactive look)
row.alert = True        # Red highlight
row.alignment = 'LEFT'  # 'LEFT', 'CENTER', 'RIGHT', 'EXPAND'
```

### Sub-layouts for Mixed Sizing

```python
row = layout.row(align=True)
row.operator("render.render")

sub = row.row()
sub.scale_x = 2.0
sub.operator("render.render")  # This button is 2x wider

row.operator("render.render")
```

## Sub-panels

```python
class VIEW3D_PT_main(bpy.types.Panel):
    bl_label = "Main Panel"
    bl_idname = "VIEW3D_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "My Tab"

class VIEW3D_PT_sub(bpy.types.Panel):
    bl_label = "Sub Panel"
    bl_idname = "VIEW3D_PT_sub"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "My Tab"
    bl_parent_id = "VIEW3D_PT_main"    # Parent panel's bl_idname
    bl_options = {'DEFAULT_CLOSED'}
```

## Common Icons

Use `bpy.types.UILayout.icon()` or browse icons in Blender's Script editor.

Common icons: `'NONE'`, `'OBJECT_DATA'`, `'MESH_DATA'`, `'CAMERA_DATA'`, `'LIGHT_DATA'`, `'MATERIAL'`, `'WORLD'`, `'SCENE_DATA'`, `'RENDER_STILL'`, `'RENDER_ANIMATION'`, `'PLAY'`, `'PAUSE'`, `'TRIA_RIGHT'`, `'TRIA_DOWN'`, `'ADD'`, `'REMOVE'`, `'X'`, `'CHECKMARK'`, `'ERROR'`, `'INFO'`, `'QUESTION'`, `'PLUGIN'`, `'FILE_FOLDER'`, `'FILE'`, `'EXPORT'`, `'IMPORT'`, `'DOWNARROW_HLT'`, `'RIGHTARROW'`, `'PREFERENCES'`, `'MODIFIER'`, `'CONSTRAINT'`, `'PARTICLE_DATA'`, `'PHYSICS'`
