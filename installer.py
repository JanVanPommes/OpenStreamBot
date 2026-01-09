import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import sys
import os
import shutil
import threading
import subprocess

# PyInstaller creates a temp folder at sys._MEIPASS
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OpenStreamBot Installer")
        self.geometry("500x400")
        self.resizable(False, False)
        
        # Default Install Path
        self.install_path = tk.StringVar(value=os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser("~")), "OpenStreamBot"))
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        frame_top = tk.Frame(self, bg="#3B82F6", height=80)
        frame_top.pack(fill="x")
        
        lbl_title = tk.Label(frame_top, text="Install OpenStreamBot", bg="#3B82F6", fg="white", font=("Segoe UI", 16, "bold"))
        lbl_title.place(x=20, y=25)
        
        # Content
        frame_body = tk.Frame(self, padx=20, pady=20)
        frame_body.pack(fill="both", expand=True)
        
        tk.Label(frame_body, text="Select Installation Folder:", font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 5))
        
        frame_path = tk.Frame(frame_body)
        frame_path.pack(fill="x")
        
        entry_path = tk.Entry(frame_path, textvariable=self.install_path)
        entry_path.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        btn_browse = tk.Button(frame_path, text="Browse...", command=self.browse_folder)
        btn_browse.pack(side="right")
        
        # Shortcuts
        self.var_desktop = tk.BooleanVar(value=True)
        cb_desktop = tk.Checkbutton(frame_body, text="Create Desktop Shortcut", variable=self.var_desktop)
        cb_desktop.pack(anchor="w", pady=(20, 5))
        
        # Progress
        self.progress = ttk.Progressbar(frame_body, mode="determinate")
        self.progress.pack(fill="x", pady=(40, 5))
        
        self.lbl_status = tk.Label(frame_body, text="Ready", fg="gray")
        self.lbl_status.pack(anchor="w")
        
        # Buttons
        frame_bottom = tk.Frame(self, height=60)
        frame_bottom.pack(fill="x", side="bottom")
        
        self.btn_install = tk.Button(frame_bottom, text="Install", bg="green", fg="white", width=15, command=self.start_install)
        self.btn_install.pack(side="right", padx=20, pady=15)
        
        btn_cancel = tk.Button(frame_bottom, text="Cancel", width=10, command=self.destroy)
        btn_cancel.pack(side="right", pady=15)

    def browse_folder(self):
        d = filedialog.askdirectory(initialdir=self.install_path.get())
        if d:
            self.install_path.set(d)

    def start_install(self):
        self.btn_install.config(state="disabled")
        threading.Thread(target=self.run_installation, daemon=True).start()

    def run_installation(self):
        target_dir = self.install_path.get()
        source_data = resource_path("DATA") # "DATA" folder packed by build script
        
        if not os.path.exists(source_data):
            # Fallback for dev testing
            source_data = os.path.join("dist", "OpenStreamBot_Dist")
            if not os.path.exists(source_data):
                self.update_status("Error: Source files not found!", error=True)
                return

        try:
            self.update_status("Preparing target directory...")
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            
            # Copy Files
            self.update_status("Copying files...")
            self.progress["value"] = 20
            
            # Simple recursive copy
            for root, dirs, files in os.walk(source_data):
                rel_path = os.path.relpath(root, source_data)
                target_root = os.path.join(target_dir, rel_path)
                
                if not os.path.exists(target_root):
                    os.makedirs(target_root)
                
                for f in files:
                    s_file = os.path.join(root, f)
                    d_file = os.path.join(target_root, f)
                    
                    # Don't overwrite config if it exists?
                    if f == "config.yaml" and os.path.exists(d_file):
                        continue
                        
                    shutil.copy2(s_file, d_file)
            
            self.progress["value"] = 80
            
            # Shortcuts
            if self.var_desktop.get():
                self.update_status("Creating shortcut...")
                self.create_shortcut(target_dir)
            
            self.progress["value"] = 100
            self.update_status("Installation Complete!", success=True)
            messagebox.showinfo("Success", "OpenStreamBot installed successfully!")
            self.destroy()
            
        except Exception as e:
            self.update_status(f"Error: {e}", error=True)
            print(e)
            self.btn_install.config(state="normal")

    def create_shortcut(self, target_dir):
        # Create VBScript to make shortcut (Standard Windows trick, no deps)
        exe_path = os.path.join(target_dir, "OpenStreamBot.exe")
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        link_path = os.path.join(desktop, "OpenStreamBot.lnk")
        
        vbs_script = f"""
            Set oWS = WScript.CreateObject("WScript.Shell")
            sLinkFile = "{link_path}"
            Set oLink = oWS.CreateShortcut(sLinkFile)
            oLink.TargetPath = "{exe_path}"
            oLink.WorkingDirectory = "{target_dir}"
            oLink.Description = "OpenStreamBot Launcher"
            oLink.IconLocation = "{exe_path},0"
            oLink.Save
        """
        
        vbs_file = os.path.join(target_dir, "create_shortcut.vbs")
        with open(vbs_file, "w") as f:
            f.write(vbs_script)
        
        subprocess.call(["cscript", "//NoLogo", vbs_file], shell=True)
        os.remove(vbs_file)

    def update_status(self, text, error=False, success=False):
        color = "red" if error else ("green" if success else "black")
        self.lbl_status.config(text=text, fg=color)
        self.update_idletasks()

if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
