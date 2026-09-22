# Session Manager (core/session_manager.py)

Manages real-time Gemini Live WebSocket connection loop. It captures microphone audio chunks, streams speaker responses, and processes live actions.

## Key Features
- **Wake Word Detection**: Spotter checks config for custom words.
- **Offline TTS Fallback**: Falls back to Windows SAPI5 (`comtypes.SpVoice`) if server is disconnected.
- **Offline STT Fallback**: Uses Google Web Speech API if live connection fails.

## Connections
- Pulls configuration from settings.
- Feeds conversation history to [[Memory Manager]] for retention.
- Routes tool execution requests to [[Tool Dispatcher]].
- Updates [[User Interface (UI)]] with streaming logs and audio levels.