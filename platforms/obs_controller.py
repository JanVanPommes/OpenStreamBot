import obsws_python as obs
import asyncio
import threading

class OBSController:
    def __init__(self, config, event_server=None, action_engine=None):
        self.config = config
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 4455)
        self.password = config.get('password', '')
        self.event_server = event_server
        self.action_engine = action_engine
        
        self.client = None
        self.is_connected = False
        self.loop = asyncio.get_event_loop()

    def connect(self):
        try:
            # Standard Request Client
            self.client = obs.ReqClient(host=self.host, port=self.port, password=self.password)
            self.is_connected = True
            print(f"[OBS] Connected to {self.host}:{self.port}")
            
            # Add Event Client for Triggers in separate thread
            self.event_thread = threading.Thread(target=self._run_event_client, daemon=True)
            self.event_thread.start()
            
        except Exception as e:
            print(f"[OBS] Connection failed: {e}")
            self.is_connected = False

    def _run_event_client(self):
        """Internal method to run EventClient in a thread"""
        print(f"[OBS Event] Thread started, connecting to {self.host}:{self.port}...")
        
        class OBSEventHandler:
            def __init__(self, controller):
                self.controller = controller
            
            def trigger(self, event_type, data):
                """Generic trigger method called by obsws-python"""
                try:
                    # event_type is a string like 'CurrentProgramSceneChanged'
                    # data is a dictionary in newest versions or an object in others
                    if event_type == 'CurrentProgramSceneChanged':
                        # Try both dict and attribute access
                        scene_name = None
                        if isinstance(data, dict):
                            scene_name = data.get('sceneName')
                        else:
                            scene_name = getattr(data, 'scene_name', None)
                        
                        if scene_name:
                            print(f"[OBS Event] Scene changed to: {scene_name}")
                            if self.controller.action_engine:
                                asyncio.run_coroutine_threadsafe(
                                    self.controller.action_engine.handle_event("obs_scene", {"scene_name": scene_name}),
                                    self.controller.loop
                                )
                except Exception as e:
                    print(f"[OBS Event Callback Error] {e}")

        try:
            # Note: EventClient needs same connection details
            with obs.EventClient(host=self.host, port=self.port, password=self.password) as event_client:
                print(f"[OBS Event] Connected to Event Stream.")
                event_client.callback = OBSEventHandler(self)
                
                # Keep thread alive as long as connected
                while self.is_connected:
                    import time
                    time.sleep(1)
                
        except Exception as e:
            print(f"[OBS Event] Error in event client: {e}")
            import traceback
            traceback.print_exc()

    async def set_scene(self, scene_name):
        if not self.is_connected: return
        try:
            # Run in thread because obs-websocket-py is sync
            await asyncio.to_thread(self.client.set_current_program_scene, scene_name)
            print(f"[OBS] Switched to scene: {scene_name}")
        except Exception as e:
            print(f"[OBS] Error setting scene: {e}")

    async def set_source_visibility(self, scene_name, source_name, visible):
        if not self.is_connected: return
        try:
            # Note: obs-websocket-py syntax check needed for GetSceneItemId
            # 5.x requires id
            item_id = await self.get_scene_item_id(scene_name, source_name)
            if item_id:
                 await asyncio.to_thread(self.client.set_scene_item_enabled, scene_name, item_id, visible)
        except Exception as e:
            print(f"[OBS] Error setting visibility: {e}")

    async def get_scene_item_id(self, scene_name, source_name):
        try:
            resp = await asyncio.to_thread(self.client.get_scene_item_list, scene_name)
            for item in resp.scene_items:
                if item['sourceName'] == source_name:
                    return item['sceneItemId']
        except:
            pass
        return None

    def get_scene_list(self):
        if not self.is_connected: return []
        try:
            resp = self.client.get_scene_list()
            # return array of scene names
            return [s['sceneName'] for s in resp.scenes]
        except Exception as e:
            print(f"[OBS] GetSceneList Error: {e}")
            return []
