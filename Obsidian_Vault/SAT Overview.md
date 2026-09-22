# S.A.T.U.R.D.A.Y Assistant (SAT)

Welcome to the documentation vault for Saturday Assistant. Saturday is a high-performance voice-activated desktop assistant integrated with Gemini Live API, featuring real-time speech, memory retention, system monitoring, and tool actions.

## Core Architecture Nodes
- [[Main Entrypoint]] - The main thread entry point.
- [[User Interface (UI)]] - The Qt6 GUI panel.
- [[Session Manager]] - Gemini Live session connection loop.
- [[Memory Manager]] - Encrypted long-term memory extraction.
- [[Tool Dispatcher]] - Translates AI requests to actions.
- [[Actions & Tools]] - Tool implementations.