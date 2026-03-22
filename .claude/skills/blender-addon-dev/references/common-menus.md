# Common Blender Menus for Addon Integration

Append your draw function to these menus to add addon entries.

## 3D Viewport Menus

### Add Menu (Shift+A)
```python
bpy.types.VIEW3D_MT_add              # Top-level Add menu
bpy.types.VIEW3D_MT_mesh_add         # Add > Mesh
bpy.types.VIEW3D_MT_curve_add        # Add > Curve
bpy.types.VIEW3D_MT_surface_add      # Add > Surface
bpy.types.VIEW3D_MT_light_add        # Add > Light
bpy.types.VIEW3D_MT_camera_add       # Add > Camera
bpy.types.VIEW3D_MT_armature_add     # Add > Armature
```

### Object Menu
```python
bpy.types.VIEW3D_MT_object           # Object menu
bpy.types.VIEW3D_MT_object_context_menu  # Right-click context menu
```

### Mesh Edit Mode
```python
bpy.types.VIEW3D_MT_edit_mesh        # Mesh menu (edit mode)
bpy.types.VIEW3D_MT_edit_mesh_context_menu  # Right-click (edit mode)
bpy.types.VIEW3D_MT_edit_mesh_vertices  # Vertex menu
bpy.types.VIEW3D_MT_edit_mesh_edges    # Edge menu
bpy.types.VIEW3D_MT_edit_mesh_faces    # Face menu
```

## Top Bar Menus

### File Menu
```python
bpy.types.TOPBAR_MT_file             # File menu
bpy.types.TOPBAR_MT_file_import      # File > Import
bpy.types.TOPBAR_MT_file_export      # File > Export
```

### Edit Menu
```python
bpy.types.TOPBAR_MT_edit             # Edit menu
bpy.types.TOPBAR_MT_edit_preferences # Edit > Preferences submenu area
```

### Render Menu
```python
bpy.types.TOPBAR_MT_render           # Render menu
```

## Properties Editor Menus

```python
bpy.types.MATERIAL_MT_context_menu   # Material slot context menu
bpy.types.OBJECT_MT_context_menu     # Object properties context menu
```

## Node Editor Menus

```python
bpy.types.NODE_MT_add                # Add node menu
bpy.types.NODE_MT_context_menu       # Right-click context menu
```

## Pattern: Appending to a Menu

```python
def draw_menu_item(self, context):
    self.layout.operator("my_addon.my_operator", text="My Action", icon='PLUGIN')

def register():
    bpy.types.VIEW3D_MT_mesh_add.append(draw_menu_item)

def unregister():
    bpy.types.VIEW3D_MT_mesh_add.remove(draw_menu_item)
```

## Pattern: Creating a Custom Menu

```python
class MY_MT_custom_menu(bpy.types.Menu):
    bl_idname = "MY_MT_custom_menu"
    bl_label = "My Custom Menu"

    def draw(self, context):
        layout = self.layout
        layout.operator("my_addon.action_a", text="Action A")
        layout.operator("my_addon.action_b", text="Action B")
        layout.separator()
        layout.operator("my_addon.action_c", text="Action C")

def register():
    bpy.utils.register_class(MY_MT_custom_menu)

def unregister():
    bpy.utils.unregister_class(MY_MT_custom_menu)
```

## Pattern: Creating a Pie Menu

```python
class MY_MT_pie_menu(bpy.types.Menu):
    bl_idname = "MY_MT_pie_menu"
    bl_label = "My Pie Menu"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Items placed in order: W, E, S, N, NW, NE, SW, SE
        pie.operator("my_addon.action_west")
        pie.operator("my_addon.action_east")
        pie.operator("my_addon.action_south")
        pie.operator("my_addon.action_north")
```
