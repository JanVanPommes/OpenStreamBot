# OpenStreamBot

**Version:** 0.1.2 Alpha  
**A Multi-Platform Stream Bot for Twitch & YouTube**

OpenStreamBot is an open-source bot for streamers that integrates Twitch and YouTube, can control OBS Studio, and offers a flexible action system. Perfect for creators who want to automate and make their streams more interactive.

---

## 🎯 Features

- **Multi-Platform Chat**: Twitch and YouTube Live Chat in one dashboard
- **OBS Studio Integration**: Switch scenes, control sources, react to OBS events
- **Flexible Action System**: 
  - Create custom commands (!command)
  - Play sounds (with auto-stop & device selection)
  - **New:** Playlists (Random music folder playback)
  - **New:** YouTube Shorts (Random Shorts playback with Overlay)
  - **New:** Auto-Ducking (Lowers music during videos)
  - **New:** Timer Triggers (Interval based actions)
  - React to events (raids, subs, etc.)
  - Grouping and organization
- **Profile Manager**: Save and load different bot configurations
- **Web Dashboard**: Modern web UI for chat management and overview
- **Quota Optimization**: Activate YouTube only on-demand (saves API quota)
- **GUI Launcher**: Easy management via desktop application

---

## 📋 Requirements

- **Python 3.10+** (recommended: 3.12)
- **OBS Studio** (optional, for OBS features)
- **OBS WebSocket Plugin** (integrated in OBS 28+)
- **Operating System**: Linux, macOS, or Windows

---

## 🚀 Installation

### 🛠️ OS-Specific Installation

#### **Windows**
1. **Install Python**: Download Python 3.10+ from [python.org](https://www.python.org/downloads/windows/) (Check "Add Python to PATH"!).
2. **Clone**: `git clone https://github.com/JanVanPommes/OpenStreamBot.git`
3. **Setup**: Double-click `start.bat`. It will help you create a venv on first run.
   - *Manual alternative*:
     ```cmd
     python -m venv venv
     venv\Scripts\activate
     pip install -r requirements.txt
     ```

#### **macOS**
1. **Python / Homebrew**: `brew install python` (standard if Homebrew is installed).
2. **Clone**: `git clone https://github.com/JanVanPommes/OpenStreamBot.git`
3. **Setup**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   chmod +x start_launcher.sh
   ```

#### **Linux (Ubuntu/Debian)**
1. **Prerequisites**:
   ```bash
   sudo apt update
   sudo apt install python3-venv python3-tk
   ```
2. **Clone & Setup**:
   ```bash
   git clone https://github.com/JanVanPommes/OpenStreamBot.git
   cd OpenStreamBot
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   chmod +x start_launcher.sh
   ```

### 4. Create Configuration
Copy the example configuration:
```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` with your data:
```yaml
server:
  host: localhost
  port: 8080

twitch:
  enabled: true
  client_id: YOUR_TWITCH_CLIENT_ID      # From https://dev.twitch.tv/console
  client_secret: YOUR_TWITCH_SECRET
  channel: your_twitch_username

youtube:
  enabled: true  # Set to false if not needed
  client_secret_file: client_secret.json
  token_file: token_youtube.json

obs:
  host: localhost
  port: 4455
  password: ''  # Your OBS WebSocket password (if set)
```

---

## 🔐 Connect Accounts

### Twitch
1. Create an app on [Twitch Developer Console](https://dev.twitch.tv/console/apps)
2. **OAuth Redirect URL**: `http://localhost:8080`
3. Copy **Client ID** and **Secret** to `config.yaml`
4. Start the launcher: `python launcher.py`
5. Go to **Accounts** → **"Login with Twitch"**

### YouTube (Optional)
For YouTube, you need your own Google Cloud Project due to API quota limits.

➡️ **Detailed Guide**: See [`YOUTUBE_SETUP_EN.md`](YOUTUBE_SETUP_EN.md)

**Quick Summary**:
1. [Google Cloud Console](https://console.cloud.google.com/) → Create project
2. Enable YouTube Data API v3
3. Create OAuth Client (Desktop App)
4. Download `client_secret.json` and place in project folder
5. In Launcher: **Accounts** → **"Login with Google"**

---

## ▶️ Start Bot

- **Windows**: Double-click `start.bat`
- **Linux/macOS**: `./start_launcher.sh` in terminal or `python launcher.py`
```bash
# Manual execution
python launcher.py
```

- **Dashboard**: Start/stop bot, view logs
- **Settings**: Edit config
- **Accounts**: Manage Twitch/YouTube login
- **Actions Editor**: Create custom commands and actions
- **Profiles**: Switch between different configurations

### Headless (bot only, no GUI)
```bash
python main.py
```

---

## 🎮 OBS Studio Setup

1. **Start OBS** (version 28+ recommended)
2. **Tools** → **WebSocket Server Settings**
3. **Enable Server** (default port 4455)
4. Optional: **Set password** (then add to `config.yaml`)
5. Start bot → Connection established automatically

---

## 📝 Create Actions

The action system allows you to create custom commands and reactions:

### Example: Sound Command
1. Start launcher → **Actions Editor** tab
2. Click **"+ New Action"**
3. Name: `Fanfare`
4. **"+ Add Trigger"** → `twitch_command` → `!fanfare`
5. **"+ Add Sub-Action"** → `play_sound` → Select sound file
6. **"Save Actions"**

Now `!fanfare` in chat will play the sound! 🎺
174: 
175: ### New in 0.1.1:
176: - **Profiles**: Use the **Profiles** tab in the launcher to save your current config as a named profile (e.g. "Gaming", "Just Chatting") and switch between them.
177: - **Audio Devices**: In `play_sound` or `playlist` actions, you can now select a specific audio output device.
178: - **Playlist**: Add a `playlist` sub-action, select a music folder, and the bot will play random songs from it continuously. Stop it with `stop_playlist`.
179: - **Timer**: Use the `timer` trigger to run actions every X seconds (e.g. for chat announcements).
180: 
181: ### More Possibilities:

### More Possibilities:
- **Switch OBS scene** on specific commands
- **Send chat messages** as responses
- **Delays** between actions
- **Stop sounds** after X seconds

---

## 🌐 Web Dashboard

Available after starting at:
```
http://localhost:8000/interface/dashboard.html
```

Features:
- Live chat view (Twitch + YouTube combined)
- Send messages
- Emote support
- Badge display (Mod, VIP, Sub, etc.)

---

## 📊 Project Structure

```
OpenStreamBot/
├── launcher.py              # GUI Launcher
├── main.py                  # Main program (headless)
├── config.yaml              # Your configuration
├── actions.yaml             # Saved actions
├── requirements.txt         # Python dependencies
├── YOUTUBE_SETUP_EN.md      # YouTube API Setup Guide
│
├── core/                    # Core modules
│   ├── event_server.py      # WebSocket event system
│   ├── action_engine.py     # Action execution
│   └── http_server.py       # Web server for dashboard
│
├── platforms/               # Platform integrations
│   ├── twitch_bot.py        # Twitch chat bot
│   ├── youtube_bot.py       # YouTube live chat
│   └── obs_controller.py    # OBS WebSocket client
│
└── interface/               # GUI & web interfaces
    ├── gui_actions.py       # Actions editor (GUI)
    ├── dashboard.html       # Web dashboard
    └── dashboard.js         # Dashboard logic
```

---

## 🛠️ Troubleshooting

### "Port 8000 / 8080 already in use"
An old bot process is still running in the background:
```bash
pkill -f main.py
```
Or: Close launcher completely, wait briefly, restart.

### YouTube: "Quota Exceeded"
- **Cause**: Daily API limit reached (10,000 units)
- **Solution**: 
  - Use the **"Connect YouTube Stream"** button only when needed
  - Quota resets daily around 9:00 AM CET
  - See [`YOUTUBE_SETUP_EN.md`](YOUTUBE_SETUP_EN.md) for optimization tips

### OBS not connecting
- Check if **WebSocket Server** is enabled in OBS
- Password correct in `config.yaml`?
- OBS running on the same PC?

### Sounds not playing
- File format supported? (MP3, WAV, OGG)
- File path correct? (Use absolute paths)
- Check logs for error messages

---

## 🤝 Contributing

Contributions are welcome! 

1. Fork the repository
2. Create feature branch: `git checkout -b feature/MyFeature`
3. Commit: `git commit -m 'Add: My new feature'`
4. Push: `git push origin feature/MyFeature`
5. Open pull request

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 🐛 Bug Reports & Feature Requests

Use [GitHub Issues](https://github.com/JanVanPommes/OpenStreamBot/issues) to:
- Report bugs
- Suggest features
- Ask questions

---

## 🙏 Credits

- **TwitchIO**: Twitch chat integration
- **Google APIs**: YouTube live chat
- **obs-websocket-py**: OBS Studio control
- **CustomTkinter**: Modern GUI
- **Pygame**: Audio playback

---

**Good luck with your stream! 🎬🚀**
