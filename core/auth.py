import os
import json
import asyncio
import webbrowser
from aiohttp import web, ClientSession

# --- TWITCH AUTH ---

async def perform_twitch_oauth_flow(client_id, client_secret, redirect_uri="http://localhost:3000"):
    """Startet lokalen Webserver und öffnet Browser für Twitch Login"""
    code_future = asyncio.Future()
    
    async def callback(request):
        code = request.query.get('code')
        if code:
            if not code_future.done():
                code_future.set_result(code)
            return web.Response(text="<h1>Login erfolgreich!</h1><p>Du kannst dieses Fenster jetzt schliessen.</p>")
        return web.Response(text="Fehler: Kein Code gefunden.")

    app = web.Application()
    app.add_routes([web.get('/', callback)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 3000)
    await site.start()

    # Browser öffnen
    scope = "chat:read+chat:edit+channel:read:redemptions" 
    auth_url = (f"https://id.twitch.tv/oauth2/authorize?response_type=code&client_id={client_id}"
                f"&redirect_uri={redirect_uri}&scope={scope}")
    
    print(f"Öffne Browser: {auth_url}")
    webbrowser.open(auth_url)
    
    try:
        # Warte auf Code (120s Timeout)
        code = await asyncio.wait_for(code_future, timeout=120)
    except asyncio.TimeoutError:
        await site.stop()
        raise Exception("Zeitüberschreitung beim Login.")
        
    await site.stop()

    # Code gegen Token tauschen
    token_url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    
    async with ClientSession() as session:
        async with session.post(token_url, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                text = await resp.text()
                raise Exception(f"Token Exchange fehlgeschlagen: {text}")

# --- YOUTUBE AUTH ---

def perform_youtube_oauth_flow(client_secret_file, token_file):
    """
    Führt den Google OAuth Flow aus.
    Dies ist BLOCKIEREND, sollte in einem Thread ausgeführt werden wenn GUI aktiv.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow
    
    SCOPES = ['https://www.googleapis.com/auth/youtube.readonly', 'https://www.googleapis.com/auth/youtube.force-ssl']
    
    if not os.path.exists(client_secret_file):
        raise FileNotFoundError(f"Client Secret Datei nicht gefunden: {client_secret_file}")

    flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
    creds = flow.run_local_server(port=0)
    
    # Speichern
    with open(token_file, 'w') as token:
        token.write(creds.to_json())
        
    return True
