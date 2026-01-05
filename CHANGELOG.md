# Changelog

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
