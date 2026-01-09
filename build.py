import os
import subprocess
import shutil
import sys

# Requirements: pip install pyinstaller

def run_command(cmd):
    print(f"[Build] Running: {cmd}")
    subprocess.check_call(cmd, shell=True)

def cleanup():
    print("[Build] Cleaning up old build artifacts...")
    dirs = ["build", "dist"]
    for d in dirs:
        if os.path.exists(d):
            shutil.rmtree(d)
    
    # Clean spec files
    for f in os.listdir("."):
        if f.endswith(".spec"):
            os.remove(f)

def build_bot_internal():
    print("\n[Build] Building Bot Internal (main.py)...")
    # We build main.py as a directory ("onedir") so we can easily debug issues 
    # and potential future plugin structures.
    
    cmd_parts = [
        'pyinstaller', '--noconfirm', '--onedir', '--clean', '--name "bot_internal"',
        '--add-data "core:core"',
        '--add-data "platforms:platforms"',
        '--add-data "interface:interface"',
        '--exclude-module "tkinter"',  # main.py usually no GUI
        'main.py'
    ]
    run_command(" ".join(cmd_parts))

def build_launcher():
    print("\n[Build] Building Launcher (launcher.py)...")
    
    cmd_parts = [
        'pyinstaller', '--noconfirm', '--onefile', '--clean', '--windowed', '--name "OpenStreamBot"',
        '--add-data "assets:assets"',
        '--add-data "interface:interface"',
        '--add-data "core:core"' # Launcher imports core.profile_manager etc.
    ]
    
    if os.path.exists("assets/logo.ico"):
        cmd_parts.append('--icon "assets/logo.ico"')
        
    cmd_parts.append('launcher.py')
    
    run_command(" ".join(cmd_parts))

def build_installer():
    print("\n[Build] Building Installer (installer.py)...")
    
    cmd_parts = [
        'pyinstaller', '--noconfirm', '--onefile', '--clean', '--windowed', '--name "OpenStreamBot_Installer"'
    ]
    
    if os.path.exists("assets/logo.ico"):
        cmd_parts.append('--icon "assets/logo.ico"')
        
    cmd_parts.append('installer.py')
    
    run_command(" ".join(cmd_parts))

def prepare_dist_folder():
    print("\n[Build] Assembling Distribution Folder...")
    dist_dir = "dist/OpenStreamBot_Dist"
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)

    # 1. Copy Launcher EXE
    if os.path.exists("dist/OpenStreamBot.exe"):
        shutil.copy("dist/OpenStreamBot.exe", dist_dir)
    elif os.path.exists("dist/OpenStreamBot"): # Linux fallback
        shutil.copy("dist/OpenStreamBot", dist_dir)

    # 2. Copy Bot Internal Logic
    # PyInstaller onedir put it in dist/bot_internal
    if os.path.exists("dist/bot_internal"):
        shutil.copytree("dist/bot_internal", os.path.join(dist_dir, "bot_internal"))

    # 3. Copy External Resources (Config templates, etc)
    files_to_copy = ["config.example.yaml", "actions.yaml"]
    for f in files_to_copy:
        if os.path.exists(f):
            shutil.copy(f, dist_dir)
    
    # 4. Copy Assets (Needed by bot_internal sometimes even if packed, or for user customization)
    if os.path.exists("assets"):
         shutil.copytree("assets", os.path.join(dist_dir, "assets"))

    print(f"[Build] Distribution assembled at {dist_dir}")
    return dist_dir

def main():
    cleanup()
    
    # 1. Build Components
    build_bot_internal()
    build_launcher()
    
    # 2. Layout Files for Installer
    dist_path = prepare_dist_folder()
    
    # 3. Build The Installer application itself
    # The installer needs to EMBED the dist_path files. 
    # PyInstaller --add-data "dist/OpenStreamBot_Dist:DATA"
    print("\n[Build] Building Final Installer EXE...")
    
    # We pass the assembled folder as data to the installer
    sep = ";" if os.name == 'nt' else ":"
    
    cmd_parts = [
        'pyinstaller', '--noconfirm', '--onefile', '--clean', '--windowed', '--name "OpenStreamBot_Setup"',
        f'--add-data "dist/OpenStreamBot_Dist{sep}DATA"'
    ]
    
    if os.path.exists("assets/logo.ico"):
        cmd_parts.append('--icon "assets/logo.ico"')
        
    cmd_parts.append('installer.py')

    run_command(" ".join(cmd_parts))
    
    print("\n[Build] SUCCESS! Setup file is in dist/OpenStreamBot_Setup.exe")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    main()
