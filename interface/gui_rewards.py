import customtkinter as ctk
from tkinter import messagebox, simpledialog, colorchooser
import requests
import json
import os
import threading

class RewardEditorFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        self.rewards = []
        self.broadcaster_id = None
        self.client_id = None
        self.token = None
        
        # --- UI LAYOUT ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        ctk.CTkLabel(self.header, text="Channel Points Rewards", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkButton(self.header, text="Refresh", command=self.refresh_rewards).pack(side="right")
        
        # List Area
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=5)
        
        # Footer (Add Button)
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.grid(row=2, column=0, sticky="ew", padx=20, pady=20)
        
        ctk.CTkButton(self.footer, text="+ Create New Reward", command=self.add_reward_dialog, fg_color="green").pack(fill="x")
        
        # Initial Load
        self.load_creds()
        self.refresh_rewards()
        
    def load_creds(self):
        # 1. Load Client ID from config
        if os.path.exists("config.yaml"):
            import yaml
            with open("config.yaml", "r") as f:
                cfg = yaml.safe_load(f)
                self.client_id = cfg.get("twitch", {}).get("client_id")
                
        # 2. Load Token
        if os.path.exists("token_twitch.json"):
            with open("token_twitch.json", "r") as f:
                data = json.load(f)
                self.token = data.get("access_token")

    def get_broadcaster_id(self):
        if self.broadcaster_id: return self.broadcaster_id
        
        if not self.token or not self.client_id: return None
        
        headers = {
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {self.token}"
        }
        try:
            resp = requests.get("https://api.twitch.tv/helix/users", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data['data']:
                    self.broadcaster_id = data['data'][0]['id']
                    return self.broadcaster_id
        except Exception as e:
            print(f"Error fetching user ID: {e}")
        return None

    def refresh_rewards(self):
        # Run in thread to allow UI to show "Loading..."
        for w in self.scroll_frame.winfo_children(): w.destroy()
        ctk.CTkLabel(self.scroll_frame, text="Loading...").pack()
        
        threading.Thread(target=self._fetch_rewards_thread, daemon=True).start()

    def _fetch_rewards_thread(self):
        self.load_creds()
        bid = self.get_broadcaster_id()
        
        if not bid:
            self.after(0, lambda: messagebox.showerror("Error", "Could not fetch Broadcaster ID.\nCheck Twitch Login."))
            return

        headers = {
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            url = f"https://api.twitch.tv/helix/channel_points/custom_rewards?broadcaster_id={bid}"
            resp = requests.get(url, headers=headers)
            
            if resp.status_code == 200:
                self.rewards = resp.json().get('data', [])
                self.after(0, self.update_ui_list)
            elif resp.status_code == 401:
                self.after(0, lambda: messagebox.showerror("Auth Error", "Token invalid or missing scope 'channel:manage:redemptions'."))
            else:
                self.after(0, lambda: messagebox.showerror("API Error", f"Status: {resp.status_code}\n{resp.text}"))
                
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def update_ui_list(self):
        for w in self.scroll_frame.winfo_children(): w.destroy()
        
        if not self.rewards:
            ctk.CTkLabel(self.scroll_frame, text="No custom rewards found.").pack(pady=20)
            return
            
        for r in self.rewards:
            self.create_reward_item(r)

    # --- SCROLL FIX START ---
    def _on_mouse_wheel(self, event):
        # Linux (Button-4/5)
        if event.num == 4:
            self.scroll_frame._parent_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.scroll_frame._parent_canvas.yview_scroll(1, "units")
        # Windows/Mac (Delta)
        else:
            delta = int(-1*(event.delta/120))
            self.scroll_frame._parent_canvas.yview_scroll(delta, "units")
            
    def _bind_scroll_events(self, widget):
        # Bind for Windows/Mac
        widget.bind("<MouseWheel>", self._on_mouse_wheel)
        # Bind for Linux
        widget.bind("<Button-4>", self._on_mouse_wheel)
        widget.bind("<Button-5>", self._on_mouse_wheel)
        
        # Recursively bind children
        for child in widget.winfo_children():
            self._bind_scroll_events(child)
    # --- SCROLL FIX END ---

    def create_reward_item(self, r):
        f = ctk.CTkFrame(self.scroll_frame)
        f.pack(fill="x", pady=5)
        
        # Color indicator
        color = r.get('background_color', "#555")
        try:
            # Create a small color box
            c_box = ctk.CTkLabel(f, text="  ", fg_color=color, width=20, corner_radius=5)
            c_box.pack(side="left", padx=10, pady=10)
        except: pass
        
        # Details
        info_frame = ctk.CTkFrame(f, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)
        
        title = ctk.CTkLabel(info_frame, text=r['title'], font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(anchor="w")
        
        cost_txt = f"{r['cost']} pts"
        if not r['is_enabled']: cost_txt += " (DISABLED)"
        ctk.CTkLabel(info_frame, text=cost_txt, text_color="gray" if r['is_enabled'] else "red").pack(anchor="w")

        # Controls
        btn_frame = ctk.CTkFrame(f, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)
        
        # Toggle
        state_txt = "Disable" if r['is_enabled'] else "Enable"
        ctk.CTkButton(btn_frame, text=state_txt, width=60, 
                      command=lambda: self.toggle_reward(r['id'], not r['is_enabled'])).pack(side="left", padx=2)
        
        # Edit
        ctk.CTkButton(btn_frame, text="Edit", width=60, 
                      command=lambda: self.edit_reward_dialog(r)).pack(side="left", padx=2)
                      
        # Delete
        ctk.CTkButton(btn_frame, text="Del", width=40, fg_color="red", 
                      command=lambda: self.delete_reward(r['id'])).pack(side="left", padx=2)
        
        # Fix Scroll
        self._bind_scroll_events(f)

    def add_reward_dialog(self):
        RewardDialog(self, mode="create")

    def edit_reward_dialog(self, reward_data):
        RewardDialog(self, mode="edit", initial_data=reward_data)

    # --- API ACTIONS ---
    def delete_reward(self, rid):
        if not messagebox.askyesno("Confirm", "Delete this reward permanently?"): return
        
        headers = {
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {self.token}"
        }
        url = f"https://api.twitch.tv/helix/channel_points/custom_rewards?broadcaster_id={self.broadcaster_id}&id={rid}"
        
        try:
            resp = requests.delete(url, headers=headers)
            if resp.status_code == 204:
                self.refresh_rewards()
            else:
                messagebox.showerror("Error", resp.text)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def toggle_reward(self, rid, new_state):
        self.update_reward(rid, {"is_enabled": new_state})

    def update_reward(self, rid, data):
        headers = {
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        url = f"https://api.twitch.tv/helix/channel_points/custom_rewards?broadcaster_id={self.broadcaster_id}&id={rid}"
        
        try:
            resp = requests.patch(url, headers=headers, json=data)
            if resp.status_code == 200:
                self.refresh_rewards()
            else:
                messagebox.showerror("Error", resp.text)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def create_reward(self, data):
        headers = {
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        url = f"https://api.twitch.tv/helix/channel_points/custom_rewards?broadcaster_id={self.broadcaster_id}"
        
        try:
            resp = requests.post(url, headers=headers, json=data)
            if resp.status_code == 200:
                self.refresh_rewards()
            else:
                messagebox.showerror("Error", resp.text)
        except Exception as e:
            messagebox.showerror("Error", str(e))


class RewardDialog(ctk.CTkToplevel):
    def __init__(self, parent, mode="create", initial_data=None):
        super().__init__(parent)
        self.parent_frame = parent
        self.mode = mode
        self.initial_data = initial_data or {}
        
        self.title("Create Reward" if mode=="create" else "Edit Reward")
        self.geometry("400x500")
        
        # PROPS
        ctk.CTkLabel(self, text="Title:").pack(anchor="w", padx=10)
        self.entry_title = ctk.CTkEntry(self)
        self.entry_title.pack(fill="x", padx=10)
        if initial_data: self.entry_title.insert(0, initial_data.get('title', ''))
        
        ctk.CTkLabel(self, text="Cost:").pack(anchor="w", padx=10)
        self.entry_cost = ctk.CTkEntry(self)
        self.entry_cost.pack(fill="x", padx=10)
        if initial_data: self.entry_cost.insert(0, str(initial_data.get('cost', 100)))

        ctk.CTkLabel(self, text="Prompt (Description):").pack(anchor="w", padx=10)
        self.entry_prompt = ctk.CTkEntry(self)
        self.entry_prompt.pack(fill="x", padx=10)
        if initial_data: self.entry_prompt.insert(0, initial_data.get('prompt', ''))
        
        # User Input
        self.var_input = ctk.BooleanVar(value=initial_data.get('is_user_input_required', False) if initial_data else False)
        ctk.CTkCheckBox(self, text="User Input Required?", variable=self.var_input).pack(anchor="w", padx=10, pady=10)
        
        # Color
        self.color = initial_data.get('background_color', '#00FF00') if initial_data else '#00FF00'
        self.btn_color = ctk.CTkButton(self, text=f"Color: {self.color}", fg_color=self.color, command=self.pick_color)
        self.btn_color.pack(fill="x", padx=10, pady=10)
        
        # Is Enabled
        self.var_enabled = ctk.BooleanVar(value=initial_data.get('is_enabled', True) if initial_data else True)
        ctk.CTkSwitch(self, text="Enabled", variable=self.var_enabled).pack(anchor="w", padx=10, pady=5)
        
        
        ctk.CTkButton(self, text="Save", command=self.save).pack(pady=20)
        
    def pick_color(self):
        # We need a tkinter colorchooser, ctk doesn't have one
        try:
            color = colorchooser.askcolor(initialcolor=self.color, title="Choose Reward Color")[1]
            if color:
                self.color = color
                self.btn_color.configure(text=f"Color: {self.color}", fg_color=self.color)
        except: pass

    def save(self):
        try:
            data = {
                "title": self.entry_title.get(),
                "cost": int(self.entry_cost.get()),
                "prompt": self.entry_prompt.get(),
                "is_user_input_required": self.var_input.get(),
                "background_color": self.color,
                "is_enabled": self.var_enabled.get()
            }
            
            if self.mode == "create":
                self.parent_frame.create_reward(data)
            else:
                self.parent_frame.update_reward(self.initial_data['id'], data)
                
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Cost must be a number!")
