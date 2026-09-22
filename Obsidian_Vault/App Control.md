# App Control (actions/open_app.py & actions/switch_app.py)

Launches and switches native Windows applications.

## Implementation
- Uses `win32gui` and `win32process`.
- Implements callback preservation to prevent python WNDENUMPROC garbage collection crashes.

## Connections
- Part of [[Actions & Tools]].