# Memory Manager (memory/memory_manager.py)

Responsible for processing and saving information about the user across sessions.

## Key Features
- **Turn Accumulator**: Batches conversation turns (threshold: 5 turns).
- **Gemini Structured Output**: Uses Gemini API to extract name, facts, project details, and preferences.
- **AES Encryption**: Encrypts extracted memories into `long_term.json`.
- **Idle & Exit Flushes**: Auto-flushes memories on 15s idle or application close.

## Connections
- Receives turns from [[Session Manager]].
- Feeds data to [[User Interface (UI)]]'s user profile dashboard.