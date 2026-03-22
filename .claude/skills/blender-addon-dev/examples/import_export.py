# Import/Export addon example
# Demonstrates both ImportHelper and ExportHelper patterns.
# These helpers provide the file browser dialog automatically.

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper


# ---------------------------------------------------------------------------
# Import Operator
# ---------------------------------------------------------------------------

class MY_OT_import_data(Operator, ImportHelper):
    """Import data from a custom file format"""
    bl_idname = "my_addon.import_data"
    bl_label = "Import My Data"
    bl_options = {'REGISTER', 'UNDO'}

    # ImportHelper provides: self.filepath, self.filename, self.directory

    # File browser filter
    filename_ext = ".mydata"
    filter_glob: StringProperty(
        default="*.mydata;*.txt",
        options={'HIDDEN'},
        maxlen=255,
    )

    # Operator-specific settings (shown in file browser sidebar)
    import_normals: BoolProperty(
        name="Import Normals",
        description="Import custom normals if available",
        default=True,
    )
    axis_forward: EnumProperty(
        name="Forward Axis",
        items=[
            ('X', "X", ""),
            ('Y', "Y", ""),
            ('Z', "Z", ""),
            ('NEGATIVE_X', "-X", ""),
            ('NEGATIVE_Y', "-Y", ""),
            ('NEGATIVE_Z', "-Z", ""),
        ],
        default='NEGATIVE_Z',
    )

    def execute(self, context):
        """Called after user selects a file and clicks Import."""
        # self.filepath is set by ImportHelper
        return self._read_file(context, self.filepath)

    def _read_file(self, context, filepath):
        """Read the file and create Blender objects."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = f.read()
        except (IOError, OSError) as e:
            self.report({'ERROR'}, f"Failed to read file: {e}")
            return {'CANCELLED'}

        # Process data and create objects...
        # (Replace with your actual import logic)
        self.report({'INFO'}, f"Imported from {filepath}")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Export Operator
# ---------------------------------------------------------------------------

class MY_OT_export_data(Operator, ExportHelper):
    """Export selected objects to a custom file format"""
    bl_idname = "my_addon.export_data"
    bl_label = "Export My Data"

    # ExportHelper provides: self.filepath

    filename_ext = ".mydata"
    filter_glob: StringProperty(
        default="*.mydata",
        options={'HIDDEN'},
        maxlen=255,
    )

    # Export settings
    export_selected_only: BoolProperty(
        name="Selected Only",
        description="Export only selected objects",
        default=True,
    )
    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers before exporting",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        return len(context.scene.objects) > 0

    def execute(self, context):
        """Called after user picks a save location and clicks Export."""
        return self._write_file(context, self.filepath)

    def _write_file(self, context, filepath):
        """Write object data to file."""
        if self.export_selected_only:
            objects = context.selected_objects
        else:
            objects = context.scene.objects

        if not objects:
            self.report({'WARNING'}, "No objects to export")
            return {'CANCELLED'}

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for obj in objects:
                    f.write(f"object: {obj.name}\n")
                    f.write(f"  location: {obj.location[0]:.4f} {obj.location[1]:.4f} {obj.location[2]:.4f}\n")
                    f.write(f"  type: {obj.type}\n")
                    if obj.type == 'MESH':
                        mesh = obj.data
                        f.write(f"  vertices: {len(mesh.vertices)}\n")
                        f.write(f"  polygons: {len(mesh.polygons)}\n")
                    f.write("\n")
        except (IOError, OSError) as e:
            self.report({'ERROR'}, f"Failed to write file: {e}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Exported {len(list(objects))} objects to {filepath}")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Menu integration — add to File > Import and File > Export
# ---------------------------------------------------------------------------

def menu_func_import(self, context):
    self.layout.operator(MY_OT_import_data.bl_idname, text="My Data (.mydata)")


def menu_func_export(self, context):
    self.layout.operator(MY_OT_export_data.bl_idname, text="My Data (.mydata)")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    MY_OT_import_data,
    MY_OT_export_data,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
