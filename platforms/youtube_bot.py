import asyncio
import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import datetime
import re
import random
import time

# Scopes für YouTube Chat
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly', 'https://www.googleapis.com/auth/youtube.force-ssl']

class QuotaManager:
    """Trackt den YouTube API Quota Verbrauch"""
    def __init__(self, quota_file="youtube_quota.json"):
        self.quota_file = quota_file
        self.daily_limit = 10000
        self.consumed = 0
        self.last_reset = ""
        self.load()

    def load(self):
        if os.path.exists(self.quota_file):
            try:
                with open(self.quota_file, 'r') as f:
                    data = json.load(f)
                    self.consumed = data.get("consumed", 0)
                    self.last_reset = data.get("last_reset", "")
            except:
                pass
        self.check_reset()

    def save(self):
        with open(self.quota_file, 'w') as f:
            json.dump({
                "consumed": self.consumed,
                "last_reset": self.last_reset
            }, f)

    def check_reset(self):
        # YouTube Reset ist um Mitternacht Pacific Time (PT)
        # Wir nehmen einfach den aktuellen Tag UTC als einfache Annäherung
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        if self.last_reset != today:
            self.consumed = 0
            self.last_reset = today
            self.save()

    def consume(self, units):
        self.check_reset()
        self.consumed += units
        self.save()
        
        # Logging
        percent = (self.consumed / self.daily_limit) * 100
        if percent >= 90:
            print(f"[YouTube Quota] CRITICAL: {self.consumed}/{self.daily_limit} ({percent:.1f}%)")
        elif percent >= 80:
            print(f"[YouTube Quota] WARNING: {self.consumed}/{self.daily_limit} ({percent:.1f}%)")
        else:
            print(f"[YouTube Quota] Info: {self.consumed}/{self.daily_limit} ({percent:.1f}%)")
        
        return self.consumed

class YouTubeBot:
    def __init__(self, config, event_server):
        self.config = config
        self.event_server = event_server
        self.creds = None
        self.youtube = None
        self.live_chat_id = None
        self.next_page_token = None
        self.polling_task = None
        self.is_running = False
        self.quota = QuotaManager()
        self.chat_cache_file = "youtube_active_chat.json"
        self.min_polling_interval = 15.0 # Aggressive optimization
        
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
            self.quota.consume(100)
            resp = await asyncio.to_thread(req.execute)
            
            items = resp.get("items", [])
            if not items:
                print("[YouTube] Kein aktiver Stream gefunden.")
                return None

            broadcast = items[0]
            chat_id = broadcast['snippet']['liveChatId']
            print(f"[YouTube] Live Stream gefunden: {broadcast['snippet']['title']} (Chat ID: {chat_id})")
            
            # Broadcast Erfolg an Dashboard
            await self.event_server.broadcast("SystemEvent", {
                "type": "youtube_connected",
                "message": f"YouTube Stream verbunden: {broadcast['snippet']['title']}"
            })
            
            # Cache Chat ID
            with open(self.chat_cache_file, 'w') as f:
                json.dump({"chat_id": chat_id, "timestamp": time.time()}, f)
                
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
                # Quota Check before request
                if self.quota.consumed >= 9900:
                    print("[YouTube] Quota fast am Limit. Polling pausiert für 5 Min.")
                    await asyncio.sleep(300)
                    continue

                req = self.youtube.liveChatMessages().list(
                    liveChatId=self.live_chat_id,
                    part="id,snippet,authorDetails",
                    pageToken=self.next_page_token,
                    maxResults=50 # Max messages per poll
                )
                self.quota.consume(5)
                resp = await asyncio.to_thread(req.execute)
                
                self.next_page_token = resp.get('nextPageToken')
                
                # Polling interval optimization
                api_interval = resp.get('pollingIntervalMillis', 5000) / 1000.0
                polling_interval = max(api_interval, self.min_polling_interval)
                
                # Nachrichten verarbeiten
                items = resp.get('items', [])
                for item in items:
                    await self.handle_message(item)
                
                await asyncio.sleep(polling_interval)
                
            except Exception as e:
                err_str = str(e)
                wait_time = 15
                
                if "quotaExceeded" in err_str:
                    print("[YouTube] CRITICAL: Quota Exceeded! Pausiere für 1 Stunde.")
                    wait_time = 3600 # 1 Hour
                    self.live_chat_id = None # Stop polling current chat to be safe
                elif "404" in err_str or "forbidden" in err_str.lower():
                    print(f"[YouTube] Stream scheint beendet (Chat ID {self.live_chat_id} nicht mehr gültig).")
                    self.live_chat_id = None
                    if os.path.exists(self.chat_cache_file):
                        os.remove(self.chat_cache_file)
                    break
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

        # 2. Caching: Versuche gecachte Chat-ID
        if os.path.exists(self.chat_cache_file):
            try:
                with open(self.chat_cache_file, 'r') as f:
                    cached = json.load(f)
                    # Wenn Cache jünger als 12 Stunden, versuchen wir es
                    if time.time() - cached.get("timestamp", 0) < 43200:
                        print(f"[YouTube] Verwende gecachte Chat ID: {cached['chat_id']}")
                        self.live_chat_id = cached['chat_id']
            except:
                pass

        # 3. Stream Loop
        while self.is_running:
            if self.live_chat_id:
                # Starte Polling Loop
                await self.poll_chat()
                # Wenn poll_chat returned, ist der Stream wohl vorbei oder Error
                self.live_chat_id = None
            
            # Wartezeit vor nächstem Check oder manuellem Start
            # Wir checken nur noch alle 10 Minuten automatisch, um Quota zu sparen
            # Der User soll den manuellen Start Button im Dashboard nutzen.
            print("[YouTube] Warte auf manuellen Start oder nächsten Auto-Check (10 Min)...")
            
            # Use smaller steps to allow faster interrupt
            for _ in range(600):
                if not self.is_running or self.live_chat_id: break
                await asyncio.sleep(1)
            
            if self.is_running and not self.live_chat_id:
                # Auto-Discovery (Backup, falls Dashboard nicht genutzt wird)
                chat_id = await self.find_active_broadcast()
                if chat_id:
                    self.live_chat_id = chat_id
                
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
            
            elif action == "youtube_stream_start":
                print("[YouTube] Manueller Stream-Start angefordert.")
                chat_id = await self.find_active_broadcast()
                if chat_id:
                    self.live_chat_id = chat_id
                    # poll_chat wird von start() loop bemerkt
                else:
                    await self.event_server.broadcast("Error", {"message": "Kein aktiver YouTube Stream gefunden."})

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
            self.quota.consume(50)
            await asyncio.to_thread(req.execute)
            print(f"[YouTube -> Chat] {message_text}")
        except Exception as e:
            print(f"[YouTube] Fehler beim Senden: {e}")

    # --- SHORTS CACHING ---
    
    async def sync_shorts_cache(self):
        """Builds a local cache of videos <= 60s."""
        print("[YouTube] Starting Shorts Sync (this may take a moment)...")
        cache_file = "shorts_cache.json"
        shorts_ids = []
        
        try:
            # Ensure we are authenticated (lazy auth)
            if not self.youtube:
                print("[YouTube] Not authenticated. Attempting login for sync...")
                if not await self.authenticate():
                    print("[YouTube] Sync aborted: Login failed.")
                    return 0

            # 1. Get Uploads Playlist ID
            self.quota.consume(1)
            resp = await asyncio.to_thread(req.execute)
            uploads_playlist_id = resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # 2. Iterate Playlist
            next_token = None
            video_ids_buffer = []
            
            # Limit to last 1000 videos to protect quota in extreme cases, though specific logic handles wait
            fetched_count = 0
            
            while True:
                self.quota.consume(1)
                pl_resp = await asyncio.to_thread(pl_req.execute)
                
                # Collect IDs
                for item in pl_resp.get('items', []):
                    vid = item['contentDetails']['videoId']
                    video_ids_buffer.append(vid)
                    
                fetched_count += len(pl_resp.get('items', []))
                
                # Process buffer if >= 50 or no more pages
                next_token = pl_resp.get('nextPageToken')
                
                if len(video_ids_buffer) >= 50 or not next_token:
                    # Flush Buffer: Get Durations
                    # Join up to 50
                    batch = video_ids_buffer[:50]
                    video_ids_buffer = video_ids_buffer[50:] # keep rest
                    
                    if batch:
                        self.quota.consume(1)
                        vid_resp = await asyncio.to_thread(vid_req.execute)
                        
                        for vid_item in vid_resp.get('items', []):
                            duration_str = vid_item['contentDetails']['duration']
                            if self._is_short(duration_str) and vid_item['id'] not in shorts_ids:
                                shorts_ids.append(vid_item['id'])
                
                print(f"[YouTube] Stats: Checked {fetched_count} videos, found {len(shorts_ids)} Shorts so far...")
                
                if not next_token: # or fetched_count >= 1000: # Removed limit for now as per user request (wants full scan logic)
                    break
            
            # Save to file
            with open(cache_file, 'w') as f:
                json.dump(shorts_ids, f)
            print(f"[YouTube] Cache update done! Saved {len(shorts_ids)} videos to {cache_file}.")
            return len(shorts_ids)
            
        except Exception as e:
            print(f"[YouTube] Sync Error: {e}")
            return 0

    def get_random_short(self):
        """Returns a random cached video ID. Triggers sync if empty."""
        cache_file = "shorts_cache.json"
        
        if not os.path.exists(cache_file):
             print("[YouTube] Cache empty, please sync first! (Returning None)")
             return None
             
        try:
            with open(cache_file, 'r') as f:
                ids = json.load(f)
            
            if not ids: return None
            return random.choice(ids)
            
        except:
            return None
            
    def _is_short(self, duration_iso):
        """Parses PT#M#S to seconds. Returns True if <= 60s."""
        # Simple Regex for PT1M30S style
        # Format is usually PT#M#S or PT#S. Hours are unlikely for Shorts triggers but possible for parser.
        
        # Extract matches
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
        if not match: return False # Unknown format
        
        h = int(match.group(1) or 0)
        m = int(match.group(2) or 0)
        s = int(match.group(3) or 0)
        
        total_seconds = h*3600 + m*60 + s
        return 0 < total_seconds <= 61 # 61 just to be safe with rounding
