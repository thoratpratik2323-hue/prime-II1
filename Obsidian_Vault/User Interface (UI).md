# User Interface (ui.py)

A premium cyberpunk Qt6 diagnostic panel that displays metrics, logs, and system status in real-time.

## Key Sub-components
- **HudCanvas**: Displays a glowing visualizer orb, diagnostic metrics, and rotating telemetry circles.
- **MediaWaveVisualizer**: Redesigned mirrored gradient voice waveform.
- **Settings Panel**: Settings for voice selection (Charon, Puck, Fenrir, Kore, Aoede), custom wake words, and headless browser.
- **User Profile Widget**: Displays personal facts retrieved from [[Memory Manager]].

## Connections
- Connects settings triggers to [[Session Manager]].
- Receives logs and audio activity signals from [[Session Manager]] to animate the HUD.
- Interacts with [[Main Entrypoint]] on startup/shutdown.