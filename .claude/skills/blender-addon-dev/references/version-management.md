# Blender Addon Version Management

## Version Compatibility Strategy

Blender major versions (4.x → 5.x → 6.x) can introduce breaking API changes. Each addon version should target a specific Blender version range.

### blender_manifest.toml Version Fields

```toml
# Minimum Blender version required (inclusive)
blender_version_min = "5.0.0"

# Maximum Blender version supported (exclusive) - optional
# Set this when you KNOW a newer version breaks your addon
# blender_version_max = "6.0.0"
```

### When to set blender_version_max

- Do NOT set it preemptively — only when a breaking change is confirmed
- The extensions platform allows setting this retroactively if an issue is found
- Users on newer Blender versions won't be able to install if max is set

## Branching Strategy for Multi-Version Support

```
main (or blender-5x)     ← Active development for current Blender
├── blender-4x            ← Maintenance branch for Blender 4.x users
└── blender-6x            ← Future branch when Blender 6.0 releases
```

### When Blender 6.0 releases:
1. Create `blender-5x` branch from current main
2. Update `blender_version_max` on the 5.x branch: `blender_version_max = "6.0.0"`
3. Continue main for 6.x development
4. Update `blender_version_min` on main: `blender_version_min = "6.0.0"`
5. Fix any API breakages on main

## Packaging Separate Versions

Each Blender version gets its own zip:

```bash
# Package for Blender 5.x
git checkout blender-5x
cd my_addon
zip -r ../my_addon_blender5x_v1.2.0.zip . -x "*.git*" "__pycache__/*"

# Package for Blender 6.x
git checkout main
cd my_addon
zip -r ../my_addon_blender6x_v2.0.0.zip . -x "*.git*" "__pycache__/*"
```

Or use Blender's built-in extension build:
```bash
"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" --command extension build
```

## Checking Blender Version at Runtime

```python
import bpy

# Check version tuple
if bpy.app.version >= (5, 0, 0):
    # Blender 5.0+ code path
    pass
elif bpy.app.version >= (4, 2, 0):
    # Blender 4.2-4.x code path
    pass
```

Use this sparingly — prefer separate branches over version checks in code.

## Common Breaking Changes Between Versions

### Blender 4.x → 5.x
- Extension system (`blender_manifest.toml`) became the standard
- Some operators renamed or removed
- Property annotation syntax enforced (was already recommended in 4.x)

### General patterns that break:
- Removed/renamed operators (`bpy.ops.*`)
- Changed RNA property names
- Moved menu types
- Python version upgrades (3.10 → 3.11 → 3.12)
- UI layout API changes

### How to detect breaking changes:
1. Read Blender release notes (wiki.blender.org)
2. Check Python API changelog (docs.blender.org/api/current/change_log.html)
3. Test addon in new Blender version
4. Watch for `DeprecationWarning` in console output

## Addon Version Numbering

Recommended versioning scheme:
```
MAJOR.MINOR.PATCH

MAJOR: Breaking changes to addon functionality
MINOR: New features, backward compatible
PATCH: Bug fixes
```

In `blender_manifest.toml`:
```toml
version = "1.2.3"
```

In legacy `bl_info`:
```python
"version": (1, 2, 3),
```

## Distribution

### Blender Extensions Platform
The official distribution channel: https://extensions.blender.org/
- Submit your `.zip` package
- Set compatibility in the platform UI
- Users install directly from Blender's preferences

### Manual Distribution
- Provide `.zip` file for download
- Users install via Edit > Preferences > Add-ons > Install from Disk
- Or extract to `%APPDATA%\Blender Foundation\Blender\5.0\extensions\`
