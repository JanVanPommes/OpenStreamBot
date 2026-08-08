import os
import shutil
import zipfile
import json
import yaml
from datetime import datetime

CONFIG_FILE = "config.yaml"
ACTIONS_FILE = "actions.yaml"
PROFILES_DIR = "profiles"

PATH_KEYS = {
    "file", "path", "folder", "sound", "sound_path",
    "script_path", "image_path", "client_secret_file", "token_file"
}


def _find_path_entries(obj, path_keys=PATH_KEYS):
    """
    Recursively scans dicts/lists and yields tuples of (container_dict, key, path_value)
    for any keys matching path_keys where path_value is a non-empty string.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in path_keys and isinstance(v, str) and v.strip():
                yield (obj, k, v.strip())
            elif isinstance(v, (dict, list)):
                yield from _find_path_entries(v, path_keys)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                yield from _find_path_entries(item, path_keys)


class BackupManager:
    """
    Manages Full Backup Export and Import for OpenStreamBot profiles,
    including all referenced media files (audio, scripts, assets) with
    cross-platform path resolution and path rewriting.
    """

    def __init__(self, base_dir="."):
        self.base_dir = os.path.abspath(base_dir)

    def scan_referenced_paths(self, actions_path, config_path):
        """
        Scans actions.yaml and config.yaml to find all referenced local files,
        directories, and assets.
        Returns a tuple of (referenced_files_set, referenced_folders_set, path_items_list).
        """
        files_to_pack = set()
        folders_to_pack = set()
        path_items = []  # list of (raw_path, abs_path, is_dir)

        def register_path(raw_path):
            if not raw_path or not isinstance(raw_path, str):
                return
            p_abs = os.path.abspath(raw_path)
            if os.path.isfile(p_abs):
                files_to_pack.add(p_abs)
                path_items.append((raw_path, p_abs, False))
            elif os.path.isdir(p_abs):
                folders_to_pack.add(p_abs)
                path_items.append((raw_path, p_abs, True))
                for root, _, filenames in os.walk(p_abs):
                    for fname in filenames:
                        files_to_pack.add(os.path.abspath(os.path.join(root, fname)))

        # 1. Scan actions.yaml
        if os.path.exists(actions_path):
            try:
                with open(actions_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                for _, _, val in _find_path_entries(data):
                    register_path(val)
            except Exception as e:
                print(f"[BackupManager] Error scanning actions file: {e}")

        # 2. Scan config.yaml
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg_data = yaml.safe_load(f) or {}
                for _, _, val in _find_path_entries(cfg_data):
                    register_path(val)
            except Exception as e:
                print(f"[BackupManager] Error scanning config file: {e}")

        # 3. Check assets/ directory if exists
        assets_dir = os.path.join(self.base_dir, "assets")
        if os.path.isdir(assets_dir):
            for root, _, filenames in os.walk(assets_dir):
                for fname in filenames:
                    files_to_pack.add(os.path.abspath(os.path.join(root, fname)))

        return files_to_pack, folders_to_pack, path_items

    def export_backup(self, profile_name="Default", export_filepath=None):
        """Exports a complete profile with all configuration and media files to a .osbbackup ZIP archive."""
        if not export_filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_filepath = os.path.join(self.base_dir, f"backup_{profile_name}_{timestamp}.osbbackup")

        # Determine config file locations
        profile_dir = os.path.join(self.base_dir, PROFILES_DIR, profile_name)
        if os.path.isdir(profile_dir):
            cfg_path = os.path.join(profile_dir, CONFIG_FILE)
            act_path = os.path.join(profile_dir, ACTIONS_FILE)
        else:
            cfg_path = os.path.join(self.base_dir, CONFIG_FILE)
            act_path = os.path.join(self.base_dir, ACTIONS_FILE)

        files_to_pack, folders_to_pack, path_items = self.scan_referenced_paths(act_path, cfg_path)

        path_mappings = {}  # orig_path_str -> relative_zip_path (forward slashes)
        used_zip_paths = set()

        # Build mapping for folder paths first
        for folder_abs in folders_to_pack:
            folder_base = os.path.basename(folder_abs.rstrip("/\\")) or "folder"
            zip_dir = f"assets/media/{folder_base}"
            counter = 1
            while zip_dir in used_zip_paths:
                zip_dir = f"assets/media/{folder_base}_{counter}"
                counter += 1
            used_zip_paths.add(zip_dir)
            path_mappings[folder_abs] = zip_dir.replace("\\", "/")

        manifest = {
            "version": "0.6.2",
            "created_at": datetime.now().isoformat(),
            "profile_name": profile_name,
            "path_mappings": {},
            "assets": []
        }

        with zipfile.ZipFile(export_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Add root config files
            if os.path.isfile(cfg_path):
                zipf.write(cfg_path, CONFIG_FILE)
            if os.path.isfile(act_path):
                zipf.write(act_path, ACTIONS_FILE)

            # Add optional state files
            for opt_file in ["available_rewards.json", ".group_state.json"]:
                full_opt = os.path.join(self.base_dir, opt_file)
                if os.path.isfile(full_opt):
                    zipf.write(full_opt, opt_file)

            # Add asset files
            for file_abs in files_to_pack:
                if not os.path.isfile(file_abs):
                    continue

                # Determine relative ZIP target path
                zip_target = None

                # Check if file is inside base_dir
                try:
                    rel_to_base = os.path.relpath(file_abs, self.base_dir)
                    if not rel_to_base.startswith("..") and not os.path.isabs(rel_to_base):
                        if rel_to_base.startswith("assets"):
                            zip_target = rel_to_base
                        else:
                            zip_target = os.path.join("assets", rel_to_base)
                except ValueError:
                    pass

                # Check if file is inside one of the scanned folder_abs
                if not zip_target:
                    for folder_abs in folders_to_pack:
                        if file_abs.startswith(folder_abs):
                            rel_inside = os.path.relpath(file_abs, folder_abs)
                            zip_target = os.path.join(path_mappings[folder_abs], rel_inside)
                            break

                # Fallback for standalone external files
                if not zip_target:
                    fname = os.path.basename(file_abs)
                    zip_target = os.path.join("assets", "media", fname)

                # Ensure unique zip_target path
                zip_target_norm = zip_target.replace("\\", "/")
                counter = 1
                base_target = zip_target_norm
                while zip_target_norm in used_zip_paths:
                    parts = base_target.rsplit(".", 1)
                    if len(parts) == 2:
                        zip_target_norm = f"{parts[0]}_{counter}.{parts[1]}"
                    else:
                        zip_target_norm = f"{base_target}_{counter}"
                    counter += 1

                used_zip_paths.add(zip_target_norm)
                zipf.write(file_abs, zip_target_norm)

                path_mappings[file_abs] = zip_target_norm
                manifest["assets"].append({
                    "original_path": file_abs,
                    "zip_path": zip_target_norm
                })

            # Save mapping into manifest
            # Record raw un-normalized original paths from actions/config for direct lookup
            for raw_orig, abs_orig, _ in path_items:
                if abs_orig in path_mappings:
                    manifest["path_mappings"][raw_orig] = path_mappings[abs_orig]
                    manifest["path_mappings"][abs_orig] = path_mappings[abs_orig]
                    manifest["path_mappings"][abs_orig.replace("\\", "/")] = path_mappings[abs_orig]

            # Add manifest
            zipf.writestr("manifest.json", json.dumps(manifest, indent=2))

        print(f"[BackupManager] Successfully exported backup to: {export_filepath}")
        return export_filepath

    def _resolve_imported_path(self, orig_val, path_mappings):
        """
        Attempts to map an original path to its extracted location in self.base_dir.
        """
        if not orig_val or not isinstance(orig_val, str):
            return None

        val_clean = orig_val.strip()
        val_norm = os.path.normpath(val_clean)
        val_slash = val_clean.replace("\\", "/")

        # 1. Exact match in path_mappings
        rel_zip = (
            path_mappings.get(val_clean) or
            path_mappings.get(val_norm) or
            path_mappings.get(val_slash)
        )

        if not rel_zip:
            # Case-insensitive / normalized lookup
            for k, v in path_mappings.items():
                if k.lower() in [val_clean.lower(), val_norm.lower(), val_slash.lower()]:
                    rel_zip = v
                    break

        if rel_zip:
            local_target = os.path.abspath(os.path.join(self.base_dir, rel_zip))
            return local_target

        # 2. Heuristic fallback: check if assets/media/<basename> or assets/<basename> exists
        basename = os.path.basename(val_clean.rstrip("/\\"))
        if basename:
            candidates = [
                os.path.abspath(os.path.join(self.base_dir, "assets", "media", basename)),
                os.path.abspath(os.path.join(self.base_dir, "assets", basename)),
            ]
            for candidate in candidates:
                if os.path.exists(candidate):
                    return candidate

        return None

    def import_backup(self, backup_filepath, target_profile_name=None):
        """Imports a .osbbackup archive, extracts assets, and rewrites config/action paths for local host OS."""
        if not os.path.isfile(backup_filepath):
            raise FileNotFoundError(f"Backup file not found: {backup_filepath}")

        with zipfile.ZipFile(backup_filepath, "r") as zipf:
            namelist = zipf.namelist()
            manifest = {}
            if "manifest.json" in namelist:
                try:
                    manifest = json.loads(zipf.read("manifest.json").decode("utf-8"))
                except Exception as e:
                    print(f"[BackupManager] Warning reading manifest.json: {e}")

            import_profile_name = target_profile_name or manifest.get("profile_name", "Imported_Profile")
            target_dir = os.path.join(self.base_dir, PROFILES_DIR, import_profile_name)
            os.makedirs(target_dir, exist_ok=True)

            path_mappings = manifest.get("path_mappings", {})

            # If path_mappings is missing or empty, attempt to build from manifest assets list
            if not path_mappings and "assets" in manifest:
                for a in manifest["assets"]:
                    orig = a.get("original_path")
                    zp = a.get("zip_path")
                    if orig and zp:
                        path_mappings[orig] = zp
                        path_mappings[orig.replace("\\", "/")] = zp

            # Extract assets & configuration
            for member in namelist:
                if member in [CONFIG_FILE, ACTIONS_FILE, "available_rewards.json", ".group_state.json"]:
                    zipf.extract(member, target_dir)
                elif member.startswith("assets/"):
                    # Safe extraction into base_dir
                    zipf.extract(member, self.base_dir)

            # Rewrite paths in actions.yaml
            target_act_path = os.path.join(target_dir, ACTIONS_FILE)
            if os.path.isfile(target_act_path):
                try:
                    with open(target_act_path, "r", encoding="utf-8") as f:
                        act_data = yaml.safe_load(f) or {}

                    for container, key, val in _find_path_entries(act_data):
                        new_p = self._resolve_imported_path(val, path_mappings)
                        if new_p:
                            container[key] = new_p

                    with open(target_act_path, "w", encoding="utf-8") as f:
                        yaml.dump(act_data, f, default_flow_style=False, sort_keys=False)
                    print(f"[BackupManager] Rewrote asset paths in {target_act_path}")
                except Exception as e:
                    print(f"[BackupManager] Error rewriting actions.yaml: {e}")

            # Rewrite paths in config.yaml
            target_cfg_path = os.path.join(target_dir, CONFIG_FILE)
            if os.path.isfile(target_cfg_path):
                try:
                    with open(target_cfg_path, "r", encoding="utf-8") as f:
                        cfg_data = yaml.safe_load(f) or {}

                    for container, key, val in _find_path_entries(cfg_data):
                        new_p = self._resolve_imported_path(val, path_mappings)
                        if new_p:
                            container[key] = new_p

                    with open(target_cfg_path, "w", encoding="utf-8") as f:
                        yaml.dump(cfg_data, f, default_flow_style=False, sort_keys=False)
                    print(f"[BackupManager] Rewrote asset paths in {target_cfg_path}")
                except Exception as e:
                    print(f"[BackupManager] Error rewriting config.yaml: {e}")

            print(f"[BackupManager] Successfully imported backup as profile '{import_profile_name}'")
            return import_profile_name

