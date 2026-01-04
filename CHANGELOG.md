# Changelog

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
