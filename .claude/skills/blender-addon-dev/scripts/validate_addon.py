"""
Blender Addon Validator
Checks addon structure and common issues WITHOUT requiring Blender.
Run with: python validate_addon.py <path_to_addon>

Checks:
  1. blender_manifest.toml or bl_info exists
  2. register() and unregister() functions exist
  3. Class naming conventions (bl_idname patterns)
  4. Property annotation syntax (: not =)
  5. Operator return values
"""

import sys
import os
import re
import ast


class AddonValidator:
    def __init__(self, addon_path):
        self.addon_path = os.path.abspath(addon_path)
        self.errors = []
        self.warnings = []
        self.info = []

    def validate(self):
        if os.path.isfile(self.addon_path):
            self._validate_single_file(self.addon_path)
        elif os.path.isdir(self.addon_path):
            self._validate_package(self.addon_path)
        else:
            self.errors.append(f"Path does not exist: {self.addon_path}")
            return False

        return len(self.errors) == 0

    def _validate_package(self, path):
        init_file = os.path.join(path, "__init__.py")
        if not os.path.exists(init_file):
            self.errors.append("Package addon missing __init__.py")
            return

        # Check for manifest
        manifest = os.path.join(path, "blender_manifest.toml")
        if os.path.exists(manifest):
            self.info.append("Found blender_manifest.toml (extension format)")
            self._validate_manifest(manifest)
        else:
            self.warnings.append("No blender_manifest.toml found. Consider using extension format for Blender 4.2+")

        # Validate all .py files
        for root, dirs, files in os.walk(path):
            # Skip __pycache__
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if fname.endswith(".py"):
                    fpath = os.path.join(root, fname)
                    self._validate_single_file(fpath)

        # Check __init__.py specifically for register/unregister
        self._check_register_functions(init_file, is_init=True)

    def _validate_single_file(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
        except (IOError, OSError) as e:
            self.errors.append(f"Cannot read {filepath}: {e}")
            return

        relpath = os.path.relpath(filepath, self.addon_path)
        if relpath == ".":
            relpath = os.path.basename(filepath)

        # Check for property assignment syntax (= instead of :)
        self._check_property_syntax(source, relpath)

        # Check bl_idname patterns
        self._check_bl_idname(source, relpath)

        # Check operator return values
        self._check_operator_returns(source, relpath)

        # Check for register/unregister in __init__.py
        basename = os.path.basename(filepath)
        if basename == "__init__.py" or (os.path.isfile(self.addon_path) and filepath == self.addon_path):
            self._check_register_functions(filepath)
            self._check_bl_info(source, relpath)

    def _validate_manifest(self, manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (IOError, OSError):
            self.errors.append("Cannot read blender_manifest.toml")
            return

        required_fields = ["schema_version", "id", "version", "name", "maintainer", "type", "license"]
        for field in required_fields:
            pattern = rf'^\s*{re.escape(field)}\s*='
            if not re.search(pattern, content, re.MULTILINE):
                self.errors.append(f"blender_manifest.toml missing required field: {field}")

    def _check_property_syntax(self, source, relpath):
        # Look for lines like: prop_name = bpy.props.XxxProperty(
        # This is the WRONG syntax (should use : annotation)
        pattern = r'^\s+(\w+)\s*=\s*bpy\.props\.\w+Property\('
        for i, line in enumerate(source.splitlines(), 1):
            if re.match(pattern, line):
                # Exclude class-level assignments that are valid (like in register())
                stripped = line.strip()
                if not stripped.startswith("bpy.types."):
                    self.errors.append(
                        f"{relpath}:{i}: Property uses assignment (=) instead of annotation (:). "
                        f"Change '=' to ':' for class properties."
                    )

    def _check_bl_idname(self, source, relpath):
        # Check operator bl_idname has exactly one dot
        op_pattern = r'bl_idname\s*=\s*["\']([^"\']+)["\']'
        for i, line in enumerate(source.splitlines(), 1):
            match = re.search(op_pattern, line)
            if match:
                idname = match.group(1)
                # Check for operator-style (module.name)
                if "." in idname:
                    parts = idname.split(".")
                    if len(parts) != 2:
                        self.errors.append(
                            f"{relpath}:{i}: bl_idname '{idname}' has {len(parts) - 1} dots, expected exactly 1"
                        )
                    if parts[0] != parts[0].lower() or parts[1] != parts[1].lower():
                        self.warnings.append(
                            f"{relpath}:{i}: Operator bl_idname '{idname}' should be all lowercase"
                        )
                # Check for panel/menu style (CATEGORY_XX_name)
                elif "_" in idname:
                    panel_pattern = r'^[A-Z]+_(PT|MT|HT|UL|PIE)_\w+$'
                    if not re.match(panel_pattern, idname):
                        self.warnings.append(
                            f"{relpath}:{i}: bl_idname '{idname}' doesn't match CATEGORY_XX_name pattern"
                        )

    def _check_operator_returns(self, source, relpath):
        # Check that operator execute/modal/invoke methods return proper sets
        try:
            tree = ast.parse(source)
        except SyntaxError:
            self.warnings.append(f"{relpath}: Could not parse Python AST (syntax error)")
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in ('execute', 'modal', 'invoke'):
                for child in ast.walk(node):
                    if isinstance(child, ast.Return) and child.value:
                        # Check it's a set like {'FINISHED'}
                        if isinstance(child.value, ast.Set):
                            for elt in child.value.elts:
                                if isinstance(elt, ast.Constant):
                                    valid = {'FINISHED', 'CANCELLED', 'RUNNING_MODAL', 'PASS_THROUGH', 'INTERFACE'}
                                    if elt.value not in valid:
                                        self.warnings.append(
                                            f"{relpath}:{child.lineno}: Unknown return value '{elt.value}' in {node.name}()"
                                        )

    def _check_register_functions(self, filepath, is_init=False):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
        except (IOError, OSError):
            return

        relpath = os.path.relpath(filepath, os.path.dirname(self.addon_path))

        has_register = bool(re.search(r'^def register\(\)', source, re.MULTILINE))
        has_unregister = bool(re.search(r'^def unregister\(\)', source, re.MULTILINE))

        if is_init or os.path.isfile(self.addon_path):
            if not has_register:
                self.errors.append(f"{relpath}: Missing register() function")
            if not has_unregister:
                self.errors.append(f"{relpath}: Missing unregister() function")

    def _check_bl_info(self, source, relpath):
        has_bl_info = "bl_info" in source
        manifest_path = os.path.join(os.path.dirname(os.path.abspath(relpath)), "blender_manifest.toml")
        has_manifest = os.path.exists(os.path.join(self.addon_path, "blender_manifest.toml")) if os.path.isdir(self.addon_path) else False

        if not has_bl_info and not has_manifest:
            self.warnings.append(f"{relpath}: No bl_info dict or blender_manifest.toml found")

    def print_results(self):
        if self.info:
            for msg in self.info:
                print(f"  INFO: {msg}")
        if self.warnings:
            for msg in self.warnings:
                print(f"  WARN: {msg}")
        if self.errors:
            for msg in self.errors:
                print(f"  ERROR: {msg}")

        print()
        if self.errors:
            print(f"FAILED: {len(self.errors)} error(s), {len(self.warnings)} warning(s)")
        else:
            print(f"PASSED: 0 errors, {len(self.warnings)} warning(s)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_addon.py <path_to_addon_file_or_directory>")
        sys.exit(1)

    path = sys.argv[1]
    print(f"Validating addon: {path}\n")

    validator = AddonValidator(path)
    success = validator.validate()
    validator.print_results()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
