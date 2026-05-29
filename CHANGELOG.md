# Changelog

## [0.5.0] - 2026-05-06
### Added
- **Stream Deck & OpenDeck Plugin**: Native support for Elgato Stream Deck and OpenDeck via a local `.sdPlugin`. Easily trigger OpenStreamBot actions by name using physical buttons.
- **YouTube Events**: Added triggers for YouTube specific events, including **New Memberships**, **Member Milestones** (with month filtering), and **Super Chats** (with amount filtering).
- **Twitch Watch Streaks**: Added a trigger for Twitch Watch Streaks, allowing you to react to specific viewer streak milestones.
- **Animated & Gigantified Emotes**: The OBS Chat Dock now fully supports Twitch animated emotes. "Emote Only" messages scale up correctly, and emotes gigantified via Bits display at maximum size.
- **Action Group Persistence**: The Action Editor now remembers which action groups you have collapsed or expanded across restarts.
- **Linux App Launcher**: The bot now automatically creates a `.desktop` shortcut on Linux systems for easy launching from application menus or OpenDeck.

### Fixed
- **Twitch Moderation Commands**: Fully migrated the "Twitch Befehl ausführen" sub-action (Announce, Ban, Timeout, VIP, etc.) from deprecated IRC chat commands to the modern Twitch Helix API. This restores full functionality.
- **Action Editor UI Bug**: Fixed a bug where the sub-action configuration form for "Twitch Befehl ausführen" and "YouTube Nachricht" would unexpectedly disappear or render completely empty.
## [0.4.0] - 2026-05-06
### Added
- **ElevenLabs TTS**: New sub-action to generate and play text-to-speech using the ElevenLabs API.

### Fixed
- **Twitch Authentication**: Resolved a recurring authentication bug that forced a Twitch re-login on system startup. Implemented network-aware token validation to gracefully handle offline boots and prevent "Could not fetch Broadcaster ID" errors.
- **OBS Browser Docks**: Fully resolved UI caching issues when loading the dashboard in OBS browser docks.

## [0.3.4 Beta] - 2026-03-19
### Fixed
- **Action Editor UI**: Increased the height of the Trigger Dialog to ensure the "Add/Save" button is fully visible.
- **Twitch Clip Scope**: Added the missing `clips:edit` scope to the Twitch authentication flow to fix permission errors.
- **Twitch Authentication Persistence**: Fixed a bug where a PC restart would cause Twitch authentication to fail by correcting the OAuth token payload format.

## [0.3.3 Beta] - 2026-02-22
### Added
- **Action Groups**: New sub-action (`random_action_group`) to randomly select and execute one of several nested sub-actions based on configurable probabilities. Perfect for diverse random responses.
- **YouTube First Words**: New trigger (`youtube_first_message`) corresponding to Twitch's First Words, firing when a user sends their first chat message of the stream.
- **User Blacklist for Triggers**: You can now define a comma-separated list of usernames to ignore for specific triggers (e.g. keeping bots out of "First Words").
- **UI Polish**: Complete visual overhaul of the Launcher and Action Editor. Introduced a modern "Card" design with rounded corners, better spacing, and distinct accent colors to improve readability and user experience.

### Fixed
- **Action Editor Layout**: Fixed an issue where the `CTkScrollableFrame` would overlap and block clicks on the "Add Trigger" / "Add Sub-Action" buttons. Add-buttons are now securely anchored at the bottom.
- **Action Group Persistence**: Fixed a bug where actions belonging to a group would "lose" their group assignment in the UI after a restart.
## [0.3.2 Beta] - 2026-02-18
### Added
- **First Words Trigger**: New trigger type (`twitch_first_message`) that fires only on the first message of a user in the current session. Can be restricted to a specific user.
- **Twitch Clips**: New sub-action (`twitch_create_clip`) to create a clip of the stream. Includes option to post the clip link to chat.
- **Probability**: Sub-actions can now have a probability (0-100%) of executing. Useful for random sound effects or events.
- **C# Code Execution**: New sub-action (`execute_csharp`) to run external scripts or programs.
    - **Modes**: Project (`.csproj`), Script (`.csx`), Executable (`.exe`), and **Direct Code Input** (with built-in editor).
    - **Variables**: Scripts can return data to the bot using `SetVar: key=value`.
    - **Example**: Added `scripts/counter.csx` showcasing persistent variables.
- **GUI Improvements**:
    - `SubActionDialog` is now larger and scrollable to accommodate complex configurations.
    - Added visible version number to the Launcher sidebar.
- **Twitch Auth Update**: Improved token handling to better preserve `refresh_token` across restarts.

### Fixed
- **First Words Logic**: Fixed a bug where the user filter for the First Words trigger was ignored.
- **UI Overflow**: Fixed an issue where the "Save" button in the SubActionDialog was hidden for actions with many options.
- **C# Execution**: Fixed `dotnet-script` not being found on Linux by automatically adding `~/.dotnet/tools` to PATH.

## [0.3.1 Beta] - 2026-02-09
### Fixed
- **Twitch Rewards List**: Fixed an issue where the list of available Channel Points rewards was not loading in the Action Editor.
- **WebSocket Port Mismatch**: Fixed a clearer bug where the GUI tried to connect on port 8000 even if the bot was configured for 8080 (or other ports).
- **Twitch Cooldown Handling**: 
    - Implemented **Native Cooldown Sync**: Actions with a cooldown now automatically update the corresponding Twitch Reward to have a Global Cooldown, preventing users from redeeming it while it's unavailable.
    - Added **Automatic Refund**: As a fallback, if a redemption still goes through during a cooldown (race condition), the points are automatically refunded to the user.
- **Bot Startup**: Fixed a race condition where the bot would signal "Ready" before it had fully loaded channel information.

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
