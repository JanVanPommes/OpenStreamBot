import os
import shutil
import yaml

PROFILE_DIR = "profiles"
CONFIG_FILE = "config.yaml"
ACTIONS_FILE = "actions.yaml"

class ProfileManager:
    def __init__(self, profile_dir=PROFILE_DIR):
        self.profile_dir = profile_dir
        if not os.path.exists(self.profile_dir):
            os.makedirs(self.profile_dir)

    def get_profiles(self):
        """Returns a list of available profile names."""
        if not os.path.exists(self.profile_dir):
            return []
        
        profiles = []
        for entry in os.scandir(self.profile_dir):
            if entry.is_dir():
                profiles.append(entry.name)
        return sorted(profiles)

    def save_profile(self, profile_name):
        """Saves the current root config files to the specified profile folder."""
        target_dir = os.path.join(self.profile_dir, profile_name)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        # Save Config
        if os.path.exists(CONFIG_FILE):
            shutil.copy2(CONFIG_FILE, os.path.join(target_dir, CONFIG_FILE))
            
        # Save Actions
        if os.path.exists(ACTIONS_FILE):
            shutil.copy2(ACTIONS_FILE, os.path.join(target_dir, ACTIONS_FILE))
            
        print(f"[ProfileManager] Profile '{profile_name}' saved.")

    def load_profile(self, profile_name):
        """Loads a profile by copying its files to the root directory."""
        source_dir = os.path.join(self.profile_dir, profile_name)
        if not os.path.exists(source_dir):
            raise FileNotFoundError(f"Profile '{profile_name}' not found.")
            
        # Load Config
        src_config = os.path.join(source_dir, CONFIG_FILE)
        if os.path.exists(src_config):
            shutil.copy2(src_config, CONFIG_FILE)
            
        # Load Actions
        src_actions = os.path.join(source_dir, ACTIONS_FILE)
        if os.path.exists(src_actions):
            shutil.copy2(src_actions, ACTIONS_FILE)
            
        print(f"[ProfileManager] Profile '{profile_name}' loaded.")
        
    def create_default_profile(self):
        """Creates a 'Default' profile if no profiles exist."""
        if not self.get_profiles():
            self.save_profile("Default")
