import os
import shutil
import zipfile
import json
import yaml
from datetime import datetime

CONFIG_FILE = "config.yaml"
ACTIONS_FILE = "actions.yaml"
PROFILES_DIR = "profiles"

class BackupManager:
    """
    Manages Full Backup Export and Import for OpenStreamBot profiles,
    including all referenced media files (audio, scripts, assets).
    """

    def __init__(self, base_dir="."):
        self.base_dir = os.path.abspath(base_dir)

    def scan_referenced_files(self, actions_path, config_path):
        """Scans actions.yaml and config.yaml to find all referenced local files and directories."""
        files_to_pack = set()
        
        # 1. Scan actions.yaml
        if os.path.exists(actions_path):
            try:
                with open(actions_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                actions = data.get("actions", [])
                for action in actions:
                    for sub in action.get("sub_actions", []):
                        # Check file fields
                        for key in ["file", "path"]:
                            if key in sub and sub[key]:
                                filepath = sub[key]
                                if os.path.isfile(filepath):
                                    files_to_pack.add(os.path.abspath(filepath))

                        # Check folder fields (e.g. playlist)
                        if "folder" in sub and sub["folder"]:
                            folderpath = sub["folder"]
                            if os.path.isdir(folderpath):
                                for root, _, filenames in os.walk(folderpath):
                                    for fname in filenames:
                                        files_to_pack.add(os.path.abspath(os.path.join(root, fname)))
            except Exception as e:
                print(f"[BackupManager] Error scanning actions file: {e}")

        # 2. Check assets/ directory if exists
        assets_dir = os.path.join(self.base_dir, "assets")
        if os.path.isdir(assets_dir):
            for root, _, filenames in os.walk(assets_dir):
                for fname in filenames:
                    files_to_pack.add(os.path.abspath(os.path.join(root, fname)))

        return list(files_to_pack)

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

        referenced_files = self.scan_referenced_files(act_path, cfg_path)

        manifest = {
            "version": "0.6.0",
            "created_at": datetime.now().isoformat(),
            "profile_name": profile_name,
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
            for file_abs in referenced_files:
                if os.path.isfile(file_abs):
                    try:
                        rel_path = os.path.relpath(file_abs, self.base_dir)
                    except ValueError:
                        rel_path = os.path.basename(file_abs)
                    
                    zip_target = os.path.join("assets", rel_path)
                    zipf.write(file_abs, zip_target)
                    manifest["assets"].append({
                        "original_path": file_abs,
                        "zip_path": zip_target
                    })

            # Add manifest
            zipf.writestr("manifest.json", json.dumps(manifest, indent=2))

        print(f"[BackupManager] Successfully exported backup to: {export_filepath}")
        return export_filepath

    def import_backup(self, backup_filepath, target_profile_name=None):
        """Imports a .osbbackup archive and restores configuration and media assets."""
        if not os.path.isfile(backup_filepath):
            raise FileNotFoundError(f"Backup file not found: {backup_filepath}")

        with zipfile.ZipFile(backup_filepath, "r") as zipf:
            namelist = zipf.namelist()
            if "manifest.json" in namelist:
                manifest = json.loads(zipf.read("manifest.json").decode("utf-8"))
                import_profile_name = target_profile_name or manifest.get("profile_name", "Imported_Profile")
            else:
                manifest = {}
                import_profile_name = target_profile_name or "Imported_Profile"

            target_dir = os.path.join(self.base_dir, PROFILES_DIR, import_profile_name)
            os.makedirs(target_dir, exist_ok=True)

            # Extract config & actions into target profile directory
            for member in namelist:
                if member in [CONFIG_FILE, ACTIONS_FILE, "available_rewards.json", ".group_state.json"]:
                    zipf.extract(member, target_dir)
                elif member.startswith("assets/"):
                    # Extract assets to root base_dir
                    zipf.extract(member, self.base_dir)

            print(f"[BackupManager] Successfully imported backup as profile '{import_profile_name}'")
            return import_profile_name
