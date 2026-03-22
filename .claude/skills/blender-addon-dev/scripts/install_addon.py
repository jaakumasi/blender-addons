"""
Blender Addon Development Installer
Creates a symlink from your development directory to Blender's addon directory
so changes are picked up immediately without copying files.

Usage:
    python install_addon.py <addon_source_path> [--blender-version 5.0]

Requirements:
    - Must run as Administrator on Windows (for symlink creation)
    - Or enable Developer Mode in Windows Settings > For Developers

Examples:
    python install_addon.py ./my_addon
    python install_addon.py ./my_addon --blender-version 4.5
    python install_addon.py ./my_addon --remove
"""

import sys
import os
import argparse
import subprocess


def get_blender_addons_path(version="5.0"):
    """Get the Blender user addons directory path."""
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        print("ERROR: APPDATA environment variable not set")
        sys.exit(1)

    path = os.path.join(appdata, "Blender Foundation", "Blender", version, "scripts", "addons")
    return path


def ensure_directory(path):
    """Create directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")


def create_symlink(source, target):
    """Create a directory symlink (junction on Windows)."""
    if os.path.exists(target):
        if os.path.islink(target) or os.path.isdir(target):
            print(f"Target already exists: {target}")
            print("Use --remove first to unlink, then re-run.")
            sys.exit(1)

    # On Windows, use mklink /J (junction) which doesn't require admin
    # Junctions work for directories and don't need elevated privileges
    if sys.platform == "win32":
        # Use junction (/J) instead of symlink (/D) — no admin needed
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", target, source],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"ERROR: Failed to create junction")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
            print("\nTry running as Administrator, or use:")
            print(f'  mklink /J "{target}" "{source}"')
            sys.exit(1)
    else:
        os.symlink(source, target)

    print(f"Linked: {target} -> {source}")


def remove_symlink(target):
    """Remove a symlink/junction."""
    if not os.path.exists(target):
        print(f"Not found: {target}")
        return

    if sys.platform == "win32":
        # For junctions, use rmdir (not del)
        result = subprocess.run(
            ["cmd", "/c", "rmdir", target],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"ERROR: Failed to remove junction: {result.stderr}")
            sys.exit(1)
    else:
        os.unlink(target)

    print(f"Removed: {target}")


def main():
    parser = argparse.ArgumentParser(description="Install Blender addon for development via symlink")
    parser.add_argument("addon_path", help="Path to addon source directory")
    parser.add_argument("--blender-version", default="5.0", help="Blender version (default: 5.0)")
    parser.add_argument("--remove", action="store_true", help="Remove existing symlink instead of creating one")
    args = parser.parse_args()

    source = os.path.abspath(args.addon_path)
    if not os.path.isdir(source):
        print(f"ERROR: Source is not a directory: {source}")
        sys.exit(1)

    addon_name = os.path.basename(source)
    addons_dir = get_blender_addons_path(args.blender_version)
    target = os.path.join(addons_dir, addon_name)

    if args.remove:
        remove_symlink(target)
        print(f"\nAddon '{addon_name}' unlinked from Blender {args.blender_version}")
    else:
        ensure_directory(addons_dir)
        create_symlink(source, target)
        print(f"\nAddon '{addon_name}' installed for Blender {args.blender_version}")
        print(f"Enable it in: Edit > Preferences > Add-ons > search '{addon_name}'")
        print("Changes to source files will be reflected immediately (reload scripts with F3 > 'Reload Scripts')")


if __name__ == "__main__":
    main()
