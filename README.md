# OpenStreamBot

**Version:** 0.6.1  
**Author:** JanVanPommes  
**A Multi-Platform Stream Bot for Twitch & YouTube**

OpenStreamBot is a powerful, open-source automation bot for streamers that integrates Twitch and YouTube, controls OBS Studio, and provides a multi-queue action system with audio, overlays, and hardware stream deck support.

---

## 🎯 Key Features (v0.6.0)

- **⚡ Multi-Queue Action Architecture**:
  - Assign actions to dedicated execution queues (`Default`, `TTS`, `Overlays`, `SoundFX`, or `Parallel`).
  - Configure delays between queue items, pause/resume queues on demand, or clear pending tasks.
  - Live Action Queue Status widget in the Control Center dashboard.
- **📦 Full Backup & Migration System**:
  - Export complete bot profiles into `.osbbackup` ZIP archives including all local audio, scripts, and image assets.
  - One-click import to restore profiles on any new OpenStreamBot installation.
- **💜 Advanced Twitch Integration**:
  - React to Chat Commands, Raids, Subscriptions, Followers, First Words, Watch Streaks, and Channel Point Redemptions.
  - **Dynamic Reward Controls**: Enable (`twitch_enable_reward`) or Pause (`twitch_disable_reward`) Twitch Channel Point rewards on the fly without deleting them.
  - Full support for animated chat emotes and scaled "Emote Only" chat messages.
- **🔴 YouTube Live Chat & Events**:
  - Trigger actions on YouTube Chat Messages, YouTube First Words, New Memberships, Member Milestones, and Super Chats.
  - Play random YouTube Shorts with overlay auto-ducking.
- **🗣️ ElevenLabs Text-to-Speech (TTS)**:
  - Generate natural AI voice output directly from chat triggers or sub-actions.
- **🎮 Stream Deck & OpenDeck Support**:
  - Native `.sdPlugin` for Elgato Stream Deck and OpenDeck controllers to trigger actions by name with physical buttons.
- **🎥 OBS Studio Integration**:
  - Control OBS WebSocket 5.x: Switch scenes, toggle sources, change audio filters, and capture screenshots.
- **⚙️ Modern GUI Launcher & Settings**:
  - Structured card-based Configuration screen for Twitch, YouTube, OBS, and Audio settings.
  - Smooth action editor with zero UI flickering and 100% reliable sub-action list scrolling.

---

## 📋 Requirements

- **Python 3.10+** (recommended: 3.12)
- **OBS Studio** (optional, for OBS features)
- **OBS WebSocket Plugin** (built into OBS 28+)
- **Operating System**: Linux, macOS, or Windows

---

## 🚀 Installation & Setup

### 📦 Windows Setup (Installer / Direct)

1. Download `OpenStreamBot_Setup.exe` from [Releases](https://github.com/JanVanPommes/OpenStreamBot/releases).
2. Run the setup wizard and start **OpenStreamBot** from your Start Menu or Desktop shortcut.

### 🛠️ Manual Installation (Linux / macOS / Windows)

```bash
# Clone the repository
git clone https://github.com/JanVanPommes/OpenStreamBot.git
cd OpenStreamBot

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the Launcher GUI
python launcher.py
```

---

## 🔐 Account Connection

### Twitch Setup
1. Go to **Accounts** → Click **"Login with Twitch"**.
2. Follow the web authorization to grant bot permissions for chat, channel points, clips, and moderation commands.

### YouTube Setup (Optional)
1. Create a Google Cloud project and enable **YouTube Data API v3**.
2. Download `client_secret.json` into the OpenStreamBot folder.
3. In **Accounts** → Click **"Login with Google"**.

---

## 📝 Creating Actions & Queues

1. Open the **Actions Editor** tab in the Launcher.
2. Click **"+ New Action"** and select an Execution Queue (e.g. `TTS` or `Parallel`).
3. Add **Triggers** (e.g. `twitch_command` `!hello` or `twitch_redemption`).
4. Add **Sub-Actions** (e.g. `play_sound`, `elevenlabs_tts`, `twitch_disable_reward`, `obs_scene`).
5. Open **`⚙ Queues`** to set delays between actions or pause specific queues.
6. Click **"Save Actions"**.

---

## 🌐 Web Dashboard & Overlay

Access the built-in web dashboard at:
```
http://localhost:8000/interface/dashboard.html
```
Features:
- Unified live chat (Twitch + YouTube) with badges & animated emotes.
- OBS Browser Dock compatible overlay.

---

## 📄 License

Distributed under the [MIT License](LICENSE).
