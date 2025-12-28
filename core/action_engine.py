import yaml
import os
import asyncio
import logging
import pygame.mixer as sa # alias to keep code similar or just rename
import time

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
        
        self.load_actions()

    def load_actions(self):
        if not os.path.exists(self.config_file):
            self.actions = []
            return

        with open(self.config_file, 'r') as f:
            data = yaml.safe_load(f) or {}
            self.actions = data.get('actions', [])
        
        print(f"[ActionEngine] Loaded {len(self.actions)} actions.")

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
        for action in self.actions:
            if not action.get('enabled', True):
                continue
                
            triggers = action.get('triggers', [])
            for trigger in triggers:
                if self.check_trigger(trigger, event_type, data):
                    print(f"[ActionEngine] Trigger fired: {action['name']} (Event: {event_type})")
                    # Execute async
                    asyncio.create_task(self.execute_action(action, data))
                    break # One trigger per action is enough

    def check_trigger(self, trigger_config, event_type, data):
        # MAPPING: EventServer events -> Action triggers
        mapped_type = event_type
        
        if event_type == "CommandTriggered":
            mapped_type = "twitch_command"
        elif event_type == "SystemEvent":
             if data.get("type") == "raid": mapped_type = "twitch_raid"
             elif data.get("type") == "sub": mapped_type = "twitch_sub"
        
        # Check Type
        if trigger_config.get('type') != mapped_type:
            return False
            
        # Condition Check
        if mapped_type == "twitch_command": # Use mapped_type instead of event_type
            cmd = trigger_config.get('command', '').lower()
            if cmd and cmd != data.get('command', '').lower():
                return False
                
        # 2. Twitch Raid (Min Viewers)
        elif event_type == "twitch_raid":
            min_v = trigger_config.get('min_viewers', 0)
            if data.get('viewers', 0) < min_v:
                return False
                
        # 3. OBS Scene Changed
        elif event_type == "obs_scene":
            scene = trigger_config.get('scene_name', '')
            if scene and scene != data.get('scene_name'):
                return False

        return True

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
            msg = self.replace_vars(config.get('message', ''), ctx)
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
            if os.path.exists(file_path):
                 # Run in thread to not block loop
                 await asyncio.to_thread(self.play_sound_sync, file_path)
            else:
                print(f"[ActionError] Sound file not found: {file_path}")

        elif sa_type == "stop_sounds":
            if sa.get_init():
                sa.stop() # Stops all playback on all channels
                print("[Action] Stopped all sounds.")

    def replace_vars(self, text, ctx):
        if not isinstance(text, str): return text
        for k, v in ctx.items():
            text = text.replace(f"%{k}%", str(v))
        return text

    def play_sound_sync(self, path):
        try:
            if not sa.get_init():
                sa.init()
            
            # Use Sound object for SFX (allows overlapping sounds)
            sound = sa.Sound(path)
            sound.play()
            
            # We don't block here anymore because Sound.play is fire-and-forget
            # This allows multiple sounds to play at once!
            
        except Exception as e:
            print(f"[Sound Error] Failed to play {os.path.basename(path)}: {e}")
            # Hint for the user
            if "mpg123" in str(e) or "unrecognized" in str(e):
                 print("[Hint] The file might be corrupted or renamed incorrectly (e.g. mp3 extension on a wav file). Try converting it.")
