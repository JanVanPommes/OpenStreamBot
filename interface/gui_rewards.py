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
        self._reward_item_widgets = {} # rid -> (frame, color_box, title_lbl, cost_lbl, toggle_btn)
        
        # --- UI LAYOUT ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        ctk.CTkLabel(self.header, text="Channel Points Rewards", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        self.btn_refresh = ctk.CTkButton(self.header, text="🔄 Refresh", command=lambda: self.refresh_rewards(manual=True))
        self.btn_refresh.pack(side="right")
        
        # List Area
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=5)
        
        # Footer (Add Button)
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.grid(row=2, column=0, sticky="ew", padx=20, pady=20)
        
        ctk.CTkButton(self.footer, text="+ Create New Reward", command=self.add_reward_dialog, fg_color="#10B981", hover_color="#059669").pack(fill="x")
        
        # 1. Load Credentials from disk
        self.load_creds()
        
        # 2. Fast Initial Render from local cache (Instant UI!)
        self.load_cached_rewards()
        
        # 3. Background Sync with Twitch API
        self.refresh_rewards(manual=False)

    def load_creds(self):
        # 1. Load Client ID from config
        if os.path.exists("config.yaml"):
            try:
                import yaml
                with open("config.yaml", "r") as f:
                    cfg = yaml.safe_load(f) or {}
                    self.client_id = cfg.get("twitch", {}).get("client_id")
            except Exception:
                pass
                
        # 2. Load Token & Broadcaster ID
        if os.path.exists("token_twitch.json"):
            try:
                with open("token_twitch.json", "r") as f:
                    data = json.load(f)
                    self.token = data.get("access_token")
                    self.broadcaster_id = data.get("user_id") or data.get("broadcaster_id")
            except Exception:
                pass

    def get_broadcaster_id(self):
        if self.broadcaster_id:
            return self.broadcaster_id
        
        if not self.token or not self.client_id:
            return None
        
        headers = {
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            resp = requests.get("https://api.twitch.tv/helix/users", headers=headers, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('data'):
                    self.broadcaster_id = data['data'][0]['id']
                    # Persist broadcaster_id into token_twitch.json for instant future loads
                    try:
                        if os.path.exists("token_twitch.json"):
                            with open("token_twitch.json", "r") as f:
                                tdata = json.load(f)
                            tdata["broadcaster_id"] = self.broadcaster_id
                            tdata["user_id"] = self.broadcaster_id
                            with open("token_twitch.json", "w") as f:
                                json.dump(tdata, f)
                    except Exception:
                        pass
                    return self.broadcaster_id
            elif resp.status_code == 401:
                print("[Rewards] Token invalid or expired.")
                return None
        except Exception as e:
            print(f"[Rewards] Error fetching user ID: {e}")
            return None
        return None

    def load_cached_rewards(self):
        """Loads cached rewards from available_rewards.json for 0ms initial render."""
        if os.path.exists("available_rewards.json"):
            try:
                with open("available_rewards.json", "r", encoding="utf-8") as f:
                    cached_list = json.load(f)
                    if isinstance(cached_list, list) and cached_list:
                        self.rewards = [
                            {
                                "id": r.get("id"),
                                "title": r.get("title", ""),
                                "cost": r.get("cost", 0),
                                "is_enabled": r.get("is_enabled", True),
                                "background_color": r.get("background_color", "#9146FF"),
                                "prompt": r.get("prompt", "")
                            }
                            for r in cached_list if isinstance(r, dict) and r.get("id")
                        ]
                        self.update_ui_list()
            except Exception as e:
                print(f"[Rewards] Error loading cached rewards: {e}")

    def save_local_rewards_cache(self):
        """Saves current rewards state to available_rewards.json for local persistence."""
        try:
            cached_list = []
            for r in self.rewards:
                cached_list.append({
                    "id": r.get("id"),
                    "title": r.get("title", ""),
                    "cost": r.get("cost", 0),
                    "is_enabled": r.get("is_enabled", True),
                    "background_color": r.get("background_color", "#9146FF"),
                    "prompt": r.get("prompt", "")
                })
            with open("available_rewards.json", "w", encoding="utf-8") as f:
                json.dump(cached_list, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[Rewards] Failed to write available_rewards.json: {e}")

    def refresh_rewards(self, manual=False):
        if manual:
            self.btn_refresh.configure(state="disabled", text="⏳ Syncing...")
            if not self.rewards:
                for w in self.scroll_frame.winfo_children(): w.destroy()
                ctk.CTkLabel(self.scroll_frame, text="Loading rewards from Twitch...").pack(pady=20)
        
        threading.Thread(target=self._fetch_rewards_thread, args=(manual,), daemon=True).start()

    def _fetch_rewards_thread(self, manual=False):
        self.load_creds()
        bid = self.get_broadcaster_id()
        
        if not bid:
            if manual or not self.rewards:
                self.after(0, self.show_error_in_ui, "Could not fetch Broadcaster ID.\nWait for Bot to start (auto-refresh) or check Login.")
            if manual:
                self.after(0, lambda: self.btn_refresh.configure(state="normal", text="🔄 Refresh"))
            return

        headers = {
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            url = f"https://api.twitch.tv/helix/channel_points/custom_rewards?broadcaster_id={bid}"
            resp = requests.get(url, headers=headers, timeout=5)
            
            if resp.status_code == 200:
                self.rewards = resp.json().get('data', [])
                self.save_local_rewards_cache()
                self.after(0, self.update_ui_list)
            elif resp.status_code == 401:
                if manual or not self.rewards:
                    self.after(0, self.show_error_in_ui, "Token expired.\nPlease start the bot to auto-refresh the token,\nthen click 'Refresh' here.")
            else:
                if manual or not self.rewards:
                    self.after(0, self.show_error_in_ui, f"API Error: {resp.status_code}\n{resp.text}")
                
        except Exception as e:
            if manual or not self.rewards:
                self.after(0, self.show_error_in_ui, f"Error: {str(e)}")
        finally:
            if manual:
                self.after(0, lambda: self.btn_refresh.configure(state="normal", text="🔄 Refresh"))

    def show_error_in_ui(self, msg):
        for w in self.scroll_frame.winfo_children(): w.destroy()
        self._reward_item_widgets.clear()
        lbl = ctk.CTkLabel(self.scroll_frame, text=msg, text_color="red")
        lbl.pack(pady=20)

    def update_ui_list(self):
        if not self.rewards:
            for w in self.scroll_frame.winfo_children(): w.destroy()
            self._reward_item_widgets.clear()
            ctk.CTkLabel(self.scroll_frame, text="No custom rewards found.").pack(pady=20)
            return

        current_rids = [r['id'] for r in self.rewards if r.get('id')]
        existing_rids = set(self._reward_item_widgets.keys())

        # If list structure changed (items added/removed), rebuild widgets cleanly
        if set(current_rids) != existing_rids:
            for w in self.scroll_frame.winfo_children(): w.destroy()
            self._reward_item_widgets.clear()
            for r in self.rewards:
                self.create_reward_item(r)
        else:
            # Fast in-place update of existing widgets (Zero flickering!)
            for r in self.rewards:
                rid = r['id']
                if rid in self._reward_item_widgets:
                    _, c_box, title_lbl, cost_lbl, toggle_btn = self._reward_item_widgets[rid]
                    
                    color = r.get('background_color', "#555")
                    try: c_box.configure(fg_color=color)
                    except: pass
                    
                    title_lbl.configure(text=r['title'])
                    
                    cost_txt = f"{r['cost']} pts"
                    if not r['is_enabled']: cost_txt += " (DISABLED)"
                    cost_lbl.configure(text=cost_txt, text_color="gray" if r['is_enabled'] else "red")
                    
                    state_txt = "Disable" if r['is_enabled'] else "Enable"
                    toggle_color = "#6B7280" if r['is_enabled'] else "#10B981"
                    toggle_btn.configure(text=state_txt, fg_color=toggle_color)

        self._bind_scroll_events(self.scroll_frame)
        if hasattr(self.scroll_frame, '_parent_canvas'):
            self._bind_scroll_events(self.scroll_frame._parent_canvas)
        if hasattr(self.scroll_frame, '_parent_frame'):
            self._bind_scroll_events(self.scroll_frame._parent_frame)

    # --- SCROLL FIX START ---
    def _on_mouse_wheel(self, event):
        try:
            canvas = getattr(self.scroll_frame, '_parent_canvas', None)
            if not canvas:
                return "break"
            if hasattr(event, 'num') and event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif hasattr(event, 'num') and event.num == 5:
                canvas.yview_scroll(1, "units")
            elif hasattr(event, 'delta') and event.delta:
                units = -1 if event.delta > 0 else 1
                canvas.yview_scroll(units, "units")
        except Exception:
            pass
        return "break"
            
    def _bind_scroll_events(self, widget):
        if not widget: return
        try:
            widget.bind("<MouseWheel>", self._on_mouse_wheel, add="+")
            widget.bind("<Button-4>", self._on_mouse_wheel, add="+")
            widget.bind("<Button-5>", self._on_mouse_wheel, add="+")
        except Exception:
            pass
        
        try:
            for child in widget.winfo_children():
                self._bind_scroll_events(child)
        except Exception:
            pass
    # --- SCROLL FIX END ---

    def create_reward_item(self, r):
        rid = r['id']
        f = ctk.CTkFrame(self.scroll_frame, fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), corner_radius=10)
        f.pack(fill="x", pady=5, padx=5)
        
        # Color indicator
        color = r.get('background_color', "#555")
        c_box = None
        try:
            c_box = ctk.CTkLabel(f, text="  ", fg_color=color, width=20, corner_radius=5)
            c_box.pack(side="left", padx=10, pady=10)
        except: pass
        
        # Details
        info_frame = ctk.CTkFrame(f, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)
        
        title_lbl = ctk.CTkLabel(info_frame, text=r['title'], font=ctk.CTkFont(size=16, weight="bold"))
        title_lbl.pack(anchor="w")
        
        cost_txt = f"{r['cost']} pts"
        if not r['is_enabled']: cost_txt += " (DISABLED)"
        cost_lbl = ctk.CTkLabel(info_frame, text=cost_txt, text_color="gray" if r['is_enabled'] else "red")
        cost_lbl.pack(anchor="w")

        # Controls
        btn_frame = ctk.CTkFrame(f, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)
        
        # Toggle
        state_txt = "Disable" if r['is_enabled'] else "Enable"
        toggle_color = "#6B7280" if r['is_enabled'] else "#10B981"
        toggle_btn = ctk.CTkButton(btn_frame, text=state_txt, width=60, fg_color=toggle_color,
                                   command=lambda id_val=rid: self.toggle_reward(id_val))
        toggle_btn.pack(side="left", padx=2)
        
        # Edit
        ctk.CTkButton(btn_frame, text="Edit", width=60, fg_color="#3B82F6", hover_color="#2563EB",
                      command=lambda id_val=rid: self.edit_reward_dialog(id_val)).pack(side="left", padx=2)
                      
        # Delete
        ctk.CTkButton(btn_frame, text="Del", width=40, fg_color="#EF4444", hover_color="#DC2626",
                      command=lambda id_val=rid: self.delete_reward(id_val)).pack(side="left", padx=2)
        
        self._reward_item_widgets[rid] = (f, c_box, title_lbl, cost_lbl, toggle_btn)
        self._bind_scroll_events(f)

    def add_reward_dialog(self):
        RewardDialog(self, mode="create")

    def edit_reward_dialog(self, rid):
        r_data = next((item for item in self.rewards if item['id'] == rid), None)
        if r_data:
            RewardDialog(self, mode="edit", initial_data=r_data)

    # --- FAST ASYNCHRONOUS API ACTIONS ---
    def toggle_reward(self, rid):
        """Optimistically toggles reward state instantly in UI and sends PATCH request in background."""
        r_item = next((item for item in self.rewards if item['id'] == rid), None)
        if not r_item: return

        # 1. Optimistic local state update (0ms lag!)
        new_state = not r_item.get('is_enabled', True)
        r_item['is_enabled'] = new_state
        self.update_ui_list()
        self.save_local_rewards_cache()

        # 2. Async API dispatch
        def _async_patch():
            headers = {
                "Client-Id": self.client_id,
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            url = f"https://api.twitch.tv/helix/channel_points/custom_rewards?broadcaster_id={self.broadcaster_id}&id={rid}"
            try:
                resp = requests.patch(url, headers=headers, json={"is_enabled": new_state}, timeout=5)
                if resp.status_code != 200:
                    # Revert on error
                    r_item['is_enabled'] = not new_state
                    self.after(0, self.update_ui_list)
                    self.after(0, lambda: messagebox.showerror("Error", f"Failed to update reward:\n{resp.text}"))
            except Exception as e:
                r_item['is_enabled'] = not new_state
                self.after(0, self.update_ui_list)
                self.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=_async_patch, daemon=True).start()

    def delete_reward(self, rid):
        if not messagebox.askyesno("Confirm", "Delete this reward permanently?"): return
        
        # Optimistic remove
        r_item = next((item for item in self.rewards if item['id'] == rid), None)
        if not r_item: return
        
        self.rewards = [r for r in self.rewards if r['id'] != rid]
        self.update_ui_list()
        self.save_local_rewards_cache()

        def _async_delete():
            headers = {
                "Client-Id": self.client_id,
                "Authorization": f"Bearer {self.token}"
            }
            url = f"https://api.twitch.tv/helix/channel_points/custom_rewards?broadcaster_id={self.broadcaster_id}&id={rid}"
            try:
                resp = requests.delete(url, headers=headers, timeout=5)
                if resp.status_code not in (200, 204):
                    # Revert on error
                    self.rewards.append(r_item)
                    self.after(0, self.update_ui_list)
                    self.after(0, lambda: messagebox.showerror("Error", f"Failed to delete reward:\n{resp.text}"))
            except Exception as e:
                self.rewards.append(r_item)
                self.after(0, self.update_ui_list)
                self.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=_async_delete, daemon=True).start()

    def update_reward(self, rid, data):
        r_item = next((item for item in self.rewards if item['id'] == rid), None)
        if not r_item: return

        # Optimistic update
        old_copy = dict(r_item)
        r_item.update(data)
        self.update_ui_list()
        self.save_local_rewards_cache()

        def _async_update():
            headers = {
                "Client-Id": self.client_id,
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            url = f"https://api.twitch.tv/helix/channel_points/custom_rewards?broadcaster_id={self.broadcaster_id}&id={rid}"
            try:
                resp = requests.patch(url, headers=headers, json=data, timeout=5)
                if resp.status_code != 200:
                    r_item.update(old_copy)
                    self.after(0, self.update_ui_list)
                    self.after(0, lambda: messagebox.showerror("Error", f"Failed to update reward:\n{resp.text}"))
            except Exception as e:
                r_item.update(old_copy)
                self.after(0, self.update_ui_list)
                self.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=_async_update, daemon=True).start()

    def create_reward(self, data):
        def _async_create():
            headers = {
                "Client-Id": self.client_id,
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            url = f"https://api.twitch.tv/helix/channel_points/custom_rewards?broadcaster_id={self.broadcaster_id}"
            try:
                resp = requests.post(url, headers=headers, json=data, timeout=5)
                if resp.status_code == 200:
                    created_data = resp.json().get('data', [])
                    if created_data:
                        self.rewards.append(created_data[0])
                        self.after(0, self.update_ui_list)
                        self.after(0, self.save_local_rewards_cache)
                else:
                    self.after(0, lambda: messagebox.showerror("Error", f"Failed to create reward:\n{resp.text}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=_async_create, daemon=True).start()


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
