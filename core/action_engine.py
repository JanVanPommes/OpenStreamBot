import yaml
import os
import json
import asyncio
import logging
import pygame.mixer as sa # alias to keep code similar or just rename
import time
import random
import pygame._sdl2.audio as sdl_audio

# Absolute path to queue status JSON
import sys
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE_STATUS_FILE = os.path.join(BASE_DIR, ".queue_status.json")

# Logging setup
logger = logging.getLogger("ActionEngine")

class ActionEngine:
    def __init__(self, config_file="actions.yaml", event_server=None, obs_controller=None, twitch_bot=None, youtube_bot=None, elevenlabs_tts=None):
        self.config_file = config_file
        self.event_server = event_server
        self.obs = obs_controller
        self.twitch = twitch_bot
        self.youtube = youtube_bot
        self.elevenlabs = elevenlabs_tts
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

        # Action Queues (Multi-Queue Architecture)
        self.queues = {}
        self.queue_tasks = {}
        self.queue_configs = {}
        self.queue_status = {}
        self._load_persisted_queue_status()
        self.get_or_create_queue("Default")

        self.load_actions()

    def _load_persisted_queue_status(self):
        """Loads historical queue status from disk so last_action persists across restarts."""
        if os.path.exists(QUEUE_STATUS_FILE):
            try:
                with open(QUEUE_STATUS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for q_name, stat in data.items():
                            if isinstance(stat, dict):
                                self.queue_status[q_name] = {
                                    "current_action": None,
                                    "last_action": stat.get("last_action"),
                                    "last_executed_at": stat.get("last_executed_at"),
                                    "pending": 0,
                                    "status": "Idle"
                                }
            except Exception as e:
                print(f"[ActionEngine] Error reading initial queue status: {e}")

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
            elif event == "trigger_action_by_name":
                payload = data.get("data", {})
                a_name = payload.get("action")
                if a_name:
                    print(f"[ActionEngine] External trigger requested for action: {a_name}")
                    for action in self.actions:
                        if action.get('name') == a_name and action.get('enabled', True):
                            # Execute without context, since it's a manual trigger
                            asyncio.create_task(self.execute_action(action, {}))
                            break
                
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
             elif data.get("type") == "twitch_first_message": mapped_type = "twitch_first_message"
             elif data.get("type") == "youtube_first_message": mapped_type = "youtube_first_message"
             elif data.get("type") == "twitch_watch_streak": mapped_type = "twitch_watch_streak"
             elif data.get("type") == "youtube_new_member": mapped_type = "youtube_new_member"
             elif data.get("type") == "youtube_member_milestone": mapped_type = "youtube_member_milestone"
             elif data.get("type") == "youtube_super_chat": mapped_type = "youtube_super_chat"
        elif event_type == "TwitchRedemption":
            mapped_type = "twitch_redemption"
        
        # Check Type
        if trigger_config.get('type') != mapped_type:
            return False, {}
            
        # --- BLACKLIST CHECK ---
        blacklist_raw = trigger_config.get('blacklist_users', '').strip()
        if blacklist_raw:
            bl_users = [u.strip().lower() for u in blacklist_raw.split(',') if u.strip()]
            user = data.get('user', '')
            if not user and 'author' in data: user = data['author']
            
            if user and user.lower() in bl_users:
                print(f"[ActionEngine] Trigger '{mapped_type}' blocked for blacklisted user: {user}")
                return False, {}
            
        # Condition Check
        
        # --- REDEMPTION ---
        if mapped_type == "twitch_redemption":
            req_title = trigger_config.get('reward_title', '').lower()
            evt_title = data.get('reward_title', '').lower()
            
            if req_title == evt_title:
                msg = data.get('input', '')
                return True, {
                    "user": data.get('user', ''),
                    "input": msg,
                    "message": msg
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

                # --- Shared Chat Check ---
                ignore_shared = trigger_config.get('ignore_shared_chat', False)
                if ignore_shared and data.get('is_shared', False):
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
        elif mapped_type == "obs_scene":
            scene = trigger_config.get('scene_name', '')
            if scene and scene != data.get('scene_name'):
                return False, {}
                
        # 4. First Words
        elif mapped_type in ["twitch_first_message", "youtube_first_message"]:
             # Optional: Filter by user?
             target_user = trigger_config.get('user', '').lower()
             if target_user and target_user != data.get('user', '').lower():
                 return False, {}
                 
             return True, {
                 "user": data.get('user', ''),
                 "message": data.get('message', '')
             }

        # 5. Twitch Watch Streak (exact match, 0 = all)
        elif mapped_type == "twitch_watch_streak":
             target_streak = trigger_config.get('streak_value', 0)
             streak_count = data.get('streak_count', 0)
             if target_streak and target_streak != streak_count:
                 return False, {}
             return True, {
                 "user": data.get('user', ''),
                 "message": data.get('message', ''),
                 "streak_count": str(streak_count)
             }

        # 6. YouTube New Member
        elif mapped_type == "youtube_new_member":
             return True, {
                 "user": data.get('user', ''),
                 "message": data.get('message', '')
             }

        # 7. YouTube Member Milestone (min_months filter, 0 = all)
        elif mapped_type == "youtube_member_milestone":
             min_months = trigger_config.get('min_months', 0)
             months = data.get('months', 0)
             if min_months and months < min_months:
                 return False, {}
             return True, {
                 "user": data.get('user', ''),
                 "message": data.get('message', ''),
                 "months": str(months),
                 "user_message": data.get('user_message', '')
             }

        # 8. YouTube Super Chat (min_amount filter in micros, 0 = all)
        elif mapped_type == "youtube_super_chat":
             min_amount = trigger_config.get('min_amount', 0)
             amount_micros = data.get('amount_micros', 0)
             # min_amount is in whole units (e.g. 5 = 5 EUR), micros = 5000000
             if min_amount and amount_micros < (min_amount * 1000000):
                 return False, {}
             return True, {
                 "user": data.get('user', ''),
                 "message": data.get('message', ''),
                 "amount": data.get('amount_display', '?'),
                 "currency": data.get('currency', 'EUR'),
                 "user_message": data.get('user_message', '')
             }

        return True, {}

    def get_queue_config(self, queue_name="Default"):
        """Returns configuration dictionary for a given queue."""
        q_name = queue_name or "Default"
        if q_name not in self.queue_configs:
            self.queue_configs[q_name] = {"delay": 0.0, "paused": False, "mode": "sequential"}
        return self.queue_configs[q_name]

    def set_queue_config(self, queue_name="Default", delay=None, paused=None, mode=None):
        """Updates settings for a queue."""
        cfg = self.get_queue_config(queue_name)
        if delay is not None:
            cfg["delay"] = max(0.0, float(delay))
        if paused is not None:
            cfg["paused"] = bool(paused)
        if mode is not None:
            cfg["mode"] = str(mode)
        print(f"[ActionEngine] Updated Queue '{queue_name}' config: {cfg}")
        self.save_queue_status_file()
        return cfg

    def clear_queue(self, queue_name="Default"):
        """Clears all pending items in a queue."""
        if queue_name in self.queues:
            q = self.queues[queue_name]
            cleared = 0
            while not q.empty():
                try:
                    q.get_nowait()
                    q.task_done()
                    cleared += 1
                except asyncio.QueueEmpty:
                    break
            print(f"[ActionEngine] Cleared {cleared} pending items from Queue '{queue_name}'.")
            self.save_queue_status_file()

    def save_queue_status_file(self):
        """Persists current queue status snapshot to disk atomically for launcher UI sync across processes."""
        try:
            status_data = self.get_all_queues_status()
            tmp_file = QUEUE_STATUS_FILE + '.tmp'
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, QUEUE_STATUS_FILE)
        except Exception as e:
            print(f"[ActionEngine] Error saving queue status file: {e}")

    def get_all_queues_status(self):
        """Returns snapshot of all queue states and configs."""
        res = {}
        # Ensure Parallel is represented if tracked
        all_q_names = set(self.queues.keys()).union(set(self.queue_status.keys()))
        for q_name in sorted(all_q_names):
            q = self.queues.get(q_name)
            pending_count = q.qsize() if q else 0
            cfg = self.get_queue_config(q_name)
            stat = self.queue_status.get(q_name, {})
            res[q_name] = {
                "name": q_name,
                "pending": pending_count,
                "current_action": stat.get("current_action"),
                "last_action": stat.get("last_action"),
                "last_executed_at": stat.get("last_executed_at"),
                "status": "Paused" if cfg.get("paused") else stat.get("status", "Idle"),
                "paused": cfg.get("paused", False),
                "delay": cfg.get("delay", 0.0),
                "mode": cfg.get("mode", "sequential")
            }
        return res

    def get_or_create_queue(self, queue_name="Default"):
        """Gets existing asyncio.Queue for queue_name or initializes a new worker task for it."""
        q_name = queue_name or "Default"
        if q_name not in self.queues:
            q = asyncio.Queue()
            self.queues[q_name] = q
            self.queue_configs[q_name] = {"delay": 0.0, "paused": False, "mode": "sequential"}
            if q_name not in self.queue_status:
                self.queue_status[q_name] = {"current_action": None, "last_action": None, "pending": 0, "status": "Idle"}
            else:
                self.queue_status[q_name]["status"] = "Idle"
                self.queue_status[q_name]["current_action"] = None
                self.queue_status[q_name]["pending"] = 0
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(self.action_queue_worker(q_name, q))
                self.queue_tasks[q_name] = task
            except RuntimeError:
                pass
            print(f"[ActionEngine] Initialized Action Queue: '{q_name}'")
            self.save_queue_status_file()
        return self.queues[q_name]

    async def action_queue_worker(self, queue_name, queue_obj):
        """Worker task processing queued actions for a specific queue."""
        while True:
            # Check pause status
            cfg = self.get_queue_config(queue_name)
            while cfg.get("paused", False):
                await asyncio.sleep(0.2)
                cfg = self.get_queue_config(queue_name)

            action, context_data = await queue_obj.get()
            act_name = action.get('name', 'Unknown')
            import time
            now_ts = time.time()
            
            # Update status
            self.queue_status[queue_name] = {
                "current_action": act_name,
                "last_action": act_name,
                "last_executed_at": now_ts,
                "pending": queue_obj.qsize(),
                "status": "Running"
            }
            self.save_queue_status_file()

            try:
                print(f"[Action Queue:{queue_name}] Executing action: {act_name}")
                await self._execute_action_blocking(action, context_data)
            except Exception as e:
                print(f"[Action Queue:{queue_name}] Error: {e}")
            finally:
                queue_obj.task_done()

            # Apply queue delay if configured
            delay = cfg.get("delay", 0.0)
            if delay > 0:
                await asyncio.sleep(delay)

            # Reset status if empty
            if queue_obj.empty():
                self.queue_status[queue_name] = {
                    "current_action": None,
                    "last_action": act_name,
                    "last_executed_at": now_ts,
                    "pending": 0,
                    "status": "Idle"
                }
                self.save_queue_status_file()

    async def execute_action(self, action, context_data):
        """Dispatches an action to its assigned queue or executes in parallel."""
        queue_name = action.get('queue', 'Default') or 'Default'
        
        # Parallel / async queue bypasses sequential queueing
        if queue_name.lower() in ["parallel", "async", "none"]:
            act_name = action.get('name', 'Unknown')
            import time
            now_ts = time.time()
            self.queue_status["Parallel"] = {
                "current_action": act_name,
                "last_action": act_name,
                "last_executed_at": now_ts,
                "pending": 0,
                "status": "Running"
            }
            self.save_queue_status_file()
            async def _run_par():
                try:
                    await self._execute_action_blocking(action, context_data)
                finally:
                    self.queue_status["Parallel"] = {
                        "current_action": None,
                        "last_action": act_name,
                        "last_executed_at": now_ts,
                        "pending": 0,
                        "status": "Idle"
                    }
                    self.save_queue_status_file()
            asyncio.create_task(_run_par())
            return

        queue_obj = self.get_or_create_queue(queue_name)
        await queue_obj.put((action, context_data))
        self.save_queue_status_file()

    async def _execute_action_blocking(self, action, context_data):
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
        
        # --- PROBABILITY CHECK ---
        probability = float(config.get('probability', 1.0))
        if probability < 1.0:
            roll = random.random() # 0.0 to 1.0
            if roll > probability:
                print(f"[ActionEngine] Skipping sub-action {sa_type} (Prob: {probability}, Roll: {roll:.2f})")
                return

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

        elif sa_type == "youtube_chat":
            msg_raw = config.get('message', '')
            msg = self.replace_vars(msg_raw, ctx)
            if self.youtube:
                await self.youtube.send_chat_message(msg)

        elif sa_type == "twitch_command":
            if self.twitch and self.twitch.connected_channels:
                cmd = config.get('command', 'Announce')
                target = self.replace_vars(config.get('target', ''), ctx).strip('@')
                message = self.replace_vars(config.get('message', ''), ctx)
                channel = self.twitch.connected_channels[0]
                
                try:
                    if cmd == "Announce":
                        await self.twitch.execute_announcement(message)
                    elif cmd == "Shoutout":
                        await self.twitch.execute_shoutout(target)
                    elif cmd == "Ban":
                        await self.twitch.execute_ban(target, message)
                    elif cmd == "Timeout":
                        duration = 600
                        try: duration = int(message)
                        except: pass
                        await self.twitch.execute_timeout(target, duration, message)
                    elif cmd == "VIP":
                        await self.twitch.execute_vip(target)
                    elif cmd == "Un-VIP":
                        await self.twitch.execute_unvip(target)
                    elif cmd == "Commercial":
                        duration = 30
                        try: duration = int(message)
                        except: pass
                        await self.twitch.execute_commercial(duration)
                    else:
                        print(f"[ActionEngine] Unknown Twitch Command: {cmd}")
                except Exception as e:
                    print(f"[ActionEngine] Error executing Twitch Command {cmd}: {e}")

        # --- TWITCH CLIPS ---
        elif sa_type == "twitch_create_clip":
            if self.twitch:
                print("[ActionEngine] Creating Twitch Clip...")
                clip_url = await self.twitch.create_clip()
                if clip_url:
                    # Optional: Post link to chat if requested
                    if config.get('post_to_chat', True):
                         msg = f"Clip erstellt: {clip_url}"
                         if self.twitch.connected_channels:
                             await self.twitch.connected_channels[0].send(msg)
            else:
                print("[ActionEngine] Twitch Bot not available for clip creation.")

        # --- TWITCH REWARD STATE ---
        elif sa_type in ["twitch_enable_reward", "twitch_disable_reward"]:
            if self.twitch:
                reward_title = self.replace_vars(config.get('reward_title', ''), ctx)
                is_enabled = (sa_type == "twitch_enable_reward")
                if reward_title:
                    print(f"[ActionEngine] Setze Reward-Status für '{reward_title}' auf {is_enabled}")
                    await self.twitch.set_reward_state_by_title(reward_title, is_enabled)
            else:
                print("[ActionEngine] Twitch Bot nicht verfügbar für Reward-Statusänderung.")

        # --- OBS ---
        elif sa_type == "obs_set_scene":
            scene = self.replace_vars(config.get('scene', ''), ctx)
            if self.obs:
                await self.obs.set_scene(scene)

        elif sa_type.startswith("obs_"):
            # Generic OBS delegation if possible, or specific handlers
            pass
            
        # --- C# EXECUTION (CLI RUNNER) ---
        elif sa_type == "execute_csharp":
             import subprocess
             import tempfile
             
             path = self.replace_vars(config.get('path', ''), ctx)
             code = self.replace_vars(config.get('code', ''), ctx)
             mode = config.get('csharp_mode', 'File')
             args_str = self.replace_vars(config.get('args', ''), ctx)
             
             cleanup_file = None
             
             if mode == 'Code' and code.strip():
                 # Write to temp file
                 try:
                     fd, tmp_path = tempfile.mkstemp(suffix=".csx", text=True)
                     with os.fdopen(fd, 'w') as f:
                         f.write(code)
                     path = tmp_path
                     cleanup_file = path
                     print(f"[ActionEngine] Created temp script: {path}")
                 except Exception as e:
                     print(f"[ActionEngine] Failed to create temp script: {e}")
                     return

             if not path or not os.path.exists(path):
                 print(f"[ActionEngine] C# Error: Path not found: {path}")
                 if cleanup_file: os.remove(cleanup_file)
                 return

             cmd = []
             
             # Detect Type
             if path.endswith('.csproj'):
                 # Project -> dotnet run
                 cmd = ["dotnet", "run", "--project", path]
                 # Valid args for app come after --
                 if args_str:
                     cmd.append("--")
                     cmd.extend(args_str.split(' '))
                     
             elif path.endswith('.csx'):
                 # Script -> dotnet script
                 cmd = ["dotnet", "script", path]
                 if args_str:
                     cmd.append("--")
                     cmd.extend(args_str.split(' '))
                     
             else:
                 # Raw Executable or Unknown -> Try direct execution
                 cmd = [path]
                 if args_str:
                     cmd.extend(args_str.split(' '))
            
             print(f"[ActionEngine] Executing C#: {' '.join(cmd)}")
             
             try:
                 # Check for dotnet tools in PATH
                 env = os.environ.copy()
                 # Add default dotnet global tools path for Linux/Mac
                 dotnet_tools = os.path.expanduser("~/.dotnet/tools")
                 if dotnet_tools not in env.get("PATH", ""):
                     env["PATH"] = f"{env.get('PATH', '')}:{dotnet_tools}"

                 # Run async to not block bot? 
                 # subprocess.run is blocking. create_subprocess_exec is async.
                 proc = await asyncio.create_subprocess_exec(
                     *cmd,
                     stdout=asyncio.subprocess.PIPE,
                     stderr=asyncio.subprocess.PIPE,
                     env=env
                 )
                 
                 stdout, stderr = await proc.communicate()
                 
                 if stdout:
                     decoded = stdout.decode().strip()
                     print(f"[C# Output] {decoded}")
                     # Parse for "SetVar: key=value"
                     for line in decoded.split('\n'):
                         if line.startswith("SetVar:"):
                             try:
                                 # Format: SetVar: key=value
                                 parts = line.split(':', 1)[1].split('=', 1)
                                 if len(parts) == 2:
                                     key = parts[0].strip()
                                     val = parts[1].strip()
                                     ctx[key] = val
                                     print(f"[ActionEngine] Captured Variable: {key}={val}")
                             except Exception as e:
                                 print(f"[ActionEngine] Parse Error: {e}")
                 if stderr:
                     print(f"[C# Error] {stderr.decode().strip()}")
                     
             except FileNotFoundError:
                 print(f"[ActionEngine] C# Error: Command not found (dotnet installed?).")
             except Exception as e:
                 print(f"[ActionEngine] C# Execution Failed: {e}")
             finally:
                 if cleanup_file and os.path.exists(cleanup_file):
                     try:
                         os.remove(cleanup_file)
                     except: pass
        # --- MEDIA ---
        elif sa_type == "play_sound":
            file_path = self.replace_vars(config.get('file', ''), ctx)
            device = config.get('device', None)
            base_vol = float(config.get('volume', 100)) / 100.0 # 0-100 logic
            
            final_vol = self.vol_sfx * base_vol
            
            if os.path.exists(file_path):
                 duration = await asyncio.to_thread(self.play_sound_sync, file_path, device, final_vol)
                 if duration and duration > 0:
                     await asyncio.sleep(duration + 0.1) # Queue blocking
            else:
                print(f"[ActionError] Sound file not found: {file_path}")

        elif sa_type == "elevenlabs_tts":
            if self.elevenlabs:
                text = self.replace_vars(config.get('text', ''), ctx)
                voice_id = self.replace_vars(config.get('voice_id', ''), ctx)
                device = config.get('device', None)
                base_vol = float(config.get('volume', 100)) / 100.0
                
                final_vol = self.vol_sfx * base_vol
                
                print(f"[ActionEngine] Generating TTS for: {text}")
                path = await self.elevenlabs.generate_tts(text, voice_id)
                
                if path and os.path.exists(path):
                     # Getting duration and playing
                     duration = await asyncio.to_thread(self.play_sound_sync, path, device, final_vol)
                     
                     # Async cleanup task
                     async def cleanup():
                          await asyncio.sleep(2.0) # Wait a bit extra before delete
                          try:
                              os.remove(path)
                              print(f"[ActionEngine] Deleted TTS temp file: {path}")
                          except Exception as e:
                              print(f"[ActionEngine] Failed to delete TTS file: {e}")
                     asyncio.create_task(cleanup())
                     
                     if duration and duration > 0:
                         await asyncio.sleep(duration + 0.1) # Queue blocking
                else:
                     print("[ActionError] Failed to generate TTS audio.")
            else:
                print("[ActionError] Elevenlabs TTS not configured/enabled.")

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



        # --- RANDOM ACTION GROUP ---
        elif sa_type == "random_action_group":
            targets = config.get('targets', [])
            if not targets: return
            
            roll = random.uniform(0, 100)
            cumulative = 0.0
            
            for t in targets:
                weight = float(t.get('weight', 0))
                if weight <= 0: continue
                cumulative += weight
                if roll <= cumulative:
                    sub_action_data = t.get('action')
                    if sub_action_data:
                        nested_type = sub_action_data.get('type', 'Unknown')
                        print(f"[ActionEngine] Randomly selected '{nested_type}' from group (Weight: {weight}%)")
                        asyncio.create_task(self.execute_sub_action(sub_action_data, ctx))
                    else:
                        print(f"[ActionEngine] Random target action missing.")
                    break

        # --- TRIGGER ACTION ---
        elif sa_type == "trigger_action":
            # ... (unchanged) ...
            target_name = config.get('action_name', '')
            found = next((a for a in self.actions if a.get('name') == target_name), None)
            if found:
                 target_ctx = ctx.copy()
                 custom_vars = config.get('variables')
                 if isinstance(custom_vars, dict):
                     for k, v in custom_vars.items():
                         target_ctx[k] = self.replace_vars(v, ctx)
                 
                 v_name = config.get('var_name', '').strip()
                 v_value = config.get('var_value', '')
                 if v_name:
                     target_ctx[v_name] = self.replace_vars(v_value, ctx)
                     
                 asyncio.create_task(self.execute_action(found, target_ctx))
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
            return sound.get_length()
            
        except Exception as e:
            print(f"[Sound Error] Failed to play {os.path.basename(path)}: {e}")
            # Hint for the user
            if "mpg123" in str(e) or "unrecognized" in str(e):
                 print("[Hint] The file might be corrupted or renamed incorrectly (e.g. mp3 extension on a wav file). Try converting it.")
            return 0.0
