# Changelog

All notable changes to OpenStreamBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0-alpha] - 2025-12-28

### Added
- **Multi-Platform Chat Integration**
  - Twitch chat support with OAuth authentication
  - YouTube Live Chat integration with quota optimization
  - Manual YouTube stream connection to save API quota
  
- **OBS Studio Integration**
  - WebSocket connection to OBS
  - Scene switching via actions
  - React to OBS events (scene changes)

- **Flexible Action System**
  - Custom chat commands (!command)
  - Event triggers (raids, subs, OBS scenes)
  - Sub-actions: play sounds, delays, chat responses, OBS control
  - Action grouping and organization
  - Sound playback with auto-stop functionality

- **GUI Launcher**
  - Modern dark theme with CustomTkinter
  - Dashboard tab for bot control and logs
  - Settings editor for config.yaml
  - Accounts management (Twitch/YouTube login)
  - Actions Editor with visual trigger/sub-action builder

- **Web Dashboard**
  - Real-time chat view (Twitch + YouTube combined)
  - Send messages to chat
  - Emote rendering support
  - Badge display (Mod, VIP, Sub, Broadcaster)
  - Reconnection handling (10s interval)

- **Documentation**
  - Bilingual documentation (German & English)
  - Comprehensive README with installation guide
  - YouTube API setup guide with quota optimization tips
  - Troubleshooting section

- **Branding**
  - Professional logo design
  - Modernized UI text styling
  - Consistent branding across launcher and web dashboard

### Technical Details
- Python 3.10+ support
- Dependencies: TwitchIO, Google APIs, obs-websocket-py, CustomTkinter, Pygame
- Async architecture with asyncio
- WebSocket event server for real-time communication
- HTTP server for web dashboard

### Known Limitations
- YouTube quota limited to 10,000 units/day (requires personal API project)
- OBS WebSocket must be enabled manually
- Port conflicts can occur if bot doesn't shut down cleanly

---

**Full Changelog**: First Alpha Release
