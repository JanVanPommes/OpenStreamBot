import yaml
import os
import asyncio
import logging
import pygame.mixer as sa # alias to keep code similar or just rename
import time
import random
import pygame._sdl2.audio as sdl_audio

# Logging setup
logger = logging.getLogger("ActionEngine")

class ActionEngine:
    def __init__(self, config_file="actions.yaml", event_server=None, obs_controller=None, twitch_bot=None, youtube_bot=None):
        self.config_file = config_file
        self.event_server = event_server
        self.obs = obs_controller
        self.twitch = twitch_bot
        self.youtube = youtube_bot
        self.actions = []
        
        self.timer_tasks = []
        self.playlist_task = None
        self.current_audio_device = None # Tracks current mixer device
        self.current_playlist_sound = None # Tracks currently playing Sound object
        
        self.cooldowns = {} # Map action_name -> last_run_ts

        # Volume Control (0.0 - 1.0)
        self.vol_sfx = 1.0
        self.vol_playlist = 1.0
        self.pre_duck_volume = None # For Auto-Ducking
        
        # Register Handlers
        if self.event_server:
            self.event_server.add_message_handler(self.on_ws_message)

        self.load_actions()

    def load_actions(self):
        self.stop_timers()
        
        # Initialize from example if missing
        if not os.path.exists(self.config_file):
            if os.path.exists("actions.example.yaml"):
                import shutil
                try:
                    shutil.copy("actions.example.yaml", self.config_file)
                    print("[ActionEngine] actions.yaml initialized from example.")
                except Exception as e:
                    print(f"[ActionEngine] Error initializing actions.yaml: {e}")
        
        if not os.path.exists(self.config_file):
            self.actions = []
            return

        with open(self.config_file, 'r') as f:
            data = yaml.safe_load(f) or {}
            self.actions = data.get('actions', [])
        
        print(f"[ActionEngine] Loaded {len(self.actions)} actions.")
        self.timer_tasks = {} # Use dict for management {name: task}
        self.start_timers()
        
        # Trigger Twitch Sync if bot is ready
        if self.twitch and hasattr(self.twitch, 'is_ready') and self.twitch.is_ready:
            asyncio.create_task(self.twitch.sync_cooldowns(self.actions))

    def stop_timers(self):
        if isinstance(self.timer_tasks, list): # Legacy support during migration (init is list)
            for t in self.timer_tasks: t.cancel()
            self.timer_tasks = {}
        else:
            for t in self.timer_tasks.values():
                t.cancel()
            self.timer_tasks.clear()

    def start_timers(self):
        for action in self.actions:
            if not action.get('enabled', True): continue
            self._start_action_timer(action)

    def _start_action_timer(self, action):
        for trigger in action.get('triggers', []):
             if trigger.get('type') == 'timer':
                 interval = trigger.get('interval', 60)
                 # Cancel existing if any (restart logic)
                 if action['name'] in self.timer_tasks:
                     self.timer_tasks[action['name']].cancel()
                     
                 task = asyncio.create_task(self.run_timer(action, interval))
                 self.timer_tasks[action['name']] = task
                 print(f"[Timer] Started for {action['name']} ({interval}s)")

    def _update_action_state(self, action_name, new_state):
        target = next((a for a in self.actions if a.get('name') == action_name), None)
        if not target: return False
        
        old_state = target.get('enabled', True)
        if old_state != new_state:
            target['enabled'] = new_state
            print(f"[ActionEngine] State Change: '{action_name}' -> {'ENABLED' if new_state else 'DISABLED'}")
            self.save_actions()
            
            # Timer Management
            if new_state:
                self._start_action_timer(target)
            else:
                if action_name in self.timer_tasks:
                    self.timer_tasks[action_name].cancel()
                    del self.timer_tasks[action_name]
                    print(f"[Timer] Stopped for {action_name}")
            
            return True
        return False

    async def run_timer(self, action, interval):
        try:
            while True:
                await asyncio.sleep(interval)
                # Execute (Timers ignore cooldown currently? Or should they respect it? 
                # Ideally timers ARE the schedule, so ignore cooldown usually.
                # But let's keep it simple.)
                print(f"[Timer] Executing {action['name']}")
                asyncio.create_task(self.execute_action(action, {}))
        except asyncio.CancelledError:
            pass

    def save_actions(self):
        data = {'actions': self.actions}
        with open(self.config_file, 'w') as f:
            yaml.dump(data, f)
        print("[ActionEngine] Actions saved.")

    async def handle_event(self, event_type, data):
        """
        Main entry point for triggers.
        Checks if any action matches the event type and data.
        """
        now = time.time()
    async def handle_event(self, event_type, data):
        """
        Main entry point for triggers.
        Checks if any action matches the event type and data.
        """
        # --- SYSTEM EVENTS ---
        if event_type == "BotStatus" and self.twitch:
            if data.get("platform") == "Twitch" and data.get("status") == "Connected":
                 print("[ActionEngine] Twitch Connected. Triggering Cooldown Sync...")
                 asyncio.create_task(self.twitch.sync_cooldowns(self.actions))
            return # System events usually don't trigger actions directly (?) unless configured

        now = time.time()
        for action in self.actions:
            if not action.get('enabled', True):
                continue
            
            triggers = action.get('triggers', [])
            matched_trigger = None
            ctx_updates = None
            
            # 1. Check if ANY trigger matches this event
            for trigger in triggers:
                is_triggered, updates = self.check_trigger(trigger, event_type, data)
                if is_triggered:
                    matched_trigger = trigger
                    ctx_updates = updates
                    break
            
            if matched_trigger:
                # 2. Check Cooldown
                cd = action.get('cooldown', 0)
                is_on_cooldown = False
                if cd > 0:
                    last_run = self.cooldowns.get(action['name'], 0)
                    if now - last_run < cd:
                        is_on_cooldown = True

                if is_on_cooldown:
                    print(f"[ActionEngine] Action '{action['name']}' blocked by cooldown ({cd}s).")
                    
                    # --- REFUND LOGIC ---
                    # Check if this was a Twitch Redemption trigger
                    # We need to map the event type or check the trigger type
                    # The mapped type logic is inside check_trigger, but we know event_type
                    if event_type == "TwitchRedemption" and self.twitch:
                        redemption_id = data.get('redemption_id')
                        reward_id = data.get('reward_id')
                        if redemption_id and reward_id:
                            print(f"[ActionEngine] Refunding Twitch Points for '{action['name']}'...")
                            asyncio.create_task(self.twitch.refund_redemption(redemption_id, reward_id))
                    
                    continue # Skip execution
                
                # 3. Execute
                if cd > 0: self.cooldowns[action['name']] = now
                
                print(f"[ActionEngine] Trigger fired: {action['name']} (Event: {event_type})")
                
                # Merge context
                full_ctx = data.copy() if data else {}
                if ctx_updates:
                    full_ctx.update(ctx_updates)

                # Execute async
                asyncio.create_task(self.execute_action(action, full_ctx))
                break # One trigger per action is enough

    async def on_ws_message(self, message):
        """Handle incoming WebSocket messages from Overlay"""
        try:
            import json
            data = json.loads(message)
            event = data.get("event")
            
            if event == "YouTubeEnded":
                print("[ActionEngine] Shorts ended. Restoring volume.")
                await self.restore_ducking()
            elif event == "reload_actions":
                print("[ActionEngine] Reload requested via WS.")
                self.load_actions()
            elif event == "set_action_state":
                payload = data.get("data", {})
                a_name = payload.get("action")
                state = payload.get("state") # boolean
                
                self._update_action_state(a_name, state)
                
        except Exception as e:
            print(f"[ActionEngine] WS Message Error: {e}")

    async def restore_ducking(self):
        if self.pre_duck_volume is not None:
            print(f"[AutoDuck] Restoring playlist volume to {self.pre_duck_volume*100:.0f}%")
            self.vol_playlist = self.pre_duck_volume
            self.pre_duck_volume = None
            
            if self.current_playlist_sound:
                try: self.current_playlist_sound.set_volume(self.vol_playlist)
                except: pass

    def check_trigger(self, trigger_config, event_type, data):
        # MAPPING: EventServer events -> Action triggers
        mapped_type = event_type
        
        if event_type == "CommandTriggered":
            if data.get('platform') == 'youtube':
                mapped_type = "youtube_command"
            else:
                mapped_type = "twitch_command"
        elif event_type == "SystemEvent":
             if data.get("type") == "raid": mapped_type = "twitch_raid"
             elif data.get("type") == "sub": mapped_type = "twitch_sub"
        elif event_type == "TwitchRedemption":
            mapped_type = "twitch_redemption"
        
        # Check Type
        if trigger_config.get('type') != mapped_type:
            return False, {}
            
        # Condition Check
        
        # --- REDEMPTION ---
        if mapped_type == "twitch_redemption":
            req_title = trigger_config.get('reward_title', '').lower()
            evt_title = data.get('reward_title', '').lower()
            
            if req_title == evt_title:
                return True, {
                    "user": data.get('user', ''),
                    "input": data.get('input', '')
                }
            return False, {}

        # --- COMMANDS (Twitch & YouTube) ---
        if mapped_type in ["twitch_command", "youtube_command"]:
            trigger_cmd = trigger_config.get('command', '').lower()
            received_cmd = data.get('command', '').lower()
            
            # --- Permission Check (Only Twitch for now) ---
            if mapped_type == "twitch_command":
                req_perm = trigger_config.get('permission', 'Everyone')
                allowed = True
                is_bc = data.get('is_broadcaster', False)
                is_mod = data.get('is_mod', False)
                is_vip = data.get('is_vip', False)
                is_sub = data.get('is_subscriber', False)
                
                if req_perm == "Broadcaster":
                    if not is_bc: allowed = False
                elif req_perm == "Moderator":
                    if not (is_bc or is_mod): allowed = False
                elif req_perm == "VIP":
                    if not (is_bc or is_mod or is_vip): allowed = False
                elif req_perm == "Subscriber":
                    if not (is_bc or is_mod or is_vip or is_sub): allowed = False
                    
                if not allowed:
                    return False, {}
            
            # 1. Simple Match
            if trigger_cmd == received_cmd:
                return True, {}
            
            # 2. Parameter Match (e.g. "!shout %user%")
            if "%" in trigger_cmd:
                t_parts = trigger_cmd.split(' ')
                base_cmd = t_parts[0]
                
                # Compare base command (e.g. "!shout")
                if base_cmd == received_cmd:
                    received_msg = data.get('message', '')
                    msg_parts = [p for p in received_msg.split(' ') if p] # Remove empty
                    
                    # Check length (Trigger usually has fewer or equal parts if we handle variable args strict? 
                    # Let's say we map 1:1 for now)
                    
                    extracted = {}
                    match = True
                    
                    for i, t_part in enumerate(t_parts):
                        if i >= len(msg_parts):
                            match = False # Message too short
                            break
                        
                        if t_part.startswith('%') and t_part.endswith('%'):
                             var_name = t_part[1:-1] # e.g. "user"
                             val = msg_parts[i]
                             
                             # Cleanup @user -> user
                             if var_name == "user" and val.startswith('@'):
                                 val = val[1:]
                                 
                             extracted[var_name] = val
                        elif t_part != msg_parts[i].lower():
                             match = False
                             break
                    
                    if match:
                        return True, extracted

            return False, {}
                
        # 2. Twitch Raid (Min Viewers)
        elif event_type == "twitch_raid":
            min_v = trigger_config.get('min_viewers', 0)
            if data.get('viewers', 0) < min_v:
                return False, {}
                
        # 3. OBS Scene Changed
        elif event_type == "obs_scene":
            scene = trigger_config.get('scene_name', '')
            if scene and scene != data.get('scene_name'):
                return False, {}

        return True, {}

    async def execute_action(self, action, context_data):
        sub_actions = action.get('sub_actions', [])
        
        # Safe copy of context for variable replacement
        ctx = context_data.copy() if context_data else {}
        
        for sa_config in sub_actions:
            try:
                await self.execute_sub_action(sa_config, ctx)
            except Exception as e:
                print(f"[ActionEngine] Error in sub-action {sa_config.get('type')}: {e}")

    async def execute_sub_action(self, config, ctx):
        sa_type = config.get('type')
        
        # --- LOGIC ---
        if sa_type == "delay":
            ms = config.get('ms', 0)
            await asyncio.sleep(ms / 1000.0)
            
        elif sa_type == "log":
            msg = self.replace_vars(config.get('message', ''), ctx)
            print(f"[Action Log] {msg}")

        # --- CHAT (Generic) ---
        elif sa_type == "twitch_chat": # Name is legacy but means "Send Chat"
            msg_raw = config.get('message', '')
            
            # Resolve %game% if needed
            if "%game%" in msg_raw and "user" in ctx:
                 if self.twitch:
                     print(f"[ActionEngine] Fetching game for {ctx['user']}...")
                     game = await self.twitch.get_user_last_game(ctx['user'])
                     ctx['game'] = game
                     print(f"[ActionEngine] Game found: {game}")
                 else:
                     ctx['game'] = "Unbekannt (Bot offline)"

            msg = self.replace_vars(msg_raw, ctx)
            platform = ctx.get('platform', 'twitch') # Default to twitch if unknown
            
            if platform == 'youtube' and self.youtube:
                 await self.youtube.send_chat_message(msg)
            elif self.twitch:
                # Assuming bot handles channel sending internally
                if self.twitch.connected_channels:
                    await self.twitch.connected_channels[0].send(msg)

        # --- OBS ---
        elif sa_type == "obs_set_scene":
            scene = self.replace_vars(config.get('scene', ''), ctx)
            if self.obs:
                await self.obs.set_scene(scene)

        elif sa_type.startswith("obs_"):
            # Generic OBS delegation if possible, or specific handlers
            pass
            
        # --- MEDIA ---
        elif sa_type == "play_sound":
            file_path = self.replace_vars(config.get('file', ''), ctx)
            device = config.get('device', None)
            base_vol = float(config.get('volume', 100)) / 100.0 # 0-100 logic
            
            final_vol = self.vol_sfx * base_vol
            
            if os.path.exists(file_path):
                 # Run in thread to not block loop
                 await asyncio.to_thread(self.play_sound_sync, file_path, device, final_vol)
            else:
                print(f"[ActionError] Sound file not found: {file_path}")

        elif sa_type == "stop_sounds":
            if sa.get_init():
                sa.stop() # Stops all playback on all channels
                print("[Action] Stopped all sounds.")
                
        elif sa_type == "playlist":
            folder = self.replace_vars(config.get('folder', ''), ctx)
            device = config.get('device', None)
            
            # Update volume if provided in config
            if 'volume' in config:
                try:
                    self.vol_playlist = float(config['volume']) / 100.0
                    print(f"[Playlist] Initial volume set to {self.vol_playlist:.2f}")
                except: pass
            
            if self.playlist_task:
                self.playlist_task.cancel()
            
            self.playlist_task = asyncio.create_task(self.run_playlist(folder, device))
            
        elif sa_type == "stop_playlist":
            if self.playlist_task:
                self.playlist_task.cancel()
                self.playlist_task = None
                print("[Action] Playlist stopped.")
                
                # Stop current playback with fadeout
                if sa.get_init():
                    sa.fadeout(1500)

        # --- YOUTUBE SHORTS ---
        elif sa_type == "youtube_random_short":
             if self.youtube:
                 vid_id = self.youtube.get_random_short()
                 print(f"[Debug] YT Short ID retrieved: {vid_id} (Type: {type(vid_id)})")
                 if vid_id:
                     print(f"[Action] Playing Short: {vid_id}")
                     
                     # Auto-Duck Playlist
                     if self.vol_playlist > 0.05:
                         self.pre_duck_volume = self.vol_playlist
                         print(f"[AutoDuck] Ducking playlist to 5% (was {self.pre_duck_volume*100:.0f}%)")
                         self.vol_playlist = 0.05
                         if self.current_playlist_sound:
                             try: self.current_playlist_sound.set_volume(self.vol_playlist)
                             except: pass

                     # Broadcast to Overlay
                     print(f"[Debug] Broadcasting YouTubePlay event for {vid_id}")
                     await self.event_server.broadcast("YouTubePlay", {"videoId": vid_id})
                 else:
                     print("[Action] No Short found or cache empty.")
             else:
                 print("[Action] YouTube Bot not loaded.")


        # --- TRIGGER ACTION ---
        elif sa_type == "trigger_action":
            # ... (unchanged) ...
            target_name = config.get('action_name', '')
            found = next((a for a in self.actions if a.get('name') == target_name), None)
            if found:
                 asyncio.create_task(self.execute_action(found, ctx))
            else:
                 print(f"[Action] Trigger target '{target_name}' not found.")

        # --- SET ACTION STATE ---
        elif sa_type == "set_action_state":
            target_name = config.get('action_name', '')
            state = config.get('state', 'toggle') # on, off, toggle
            duration = int(config.get('duration', 0))
            
            target = next((a for a in self.actions if a.get('name') == target_name), None)
            
            if target:
                old_state = target.get('enabled', True)
                new_state = old_state
                
                if state == "on": new_state = True
                elif state == "off": new_state = False
                elif state == "toggle": new_state = not old_state
                
                if self._update_action_state(target_name, new_state):
                    # Duration Timer
                    if duration > 0:
                        async def revert():
                            await asyncio.sleep(duration)
                            self._update_action_state(target_name, old_state)
                            print(f"[Action] Timer expired. Action '{target_name}' reverted.")
                        
                        asyncio.create_task(revert())
            else:
                print(f"[Action] Action '{target_name}' not found.")

        # --- VOLUME CONTROL ---
        elif sa_type == "set_volume":
            target = config.get('target', 'sfx') # sfx or playlist
            mode = config.get('mode', 'set') # set or adjust
            val = float(config.get('value', 0.5))
            
            print(f"[Debug] set_volume triggered: target={target}, mode={mode}, val={val}")

            # Logic helper
            def calc_new_vol(current, m, v):
                if m == 'set': return max(0.0, min(1.0, v))
                else: return max(0.0, min(1.0, current + v))

            if target == 'sfx':
                old = self.vol_sfx
                self.vol_sfx = calc_new_vol(self.vol_sfx, mode, val)
                print(f"[Volume] SFX changed {old:.2f} -> {self.vol_sfx:.2f}")
            elif target == 'playlist':
                old = self.vol_playlist
                self.vol_playlist = calc_new_vol(self.vol_playlist, mode, val)
                print(f"[Volume] Playlist changed {old:.2f} -> {self.vol_playlist:.2f}")
                
                # Apply immediately if playing
                if self.current_playlist_sound:
                    try:
                        self.current_playlist_sound.set_volume(self.vol_playlist)
                        print(f"[Volume] Applied to current track.")
                    except:
                        pass


    async def run_playlist(self, folder, device=None):
        print(f"[Playlist] Starting playlist from {folder} on {device or 'Default'}")
        try:
            while True:
                if not os.path.exists(folder):
                    print(f"[Playlist] Folder not found: {folder}")
                    break
                
                # Scan
                files = [f for f in os.listdir(folder) if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
                if not files:
                    print("[Playlist] No files found.")
                    break
                    
                # Pick Random
                choice = random.choice(files)
                full_path = os.path.join(folder, choice)
                
                # Play & Get Duration
                # For playlist, we assume 100% base volume, scaled by global playlist volume
                duration = await asyncio.to_thread(self.play_sound_get_duration, full_path, device, self.vol_playlist)
                
                # Wait
                await asyncio.sleep(duration)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[Playlist] Error: {e}")

    def play_sound_get_duration(self, path, device=None, volume=1.0):
        try:
            self._ensure_audio_device(device)
            snd = sa.Sound(path)
            snd.set_volume(volume)
            snd.play()
            
            # Store reference for volume control
            self.current_playlist_sound = snd
            
            return snd.get_length()
        except:
            return 0

    def _ensure_audio_device(self, device_name):
        """Initializes mixer with specific device if changed."""
        if device_name is None: return # Keep current
        
        # If device changed or mixer not init
        if not sa.get_init() or self.current_audio_device != device_name:
            if sa.get_init():
                sa.quit()
                print(f"[Audio] Switching device to: {device_name}")
            
            try:
                # 'Default' is a special keyword if user selects it we pass None?
                # Actually SDL2 uses specific names. If user passes 'Default', we might handle it.
                dev = device_name if device_name != 'Default' else None
                sa.init(devicename=dev)
                self.current_audio_device = device_name
            except Exception as e:
                print(f"[Audio] Failed to init device {device_name}: {e}. Fallback to default.")
                sa.init()
                self.current_audio_device = 'Default'

    def replace_vars(self, text, ctx):
        if not isinstance(text, str): return text
        for k, v in ctx.items():
            text = text.replace(f"%{k}%", str(v))
        return text

    def play_sound_sync(self, path, device=None, volume=1.0):
        try:
            print(f"[Debug] play_sound_sync: {os.path.basename(path)} @ {volume:.2f}")
            self._ensure_audio_device(device)
            
            # Use Sound object for SFX (allows overlapping sounds)
            sound = sa.Sound(path)
            sound.set_volume(volume)
            sound.play()
            
            # We don't block here anymore because Sound.play is fire-and-forget
            # This allows multiple sounds to play at once!
            
        except Exception as e:
            print(f"[Sound Error] Failed to play {os.path.basename(path)}: {e}")
            # Hint for the user
            if "mpg123" in str(e) or "unrecognized" in str(e):
                 print("[Hint] The file might be corrupted or renamed incorrectly (e.g. mp3 extension on a wav file). Try converting it.")
