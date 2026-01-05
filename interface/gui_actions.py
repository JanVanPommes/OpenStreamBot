import customtkinter as ctk
from tkinter import messagebox, simpledialog, filedialog
import yaml
import os
import pygame._sdl2.audio as sdl_audio
import pygame

class ActionEditorFrame(ctk.CTkFrame):
    def __init__(self, master, config_file="actions.yaml"):
        super().__init__(master)
        self.config_file = config_file
        self.actions = []
        self.current_action = None
        
        self.load_actions()
        
        # --- LAYOUT ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # LEFT SIDE: Action List
        self.left_panel = ctk.CTkFrame(self, width=200)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.left_panel.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.left_panel, text="Actions", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=5)
        
        self.action_listbox = ctk.CTkScrollableFrame(self.left_panel)
        self.action_listbox.grid(row=1, column=0, sticky="nsew", padx=5)
        
        self.btn_add_action = ctk.CTkButton(self.left_panel, text="+ New Action", command=self.add_action)
        self.btn_add_action.grid(row=2, column=0, pady=10, padx=10)
        
        self.btn_delete_action = ctk.CTkButton(self.left_panel, text="Delete Action", fg_color="red", command=self.delete_current_action)
        self.btn_delete_action.grid(row=3, column=0, pady=(0, 10), padx=10)

        # RIGHT SIDE: Editor
        self.editor_panel = ctk.CTkFrame(self)
        self.editor_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.editor_panel.grid_columnconfigure(0, weight=1)
        self.editor_panel.grid_columnconfigure(1, weight=1)
        self.editor_panel.grid_rowconfigure(2, weight=1) # Subactions take space

        # Editor Header (Name + Group)
        self.header_frame = ctk.CTkFrame(self.editor_panel, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        
        self.var_action_name = ctk.StringVar()
        self.entry_name = ctk.CTkEntry(self.header_frame, textvariable=self.var_action_name, font=ctk.CTkFont(size=16, weight="bold"), placeholder_text="Action Name")
        self.entry_name.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.var_action_group = ctk.StringVar()
        self.entry_group = ctk.CTkEntry(self.header_frame, textvariable=self.var_action_group, width=100, placeholder_text="Group")
        self.entry_group.pack(side="right")
        
        # Triggers Section
        self.frame_triggers = ctk.CTkFrame(self.editor_panel)
        self.frame_triggers.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ctk.CTkLabel(self.frame_triggers, text="Triggers").pack(side="top", anchor="w", padx=5)
        
        self.btn_add_trigger = ctk.CTkButton(self.frame_triggers, text="+ Add Trigger", height=24, command=self.add_trigger_dialog)
        self.btn_add_trigger.pack(side="bottom", pady=5)

        self.scroll_triggers = ctk.CTkScrollableFrame(self.frame_triggers, height=100)
        self.scroll_triggers.pack(fill="both", expand=True, padx=5, pady=5)

        # Sub-Actions Section
        self.frame_subs = ctk.CTkFrame(self.editor_panel)
        self.frame_subs.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        ctk.CTkLabel(self.frame_subs, text="Sub-Actions").pack(side="top", anchor="w", padx=5)
        
        self.btn_add_sub = ctk.CTkButton(self.frame_subs, text="+ Add Sub-Action", command=self.add_sub_dialog)
        self.btn_add_sub.pack(side="bottom", pady=5)

        self.scroll_subs = ctk.CTkScrollableFrame(self.frame_subs)
        self.scroll_subs.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Save Button Main
        self.btn_save = ctk.CTkButton(self, text="Save Actions", fg_color="green", command=self.save_actions)
        self.btn_save.grid(row=1, column=0, columnspan=2, pady=10)

        self.refresh_action_list()

    def load_actions(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.actions = yaml.safe_load(f).get('actions', [])
        else:
            self.actions = []

    def save_actions(self):
        # Update current action loaded in UI back to self.actions list
        self.commit_current_changes()
        
        data = {'actions': self.actions}
        with open(self.config_file, 'w') as f:
            yaml.dump(data, f)
        messagebox.showinfo("Saved", "Actions saved! Restart Bot to apply.")

    def refresh_action_list(self):
        for widget in self.action_listbox.winfo_children():
            widget.destroy()
            
        # Group actions
        grouped = {}
        for action in self.actions:
            g = action.get('group', 'General') or 'General'
            if g not in grouped: grouped[g] = []
            grouped[g].append(action)
            
        # Display Groups
        for group_name in sorted(grouped.keys()):
            # Header
            header = ctk.CTkLabel(self.action_listbox, text=f"-- {group_name} --", text_color="gray70", font=ctk.CTkFont(size=12, weight="bold"))
            header.pack(fill="x", pady=(10, 2))
            
            # Items
            for action in grouped[group_name]:
                # Find original index
                idx = self.actions.index(action)
                
                btn = ctk.CTkButton(self.action_listbox, text=action.get('name', 'Untitled'), 
                                    command=lambda i=idx: self.select_action(i),
                                    fg_color="transparent", border_width=1, text_color=("gray10", "gray90"))
                btn.pack(fill="x", pady=2)

    def select_action(self, index):
        self.commit_current_changes()
        self.current_action = self.actions[index]
        self.var_action_name.set(self.current_action.get('name', ''))
        self.var_action_group.set(self.current_action.get('group', 'General'))
        self.refresh_details()

    def commit_current_changes(self):
        if self.current_action:
            self.current_action['name'] = self.var_action_name.get()
            self.current_action['group'] = self.var_action_group.get()
            # Triggers/Subs are modified directly in the list references usually, 
            # so strict commit might not be needed if references are kept.
            pass

    def add_action(self):
        new_action = {'name': 'New Action', 'group': 'General', 'enabled': True, 'triggers': [], 'sub_actions': []}
        self.actions.append(new_action)
        self.refresh_action_list()
        self.select_action(len(self.actions)-1)

    def delete_current_action(self):
        if not self.current_action: return
        if not messagebox.askyesno("Delete", "Delete this action?"): return
        
        self.actions.remove(self.current_action)
        self.current_action = None
        self.var_action_name.set("")
        self.var_action_group.set("")
        self.refresh_details()
        self.refresh_action_list()

    def refresh_details(self):
        # Clear
        for w in self.scroll_triggers.winfo_children(): w.destroy()
        for w in self.scroll_subs.winfo_children(): w.destroy()
        
        if not self.current_action: return
        
        # Triggers
        triggers = self.current_action.get('triggers', [])
        for i, t in enumerate(triggers):
            f = ctk.CTkFrame(self.scroll_triggers)
            f.pack(fill="x", pady=2)
            text = f"{t['type']}"
            if 'command' in t: text += f": {t['command']}"
            elif 'scene_name' in t: text += f": {t['scene_name']}"
            elif 'min_viewers' in t: text += f" (>{t['min_viewers']})"
            elif 'interval' in t: text += f" ({t['interval']}s)"
            
            lbl = ctk.CTkLabel(f, text=text)
            lbl.pack(side="left", padx=5)
            
            # Controls (Right side)
            # Del btn
            ctk.CTkButton(f, text="X", width=20, fg_color="red", command=lambda x=t: self.remove_trigger(x)).pack(side="right", padx=2)
            # Edit btn
            ctk.CTkButton(f, text="E", width=20, command=lambda x=t: self.edit_trigger(x)).pack(side="right", padx=2)
            
            # Move Down
            if i < len(triggers) - 1:
                ctk.CTkButton(f, text="↓", width=20, command=lambda x=i: self.move_trigger_down(x)).pack(side="right", padx=1)
            else:
                 ctk.CTkLabel(f, text=" ", width=20).pack(side="right", padx=1) # Spacer
                 
            # Move Up
            if i > 0:
                ctk.CTkButton(f, text="↑", width=20, command=lambda x=i: self.move_trigger_up(x)).pack(side="right", padx=1)
            else:
                 ctk.CTkLabel(f, text=" ", width=20).pack(side="right", padx=1) # Spacer


        # Sub Actions
        sub_actions = self.current_action.get('sub_actions', [])
        for i, s in enumerate(sub_actions):
            f = ctk.CTkFrame(self.scroll_subs)
            f.pack(fill="x", pady=2)
            
            summary = s['type']
            if 'message' in s: summary += f": {s['message'][:20]}..."
            elif 'ms' in s: summary += f": {s['ms']}ms"
            elif 'folder' in s: summary += f": {s['folder']}"
            elif 'file' in s: summary += f": {os.path.basename(s['file'])}"
            elif 'action_name' in s: summary += f": -> {s['action_name']}"
            
            lbl = ctk.CTkLabel(f, text=summary)
            lbl.pack(side="left", padx=5)
            
            # Controls
            ctk.CTkButton(f, text="X", width=20, fg_color="red", command=lambda x=s: self.remove_sub(x)).pack(side="right", padx=2)
            ctk.CTkButton(f, text="E", width=20, command=lambda x=s: self.edit_sub_action(x)).pack(side="right", padx=2)

            if i < len(sub_actions) - 1:
                ctk.CTkButton(f, text="↓", width=20, command=lambda x=i: self.move_subaction_down(x)).pack(side="right", padx=1)
            else:
                 ctk.CTkLabel(f, text=" ", width=20).pack(side="right", padx=1)

            if i > 0:
                ctk.CTkButton(f, text="↑", width=20, command=lambda x=i: self.move_subaction_up(x)).pack(side="right", padx=1)
            else:
                 ctk.CTkLabel(f, text=" ", width=20).pack(side="right", padx=1)

    def remove_trigger(self, item):
        self.current_action['triggers'].remove(item)
        self.refresh_details()

    def remove_sub(self, item):
        self.current_action['sub_actions'].remove(item)
        self.refresh_details()

    def add_trigger_dialog(self):
        if not self.current_action: return
        
        dialog = TriggerDialog(self)
        self.wait_window(dialog)
        
        if dialog.result:
             self.current_action['triggers'].append(dialog.result)
             self.refresh_details()

    def add_sub_dialog(self):
        if not self.current_action: return
        # Mockup Selection
        # We need a proper Selector Dialog here
        dialog = SubActionDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            self.current_action['sub_actions'].append(dialog.result)
            self.refresh_details()

    def edit_trigger(self, trigger_data):
        # We need the index to replace it, or modify object in place if it's the same dict ref
        # dicts are mutable, but for safety lets replace content
        dialog = TriggerDialog(self, initial_data=trigger_data)
        self.wait_window(dialog)
        
        if dialog.result:
            trigger_data.clear()
            trigger_data.update(dialog.result)
            self.refresh_details()

    def edit_sub_action(self, sub_data):
        dialog = SubActionDialog(self, initial_data=sub_data)
        self.wait_window(dialog)
        if dialog.result:
            sub_data.clear()
            sub_data.update(dialog.result)
            self.refresh_details()

    def move_trigger_up(self, index):
        if index > 0:
            self.current_action['triggers'].insert(index-1, self.current_action['triggers'].pop(index))
            self.refresh_details()

    def move_trigger_down(self, index):
        if index < len(self.current_action['triggers']) - 1:
            self.current_action['triggers'].insert(index+1, self.current_action['triggers'].pop(index))
            self.refresh_details()

    def move_subaction_up(self, index):
        if index > 0:
            self.current_action['sub_actions'].insert(index-1, self.current_action['sub_actions'].pop(index))
            self.refresh_details()

    def move_subaction_down(self, index):
         if index < len(self.current_action['sub_actions']) - 1:
            self.current_action['sub_actions'].insert(index+1, self.current_action['sub_actions'].pop(index))
            self.refresh_details()

class SubActionDialog(ctk.CTkToplevel):
    def __init__(self, parent, initial_data=None):
        super().__init__(parent)
        self.title("Edit Sub-Action" if initial_data else "Add Sub-Action")
        self.geometry("400x350")
        self.result = None
        self.initial_data = initial_data or {}
        
        # --- TYPE ---
        ctk.CTkLabel(self, text="Action Type:").pack(pady=5)
        # Use initial type or default
        start_type = self.initial_data.get('type', "twitch_chat")
        
        self.type_var = ctk.StringVar(value=start_type)
        
        # Sort and unique
        sub_types = sorted(list(set(["twitch_chat", "delay", "log", "play_sound", "stop_sounds", "playlist", "stop_playlist", "obs_set_scene", "youtube_random_short", "trigger_action", "set_volume"])))
        
        self.combo = ctk.CTkComboBox(self, variable=self.type_var, 
                                     values=sub_types,
                                     command=self.on_type_change)
        self.combo.pack(pady=5)
        
        # --- DYNAMIC FRAME ---
        self.frame_config = ctk.CTkFrame(self)
        self.frame_config.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Holders for widgets
        self.widgets = {}
        
        # OK Button
        ctk.CTkButton(self, text="Save" if initial_data else "Add", command=self.on_ok).pack(pady=10)
        
        self.on_type_change(start_type)

    def on_type_change(self, choice):
        # Clear old widgets
        for w in self.frame_config.winfo_children(): w.destroy()
        self.widgets = {}
        
        # Helper to set value if editing and types match
        def get_val(key, default=""):
            if self.initial_data and self.initial_data.get('type') == choice:
                 return str(self.initial_data.get(key, default))
            return default

        # Helper for Device Dropdown
        def add_device_selector():
            ctk.CTkLabel(self.frame_config, text="Audio Device:").pack(anchor="w")
            
            # Get Devices
            try:
                if not pygame.get_init(): pygame.init()
                devices = ['Default'] + sdl_audio.get_audio_device_names(False)
            except:
                devices = ['Default']
                
            dev_var = ctk.StringVar(value=get_val('device', 'Default'))
            combo = ctk.CTkComboBox(self.frame_config, variable=dev_var, values=devices)
            combo.pack(fill="x", pady=5)
            self.widgets['device'] = dev_var

        if choice == "twitch_chat":
            ctk.CTkLabel(self.frame_config, text="Chat Message:").pack(anchor="w")
            entry = ctk.CTkEntry(self.frame_config)
            entry.insert(0, get_val('message'))
            entry.pack(fill="x", pady=5)
            self.widgets['message'] = entry
            
        elif choice == "log":
            ctk.CTkLabel(self.frame_config, text="Log Message:").pack(anchor="w")
            entry = ctk.CTkEntry(self.frame_config)
            entry.insert(0, get_val('message'))
            entry.pack(fill="x", pady=5)
            self.widgets['message'] = entry
            
        elif choice == "delay":
            ctk.CTkLabel(self.frame_config, text="Term (ms):").pack(anchor="w")
            entry = ctk.CTkEntry(self.frame_config)
            entry.insert(0, get_val('ms', '1000'))
            entry.pack(fill="x", pady=5)
            self.widgets['ms'] = entry

        elif choice == "play_sound":
            ctk.CTkLabel(self.frame_config, text="Sound File:").pack(anchor="w")
            f_frame = ctk.CTkFrame(self.frame_config, fg_color="transparent")
            f_frame.pack(fill="x")
            
            entry = ctk.CTkEntry(f_frame)
            entry.insert(0, get_val('file'))
            entry.pack(side="left", fill="x", expand=True)
            self.widgets['file'] = entry
            
            btn = ctk.CTkButton(f_frame, text="...", width=30, command=lambda: self.browse_file(entry))
            btn.pack(side="right", padx=5)
            
            add_device_selector()
            
            ctk.CTkLabel(self.frame_config, text="Volume (0-100%):").pack(anchor="w", pady=(10,0))
            
            def update_vol_lbl(val):
                lbl_vol.configure(text=f"{int(val)}%")
                
            init_vol = float(get_val('volume', '100'))
            
            slider = ctk.CTkSlider(self.frame_config, from_=0, to=100, number_of_steps=100, command=update_vol_lbl)
            slider.set(init_vol)
            slider.pack(fill="x", pady=5)
            self.widgets['volume_slider'] = slider
            
            lbl_vol = ctk.CTkLabel(self.frame_config, text=f"{int(init_vol)}%")
            lbl_vol.pack(anchor="n")

        elif choice == "playlist":
            ctk.CTkLabel(self.frame_config, text="Music Folder:").pack(anchor="w")
            f_frame = ctk.CTkFrame(self.frame_config, fg_color="transparent")
            f_frame.pack(fill="x")
            
            entry = ctk.CTkEntry(f_frame)
            entry.insert(0, get_val('folder'))
            entry.pack(side="left", fill="x", expand=True)
            self.widgets['folder'] = entry
            
            btn = ctk.CTkButton(f_frame, text="...", width=30, command=lambda: self.browse_folder(entry))
            btn.pack(side="right", padx=5)
            
            add_device_selector()
            
            # Volume Slider for Playlist
            ctk.CTkLabel(self.frame_config, text="Volume (0-100%):").pack(anchor="w", pady=(10,0))
            
            def update_vol_lbl(val):
                lbl_vol.configure(text=f"{int(val)}%")
                
            init_vol = float(get_val('volume', '100'))
            
            slider = ctk.CTkSlider(self.frame_config, from_=0, to=100, number_of_steps=100, command=update_vol_lbl)
            slider.set(init_vol)
            slider.pack(fill="x", pady=5)
            self.widgets['volume_slider'] = slider
            
            lbl_vol = ctk.CTkLabel(self.frame_config, text=f"{int(init_vol)}%")
            lbl_vol.pack(anchor="n")

        elif choice == "obs_set_scene":
            ctk.CTkLabel(self.frame_config, text="Scene Name:").pack(anchor="w")
            entry = ctk.CTkEntry(self.frame_config)
            entry.insert(0, get_val('scene'))
            entry.pack(fill="x", pady=5)
            self.widgets['scene'] = entry
            
        elif choice == "youtube_random_short":
             ctk.CTkLabel(self.frame_config, text="No configuration needed.\nMake sure to 'Sync Shorts' in 'Accounts' tab!").pack(pady=10)

        elif choice == "trigger_action":
            ctk.CTkLabel(self.frame_config, text="Action Name to Trigger:").pack(anchor="w")
            entry = ctk.CTkEntry(self.frame_config)
            entry.insert(0, get_val('action_name'))
            entry.pack(fill="x", pady=5)
            self.widgets['action_name'] = entry

        elif choice == "set_volume":
            # Target
            ctk.CTkLabel(self.frame_config, text="Target:").pack(anchor="w")
            t_var = ctk.StringVar(value=get_val('target', 'sfx'))
            ctk.CTkComboBox(self.frame_config, variable=t_var, values=['sfx', 'playlist']).pack(fill="x", pady=5)
            self.widgets['target'] = t_var
            
            # Mode
            ctk.CTkLabel(self.frame_config, text="Mode:").pack(anchor="w")
            m_var = ctk.StringVar(value=get_val('mode', 'set'))
            ctk.CTkComboBox(self.frame_config, variable=m_var, values=['set', 'adjust']).pack(fill="x", pady=5)
            self.widgets['mode'] = m_var
            
            # Value
            ctk.CTkLabel(self.frame_config, text="Value (0-100%):").pack(anchor="w")
            
            # Slider Logic
            def update_val_lbl(val):
                lbl_val.configure(text=f"{int(val)}%")
                
            init_val = float(get_val('value', '0.5'))
            # Check if stored as 0-1 or 0-100
            if init_val <= 1.0: init_val *= 100
            
            slider = ctk.CTkSlider(self.frame_config, from_=0, to=100, number_of_steps=100, command=update_val_lbl)
            slider.set(init_val)
            slider.pack(fill="x", pady=5)
            self.widgets['value_slider'] = slider # Special key
            
            lbl_val = ctk.CTkLabel(self.frame_config, text=f"{int(init_val)}%")
            lbl_val.pack(anchor="n")

    def browse_folder(self, entry_widget):
        folder = filedialog.askdirectory()
        if folder:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, folder)

    def browse_file(self, entry_widget):
        filename = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.ogg")])
        if filename:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, filename)

    def on_ok(self):
        t = self.type_var.get()
        res = {'type': t}
        
        # Harvest data
        try:
            if 'message' in self.widgets:
                res['message'] = self.widgets['message'].get()
            if 'ms' in self.widgets:
                 res['ms'] = int(self.widgets['ms'].get())
            if 'file' in self.widgets:
                res['file'] = self.widgets['file'].get()
            if 'folder' in self.widgets:
                res['folder'] = self.widgets['folder'].get()
            if 'device' in self.widgets:
                res['device'] = self.widgets['device'].get()
            if 'scene' in self.widgets:
                res['scene'] = self.widgets['scene'].get()
            if 'action_name' in self.widgets:
                res['action_name'] = self.widgets['action_name'].get()
            if 'target' in self.widgets:
                res['target'] = self.widgets['target'].get()
            if 'mode' in self.widgets:
                res['mode'] = self.widgets['mode'].get()
                
            if 'value_slider' in self.widgets:
                # Convert 0-100 slider to 0.0-1.0 for backend
                val = self.widgets['value_slider'].get()
                res['value'] = f"{val/100:.2f}"
            elif 'value' in self.widgets: # Fallback if widget name mismatch
                res['value'] = self.widgets['value'].get()
                
            if 'volume_slider' in self.widgets:
                # Keep 0-100 for play_sound config
                res['volume'] = str(int(self.widgets['volume_slider'].get()))
            elif 'volume' in self.widgets:
                res['volume'] = self.widgets['volume'].get()
                
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric value!")
            return

        self.result = res
        self.destroy()

class TriggerDialog(ctk.CTkToplevel):
    def __init__(self, parent, initial_data=None):
        super().__init__(parent)
        self.title("Edit Trigger" if initial_data else "Add Trigger")
        self.geometry("350x300")
        self.result = None
        self.initial_data = initial_data or {}
        
        # --- TYPE SELECTION ---
        ctk.CTkLabel(self, text="Trigger Type:").pack(pady=(10, 5))
        
        # Get initial type from data
        start_type = self.initial_data.get('type', "twitch_command")
        
        # Create friendly display names mapping
        trigger_types = [
            ("twitch_command", "Twitch: Chat-Befehl (!command)"),
            ("twitch_raid", "Twitch: Raid empfangen"),
            ("twitch_sub", "Twitch: Neuer Subscriber"),
            ("timer", "Timer (Intervall)"),
            ("obs_scene", "OBS: Szene gewechselt")
        ]
        
        self.type_mapping = {display: internal for internal, display in trigger_types}
        self.reverse_mapping = {internal: display for internal, display in trigger_types}
        
        # Find display name for initial type
        start_display = self.reverse_mapping.get(start_type, trigger_types[0][1])
        
        self.type_var = ctk.StringVar(value=start_display)
        self.combo = ctk.CTkComboBox(self, variable=self.type_var, 
                                     values=[display for _, display in trigger_types],
                                     command=self.on_type_change)
        self.combo.pack(pady=5)
        
        # --- DYNAMIC CONFIG FRAME ---
        self.config_frame = ctk.CTkFrame(self)
        self.config_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.entry_var = ctk.StringVar()
        self.lbl_config = ctk.CTkLabel(self.config_frame, text="Command (!cmd):")
        self.lbl_config.pack()
        
        self.entry_config = ctk.CTkEntry(self.config_frame, textvariable=self.entry_var)
        self.entry_config.pack(fill="x", padx=10, pady=5)
        
        # OK BUTTON
        ctk.CTkButton(self, text="Save" if initial_data else "Add", command=self.on_ok).pack(pady=10)
        
        self.on_type_change(start_type)

    def on_type_change(self, choice):
        self.entry_var.set("") # Clear input default
        
        # Map display name back to internal type
        internal_type = self.type_mapping.get(choice, "twitch_command")
        
        # But if editing, restore value
        val = ""
        if self.initial_data and self.initial_data.get('type') == internal_type:
             if internal_type == "twitch_command": val = self.initial_data.get('command', '')
             elif internal_type == "twitch_raid": val = str(self.initial_data.get('min_viewers', 0))
             elif internal_type == "timer": val = str(self.initial_data.get('interval', 60))
             elif internal_type == "obs_scene": val = self.initial_data.get('scene_name', '')
             
        self.entry_var.set(val)

        if internal_type == "twitch_command":
            self.lbl_config.configure(text="Befehlsname (z.B. !start):")
            self.entry_config.configure(state="normal")
        elif internal_type == "twitch_raid":
            self.lbl_config.configure(text="Min. Zuschauer:")
            self.entry_config.configure(state="normal")
            if not val: self.entry_var.set("0")
        elif internal_type == "twitch_sub":
            self.lbl_config.configure(text="Keine Konfiguration nötig.")
            self.entry_config.configure(state="disabled")
        elif internal_type == "timer":
            self.lbl_config.configure(text="Intervall (Sekunden):")
            self.entry_config.configure(state="normal")
        elif internal_type == "obs_scene":
            self.lbl_config.configure(text="Szenenname:")
            self.entry_config.configure(state="normal")

    def on_ok(self):
        # Map back from display name to internal type
        display_name = self.type_var.get()
        t_type = self.type_mapping.get(display_name, "twitch_command")
        val = self.entry_var.get()
        
        data = {'type': t_type}
        
        if t_type == "twitch_command":
            if not val.startswith("!"): val = "!" + val
            data['command'] = val
        elif t_type == "twitch_raid":
            data['min_viewers'] = int(val) if val.isdigit() else 0
        elif t_type == "timer":
            data['interval'] = int(val) if val.isdigit() else 60
        elif t_type == "obs_scene":
            data['scene_name'] = val
            
        self.result = data
        self.destroy()
