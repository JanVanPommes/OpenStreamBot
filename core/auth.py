import os
import json
import asyncio
import webbrowser
from aiohttp import web, ClientSession

# --- TWITCH AUTH ---

async def perform_twitch_oauth_flow(client_id, client_secret, redirect_uri="http://localhost:3000"):
    """Startet lokalen Webserver und öffnet Browser für Twitch Login"""
    import urllib.parse
    
    # Port dynamisch aus redirect_uri ermitteln
    parsed_uri = urllib.parse.urlparse(redirect_uri)
    port = parsed_uri.port if parsed_uri.port else 80
    
    code_future = asyncio.Future()
    
    async def callback(request):
        # Log path for debugging
        print(f"[OAuth] Request received: {request.method} {request.path} | Query: {request.query_string}")
        
        # Fehlerbehandlung: Wenn Twitch einen Fehler zurückgibt (z.B. user_denied)
        error = request.query.get('error')
        if error:
            error_desc = request.query.get('error_description', 'Unbekannter Fehler')
            return web.Response(text=f"<h1>Login Fehlgeschlagen</h1><p>Fehler: {error}</p><p>Beschreibung: {error_desc}</p>", content_type='text/html')

        code = request.query.get('code')
        if code:
            if not code_future.done():
                code_future.set_result(code)
            return web.Response(text="<h1>Login erfolgreich!</h1><p>Du kannst dieses Fenster jetzt schliessen.</p>", content_type='text/html')
        
        # Fallback if accessed without code
        return web.Response(text="<h1>OpenStreamBot OAuth</h1><p>Warte auf Callback...</p>", content_type='text/html')

    app = web.Application()
    # Explicitly add root route AND catch-all to ensure Windows handling works
    app.add_routes([
        web.get('/', callback),
        web.get('/{tail:.*}', callback)
    ])
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Listen on all interfaces to be safe
    # Try generic bind (None) first or explicit 0.0.0.0
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    # Browser öffnen
    scope = "chat:read+chat:edit+channel:read:redemptions+channel:manage:redemptions" 
    auth_url = (f"https://id.twitch.tv/oauth2/authorize?response_type=code&client_id={client_id}"
                f"&redirect_uri={redirect_uri}&scope={scope}")
    
    print(f"Öffne Browser: {auth_url}")
    # Versuche den Browser zu öffnen
    try:
        webbrowser.open(auth_url)
    except Exception as e:
        print(f"Konnte Browser nicht automatisch öffnen: {e}")
        print(f"Bitte öffne diesen Link manuell: {auth_url}")
    
    try:
        # Warte auf Code (120s Timeout)
        code = await asyncio.wait_for(code_future, timeout=120)
    except asyncio.TimeoutError:
        await site.stop()
        raise Exception("Zeitüberschreitung beim Login. Bitte versuche es erneut.")
        
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

async def validate_twitch_token(access_token):
    """Prüft, ob der Token noch gültig ist."""
    headers = {"Authorization": f"OAuth {access_token}"}
    try:
        async with ClientSession() as session:
            async with session.get("https://id.twitch.tv/oauth2/validate", headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json() # Enthält 'expires_in', 'login', etc.
                return None
    except:
        return None

async def refresh_twitch_token(client_id, client_secret, refresh_token):
    """Erneuert den Access Token mithilfe des Refresh Tokens."""
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret
    }
    async with ClientSession() as session:
        async with session.post(url, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                text = await resp.text()
                raise Exception(f"Token Refresh fehlgeschlagen: {text}")

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
