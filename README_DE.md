# OpenStreamBot

**Version:** 0.6.1  
**Autor:** JanVanPommes  
**Ein Multi-Plattform Stream-Bot für Twitch & YouTube**

OpenStreamBot ist ein leistungsstarker Open-Source Bot für Streamer, der Twitch und YouTube verbindet, OBS Studio steuert und ein flexibles Multi-Queue Aktionssystem für Sound-Effekte, TTS, Overlays und Stream Deck Hardware bietet.

---

## 🎯 Hauptfeatures (v0.6.0)

- **⚡ Multi-Queue Aktions-Architektur**:
  - Aktionen können spezifischen Ausführungswarteschlangen zugewiesen werden (`Default`, `TTS`, `Overlays`, `SoundFX` oder `Parallel`).
  - Einstellbare Verzögerungen (Delays) zwischen Aktionen, Pausieren/Fortsetzen von Queues und Live-Statusmonitor im Control Center.
- **📦 Vollständiges Backup & Profil-Export**:
  - Exportiere komplette Bot-Profile als `.osbbackup` ZIP-Archiv inklusive aller lokalen Audio-Dateien, Scripte und Bilder.
  - Importiere Backups mit einem Klick in eine neue OpenStreamBot Installation.
- **💜 Erweiterte Twitch-Integration**:
  - Reagiere auf Chatbefehle, Raids, Subscriptions, Follower, First Words, Watch Streaks und Kanalpunkt-Einlösungen.
  - **Dynamische Belohnungs-Steuerung**: Twitch-Kanalpunkte belohnungen per Sub-Action pausieren (`twitch_disable_reward`) oder wieder aktivieren (`twitch_enable_reward`), ohne sie zu löschen.
  - Volle Unterstützung für animierte Chat-Emotes und vergrößerte Emote-Nachrichten.
- **🔴 YouTube Live Chat & Events**:
  - Reagiere auf YouTube Chat-Nachrichten, YouTube First Words, Neue Mitgliedschaften, Meilensteine und Super Chats.
  - Spiele zufällige YouTube Shorts mit automatischer Lautstärkeabsenkung (Auto-Ducking) ab.
- **🗣️ ElevenLabs Text-to-Speech (TTS)**:
  - Generiere natürliche KI-Sprachausgabe direkt aus Chat-Triggern oder Sub-Actions.
- **🎮 Stream Deck & OpenDeck Support**:
  - Nativer `.sdPlugin` für Elgato Stream Deck und OpenDeck Hardware-Buttons, um Aktionen per Namen auszulösen.
- **🎥 OBS Studio Integration**:
  - Steuerung über OBS WebSocket 5.x: Szenen wechseln, Quellen umschalten, Audiofilter steuern und Screenshots erstellen.
- **⚙️ Moderner GUI Launcher & Einstellungen**:
  - Übersichtlicher Einstellungs-Bildschirm im Karten-Design für Twitch, YouTube, OBS und Audio.
  - Flüssiger Action-Editor ohne Flackern und mit 100% stabilem Scrollen der Sub-Actions-Liste.

---

## 📋 Voraussetzungen

- **Python 3.10+** (empfohlen: 3.12)
- **OBS Studio** (optional, für OBS-Funktionen)
- **OBS WebSocket Plugin** (in OBS 28+ integriert)
- **Betriebssystem**: Linux, macOS oder Windows

---

## 🚀 Installation & Start

### 📦 Windows Installation (Installer)

1. Lade `OpenStreamBot_Setup.exe` von der [Releases](https://github.com/JanVanPommes/OpenStreamBot/releases) Seite herunter.
2. Führe das Setup aus und starte **OpenStreamBot** über das Startmenü oder die Desktop-Verknüpfung.

### 🛠️ Manuelle Installation (Linux / macOS / Windows)

```bash
# Repository klonen
git clone https://github.com/JanVanPommes/OpenStreamBot.git
cd OpenStreamBot

# Virtuelle Umgebung erstellen und aktivieren
python3 -m venv venv
source venv/bin/activate  # Auf Windows: venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# GUI Launcher starten
python launcher.py
```

---

## 🔐 Konten Verbinden

### Twitch Einrichtung
1. Gehe im Launcher zu **Accounts** → Klicke auf **"Login with Twitch"**.
2. Bestätige die Autorisierung im Browser für Chat, Kanalpunkte, Clips und Moderationsbefehle.

### YouTube Einrichtung (Optional)
1. Erstelle ein Projekt in der Google Cloud Console und aktiviere die **YouTube Data API v3**.
2. Speichere `client_secret.json` im OpenStreamBot Ordner.
3. Klicke im Launcher unter **Accounts** auf **"Login with Google"**.

---

## 📝 Aktionen & Queues Erstellen

1. Öffne den Tab **Actions Editor** im Launcher.
2. Klicke auf **"+ New Action"** und wähle eine Ausführungs-Queue (z.B. `TTS` oder `Parallel`).
3. Füge **Trigger** hinzu (z.B. `twitch_command` `!hallo` oder Kanalpunkte-Einlösung).
4. Füge **Sub-Actions** hinzu (z.B. `play_sound`, `elevenlabs_tts`, `twitch_disable_reward`, `obs_scene`).
5. Öffne **`⚙ Queues`**, um Verzögerungen einzustellen oder Queues zu pausieren.
6. Klicke auf **"Save Actions"**.

---

## 🌐 Web Dashboard & Overlay

Das Web-Dashboard ist nach dem Start erreichbar unter:
```
http://localhost:8000/interface/dashboard.html
```

---

## 📄 Lizenz

Lizenziert unter der [MIT License](LICENSE).
