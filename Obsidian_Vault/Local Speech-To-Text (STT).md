# Local Speech-To-Text (core/local_stt.py)

Handles offline speech recognition when the Gemini Live server is offline.

## Implementation
- Uses Python `speech_recognition` package.
- Utilizes Google Web Speech API as a lightweight fallback.

## Connections
- Linked to [[Session Manager]] voice input capture fallback.