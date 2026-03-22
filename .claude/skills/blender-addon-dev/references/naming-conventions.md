# Blender Naming Conventions

## bl_idname Format

All Blender classes that integrate with the UI must have a `bl_idname` following this strict pattern:

```
CATEGORY_XX_name
```

Where:
- `CATEGORY` = uppercase area/context identifier
- `XX` = two-letter type code
- `name` = lowercase snake_case name

### Type Codes

| Code | Type | Example |
|------|------|---------|
| `OT` | Operator | `OBJECT_OT_add_cube` |
| `PT` | Panel | `VIEW3D_PT_my_panel` |
| `MT` | Menu | `OBJECT_MT_my_menu` |
| `HT` | Header | `VIEW3D_HT_my_header` |
| `UL` | UIList | `OBJECT_UL_my_list` |
| `PIE` | Pie Menu | `VIEW3D_PIE_my_pie` |

### Common Category Prefixes

| Category | Used For |
|----------|----------|
| `OBJECT` | Object-level operations |
| `MESH` | Mesh editing operations |
| `CURVE` | Curve operations |
| `VIEW3D` | 3D Viewport panels/menus |
| `SCENE` | Scene-level panels |
| `RENDER` | Render panels |
| `MATERIAL` | Material panels |
| `NODE` | Node editor operations |
| `SEQUENCER` | Video sequence editor |
| `IMAGE` | Image editor |
| `CLIP` | Movie clip editor |
| `TEXT` | Text editor |
| `GRAPH` | Graph editor |
| `DOPESHEET` | Dope sheet |
| `NLA` | NLA editor |
| `TOPBAR` | Top bar menus |

### Operator bl_idname Special Rules

For operators, `bl_idname` determines the Python call path:
```python
bl_idname = "mesh.add_object"
# Callable as: bpy.ops.mesh.add_object()
```

Rules:
- Must contain exactly ONE dot (`.`)
- Part before dot = module (lowercase)
- Part after dot = function name (lowercase, underscores OK)
- No uppercase in operator `bl_idname`

### Panel bl_idname Rules

```python
bl_idname = "VIEW3D_PT_my_addon_panel"
```

Rules:
- Use `CATEGORY_PT_name` format
- `bl_space_type` must match the category (e.g., `VIEW3D` → `bl_space_type = 'VIEW_3D'`)
- Sub-panels set `bl_parent_id` to the parent panel's `bl_idname`

### Class Name Convention

The Python class name does NOT need to follow the `CATEGORY_XX_name` pattern, but many developers use matching names for clarity:

```python
# Both are valid:
class OBJECT_OT_my_operator(bpy.types.Operator):
    bl_idname = "object.my_operator"

class MyOperator(bpy.types.Operator):
    bl_idname = "object.my_operator"
```

### Required Class Attributes

| Class Type | Required Attributes |
|------------|-------------------|
| Operator | `bl_idname`, `bl_label` |
| Panel | `bl_idname`, `bl_label`, `bl_space_type`, `bl_region_type` |
| Menu | `bl_idname`, `bl_label` |
| Header | `bl_idname`, `bl_space_type` |
| UIList | `bl_idname` |

### bl_options for Operators

Common options (set):
- `'REGISTER'` — register in undo history
- `'UNDO'` — support undo
- `'INTERNAL'` — hide from search
- `'BLOCKING'` — block all events until finished
- `'GRAB_CURSOR'` — grab cursor during modal
- `'PRESET'` — show preset selector

Typical: `bl_options = {'REGISTER', 'UNDO'}`
