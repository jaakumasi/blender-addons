# Blender Extension Manifest (blender_manifest.toml)

Since Blender 4.2, extensions use `blender_manifest.toml` instead of the legacy `bl_info` dict.

## Full Format

```toml
schema_version = "1.0.0"

# Required fields
id = "my_addon_name"                    # Unique ID, lowercase, underscores/hyphens OK
version = "1.0.0"                       # Semantic version
name = "My Addon Name"                  # Display name
tagline = "Short description of addon"  # One-line summary
maintainer = "Your Name <email@example.com>"
type = "add-on"                         # "add-on" or "theme"

# Blender version compatibility
blender_version_min = "5.0.0"
# blender_version_max = "6.0.0"        # Optional: upper bound (exclusive)

# License (SPDX format)
license = [
  "SPDX:GPL-3.0-or-later",
]

# Optional fields
# website = "https://example.com/my-addon"
# copyright = ["2024 Your Name"]

# Optional: tags for categorization
# See https://docs.blender.org/manual/en/dev/advanced/extensions/tags.html
# tags = ["Animation", "Mesh", "UV", "Rigging", "Node", "Import-Export"]

# Optional: platform restrictions
# platforms = ["windows-x64", "macos-arm64", "linux-x64"]
# Other: "windows-arm64", "macos-x64"

# Optional: bundle Python wheels
# wheels = [
#   "./wheels/some_package-1.0-py3-none-any.whl",
# ]

# Optional: permissions the addon requires
# [permissions]
# network = "Reason for needing internet access"
# files = "Reason for filesystem access"
# clipboard = "Reason for clipboard access"
# camera = "Reason for camera access"
# microphone = "Reason for microphone access"

# Optional: build settings
# [build]
# paths_exclude_pattern = [
#   "__pycache__/",
#   "/.git/",
#   "/*.zip",
# ]
```

## Important Notes

- When using `network` permission, also check `bpy.app.online_access` at runtime
- `blender_version_min` is inclusive, `blender_version_max` is exclusive
- The `id` field becomes the addon's directory name when installed
- Use semantic versioning (MAJOR.MINOR.PATCH)

## Packaging an Extension

To build a `.zip` for distribution:
```bash
# From the addon directory
"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" --command extension build
```

Or manually zip the addon directory (excluding `__pycache__/`, `.git/`, etc.).

## Legacy bl_info (for reference)

Still works but deprecated for new addons:
```python
bl_info = {
    "name": "My Addon",
    "author": "Your Name",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > My Tab",
    "description": "Short description",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}
```

Valid categories: `3D View`, `Add Curve`, `Add Mesh`, `Animation`, `Compositing`, `Development`, `Game Engine`, `Import-Export`, `Lighting`, `Material`, `Mesh`, `Node`, `Object`, `Paint`, `Physics`, `Render`, `Rigging`, `Scene`, `Sequencer`, `System`, `Text Editor`, `UV`
