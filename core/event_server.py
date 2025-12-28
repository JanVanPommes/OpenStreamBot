import asyncio
import websockets
import json

class EventServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = set()
        self.message_callbacks = []
        self.internal_listeners = [] # ActionEngine etc.

    def add_message_handler(self, callback):
        print(f"[DEBUG] Handler registriert: {callback}")
        self.message_callbacks.append(callback)

    def add_internal_listener(self, callback):
        self.internal_listeners.append(callback)

    async def register(self, websocket):
        self.clients.add(websocket)
        print(f"[WS] Neuer Client verbunden. Total: {len(self.clients)}")

    async def unregister(self, websocket):
        self.clients.remove(websocket)
        print("[WS] Client getrennt.")

    async def broadcast(self, event_type, data):
        """Sendet Daten an alle verbundenen Clients (OBS/Browser)"""
        if not self.clients:
            return
        
        payload = json.dumps({"event": event_type, "data": data})
        
        # 1. Internal Listeners (Action Engine)
        for listener in self.internal_listeners:
             # Fire and forget (or await if async)
             # Let's assume listeners are async for now or we wrap them
             if asyncio.iscoroutinefunction(listener):
                 asyncio.create_task(listener(event_type, data))
             else:
                 listener(event_type, data)

        # 2. WebSocket Clients
        if self.clients:
            await asyncio.gather(*[client.send(payload) for client in self.clients], return_exceptions=True)

    async def handler(self, websocket): # 'path' Argument entfernt für neuere websockets versionen
        await self.register(websocket)
        try:
            async for message in websocket:
                # Hier können wir später Befehle VOM Overlay empfangen
                # print(f"[WS Empfangen]: {message}")
                for callback in self.message_callbacks:
                    await callback(message)
        except:
            pass
        finally:
            await self.unregister(websocket)

    async def start(self):
        print(f"[System] WebSocket Server startet auf ws://{self.host}:{self.port}")
        async with websockets.serve(self.handler, self.host, self.port):
            await asyncio.Future() # Hält den Server am Leben
