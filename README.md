# PRIME AI :: AUTONOMOUS NEURAL COCKPIT
> **[ Zero GUI · 24/7 Voice Driven · Pure Power ]**  
> Autonomous Digital Cockpit Built for Pratik Thorat.

---

## Overview

**PRIME AI** is a completely headless, zero-GUI, voice-first desktop operating intelligence. Designed for instant, 24/7 ambient control of Windows without touching a keyboard or mouse.

- **🎙️ Ambient 24/7 Listening:** Open-mic continuous ambient audio capture with automatic speech recognition and instant execution.
- **🔊 Elite Male Neural Voice:** Powered by Microsoft Neural Speech (`en-GB-RyanNeural`), delivering a refined, calm, and authoritative British voice persona with zero cloud lag and offline fallback to Microsoft David.
- **🧠 Cognitive Intelligence:** Powered by Google Gemini (`gemini-3.6-flash`) with dynamic multi-turn conversation and native function calling.
- **⚡ Deep Desktop Automation (200+ Actions):** Inherited full power from `IP-Prime` and `desktop_agent` — Spotify control, web browsing, application launching, volume & window management, screen OCR, filesystems, and custom Python execution.

---

## Quick Start

### 1. Launch 24/7 Voice Assistant
Double-click `run.bat` or `VOICE_24_7.bat` in File Explorer:
```cmd
run.bat
```
The neural listener calibrates ambient noise and enters continuous listening mode. Speak directly into your microphone:
- *"Open YouTube"*
- *"What is my CPU and RAM usage?"*
- *"Play lofi music on Spotify"*
- *"Open VS Code and Notepad"*
- *"Set volume to 50 percent"*
- *"Take a screenshot"*

### 2. Interactive CLI Mode
If you prefer a rich terminal interface with status tables and interactive typing + voice:
```cmd
python prime.py
```
- Type any command or question
- `/v` or `/mic`: Activate one-shot voice command
- `/tools`: List all 200+ registered desktop automation tools
- `/speak <text>`: Test the neural male voice output
- `/system`: Show live hardware telemetry (CPU, RAM, Disks, Battery)

---

## Architecture

```
                                  ┌───────────────────────────┐
                                  │    Ambient Microphone     │
                                  └─────────────┬─────────────┘
                                                │ (continuous audio)
                                                ▼
┌───────────────────────────┐     ┌───────────────────────────┐
│     voice_engine.py       │◄────┤    voice_assistant.py     │
│  (Edge-TTS RyanNeural +   │     │ (SpeechRecognition, VAD,  │
│   Pygame / pyttsx3)       │     │  Chimes, Noise Calib.)    │
└───────────────────────────┘     └─────────────┬─────────────┘
                                                │ (transcribed text)
                                                ▼
                                  ┌───────────────────────────┐
                                  │        ai_agent.py        │
                                  │ (Gemini 3.6 Flash Engine) │
                                  └─────────────┬─────────────┘
                                                │ (tool calling loop)
                                                ▼
                                  ┌───────────────────────────┐
                                  │    tool_definitions.py    │
                                  │  ├── desktop_agent (58)   │
                                  │  └── IP-Prime (140+)      │
                                  └───────────────────────────┘
```

---

## Configuration

Settings are stored in `.env` (never committed to version control):
```env
GEMINI_API_KEY=your_gemini_api_key_here
DEFAULT_MODEL=gemini-3.6-flash
TTS_VOICE=en-GB-RyanNeural
TTS_ENGINE=edge-tts
STT_MICROPHONE_INDEX=
```
