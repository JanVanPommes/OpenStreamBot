# Changelog

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
