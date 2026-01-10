from twitchio.ext import commands
import datetime
import os
import json
import asyncio
import webbrowser
from core.auth import perform_twitch_oauth_flow, validate_twitch_token, refresh_twitch_token

async def setup_twitch_token(config):
    """
    Handhabt den OAuth Flow für Twitch.
    Gibt einen gültigen Access Token zurück string.
    """
    # 1. Legacy Check
    if 'token' in config and config['token'].startswith('oauth:'):
        return config['token']

    # 2. OAuth Check
    client_id = config.get('client_id')
    client_secret = config.get('client_secret')
    token_file = config.get('token_file', 'token_twitch.json')
    
    if not client_id or not client_secret:
        # print("[Twitch] FEHLER: Weder 'token' noch 'client_id'/'client_secret' konfiguriert.")
        return None

    # Token laden/prüfen
    creds = None
    if os.path.exists(token_file):
        try:
            with open(token_file, 'r') as f:
                creds = json.load(f)
        except:
            pass

    if creds:
        # Check validity
        access_token = creds.get('access_token')
        refresh_token = creds.get('refresh_token')
        
        if access_token:
            print("[Twitch] Prüfe Token-Gültigkeit...")
            validation = await validate_twitch_token(access_token)
            
            if validation:
                print(f"[Twitch] Token ist gültig (Expires in: {validation.get('expires_in')}s)")
                return access_token
            else:
                print("[Twitch] Token abgelaufen oder ungültig.")
                
                # Versuche Refresh
                if refresh_token:
                    print("[Twitch] Versuche Token-Refresh...")
                    try:
                        new_creds = await refresh_twitch_token(client_id, client_secret, refresh_token)
                        
                        # Neue Daten speichern
                        with open(token_file, 'w') as f:
                            json.dump(new_creds, f)
                            
                        print("[Twitch] Token erfolgreich aktualisiert!")
                        return new_creds.get('access_token')
                    except Exception as e:
                        print(f"[Twitch] Refresh fehlgeschlagen: {e}")
                else:
                    print("[Twitch] Kein Refresh Token vorhanden.")
    
    # Fallback: Neuer Browser Login, wenn alles fehlschlägt
    print("[Twitch] Kein gültiger Token. Starte Browser-Login...")
    try:
        redirect_uri = config.get('redirect_uri', 'http://localhost:3000')
        creds = await perform_twitch_oauth_flow(client_id, client_secret, redirect_uri=redirect_uri)
        if creds:
            with open(token_file, 'w') as f:
                json.dump(creds, f)
            return creds.get('access_token')
    except Exception as e:
        print(f"[Twitch] Auto-Login fehlgeschlagen: {e}")
        return None
    
    return None

class TwitchBot(commands.Bot):
    def __init__(self, token, config, event_server):
        self.event_server = event_server
        self.channel_name = config['channel']
        
        # Initialisierung der TwitchIO Elternklasse
        super().__init__(
            token=token,
            client_id=config.get('client_id'), # Wichtig für API Calls
            client_secret=config.get('client_secret'),
            prefix='!',
            initial_channels=[self.channel_name]
        )
        self.is_ready = False
        # Callback registrieren für ausgehende Nachrichten vom Dashboard
        self.event_server.add_message_handler(self.on_dashboard_message)
        
        # Cache für Badges
        self.badge_map = {}

    async def on_dashboard_message(self, raw_data):
        import json
        try:
            data = json.loads(raw_data)
            action = data.get("action")
            
            if action == "send_chat":
                msg = data.get("message")
                if msg and self.connected_channels:
                    channel = self.connected_channels[0]
                    await channel.send(msg)
                    print(f"[Dashboard -> Chat] {msg}")
            
            elif action == "get_badges":
                # Sende Badges an alle (oder idealerweise nur an den neuen Client, 
                # aber Broadcast ist für jetzt okay und einfacher)
                if self.badge_map:
                   await self.event_server.broadcast("BadgeMapping", self.badge_map)
                   print(f"[Dashboard] Badges angefordert und gesendet.")

        except Exception as e:
            print(f"[Error] Failed to process dashboard message: {e}")

    async def event_ready(self):
        # Wird ausgeführt, wenn der Login erfolgreich war
        self.is_ready = True
        print(f"[Twitch] Eingeloggt als {self.nick}")
        print(f"[Twitch] Verbunden mit Kanal: {self.channel_name}")
        
        # Sende Status an WebSocket (z.B. für ein Dashboard)
        await self.event_server.broadcast("BotStatus", {"status": "Connected", "platform": "Twitch"})
        
        # --- BADGES LADEN ---
        try:
            # 1. User ID des Kanals herausfinden
            users = await self.fetch_users(names=[self.channel_name])
            if users:
                channel_id = users[0].id
                
                # Helper für API Calls
                async def fetch_badges_api(url):
                    headers = {
                        "Client-Id": self._http.client_id,
                        "Authorization": f"Bearer {self._http.token.replace('oauth:', '')}"
                    }
                    async with self._http.session.get(url, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data.get('data', [])
                        print(f"Badge API Error {url}: {resp.status}")
                        return []

                # 2. Badges von Twitch API laden (Manuell, da Methode fehlt)
                global_data = await fetch_badges_api("https://api.twitch.tv/helix/chat/badges/global")
                channel_data = await fetch_badges_api(f"https://api.twitch.tv/helix/chat/badges?broadcaster_id={channel_id}")
                
                # 3. Eine Map bauen: set_id -> version -> url
                badge_map = {}
                
                def parse_api_badges(badge_list):
                    for b in badge_list:
                        s_id = b['set_id']
                        if s_id not in badge_map: badge_map[s_id] = {}
                        for v in b['versions']:
                            badge_map[s_id][v['id']] = v['image_url_1x']

                parse_api_badges(global_data)
                parse_api_badges(channel_data)

                # Store in self
                self.badge_map = badge_map

                # 4. An Dashboard senden
                print(f"[Twitch] Badges geladen: {len(badge_map)} Sets")
                await self.event_server.broadcast("BadgeMapping", badge_map)
                
        except Exception as e:
            print(f"[Twitch] Fehler beim Laden der Badges: {e}")
            import traceback
            traceback.print_exc()

    async def get_user_last_game(self, username):
        """
        Holt das zuletzt gespielte Spiel (oder aktuelle Kategorie) eines Users.
        """
        try:
            # 1. User ID herausfinden
            users = await self.fetch_users(names=[username])
            if not users:
                return "Unbekannt (User nicht gefunden)"
            
            user_id = users[0].id
            
            # 2. Channel Info via API laden
            # Wir nutzen direkt die Session von twitchio
            headers = {
                "Client-Id": self._http.client_id,
                "Authorization": f"Bearer {self._http.token.replace('oauth:', '')}"
            }
            url = f"https://api.twitch.tv/helix/channels?broadcaster_id={user_id}"
            
            async with self._http.session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get('data', [])
                    if items:
                         game = items[0].get('game_name')
                         return game if game else "Nichts"
            
            return "Unbekannt (API Error)"
            
        except Exception as e:
            print(f"[Twitch API] Error fetching game for {username}: {e}")
            return "Unbekannt"

    async def event_message(self, message):
        # 1. Author Name sicherstellen (bei Echo manchmal None)
        author_name = message.author.display_name if message.author and message.author.display_name else (message.author.name if message.author else self.nick)
        
        # Debug-Ausgabe in der Konsole
        # print(f"[Twitch Chat] {author_name}: {message.content} | Tags: {message.tags}")

        # --- BADGES PARSEN ---
        msg_badges = []
        
        # Versuche Badges aus Tags zu lesen
        if message.tags and 'badges' in message.tags:
             badge_str = message.tags['badges']
             if isinstance(badge_str, str): 
                 for part in badge_str.split(','):
                     if '/' in part:
                         bid, version = part.split('/')
                         msg_badges.append({"id": bid, "version": version})
        
        # Fallback: Wenn Echo (eigene Nachricht) und Badges leer sind, aber wir der Broadcaster sind -> Broadcaster Badge
        if not msg_badges and author_name.lower() == self.channel_name.lower():
            msg_badges.append({"id": "broadcaster", "version": "1"})

        # 2. Datenpaket schnüren
        emotes = []
        if message.tags and 'emotes' in message.tags and message.tags['emotes']:
            # Format: id:start-end,start-end/id2:start-end
            emote_str = message.tags['emotes']
            for part in emote_str.split('/'):
                if not part: continue
                eid, positions = part.split(':')
                for pos in positions.split(','):
                    start, end = map(int, pos.split('-'))
                    emotes.append({"id": eid, "start": start, "end": end})

        # Safety-Check für Color/Mod
        color = "#a970ff" # Default Fallback
        
        if message.author and message.author.color:
            color = message.author.color
        elif message.tags and 'color' in message.tags:
             # Manchmal ist color in tags, aber leerer String
             c = message.tags['color']
             if c: color = c
        
        # Mod Status Check
        is_mod = True # Default fallback
        if message.author: 
            is_mod = message.author.is_mod
        elif message.tags and 'mod' in message.tags:
             is_mod = str(message.tags['mod']) == "1"

        chat_data = {
            "platform": "twitch",
            "user": author_name,
            "message": message.content,
            "is_mod": is_mod,
            "color": color, 
            "timestamp": str(datetime.datetime.now()),
            "emotes": emotes,
            "badges": msg_badges
        }

        # 3. An alle WebSocket-Clients senden (Overlays empfangen das jetzt!)
        await self.event_server.broadcast("ChatMessage", chat_data)

        # 4. Ignoriere Commands vom Bot selbst (Echo)
        if message.echo:
            return

        # 5. Generic Command Trigger (for Action Engine)
        if message.content.startswith('!'):
            cmd_name = message.content.split(' ')[0] # e.g. !test
            # Emit "CommandTriggered" event so ActionEngine can pick it up
            # even if it's not a hardcoded command in this class
            await self.event_server.broadcast("CommandTriggered", {
                "command": cmd_name, 
                "user": author_name,
                "message": message.content
            })

        # 6. TwitchIO Command System (Hardcoded commands)
        await self.handle_commands(message)

    # --- BEISPIEL COMMAND ---
    @commands.command()
    async def ping(self, ctx: commands.Context):
        """Ein einfacher Test-Befehl"""
        await ctx.send(f"Pong! @{ctx.author.name}")
        # Wir können auch ein Event senden, dass ein Command ausgeführt wurde
        # Wir können auch ein Event senden, dass ein Command ausgeführt wurde
        await self.event_server.broadcast("CommandTriggered", {"command": "ping", "user": ctx.author.name})

    # --- EVENTS (Subs, Raids, etc.) ---
    async def event_subscription(self, payload):
        """Wird bei einem Sub / Resub ausgelöst"""
        # payload is a SubscriptionEvent or similar depending on version, 
        # but in recent twitchio it might be event_usernotice or specific subscription event
        # We will use a safe approach extracting data
        
        # Note: TwitchIO 2.x often differs. For safety, we use manual construction or event_raw_usernotice if unsure,
        # but let's try the standard hook first.
        # Actually payload for event_subscription in 2.10 might be a dict or object. 
        # Let's assume standard parameters.
        
        user_name = payload.user.name if payload.user else "Unknown"
        # Type: 'sub', 'resub', 'subgift', etc.
        # Simple message construction
        msg = f"New Subscription: {user_name}!"
        
        data = {
            "type": "subscription",
            "message": msg,
            "user": user_name
        }
        print(f"[Twitch Event] {msg}")
        await self.event_server.broadcast("SystemEvent", data)

    async def event_raid(self, users):
        """Wird bei einem Raid ausgelöst"""
        # users is a list of User objects (raiders)
        # Note: Usually providing the raider name is tricky in simple callbacks.
        # Often easier to capture from chat message "x is raiding with y viewers"
        print("[Twitch Event] Raid detected")
        # For now, we might receive a notification or chat message.
        # If this event triggers, we just say "Raid detected"
        pass
    
    # Using event_raw_usernotice is often more reliable for all alerts
    async def event_raw_usernotice(self, channel, tags):
        """Fängt Subs, Resubs, Raids etc. via Raw Tags"""
        msg_id = tags.get('msg-id')
        
        if msg_id in ['sub', 'resub', 'subgift', 'anonsubgift', 'giftpaidupgrade']:
           display_name = tags.get('display-name', 'Jemand')
           plan = tags.get('msg-param-sub-plan', 'Prime')
           
           event_text = f"★ {display_name} hat abonniert! ({plan})"
           if msg_id == 'resub':
               months = tags.get('msg-param-cumulative-months', '1')
               event_text = f"★ {display_name} ist seit {months} Monaten dabei!"
               
           data = {"type": "sub", "message": event_text}
           await self.event_server.broadcast("SystemEvent", data)
           
        elif msg_id == 'raid':
            raider = tags.get('msg-param-displayName', 'Jemand')
            viewers = tags.get('msg-param-viewerCount', '0')
            event_text = f"RUN! {raider} raidet mit {viewers} Zuschauern!"
            data = {"type": "raid", "message": event_text}
            await self.event_server.broadcast("SystemEvent", data)

    # --- TEST COMMANDS ---
    @commands.command()
    async def testsub(self, ctx: commands.Context):
        """Simuliert einen Sub"""
        # Broadcaster ist auch erlaubt
        if not ctx.author.is_mod and ctx.author.name.lower() != self.channel_name.lower(): 
            print(f"[Command] Permission denied for {ctx.author.name}")
            return
            
        print(f"[Command] !testsub triggered by {ctx.author.name}")
        data = {"type": "sub", "message": f"★ {ctx.author.name} hat abonniert! (Test)"}
        await self.event_server.broadcast("SystemEvent", data)

    async def event_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            # Ignore command not found errors, as they might be handled by ActionEngine
            return
        
        print(f"[Twitch Command Error] {error}")

    @commands.command()
    async def testraid(self, ctx: commands.Context):
        """Simuliert einen Raid"""
        if not ctx.author.is_mod and ctx.author.name.lower() != self.channel_name.lower():
            return

        print(f"[Command] !testraid triggered by {ctx.author.name}")
        data = {"type": "raid", "message": f"RUN! {ctx.author.name} raidet mit 9000 Zuschauern! (Test)"}
        await self.event_server.broadcast("SystemEvent", data)
