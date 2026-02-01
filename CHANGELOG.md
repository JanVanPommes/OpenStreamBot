# Changelog

## [0.3.0 Beta] - 2026-02-01
### WICHTIG / IMPORTANT
- **Twitch Login**: Bitte lösche die Datei `token_twitch.json` und melde dich neu an! Es wurden neue Berechtigungen (Scopes) für Kanalpunkte und Follower hinzugefügt.
- **Twitch Login**: Please delete `token_twitch.json` and login again! New scopes for Channel Points and Followers have been added.

### Neu / New
- **User Permissions**: Aktionen können nun auf bestimmte Nutzergruppen beschränkt werden (Broadcaster, Moderator, VIP, Subscriber).
  - Actions can now be restricted to specific user roles.
- **HotSwitch**: Aktionen können nun "on-the-fly" aktiviert/deaktiviert werden, ohne den Bot neu zu starten.
  - Actions can now be toggled on/off instantly without restart.
- **Timer Management**: Timer starten/stoppen nun automatisch, wenn die zugehörige Aktion aktiviert/deaktiviert wird.
  - Timers now start/stop automatically when their action is toggled.
- **Action State Sub-Action**: Neue Sub-Action zum automatischen Aktivieren/Deaktivieren anderer Aktionen (mit optionalem Timer).
  - New Sub-Action to enable/disable other actions automatically (with optional duration).
- **Channel Points Manager**: Neuer Tab zum Verwalten von Kanalpunkt-Belohnungen (Erstellen, Bearbeiten, Löschen).
  - New tab to manage Channel Points Rewards.
- **Twitch Trigger**: Auslösen von Aktionen bei Kanalpunkt-Einlösungen.
  - Trigger actions on Channel Point Redemptions.
- **YouTube Chat Trigger**: Separater Trigger für YouTube Chat Befehle.
  - Distinct trigger for YouTube Chat commands.
- **Action Cooldown**: Aktionen können nun eine Abklingzeit (Cooldown) haben.
  - Actions can now have a cooldown.
- **Window Resizing**: Das Fenster kann nun kleiner gezogen werden (min. 900x600).
  - Window minimum size reduced to 900x600.
- **Update Safety**: `actions.yaml` wird nicht mehr überschrieben. Neue Scopes werden automatisch geprüft.
  - `actions.yaml` is safe from overwrites.

### Fixes
- **YouTube Shorts**: Sync-Fehler und Abspiel-Bug behoben.
- **Scrolling**: Mausrad-Scrollen in der Belohnungsliste behoben.
- **Twitch Scopes**: Fehlende Berechtigung für Kanalpunkte hinzugefügt.


## [0.2.2 Beta] - 2026-01-21
### Fixed
- **Update Loop**: Bumped version to `0.2.2` to resolve an issue where the launcher constantly requested an update.
- **Twitch OAuth**: Fixed "Resource not found" error on Windows by implementing explicit root routing for the callback.

## [0.2.1 Beta] - 2026-01-10
### Fixed
- **Twitch Authentication**: Fixed "redirect_mismatch" error by allowing custom `redirect_uri` in `config.yaml`.
- **Local Webserver**: Now listens on `0.0.0.0` (all interfaces) to resolve IPv4/IPv6 localhost binding issues on Windows.
- **Login Feedback**: Detailed error messages are now shown in the browser if the Twitch login fails.

## [0.2.0 Beta] - 2026-01-09
### Added
- **Windows Installer**: Easier installation via `OpenStreamBot_Setup.exe` (no Python installation required).
- **Executable Support**: Bot now runs as a standalone `OpenStreamBot.exe` on Windows.
- **Build System**: New `build.py` script to generate executables and installers using PyInstaller.
- **Auto-Update Check**: Launcher now notifies you when a new version is available on GitHub.
- **CI/CD**: Automatic build of Windows Installer via GitHub Actions on every push.

## [0.1.3 Alpha] - 2026-01-07

### Added
- **YouTube Quota Optimization**: Reduced API consumption by ~87%, allowing 7+ hour streams within the 10,000 unit limit.
- **Manual Stream Trigger**: New "▶ YouTube Start" button in the Dashboard for precise control and unit savings.
- **Quota Monitoring**: Real-time tracking of used API units in the console and persistent `youtube_quota.json` storage.
- **Chat ID Caching**: Active Chat IDs are now cached to resume sessions without redundant API calls.

### Changed
- **Aggressive Polling**: Increased minimum polling interval for YouTube Chat to 15 seconds.
- **Stream Discovery**: Automatic stream checking reduced to once every 10 minutes (favoring manual start).

### Fixed
- **Quota Exceeded Crashes**: Improved error handling for 403/404 errors during YouTube polling.

## [0.1.2 Alpha] - 2026-01-05

### Added
- **YouTube Shorts**: Play random Shorts from a channel with a dedicated browser overlay (`youtube_random_short`).
- **Volume Control**: Sliders (0-100%) for Global Volume (`set_volume`) and Per-Action Volume (`play_sound`, `playlist`).
- **Auto-Ducking**: Playlist volume automatically drops to 5% when a YouTube Short plays and restores afterwards.
- **Action Chaining**: New `trigger_action` sub-action allows actions to trigger other actions by name.
- **Action Reordering**: Triggers and Sub-Actions can now be reordered in the GUI using Up/Down arrows.
- **Session Logging**: Logs are now saved to files (`session.0.log`, etc.) with 3-session rotation.
- **Overlay Improvements**: YouTube Overlay now shows a black screen when inactive.

### Fixed
- **Overlay Connectivity**: Fixed WebSocket port mismatch preventing the overlay from connecting.
- **UI Duplicates**: Removed duplicate entries in the Action Type selectors.
- **Playback**: Fixed issues where YouTube Shorts would not report their "Ended" state correctly.

## [0.1.1 Alpha] - 2026-01-04

### Added
- **Profile System**: Create, save, load, and delete bot configuration profiles directly from the Launcher.
- **Playlist Action**: New sub-action to play random audio files from a folder continuously.
- **Timer Trigger**: Execute actions automatically at set intervals.
- **Audio Device Selection**: Select a specific audio output device for `play_sound` and `playlist` actions.
- **Fade Out**: `stop_playlist` now smoothly fades out music over 1.5 seconds.
- **Process Cleanup**: Launcher now automatically detects and kills orphaned bot processes to prevent port conflicts.

### Fixed
- **Port Usage**: Fixed "Address already in use" errors by enabling `SO_REUSEADDR` and improving process termination.
- **Command Recognition**: Commands are now recognized even if the Web Dashboard is closed.
- **Twitch Chat**: Usernames now display with correct capitalization (Display Name).

### Changed
- **Documentation**: `README.md` is now in English by default (German moved to `README_DE.md`).
