# OpenStreamBot

**Version:** 0.4.0  
**Autor:** JanVanPommes
**Ein Multi-Plattform Stream-Bot für Twitch & YouTube**

OpenStreamBot ist ein Open-Source-Bot für Streamer, der Twitch und YouTube integriert, OBS Studio steuern kann und ein flexibles Action-System bietet. Ideal für Creator, die ihre Streams automatisieren und interaktiver gestalten möchten.

---

## 🎯 Features

- **Multi-Plattform Chat**: Twitch und YouTube Live-Chat in einem Dashboard
- **OBS Studio Integration**: Szenen wechseln, Quellen steuern, auf OBS-Events reagieren
- **Flexibles Action-System**: 
  - Eigene Befehle erstellen (!command)
  - Sounds abspielen (mit Auto-Stop & Gerätewahl)
  - **Neu:** Playlists (Zufällige Wiedergabe aus Ordner)
  - **Neu:** YouTube Shorts (Shorts abspielen mit Overlay)
  - **Neu:** Auto-Ducking (Musik leiser bei Videos)
  - **Neu:** Timer Trigger (Intervall-basierte Aktionen)
  - **Neu:** Kanalpunkte (Trigger & Verwaltung)
  - **Neu:** User Permissions (Befehle nur für Mods/VIPs)
  - **Neu:** HotSwitch (Sofortige Action-Steuerung)
  - **Neu in 0.4.0:** ElevenLabs TTS Integration (Text-to-Speech)
  - **Neu in 0.4.0:** Netzwerk-bewusste Twitch-Authentifizierung (Offline-Boot-Unterstützung)
  - **Neu in 0.3.3:** YouTube First Words & User Blacklist
  - **Neu in 0.3.3:** Action Groups (Verschachtelte Wahrscheinlichkeits-Actions)
  - **Neu in 0.3.3:** Modernisiertes GUI "Card" Layout
  - **Neu in 0.3.2:** "First Words" Trigger
  - **Neu in 0.3.2:** Twitch Clips & Wahrscheinlichkeits-Actions
  - **Neu in 0.3.2:** C# Code Ausführung (Führe .cs/Skripte/Projekte aus)
  - Auf Events reagieren (Raids, Subs, etc.)
  - Gruppierung und Organisation
- **Profil Manager**: Speichern und Laden von Bot-Konfigurationen
- **Web Dashboard**: Moderne Web-UI für Chat-Verwaltung und Übersicht
- **Quota-Optimierung**: YouTube nur auf Knopfdruck aktivieren (spart API-Quota)
- **GUI Launcher**: Einfache Verwaltung über Desktop-Anwendung
- **Windows Installer**: Einfacher Setup-Assistent für Windows-Nutzer

---

## 📋 Voraussetzungen

- **Python 3.10+** (empfohlen: 3.12)
- **OBS Studio** (optional, für OBS-Features)
- **OBS WebSocket Plugin** (ab OBS 28+ bereits integriert)
- **Betriebssystem**: Linux, macOS, oder Windows

---

## 🚀 Installation

### 📦 Einfache Installation (Windows)

1. **Download**: Gehe zur [Releases](https://github.com/JanVanPommes/OpenStreamBot/releases) Seite.
2. **Installer laden**: Lade die neuste `OpenStreamBot_Setup.exe` herunter.
   > **Hinweis**: Dank GitHub Actions wird diese Datei nun automatisch für jedes Update erstellt!
3. **Installieren**: Ausführen, Installationsort wählen, fertig.
4. **Updates**: Der Launcher zeigt dir automatisch an, wenn eine neue Version verfügbar ist!

### 🛠️ Manuelle Installation / Vom Quellcode

#### **Windows**
1. **Python installieren**: Lade Python 3.10+ von [python.org](https://www.python.org/downloads/windows/) herunter (Häkchen bei "Add Python to PATH" setzen!).
2. **Klonen**: `git clone https://github.com/JanVanPommes/OpenStreamBot.git`
3. **Einrichten**: Doppelklick auf `start.bat`. Das Skript fragt nach der venv-Erstellung beim ersten Mal.
   - *Alternativ manuell*:
     ```cmd
     python -m venv venv
     venv\Scripts\activate
     python -m pip install -r requirements.txt
     ```
   - *EXE selbst bauen*:
     ```cmd
     pip install pyinstaller
     python build.py
     ```

#### **macOS**
1. **Python / Homebrew**: `brew install python` (falls Homebrew installiert ist).
2. **Klonen**: `git clone https://github.com/JanVanPommes/OpenStreamBot.git`
3. **Einrichten**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   chmod +x start_launcher.sh
   # Starten
   ./start_launcher.sh
   ```

#### **Linux (Ubuntu/Debian)**
1. **Prerequisites**:
   ```bash
   sudo apt update
   sudo apt install python3-venv python3-tk
   ```
2. **Klonen & Einrichten**:
   ```bash
   git clone https://github.com/JanVanPommes/OpenStreamBot.git
   cd OpenStreamBot
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   chmod +x start_launcher.sh
   # Starten
   ./start_launcher.sh
   ```

### 4. Konfiguration erstellen
Kopiere die Beispiel-Konfiguration:
```bash
cp config.example.yaml config.yaml
```

Bearbeite `config.yaml` mit deinen Daten:
```yaml
server:
  host: localhost
  port: 8080

twitch:
  enabled: true
  client_id: DEINE_TWITCH_CLIENT_ID      # Von https://dev.twitch.tv/console
  client_secret: DEIN_TWITCH_SECRET
  channel: dein_twitch_username

youtube:
  enabled: true  # Auf false setzen, wenn nicht benötigt
  client_secret_file: client_secret.json
  token_file: token_youtube.json

obs:
  host: localhost
  port: 4455
  password: ''  # Dein OBS WebSocket Passwort (falls gesetzt)
```

---

## 🔐 Accounts verbinden

### Twitch
1. Erstelle eine App auf [Twitch Developer Console](https://dev.twitch.tv/console/apps)
2. **OAuth Redirect URL**: `http://localhost:8080`
3. Kopiere **Client ID** und **Secret** in `config.yaml`
4. Starte den Launcher: `python launcher.py`
5. Gehe zu **Accounts** → **"Login with Twitch"**

### YouTube (Optional)
Für YouTube benötigst du ein eigenes Google Cloud Project wegen API-Quota-Limits.

➡️ **Detaillierte Anleitung**: Siehe [`YOUTUBE_SETUP.md`](YOUTUBE_SETUP.md)

**Kurzfassung**:
1. [Google Cloud Console](https://console.cloud.google.com/) → Projekt erstellen
2. YouTube Data API v3 aktivieren
3. OAuth-Client (Desktop-App) erstellen
4. `client_secret.json` herunterladen und im Projektordner ablegen
5. Im Launcher: **Accounts** → **"Login with Google"**

---

## ▶️ Bot starten

- **Windows**: Doppelklick auf `start.bat`
- **Linux/macOS**: `./start_launcher.sh` im Terminal oder `python launcher.py`
```bash
# Manuelle Ausführung
python launcher.py
```

- **Dashboard**: Bot starten/stoppen, Logs anzeigen
- **Settings**: Config bearbeiten
- **Accounts**: Twitch/YouTube Login verwalten
- **Actions Editor**: Eigene Commands und Aktionen erstellen
- **Profile**: Wechseln zwischen verschiedenen Konfigurationen

### Headless (nur Bot, kein GUI)
```bash
python main.py
```

---

## 🎮 OBS Studio einrichten

1. **OBS starten** (Version 28+ empfohlen)
2. **Extras** → **WebSocket Server Einstellungen**
3. **Server aktivieren** (Port standardmäßig 4455)
4. Optional: **Passwort setzen** (dann in `config.yaml` eintragen)
5. Bot starten → Verbindung wird automatisch hergestellt

---

## 📝 Actions erstellen

Das Action-System ermöglicht es dir, eigene Befehle und Reaktionen zu erstellen:

### Beispiel: Sound-Befehl
1. Launcher starten → **Actions Editor** Tab
2. **"+ New Action"** klicken
3. Name: `Fanfare`
4. **"+ Add Trigger"** → `twitch_command` → `!fanfare`
5. **"+ Add Sub-Action"** → `play_sound` → Sound-Datei auswählen
6. **"Save Actions"**

Ab jetzt wird bei `!fanfare` im Chat der Sound abgespielt! 🎺

### Neu in 0.3.0 Beta:
- **Instant HotSwitch**: Aktionen sofort an/ausschalten ohne Neustart.
- **User Permissions**: Befehle auf Mods, VIPs, Subs etc. beschränken.
- **Channel Points Manager**: Kanalpunkt-Belohnungen direkt im Bot verwalten.
- **Twitch Redemptions**: Aktionen auslösen, wenn Zuschauer Kanalpunkte einlösen.
- **Timer Management**: Timer starten/stoppen automatisch mit ihrer Aktion.
- **Action Cooldowns**: Cooldowns für Befehle setzen (Vermeidet Spam).
- **YouTube Chat Trigger**: Eigener Trigger für YouTube Chat Befehle.
- **Window Resizing**: Fenster kann nun kleiner gezogen werden (min. 900x600).

### Weitere Möglichkeiten:
- **OBS-Szene wechseln** bei bestimmten Commands
- **Chat-Nachrichten** senden als Antwort
- **Delays** zwischen Aktionen
- **Sounds stoppen** nach X Sekunden

---

## 🌐 Web Dashboard

Nach dem Start erreichbar unter:
```
http://localhost:8000/interface/dashboard.html
```

Features:
- Live-Chat-Ansicht (Twitch + YouTube vereint)
- Nachrichten senden
- Emote-Unterstützung
- Badge-Anzeige (Mod, VIP, Sub, etc.)

---

## 📊 Projektstruktur

```
OpenStreamBot/
├── launcher.py              # GUI Launcher
├── main.py                  # Hauptprogramm (headless)
├── config.yaml              # Deine Konfiguration
├── actions.yaml             # Gespeicherte Actions
├── requirements.txt         # Python-Abhängigkeiten
├── YOUTUBE_SETUP.md         # YouTube API Setup Guide
│
├── core/                    # Kernmodule
│   ├── event_server.py      # WebSocket Event-System
│   ├── action_engine.py     # Action-Ausführung
│   └── http_server.py       # Web-Server für Dashboard
│
├── platforms/               # Plattform-Integrationen
│   ├── twitch_bot.py        # Twitch Chat Bot
│   ├── youtube_bot.py       # YouTube Live Chat
│   └── obs_controller.py    # OBS WebSocket Client
│
└── interface/               # GUI & Web-Interfaces
    ├── gui_actions.py       # Actions Editor (GUI)
    ├── dashboard.html       # Web Dashboard
    └── dashboard.js         # Dashboard Logic
```

---

## 🛠️ Troubleshooting

### "Port 8000 / 8080 bereits belegt"
Ein alter Bot-Prozess läuft noch im Hintergrund:
```bash
pkill -f main.py
```
Oder: Launcher komplett schließen, kurz warten, neu starten.

### YouTube: "Quota Exceeded"
- **Ursache**: Tägliches API-Limit erreicht (10.000 Units)
- **Lösung**: 
  - Nutze den **"Connect YouTube Stream"** Button nur bei Bedarf
  - Quota wird täglich um ~9:00 Uhr MEZ zurückgesetzt
  - Siehe [`YOUTUBE_SETUP.md`](YOUTUBE_SETUP.md) für Optimierungstipps

### OBS verbindet nicht
- Prüfe, ob **WebSocket Server** in OBS aktiviert ist
- Passwort in `config.yaml` korrekt?
- OBs läuft auf dem gleichen PC?

### Sounds spielen nicht ab
- Dateiformat unterstützt? (MP3, WAV, OGG)
- Pfad zur Datei korrekt? (Absolute Pfade nutzen)
- Prüfe Logs auf Fehlermeldungen

---

## 🤝 Contributing

Beiträge sind willkommen! 

1. Fork das Repository
2. Feature-Branch erstellen: `git checkout -b feature/MeinFeature`
3. Commit: `git commit -m 'Add: Mein neues Feature'`
4. Push: `git push origin feature/MeinFeature`
5. Pull Request öffnen

---

## 📄 Lizenz

Dieses Projekt steht unter der [MIT License](LICENSE).

---

## 🐛 Bug Reports & Feature Requests

Nutze die [GitHub Issues](https://github.com/JanVanPommes/OpenStreamBot/issues) um:
- Bugs zu melden
- Features vorzuschlagen
- Fragen zu stellen

---

## 🙏 Credits

- **TwitchIO**: Twitch Chat Integration
- **Google APIs**: YouTube Live Chat
- **obs-websocket-py**: OBS Studio Control
- **CustomTkinter**: Moderne GUI
- **Pygame**: Audio Playback

---

**Viel Erfolg mit deinem Stream! 🎬🚀**
