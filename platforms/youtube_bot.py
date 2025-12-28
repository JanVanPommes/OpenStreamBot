import asyncio
import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import datetime

# Scopes für YouTube Chat
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly', 'https://www.googleapis.com/auth/youtube.force-ssl']

class YouTubeBot:
    def __init__(self, config, event_server):
        self.config = config
        self.event_server = event_server
        self.creds = None
        self.youtube = None
        self.live_chat_id = None
        self.next_page_token = None
        self.next_page_token = None
        self.polling_task = None
        self.is_running = False
        
        # Register Handler
        print(f"[DEBUG] YouTubeBot Init - Registering Handler")
        self.event_server.add_message_handler(self.on_dashboard_message)

    async def authenticate(self):
        token_file = self.config.get('token_file', 'token_youtube.json')
        client_secret = self.config.get('client_secret_file', 'client_secret.json')

        # 1. Existierende Credentials laden
        if os.path.exists(token_file):
            try:
                self.creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            except Exception as e:
                print(f"[YouTube] Fehler beim Laden des Tokens: {e}")

        # 2. Login, wenn ungültig oder nicht vorhanden
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    print("[YouTube] Token abgelaufen, aktualisiere...")
                    self.creds.refresh(Request())
                except:
                    print("[YouTube] Token Refresh fehlgeschlagen.")
                    self.creds = None
            
            if not self.creds:
                if not os.path.exists(client_secret):
                    print(f"[YouTube] FEHLER: {client_secret} fehlt! Kein Login möglich.")
                    return False
                
                print("[YouTube] Starte Browser-Login...")
                flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
                # Run local server to catch the callback
                try:
                    # Hinweis: run_local_server blockiert, daher in Executor auslagern wenn in Async Loop
                     # Aber hier sind wir initial, das ist okay. 
                    self.creds = await asyncio.to_thread(flow.run_local_server, port=0)
                except Exception as e:
                     print(f"[YouTube] Login fehlgeschlagen: {e}")
                     return False

            # Token speichern
            with open(token_file, 'w') as token:
                token.write(self.creds.to_json())
        
        # 3. Service bauen
        self.youtube = build('youtube', 'v3', credentials=self.creds)
        print("[YouTube] Authentifizierung erfolgreich!")
        return True

    async def find_active_broadcast(self):
        """Sucht nach einem aktiven Livestream des eingeloggten Users"""
        try:
            print("[YouTube] Suche nach aktivem Stream...")
            req = self.youtube.liveBroadcasts().list(
                part="id,snippet,status",
                broadcastStatus="active", # Suche nur nach aktiven Streams
                broadcastType="all"
            )
            resp = await asyncio.to_thread(req.execute)
            
            items = resp.get("items", [])
            if not items:
                print("[YouTube] Kein aktiver Stream gefunden. Polling pausiert.")
                return None

            broadcast = items[0]
            chat_id = broadcast['snippet']['liveChatId']
            print(f"[YouTube] Live Stream gefunden: {broadcast['snippet']['title']} (Chat ID: {chat_id})")
            return chat_id
            
        except Exception as e:
            print(f"[YouTube] Fehler bei der Stream-Suche: {e}")
            if "quotaExceeded" in str(e):
                 print("[YouTube] QUOTA EXCEEDED during stream search. Waiting 1 hour...")
                 await asyncio.sleep(3600)
            return None

    async def poll_chat(self):
        """Fragt regelmäßig neue Nachrichten ab"""
        print("[YouTube] Chat-Polling gestartet.")
        while self.is_running and self.live_chat_id:
            try:
                req = self.youtube.liveChatMessages().list(
                    liveChatId=self.live_chat_id,
                    part="id,snippet,authorDetails",
                    pageToken=self.next_page_token,
                    maxResults=50 # Max messages per poll
                )
                resp = await asyncio.to_thread(req.execute)
                
                self.next_page_token = resp.get('nextPageToken')
                polling_interval = resp.get('pollingIntervalMillis', 5000) / 1000.0
                
                # Nachrichten verarbeiten
                items = resp.get('items', [])
                for item in items:
                    await self.handle_message(item)
                
                await asyncio.sleep(polling_interval)
                
            except Exception as e:
                err_str = str(e)
                wait_time = 10
                
                if "quotaExceeded" in err_str:
                    print("[YouTube] CRITICAL: Quota Exceeded! Pausiere für 1 Stunde.")
                    wait_time = 3600 # 1 Hour
                    self.live_chat_id = None # Stop polling current chat to be safe
                else:
                    print(f"[YouTube] Polling Error: {e}")
                
                await asyncio.sleep(wait_time)

    async def handle_message(self, item):
        try:
            author = item['authorDetails']['displayName']
            msg = item['snippet']['displayMessage']
            
            # Timestamp konvertieren
            # yt format: 2023-10-27T10:00:00.000Z
            
            # Badge Logik (Simpel): Ist es der Owner?
            is_owner = item['authorDetails'].get('isChatOwner', False)
            is_mod = item['authorDetails'].get('isChatModerator', False)
            
            # Custom Color (YT hat keine User Colors, wir nehmen rot für YT)
            color = "#ff0000" 
            
            badges = []
            if is_owner: badges.append({"id": "broadcaster", "version": "1"})
            if is_mod: badges.append({"id": "moderator", "version": "1"})
            
            chat_data = {
                "platform": "youtube",
                "user": author,
                "message": msg,
                "is_mod": is_mod or is_owner,
                "color": color, # Fallback Farbe für YT
                "timestamp": str(datetime.datetime.now()), # oder echtes Datum parsen
                "emotes": [], # YT Emotes parsen ist komplexer, erst mal raw text
                "badges": badges
            }
            
            # An Dashboard senden
            await self.event_server.broadcast("ChatMessage", chat_data)
            print(f"[YouTube] {author}: {msg}")
            
            # --- COMMAND TRIGGER ---
            if msg.startswith('!'):
                cmd_name = msg.split(' ')[0]
                await self.event_server.broadcast("CommandTriggered", {
                    "command": cmd_name,
                    "user": author,
                    "message": msg,
                    "platform": "youtube"
                })
            
        except Exception as e:
            print(f"[YouTube] Parse Error: {e}")

    async def start(self):
        self.is_running = True
        
        # 1. Login
        if not await self.authenticate():
            print("[YouTube] Start abgebrochen.")
            return

        # 2. Stream suchen
        while self.is_running:
            chat_id = await self.find_active_broadcast()
            if chat_id:
                self.live_chat_id = chat_id
                # Starte Polling Loop
                await self.poll_chat()
                # Wenn poll_chat returned, ist der Stream wohl vorbei oder Error
                self.live_chat_id = None
            
            # Wartezeit vor nächstem Check ob Stream online ist
            print("[YouTube] Warte 60s bis zum nächsten Stream-Check...")
            
            # Use smaller steps to allow faster interrupt
            for _ in range(60):
                if not self.is_running: break
                await asyncio.sleep(1)
            
            # If we encountered a critical error (like quota) logic inside find_active_broadcast 
            # or poll_chat should ideally help delay this, but for now 60s is standard.
            # However, if find_active_broadcast failed heavily, we might want to backoff there too.
                
    async def stop(self):
        self.is_running = False

    async def on_dashboard_message(self, raw_data):
        """Reagiert auf Nachrichten vom Dashboard (send_chat)"""
        try:
            data = json.loads(raw_data)
            action = data.get("action")
            
            if action == "send_chat":
                msg = data.get("message")
                # Nur senden, wenn wir verbunden sind und eine Chat ID haben
                if msg and self.live_chat_id:
                    await self.send_chat_message(msg)

        except Exception as e:
            print(f"[YouTube Error] on_dashboard_message: {e}")

    async def send_chat_message(self, message_text):
        """Sendet eine Nachricht an den YouTube Chat"""
        try:
            body = {
                "snippet": {
                    "liveChatId": self.live_chat_id,
                    "type": "textMessageEvent",
                    "textMessageDetails": {
                        "messageText": message_text
                    }
                }
            }
            req = self.youtube.liveChatMessages().insert(
                part="snippet",
                body=body
            )
            # Execute in thread to avoid blocking loop
            await asyncio.to_thread(req.execute)
            print(f"[YouTube -> Chat] {message_text}")
        except Exception as e:
            print(f"[YouTube] Fehler beim Senden: {e}")
