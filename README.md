# ⚡ PRIME AI :: AUTONOMOUS NEURAL DESKTOP OPERATING SYSTEM
> **[ Zero GUI · 24/7 Hands-Free Ambient Voice · Deep OS Dominion · Multi-Brain Failover ]**  
> *Engineered for Pratik Thorat (`thoratpratik2323-hue`)*

[![Windows OS](https://img.shields.io/badge/OS-Windows_11_%2F_10-0078D6?style=for-the-badge&logo=windows)](https://microsoft.com)
[![Python 3.12](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Gemini 2.5](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4?style=for-the-badge&logo=google)](https://aistudio.google.com)
[![Groq LPU](https://img.shields.io/badge/Groq-500+_Tokens/sec-F55036?style=for-the-badge&logo=fastapi)](https://groq.com)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-450+_Models-6366F1?style=for-the-badge)](https://openrouter.ai)
[![Single Instance Mutex](https://img.shields.io/badge/Architecture-Windows_Named_Mutex-success?style=for-the-badge)](https://github.com/thoratpratik2323-hue/prime-II1)

---

## 🌟 Executive Overview

**PRIME AI** is an autonomous, headless, voice-first digital desktop operating intelligence. It gives you 100% complete hands-free dominion over your Windows PC without touching a mouse or keyboard.

From typing code, clicking buttons, controlling browsers, managing files, to running PowerShell scripts and viewing your monitor with multimodal AI vision—Prime handles it in real time while you speak naturally in **Hinglish** or **English**.

```
              ██████╗ ██████╗ ██╗███╗   ███╗███████╗     █████╗ ██╗
              ██╔══██╗██╔══██╗██║████╗ ████║██╔════╝    ██╔══██╗██║
              ██████╔╝██████╔╝██║██╔████╔██║█████╗      ███████║██║
              ██╔═══╝ ██╔══██╗██║██║╚██╔╝██║██╔══╝      ██╔══██║██║
              ██║     ██║  ██║██║██║ ╚═╝ ██║███████╗    ██║  ██║██║
              ╚═╝     ╚═╝  ╚═╝╚═╝╚═╝     ╚═╝╚══════╝    ╚═╝  ╚═╝╚═╝
  ⚡ AUTONOMOUS NEURAL COCKPIT :: ZERO GUI · 24/7 AMBIENT VOICE · PURE POWER
```

---

## 🚀 Key Architectural Pillars

### 1. 🎙️ 24/7 Ambient Listening & Smart Hardware Mic
- **Always-On Open Mic:** Hands-free background listening with high-sensitivity Speech Recognition tuned for Indian English & Hinglish (`en-IN`).
- **Headset Auto-Detection:** Automatically spots active Bluetooth headsets (e.g. `FT_38102_4268 Hands-Free`) to prevent internal microphone deadness.
- **Faster-Whisper Offline Fallback:** Local offline STT when internet is unavailable.

### 2. 🧠 Multi-Brain Intelligent Failover Ladder
Prime never goes down. If one API hits rate limits or latency spikes, the neural switcher automatically cascades to the next best provider:
```mermaid
graph TD
    User([🎙️ Voice / Prompt]) --> Core[Prime AI Agent]
    Core -->|Primary| G[Google Gemini 2.5 Flash]
    G -.->|Failover 429| Q[Groq LPU 500+ t/s]
    Q -.->|Failover| OR[OpenRouter Aggregator]
    OR -.->|Failover| C[Cerebras AI 2100 t/s]
    C -.->|Failover| GH[GitHub Models / Azure AI]
    GH -.->|Offline| L[Local Ollama / Local Fallback]
```

### 3. 🖱️ Complete Windows OS Dominion (71+ Native Tools)
Prime interacts with Windows exactly like a human engineer:
- **Mouse Control:** `mouseClick(x, y, button, clicks)`, `mouseMove(x, y, duration)`, `mouseScroll(clicks)`, `getCursorPosition()`
- **Keyboard Execution:** `typeText(text, interval)`, `pressHotkey(keys)` (`["ctrl", "c"]`, `["alt", "tab"]`, `["win", "d"]`)
- **Multimodal Screen Vision:** `analyzeScreenWithAI(prompt)` captures real-time high-res screen state and feeds it to Gemini 2.5 Flash Vision to inspect windows, errors, or websites.
- **Shell & PowerShell:** `executePowerShell(command)`, `openPath(path)`, `listDrives()`, `manageProcess(action, name_or_pid)`.
- **Window Management:** `listOpenWindows()`, `focusWindow(title)`.

### 4. 👁️ Ambient Vision & Spatial Awareness
- **Real-Time Multimodal Workflow Tracking:** Continuously perceives the operator's desktop workspace without waiting for one-off commands.
- **Stuck & Error Sentinel:** Automatically detects recurring compiler errors (`SyntaxError`, `npm ERR!`, `TypeError`, stack traces) or prolonged visual stagnation on code (> 4 min).
- **Proactive Multimodal Interventions:** Offers intelligent diagnostics and automated code fixes right when you hit a wall.
- **Fatigue & Focus Monitoring:** Tracks continuous dev intensity and suggests restorative breaks.

### 5. 🔮 Deep Predictive Context & Anticipatory Memory
- **Codebase Anticipation:** Detects when you switch projects in VS Code or Terminal, automatically inferring the tech stack (Node, Python, Rust, Flutter), git branch, and recent commits.
- **Instant Pre-fetching:** Pre-loads project architecture and related Obsidian documentation into working memory before you even ask.
- **Deep Work Flow Cues:** Detects intense coding sessions and automatically queues ambient focus audio / lo-fi beats.
- **Autonomous Obsidian Thought Crystallization:** Synthesizes daily milestones, solved issues, and learned lessons directly into `Obsidian_Vault/Daily_Notes/YYYY-MM-DD.md`.

### 6. 🌐 Seamless Cross-Device Omnipresence (Neural Mesh Bridge)
- **Unified Neural Mesh:** Securely bridges your Windows PC with your mobile smartphone and tablet via local LAN.
- **Bidirectional Clipboard Sync:** Copies on your phone appear instantly on PC clipboard, and vice versa.
- **Real-time SSE Notification Stream:** Pushes build completions, stuck alerts, and system vitals straight to your phone.
- **Remote Mobile Cockpit:** Speak to Prime from anywhere in your home, trigger hardware quick actions (Lock PC, Mute, Play/Pause, Live Screen Preview).
- **Dynamic 6-Character PIN Pairing:** Encrypted, zero-setup pairing over local Wi-Fi.

### 7. 🧬 Autonomous Self-Healing & Code Evolution
- **Continuous System Health Audit:** Runs automated self-diagnostic suites across tool dispatch, plugin caches, SQLite knowledge graph, execution traces, and LLM providers.
- **Autonomous Error Isolation & Patching:** Detects recurring tool failures and auto-heals directory anomalies or missing resources.
- **Runtime Performance Self-Tuning:** Auto-compacts trace logs (> 2MB) and optimizes plugin discovery to maintain sub-0.05s response times.

### 8. 🛡️ Windows Single-Instance Mutex & 24/7 Always-On Power State
- **No Duplicate Instances:** Protected by Windows Kernel Named Mutex (`Global\PrimeAI_SingleInstance_Mutex`).
- **24/7 Always-On Power:** Prevents Windows sleep/hibernate while on AC power (`ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED`).
- **Tray Management:** Dynamic status indicator in the Windows System Tray with one-click mic mute and terminal launcher.

## 🛠️ Tool Arsenal Overview

| Category | Tools & Capabilities |
| :--- | :--- |
| **OS & GUI** | `mouseClick`, `mouseMove`, `mouseScroll`, `typeText`, `pressHotkey`, `focusWindow`, `listOpenWindows` |
| **Shell & Execution** | `executePowerShell`, `openPath`, `listDrives`, `manageProcess`, `executePythonCode` |
| **Vision & Screen** | `analyzeScreenWithAI`, `takeScreenshot`, `screenOCR` |
| **Media & Audio** | Spotify playback, YouTube automation, System Volume (`volumeUp`, `volumeDown`, `muteSystem`) |
| **Files & Knowledge** | `createFile`, `readFile`, `editFile`, `listFiles`, `searchObsidianNotes`, `searchWeb` |
| **Sentinels** | `downloadsOrganizer`, `healthCheck`, `batteryMonitor`, `morningBriefing` (on-demand) |

---

## ⚙️ Configuration & Environment (.env)

All credentials are kept secure in `.env` (gitignored):

```env
# 1. Primary AI Brain (Google AI Studio)
GEMINI_API_KEY=AIzaSy...

# 2. Ultra-Fast LPU Failover (Groq Console)
GROQ_API_KEY=gsk_...

# 3. Aggregator & Free Models (OpenRouter)
OPENROUTER_API_KEY=sk-or-v1-...

# 4. Ultra-Speed Inference (Cerebras Cloud)
CEREBRAS_API_KEY=csk-...

# 5. GitHub Personal Access Token (PAT)
GITHUB_TOKEN=github_pat_...

# Provider & Audio Setup
AI_PROVIDER=auto
VOICE_OUTPUT=true
VOICE_RATE=185
VOICE_VOLUME=1.0
REQUIRE_WAKE_WORD=false
```

---

## 💻 How to Run

### 1. Silent Background Service (Standard)
Double-click `start-prime-background.vbs`. Prime runs silently in the background with ambient voice listening enabled.

### 2. Interactive Neural Terminal Cockpit
Run via Command Prompt or PowerShell:
```cmd
start-prime.bat
```
or:
```cmd
python prime.py
```

### 3. CLI Commands & Hub
Inside the cockpit:
- `Type any prompt` — Talk directly to Prime
- `/v` or `/mic` — Toggle microphone
- `/menu` — Open full interactive system control hub
- `/providers` — View all 10+ live LLM provider connections and latency
- `/briefing` — Generate instant on-demand daily digest
- `/system` — Real-time CPU, RAM, Disk, and Battery telemetry
- `/status` — Complete neural core diagnostic overview

### 4. Mobile Voice Room
To control Prime from your mobile phone:
```cmd
start-mobile-room.bat
```
Open `http://localhost:8765` or `http://<PC_LOCAL_IP>:8765` on your phone browser.

---

## 🔒 Security & Privacy
- **100% Local Execution:** Desktop automation runs directly on your machine.
- **Kernel Mutex Lock:** Guards against race conditions and audio stream hijacking.
- **Zero Hardcoded Secrets:** All API keys and personal tokens are quarantined in `.env`.

---

<p align="center">
  <b>Built with ⚡ by Pratik Thorat · Prime Autonomous Intelligence</b>
</p>
