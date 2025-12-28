import asyncio
import yaml
import sys
import os
from core.event_server import EventServer
# NEU: Importiere den Twitch Bot
from platforms.twitch_bot import TwitchBot

def load_config():
    try:
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("FEHLER: config.yaml nicht gefunden! Bitte erstellen.")
        sys.exit(1)

async def main():
    cfg = load_config()
    
    # 1. Event Server initialisieren
    ws_server = EventServer(cfg['server']['host'], cfg['server']['port'])

    # 1.5 HTTP Server starten (für OBS/Dashboard)
    from core.http_server import SimpleWebServer
    web_server = SimpleWebServer(port=8000)
    web_server.start()
    
    # 2. Twitch Bot initialisieren (nur wenn in Config aktiviert)
    tasks = []
    
    # Server Task starten
    tasks.append(asyncio.create_task(ws_server.start()))

    # --- ACTIONS & OBS (NEU) ---
    from platforms.obs_controller import OBSController
    from core.action_engine import ActionEngine
    
    # OBS Config (Safe get)
    if 'obs' not in cfg: cfg['obs'] = {'host': 'localhost', 'port': 4455, 'password': ''}
    
    obs_ctrl = OBSController(cfg['obs'], ws_server)
    obs_ctrl.connect() # Non-blocking initial connect attempt
    
    # Action Engine initialization
    action_engine = ActionEngine("actions.yaml", ws_server, obs_ctrl)
    
    # Connect Engine to OBS
    obs_ctrl.action_engine = action_engine
    
    # Bind ActionEngine to EventServer (Internal Listener)
    ws_server.add_internal_listener(action_engine.handle_event)
    # ---------------------------

    if cfg['twitch']['enabled']:
        # Token besorgen (OAuth flow wenn nötig)
        from platforms.twitch_bot import setup_twitch_token, TwitchBot
        
        twitch_token = await setup_twitch_token(cfg['twitch'])
        
        if twitch_token:
            # Wir übergeben jetzt den Token explizit
            bot = TwitchBot(twitch_token, cfg['twitch'], ws_server)
            action_engine.twitch = bot # Linked to ActionEngine
            
            twitch_task = asyncio.create_task(bot.start())
            tasks.append(twitch_task)
        else:
            print("[System] Twitch Login fehlgeschlagen/abgebrochen.")
    else:
        print("[System] Twitch Modul ist deaktiviert.")

    # YouTube Bot - Initialize but DON'T auto-start (manual control via .yt_control file)
    yt_bot = None
    if cfg.get('youtube', {}).get('enabled', False):
        from platforms.youtube_bot import YouTubeBot
        yt_bot = YouTubeBot(cfg['youtube'], ws_server)
        action_engine.youtube = yt_bot # Link to ActionEngine
        
        # Start control file monitor instead of auto-starting YouTube
        async def youtube_control_monitor():
            """Monitor .yt_control file for start/stop commands"""
            yt_task = None
            while True:
                try:
                    if os.path.exists(".yt_control"):
                        with open(".yt_control", "r") as f:
                            cmd = f.read().strip()
                        
                        if cmd == "start" and yt_task is None:
                            print("[YouTube] Manual start requested via control file.")
                            yt_task = asyncio.create_task(yt_bot.start())
                        elif cmd == "stop" and yt_task is not None:
                            print("[YouTube] Manual stop requested.")
                            await yt_bot.stop()
                            yt_task.cancel()
                            try:
                                await yt_task
                            except asyncio.CancelledError:
                                pass
                            yt_task = None
                    
                    await asyncio.sleep(1) # Check every second
                except Exception as e:
                    print(f"[YouTube Control] Error: {e}")
                    await asyncio.sleep(5)
        
        tasks.append(asyncio.create_task(youtube_control_monitor()))
        print("[System] YouTube ready (manual start required).")
    else:
        print("[System] YouTube Modul ist deaktiviert.")

    # Status Reporting Task
    async def status_reporter():
        import json
        import os
        while True:
            try:
                status = {
                    "twitch": "Online" if (cfg['twitch']['enabled'] and 'bot' in locals() and bot and hasattr(bot, 'is_ready') and bot.is_ready) else "Offline",
                    "youtube": "Polling" if ('yt_task' in locals() and yt_task and not yt_task.done()) else "Offline",
                    "obs": "Connected" if ('obs_ctrl' in locals() and obs_ctrl and obs_ctrl.is_connected) else "Offline",
                    "pid": os.getpid()
                }
                with open(".bot_status", "w") as f:
                    json.dump(status, f)
            except Exception as e:
                # Silently ignore errors in reporter to prevent main loop crash
                pass
            await asyncio.sleep(2)

    tasks.append(asyncio.create_task(status_reporter()))
    print("--- OpenStreamBot läuft (STRG+C zum Beenden) ---")
    
    try:
        # Alles parallel laufen lassen
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        print("[System] Async Tasks cancelled.")
    finally:
        print("[System] Cleaning up resources...")
        if 'web_server' in locals() and web_server:
            web_server.stop() 
        
        # Stop Bots
        if cfg['twitch']['enabled'] and 'bot' in locals() and bot:
             try:
                 await bot.close()
             except:
                 # TwitchIO crashes on close if connection wasn't established
                 pass
        
        if cfg.get('youtube', {}).get('enabled', False) and 'yt_bot' in locals() and yt_bot:
             try:
                 await yt_bot.stop()
             except:
                 pass

if __name__ == "__main__":
    def report_status(twitch="Offline", youtube="Offline", obs="Offline"):
        import json
        import os
        status = {"twitch": twitch, "youtube": youtube, "obs": obs, "pid": os.getpid()}
        try:
            with open(".bot_status", "w") as f:
                json.dump(status, f)
        except:
            pass

    try:
        # Initial status
        report_status()
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        err_str = str(e)
        if "AuthenticationError" in str(type(e)) or "Invalid or unauthorized Access Token" in err_str:
            print("\n[CRITICAL] Twitch-Login fehlgeschlagen!")
            print("Dein Access-Token ist ungültig oder abgelaufen.")
            print("Bitte logge dich im Launcher unter 'Accounts' neu bei Twitch ein.")
        elif "Address already in use" in err_str:
            print("\n[CRITICAL] Ports blockiert! Ein alter Prozess läuft noch.")
            print("Führe 'pkill -f main.py' aus oder warte einen Moment.")
        else:
            print(f"[System] Unerwarteter Fehler: {e}")
            import traceback
            traceback.print_exc()
    finally:
        report_status() # Reset to offline
        print("[System] Shutdown complete. Bye!")
