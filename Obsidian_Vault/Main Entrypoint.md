# Main Entrypoint (main.py)

The starting point of the Saturday application. It initializes threads, sets up configuration checks, and starts the Qt main loop.

## Connections
- Launches [[User Interface (UI)]] to show the diagnostic panel.
- Spawns background worker thread to run [[Session Manager]] connection loop.
- Forces [[Memory Manager]] write-flush on exit to guarantee saved turns are encrypted.