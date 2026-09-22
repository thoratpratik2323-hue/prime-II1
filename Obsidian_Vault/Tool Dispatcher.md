# Tool Dispatcher (core/tool_dispatcher.py)

Translates JSON tool calls requested by the Gemini Live server into executable local python methods.

## Key Features
- Defines schema parameters (e.g. `query` parameter for music controls).
- Executes tasks asynchronously to prevent UI freeze.

## Connections
- Dispatches commands to [[Actions & Tools]].
- Reports results back to [[Session Manager]] to reply to the user.