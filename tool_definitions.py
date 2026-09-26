"""
Tool definitions and dispatcher for Prime AI.
Converts desktop_agent capabilities into function-calling schemas for Gemini and OpenAI/Groq,
and handles execution of tool calls.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

# Ensure desktop_agent package is on sys.path
from desktop_agent.registry import TOOLS, ToolError, load_all
from plugin_registry import registry

log = logging.getLogger("prime.tools")

# Ensure all tools are loaded
load_all()

# Catalog of available tool schemas
TOOL_SPECS: List[Dict[str, Any]] = [
    {
        "name": "getCurrentTime",
        "description": "Get the current system date, time, and timezone.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    # Applications
    {
        "name": "openApplication",
        "description": "Open a Windows application such as notepad, chrome, vscode, calculator, cmd, powershell, explorer, task manager, settings, paint.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name or alias of the application to launch (e.g. notepad, chrome, vscode, calculator)."}
            },
            "required": ["name"]
        }
    },
    {
        "name": "closeApplication",
        "description": "Close a running Windows application by name.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Application name to close (e.g. notepad, chrome, calculator)."},
                "force": {"type": "boolean", "description": "Force kill if true. Defaults to false."}
            },
            "required": ["name"]
        }
    },
    # Websites & Search
    {
        "name": "openWebsite",
        "description": "Open a website by URL or common name (e.g. youtube, github, google, twitter, reddit) in default browser.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL or named site to open."}
            },
            "required": ["url"]
        }
    },
    {
        "name": "searchWeb",
        "description": "Search the web using a query and search engine (google, youtube, github, duckduckgo, bing).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query string."},
                "engine": {"type": "string", "description": "Search engine: google, youtube, github, duckduckgo, bing. Defaults to google."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "searchYouTube",
        "description": "Search YouTube for videos, music, or channels.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "searchGoogle",
        "description": "Search Google for information or websites.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "searchGitHub",
        "description": "Search GitHub for repositories or code.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "GitHub search term."}
            },
            "required": ["query"]
        }
    },
    # Files
    {
        "name": "createFile",
        "description": "Create a text file with content on disk.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Full or relative file path."},
                "content": {"type": "string", "description": "Text content to write."}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "readFile",
        "description": "Read the contents of a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read."}
            },
            "required": ["path"]
        }
    },
    {
        "name": "listFiles",
        "description": "List files and directories inside a given folder.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Folder path (defaults to Desktop, Documents, Downloads, or current dir)."}
            }
        }
    },
    {
        "name": "searchFiles",
        "description": "Search for files by name pattern or extension (e.g. *.py, *.txt) under a directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Root folder to search within (e.g. Desktop, Documents)."},
                "pattern": {"type": "string", "description": "Filename pattern or glob, e.g. *.py, notes*."}
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "openFolder",
        "description": "Open a folder in Windows File Explorer (e.g. Desktop, Downloads, Documents).",
        "parameters": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Folder name or path."}
            },
            "required": ["folder"]
        }
    },
    {
        "name": "deleteFile",
        "description": "Safely delete a file by moving it to the Windows Recycle Bin.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path of the file to recycle."}
            },
            "required": ["path"]
        }
    },
    # PC Audio & Power Control
    {
        "name": "volumeUp",
        "description": "Increase system master volume.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "integer", "description": "Amount to increase by percentage points (default 5)."}
            }
        }
    },
    {
        "name": "volumeDown",
        "description": "Decrease system master volume.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "integer", "description": "Amount to decrease by percentage points (default 5)."}
            }
        }
    },
    {
        "name": "setVolume",
        "description": "Set system master volume to an exact percentage (0-100).",
        "parameters": {
            "type": "object",
            "properties": {
                "level": {"type": "integer", "description": "Target volume level (0 to 100)."}
            },
            "required": ["level"]
        }
    },
    {
        "name": "muteToggle",
        "description": "Toggle system mute/unmute.",
        "parameters": {"type": "object", "properties": {}}
    },
    # Windows & Display
    {
        "name": "minimizeWindow",
        "description": "Minimize the active window or a window matching a title.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Optional window title to minimize. If omitted, minimizes active window."}
            }
        }
    },
    {
        "name": "maximizeWindow",
        "description": "Maximize the active window or a window matching a title.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Optional window title to maximize."}
            }
        }
    },
    {
        "name": "closeWindow",
        "description": "Close the active window or a window matching a title.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Optional window title to close."}
            }
        }
    },
    {
        "name": "switchApplication",
        "description": "Switch focus to a window matching a title or cycle windows (Alt+Tab).",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Window title to focus on."}
            }
        }
    },
    # Clipboard
    {
        "name": "getClipboard",
        "description": "Read text from the Windows clipboard.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "pasteClipboard",
        "description": "Paste text or current clipboard into the active focused field.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Optional text to copy and paste."}
            }
        }
    },
    {
        "name": "clearClipboard",
        "description": "Clear the Windows clipboard.",
        "parameters": {"type": "object", "properties": {}}
    },
    # Screen & Vision
    {
        "name": "takeScreenshot",
        "description": "Capture the full desktop screen.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "saveScreenshot",
        "description": "Capture and save the screen to the Pictures folder.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Optional filename."}
            }
        }
    },
    {
        "name": "readScreen",
        "description": "Read text from the active window using OCR.",
        "parameters": {"type": "object", "properties": {}}
    },
    # Coding & Scripts
    {
        "name": "createPythonFile",
        "description": "Write a Python script file.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Python file name or path."},
                "code": {"type": "string", "description": "Python code content."}
            },
            "required": ["filename", "code"]
        }
    },
    {
        "name": "runPythonScript",
        "description": "Execute a Python script and capture its stdout/stderr output.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to Python script to run."}
            },
            "required": ["path"]
        }
    },
    # System Information
    {
        "name": "systemInfo",
        "description": "Get current CPU usage, RAM usage, disk space, and system uptime.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "gpuInfo",
        "description": "Get NVIDIA GPU status, temperature, VRAM usage (if available).",
        "parameters": {"type": "object", "properties": {}}
    },
    # IP-Prime Actions
    {
        "name": "mediaControl",
        "description": "Control system media playback: play, pause, next, prev, now_playing, stop.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Media action: play_pause, play, pause, next, previous, stop.",
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "spotifyControl",
        "description": "Control Spotify player or search/play music tracks by name or artist.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Spotify command, e.g. 'play Bohemian Rhapsody', 'pause', 'next', 'chill playlist'.",
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "quickNote",
        "description": "Save or view quick notes.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Note content to save."}
            },
            "required": ["text"]
        }
    },
    {
        "name": "searchObsidianNotes",
        "description": "Search user's Obsidian Vault Markdown notes and second brain for matching keywords or topics.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query, topic, or keyword."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "readObsidianNote",
        "description": "Read the full text content of a specific note from the Obsidian Vault.",
        "parameters": {
            "type": "object",
            "properties": {
                "note_name": {"type": "string", "description": "Name or title of the note (e.g. 'SAT Overview.md' or 'Memory Manager')."}
            },
            "required": ["note_name"]
        }
    },
    {
        "name": "writeObsidianNote",
        "description": "Save or update a note in the user's Obsidian Vault knowledge base.",
        "parameters": {
            "type": "object",
            "properties": {
                "note_name": {"type": "string", "description": "Title/filename of the note."},
                "content": {"type": "string", "description": "Markdown content to save in the note."}
            },
            "required": ["note_name", "content"]
        }
    },
    {
        "name": "getWeather",
        "description": "Get current live weather condition and temperature for any city or location.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The name of the city or town (e.g. Pune, Mumbai, Delhi, Ukkalgaon)."}
            },
            "required": ["city"]
        }
    },
    {
        "name": "morningBriefing",
        "description": "Generate and speak a complete personalized morning briefing including date, time, weather, PC CPU/RAM stats, and active tasks.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "briefing, schedule, or cancel. Defaults to briefing."}
            }
        }
    },
    # Claw Code Developer Engine Tools
    {
        "name": "runTerminalCommand",
        "description": "Execute any terminal, shell, PowerShell, or CLI command with real-time output and exit code capture.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The exact shell command line to execute."},
                "cwd": {"type": "string", "description": "Optional working directory path."}
            },
            "required": ["command"]
        }
    },
    {
        "name": "patchCodeFile",
        "description": "Surgically patch a code file by replacing a specific search chunk with replacement content without re-writing the whole file.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the target code file."},
                "search_content": {"type": "string", "description": "The exact string block to replace."},
                "replace_content": {"type": "string", "description": "The new replacement string."}
            },
            "required": ["file_path", "search_content", "replace_content"]
        }
    },
    {
        "name": "gitAutomate",
        "description": "Autonomous Git operations: check status, inspect diff, create conventional commit with AI, or push to remote branch.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action: 'status', 'diff', 'commit', 'push', or 'commit_and_push'."},
                "message": {"type": "string", "description": "Optional commit message (if omitted, Gemini generates one)."},
                "cwd": {"type": "string", "description": "Optional repository path."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "runUnitTests",
        "description": "Run automated test suites (pytest, unittest, cargo, npm) and parse test failure results.",
        "parameters": {
            "type": "object",
            "properties": {
                "framework": {"type": "string", "description": "Test runner: 'pytest', 'unittest', 'cargo', or 'npm'."},
                "path": {"type": "string", "description": "Optional specific test file or directory path."},
                "cwd": {"type": "string", "description": "Optional working directory."}
            }
        }
    },
    {
        "name": "debugCodeFile",
        "description": "Autonomous bug diagnosis and repair: reads code file + error traceback and generates patch chunks using Gemini.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the buggy code file."},
                "error_trace": {"type": "string", "description": "Optional error traceback or exception message."},
                "instructions": {"type": "string", "description": "Optional debugging instructions or user intent."}
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "exportProjectStarter",
        "description": "Generate and export pre-packaged starter project zip archives (from IP-Codemaker: react_vite, fastapi_app, jarvis_voice).",
        "parameters": {
            "type": "object",
            "properties": {
                "project_type": {
                    "type": "string",
                    "description": "Type of starter kit: 'react_vite', 'fastapi_app', or 'jarvis_voice'."
                },
                "destination_dir": {
                    "type": "string",
                    "description": "Optional destination directory for the zip file (defaults to exports/)."
                }
            },
            "required": ["project_type"]
        }
    },
    {
        "name": "exportWorkspaceZip",
        "description": "Package the entire live project workspace into a clean zip archive excluding git and binaries.",
        "parameters": {
            "type": "object",
            "properties": {
                "output_path": {
                    "type": "string",
                    "description": "Optional output path for the zip file (defaults to exports/prime_workspace_backup.zip)."
                }
            }
        }
    },
    {
        "name": "enableAutoStart",
        "description": "Enable Prime AI to start automatically on Windows boot (Registry Run key + Startup folder).",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "disableAutoStart",
        "description": "Disable Prime AI automatic launch on Windows boot.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "getAutoStartStatus",
        "description": "Check whether Prime AI auto-start on Windows boot is enabled or disabled.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "operatorControl",
        "description": "Control or inspect the Proactive Autonomous Background Operator (sentinels for RAM, battery, rest, briefing).",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform: 'status', 'enable', or 'disable'. Defaults to 'status'."
                }
            }
        }
    },
    # Universal OS & GUI Automation (V3)
    {
        "name": "mouseClick",
        "description": "Click the mouse at specific (x, y) screen coordinates or current position. Supports left, right, middle, and double click.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Optional X coordinate on screen."},
                "y": {"type": "integer", "description": "Optional Y coordinate on screen."},
                "button": {"type": "string", "description": "'left', 'right', or 'middle'. Defaults to 'left'."},
                "clicks": {"type": "integer", "description": "Number of clicks: 1 for single click, 2 for double click. Defaults to 1."}
            }
        }
    },
    {
        "name": "mouseMove",
        "description": "Move the mouse cursor smoothly to specific (x, y) coordinates.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Target X screen coordinate."},
                "y": {"type": "integer", "description": "Target Y screen coordinate."},
                "duration": {"type": "number", "description": "Animation duration in seconds. Defaults to 0.2."}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "mouseScroll",
        "description": "Scroll the mouse wheel at the current cursor position. Positive to scroll up, negative to scroll down.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "integer", "description": "Amount to scroll (e.g. -300 to scroll down, 300 to scroll up)."}
            },
            "required": ["amount"]
        }
    },
    {
        "name": "typeText",
        "description": "Type or paste text into the active window or input field. Supports multilingual text, emojis, and code.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The exact text to type into the active field or window."},
                "press_enter": {"type": "boolean", "description": "Whether to press Enter after typing. Defaults to false."}
            },
            "required": ["text"]
        }
    },
    {
        "name": "pressHotkey",
        "description": "Press keyboard hotkeys or shortcut combinations (e.g. ['ctrl', 'c'], ['alt', 'tab'], ['win', 'd'], 'enter', 'esc').",
        "parameters": {
            "type": "object",
            "properties": {
                "keys": {
                    "description": "Single key or list of keys to press together (e.g. ['ctrl', 'c'] or 'enter' or 'ctrl+shift+esc')."
                }
            },
            "required": ["keys"]
        }
    },
    {
        "name": "getCursorPosition",
        "description": "Get current mouse cursor position (x, y) and screen dimensions.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "listOpenWindows",
        "description": "List all open application windows on the desktop with titles, process IDs, and coordinates.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "focusWindow",
        "description": "Bring an open application window to the foreground by matching its title or name (e.g. 'Chrome', 'Visual Studio Code', 'Discord', 'Notepad').",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Partial title or process name to match and focus."}
            },
            "required": ["query"]
        }
    },
    # Universal Shell & System Control (V3)
    {
        "name": "executePowerShell",
        "description": "Execute any PowerShell command or script on Windows. Enables package installation (winget, pip, npm), registry edits, system settings, file manipulation, and network queries.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The exact PowerShell command or script block to run."},
                "timeout": {"type": "integer", "description": "Execution timeout in seconds. Defaults to 45."}
            },
            "required": ["command"]
        }
    },
    {
        "name": "openPath",
        "description": "Open any file, folder, document, video, or URL using its default Windows application (os.startfile).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File or folder path to open (e.g. 'C:\\Users\\user\\Documents\\file.pdf')."}
            },
            "required": ["path"]
        }
    },
    {
        "name": "listDrives",
        "description": "List all physical and logical disk drives on Windows with storage capacity, free space, and usage percentage.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "manageProcess",
        "description": "Inspect or terminate running processes by name or PID.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Process name to match (e.g. 'chrome.exe', 'notepad.exe')."},
                "pid": {"type": "integer", "description": "Process ID to terminate."},
                "action": {"type": "string", "description": "'kill' (default) or 'info'."}
            }
        }
    },
    {
        "name": "analyzeScreenWithAI",
        "description": "Take a live screenshot and analyze it with Gemini Multimodal Vision. Identifies open apps, reads error dialogues, locates UI buttons, inspects code, or answers questions about what is on screen.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Question or instruction for analyzing the screen (e.g. 'What error is showing on screen?' or 'Find the coordinates of the submit button')."}
            }
        }
    },
    {
        "name": "ambientVisionInspect",
        "description": "Perceive and inspect active developer workflow screen in real-time to diagnose errors, identify compiler issues, or get proactive fix recommendations.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Optional specific focus for the spatial inspection."}
            }
        }
    },
    {
        "name": "neuralMeshPair",
        "description": "Get local LAN pairing credentials, PIN token, and URL to connect smartphone or tablet to Prime AI.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "selfHealingAudit",
        "description": "Run autonomous self-diagnostic audit and self-healing across tools, memory, plugins, and providers.",
        "parameters": {"type": "object", "properties": {}}
    },
    # WhatsApp Automation Engine
    {
        "name": "sendWhatsAppMessage",
        "description": "Send a WhatsApp message to any contact name or phone number. Supports saved contacts (e.g. 'Mom', 'Rahul') or raw phone numbers with auto-formatting.",
        "parameters": {
            "type": "object",
            "properties": {
                "recipient": {"type": "string", "description": "Contact name (e.g. 'Rahul', 'Mom') or phone number (e.g. '+919876543210' or '9876543210')."},
                "message": {"type": "string", "description": "The exact message text to send."}
            },
            "required": ["recipient", "message"]
        }
    },
    {
        "name": "saveWhatsAppContact",
        "description": "Save a contact name and phone number to the WhatsApp address book for quick messaging by name.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Contact name (e.g. 'Rahul', 'Boss', 'Pooja')."},
                "phone_number": {"type": "string", "description": "10-digit or international phone number (e.g. '9876543210')."}
            },
            "required": ["name", "phone_number"]
        }
    },
    {
        "name": "listWhatsAppContacts",
        "description": "List all saved contacts in the WhatsApp address book.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "setupWhatsAppWeb",
        "description": "Launch the persistent WhatsApp Web browser setup window so the user can scan the QR code once to grant Prime full persistent background access to read chats and send messages.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "readWhatsAppChats",
        "description": "Read recent chats and unread messages from WhatsApp Web in the background.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of recent chats to inspect. Defaults to 5."}
            }
        }
    },
    {
        "name": "importWhatsAppContacts",
        "description": "Import contacts in bulk from a .vcf (vCard) file into the WhatsApp address book.",
        "parameters": {
            "type": "object",
            "properties": {
                "vcf_path": {"type": "string", "description": "Absolute path to the contacts.vcf file."}
            },
            "required": ["vcf_path"]
        }
    },
    {
        "name": "makeWhatsAppCall",
        "description": "Initiate a WhatsApp voice or video call to any contact or phone number.",
        "parameters": {
            "type": "object",
            "properties": {
                "recipient": {"type": "string", "description": "Contact name (e.g. 'Rahul', 'Mom', 'Priya') or phone number."},
                "call_type": {"type": "string", "description": "'voice' (default) or 'video' call."}
            },
            "required": ["recipient"]
        }
    },
    {
        "name": "acceptWhatsAppCall",
        "description": "Accept / pick up / answer an incoming WhatsApp voice or video call.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "rejectWhatsAppCall",
        "description": "Reject / decline an incoming WhatsApp voice or video call.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "endWhatsAppCall",
        "description": "End / hang up / disconnect an active ongoing WhatsApp call.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "toggleWhatsAppCallMute",
        "description": "Toggle microphone mute / unmute during an active WhatsApp call.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "scheduleWhatsAppCall",
        "description": "Schedule a WhatsApp voice or video call with a contact for a future time (e.g. '5:00 PM', 'in 15 minutes', '6 baje').",
        "parameters": {
            "type": "object",
            "properties": {
                "recipient": {"type": "string", "description": "Contact name or phone number."},
                "time_str": {"type": "string", "description": "Scheduled time (e.g. '5:00 PM', 'in 30 mins', '18:00', '6 baje')."},
                "call_type": {"type": "string", "description": "'voice' (default) or 'video'."},
                "note": {"type": "string", "description": "Optional reminder note for the call."}
            },
            "required": ["recipient", "time_str"]
        }
    },
    {
        "name": "listScheduledWhatsAppCalls",
        "description": "List all pending scheduled WhatsApp calls.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "cancelScheduledWhatsAppCall",
        "description": "Cancel a pending scheduled WhatsApp call by recipient name or call ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "Call ID or contact name to cancel."}
            },
            "required": ["identifier"]
        }
    },
]


# --- Built-in Specialized Tool Handlers ($O(1)$ Dispatch) ---

def _handle_time(args: Dict[str, Any]) -> Dict[str, Any]:
    from datetime import datetime
    now_str = datetime.now().strftime("%A, %B %d, %Y %I:%M:%S %p")
    return {"ok": True, "result": f"Current system time is {now_str}"}

def _handle_run_terminal_command(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import claw_developer
        return claw_developer.run_terminal_command(args.get("command", ""), cwd=args.get("cwd"))
    except Exception as e:
        return {"ok": False, "error": f"Terminal execution failed: {e}"}

def _handle_patch_code_file(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import claw_developer
        return claw_developer.patch_file(args.get("file_path", ""), args.get("search_content", ""), args.get("replace_content", ""))
    except Exception as e:
        return {"ok": False, "error": f"Patching failed: {e}"}

def _handle_git_automate(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import claw_developer
        return claw_developer.git_automate(args.get("action", "status"), message=args.get("message"), cwd=args.get("cwd"))
    except Exception as e:
        return {"ok": False, "error": f"Git automation failed: {e}"}

def _handle_run_unit_tests(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import claw_developer
        return claw_developer.run_unit_tests(args.get("framework", "pytest"), path=args.get("path"), cwd=args.get("cwd"))
    except Exception as e:
        return {"ok": False, "error": f"Test runner failed: {e}"}

def _handle_debug_code_file(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import claw_developer
        return claw_developer.debug_file(args.get("file_path", ""), error_trace=args.get("error_trace"), instructions=args.get("instructions"))
    except Exception as e:
        return {"ok": False, "error": f"Debugging failed: {e}"}

def _handle_export_project_starter(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import project_exporter
        return project_exporter.export_project_starter(args.get("project_type", "react_vite"), destination_dir=args.get("destination_dir"))
    except Exception as e:
        return {"ok": False, "error": f"Project starter export failed: {e}"}

def _handle_export_workspace_zip(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import project_exporter
        return project_exporter.export_workspace_zip(output_path=args.get("output_path"))
    except Exception as e:
        return {"ok": False, "error": f"Workspace zip export failed: {e}"}

def _handle_search_obsidian_notes(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import obsidian_rag
        q = args.get("query", "")
        notes = obsidian_rag.search_notes(q)
        if not notes:
            return {"ok": True, "result": f"No notes found matching '{q}' in Obsidian Vault."}
        return {"ok": True, "result": notes}
    except Exception as e:
        return {"ok": False, "error": f"Obsidian search error: {e}"}

def _handle_read_obsidian_note(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import obsidian_rag
        return {"ok": True, "result": obsidian_rag.read_note(args.get("note_name", ""))}
    except Exception as e:
        return {"ok": False, "error": f"Obsidian read error: {e}"}

def _handle_write_obsidian_note(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import obsidian_rag
        return {"ok": True, "result": obsidian_rag.write_note(args.get("note_name", ""), args.get("content", ""))}
    except Exception as e:
        return {"ok": False, "error": f"Obsidian write error: {e}"}

def _handle_get_weather(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.weather_report import weather_action
        city = args.get("city", "Pune")
        return {"ok": True, "result": weather_action({"city": city})}
    except Exception as e:
        return {"ok": False, "error": f"Weather fetch error: {e}"}

def _handle_morning_briefing(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.morning_briefer import morning_briefer
        res = morning_briefer({'action': args.get('action', 'briefing'), 'hour': args.get('hour', 8), 'minute': args.get('minute', 0)})
        return {"ok": True, "result": res}
    except Exception as e:
        return {"ok": False, "error": f"Morning briefing error: {e}"}

def _handle_media_control(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.media_controller import execute_media_control
        action = args.get("action", "play_pause")
        action_map = {'play_pause': 'play', 'previous': 'prev', 'stop': 'pause'}
        action = action_map.get(action.lower(), action.lower())
        return {"ok": True, "result": execute_media_control(action)}
    except Exception as e:
        return {"ok": False, "error": f"Media control error: {e}"}

def _handle_spotify_control(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.spotify_helper import execute_spotify_command
        cmd = args.get("command", "")
        action = cmd
        query = ""
        if cmd.lower().startswith('play '):
            action = 'play'
            query = cmd[5:].strip()
        elif cmd.lower().startswith('search '):
            action = 'search'
            query = cmd[7:].strip()
        
        if query:
            res = execute_spotify_command(action, query=query)
        else:
            res = execute_spotify_command(action)
        return {"ok": True, "result": res}
    except Exception as e:
        return {"ok": False, "error": f"Spotify control error: {e}"}

def _handle_quick_note(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.computer_settings import add_note
        text = args.get("text", "")
        add_note(text)
        return {"ok": True, "result": f"Note saved: {text}"}
    except Exception as e:
        return {"ok": False, "error": f"Note save error: {e}"}

def _handle_operator_control(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from prime_operator import operator
        act = str(args.get("action", "status")).lower().strip()
        if act in ("enable", "on", "1", "true"):
            operator.set_enabled(True)
            return {"ok": True, "result": "Proactive Autonomous Operator enabled."}
        elif act in ("disable", "off", "0", "false"):
            operator.set_enabled(False)
            return {"ok": True, "result": "Proactive Autonomous Operator disabled."}
        else:
            st = operator.get_status()
            return {"ok": True, "result": f"Operator running: {st['running']}, Enabled: {st['enabled']}, RAM: {st['ram_percent']}%, Battery: {st['battery']}"}
    except Exception as e:
        return {"ok": False, "error": f"Operator control error: {e}"}


def _handle_ambient_vision(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from ambient_spatial_sentinel import ambient_sentinel
        return {"ok": True, "result": ambient_sentinel.force_analyze_workflow()}
    except Exception as e:
        return {"ok": False, "error": f"Ambient vision inspection failed: {e}"}

def _handle_neural_mesh_pair(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from neural_mesh_bridge import mesh_bridge
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return {
            "ok": True,
            "result": f"Neural Mesh Pairing PIN: {mesh_bridge.auth_token}. Connect from phone browser: http://{ip}:8765/?pin={mesh_bridge.auth_token}"
        }
    except Exception as e:
        return {"ok": False, "error": f"Neural mesh pairing failed: {e}"}

def _handle_self_healing_audit(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from self_healing_engine import self_healer
        return {"ok": True, "result": self_healer.run_full_system_audit()}
    except Exception as e:
        return {"ok": False, "error": f"Self-healing audit failed: {e}"}


def _handle_send_whatsapp(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import send_whatsapp
        recipient = str(args.get("recipient") or args.get("contact") or args.get("to") or args.get("phone") or "").strip()
        message = str(args.get("message") or args.get("text") or args.get("body") or "").strip()
        if not recipient or not message:
            return {"ok": False, "error": "Both 'recipient' and 'message' are required."}
        return send_whatsapp(recipient, message)
    except Exception as e:
        return {"ok": False, "error": f"WhatsApp transmission failed: {e}"}


def _handle_save_whatsapp_contact(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import save_contact
        name = str(args.get("name") or "").strip()
        phone = str(args.get("phone_number") or args.get("phone") or args.get("number") or "").strip()
        if not name or not phone:
            return {"ok": False, "error": "Both 'name' and 'phone_number' are required."}
        return save_contact(name, phone)
    except Exception as e:
        return {"ok": False, "error": f"Failed to save contact: {e}"}


def _handle_list_whatsapp_contacts(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import list_contacts
        return list_contacts()
    except Exception as e:
        return {"ok": False, "error": f"Failed to list contacts: {e}"}


def _handle_setup_whatsapp_web(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import whatsapp_web
        return whatsapp_web.launch_setup_window()
    except Exception as e:
        return {"ok": False, "error": f"Failed to launch WhatsApp Web setup: {e}"}


def _handle_read_whatsapp_chats(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import whatsapp_web
        limit = int(args.get("limit", 5))
        return whatsapp_web.read_recent_unread_messages(limit=limit)
    except Exception as e:
        return {"ok": False, "error": f"Failed to read WhatsApp chats: {e}"}


def _handle_import_whatsapp_contacts(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import import_vcf_contacts
        path = str(args.get("vcf_path") or args.get("path") or "").strip()
        if not path:
            return {"ok": False, "error": "'vcf_path' parameter is required."}
        return import_vcf_contacts(path)
    except Exception as e:
        return {"ok": False, "error": f"Failed to import contacts: {e}"}


def _handle_make_whatsapp_call(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import make_whatsapp_call
        recipient = str(args.get("recipient") or args.get("contact") or args.get("target") or "").strip()
        call_type = str(args.get("call_type") or args.get("type") or "voice").strip()
        if not recipient:
            return {"ok": False, "error": "'recipient' is required to make a WhatsApp call."}
        return make_whatsapp_call(recipient, call_type)
    except Exception as e:
        return {"ok": False, "error": f"Failed to initiate WhatsApp call: {e}"}


def _handle_accept_whatsapp_call(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import accept_whatsapp_call
        return accept_whatsapp_call()
    except Exception as e:
        return {"ok": False, "error": f"Failed to accept WhatsApp call: {e}"}


def _handle_reject_whatsapp_call(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import reject_whatsapp_call
        return reject_whatsapp_call()
    except Exception as e:
        return {"ok": False, "error": f"Failed to reject WhatsApp call: {e}"}


def _handle_end_whatsapp_call(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import end_whatsapp_call
        return end_whatsapp_call()
    except Exception as e:
        return {"ok": False, "error": f"Failed to end WhatsApp call: {e}"}


def _handle_toggle_whatsapp_call_mute(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import toggle_whatsapp_call_mute
        return toggle_whatsapp_call_mute()
    except Exception as e:
        return {"ok": False, "error": f"Failed to toggle mute: {e}"}


def _handle_schedule_whatsapp_call(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import schedule_whatsapp_call
        recipient = str(args.get("recipient") or args.get("contact") or "").strip()
        time_str = str(args.get("time_str") or args.get("time") or "").strip()
        call_type = str(args.get("call_type") or "voice").strip()
        note = str(args.get("note") or "").strip()
        if not recipient or not time_str:
            return {"ok": False, "error": "'recipient' and 'time_str' are required to schedule a call."}
        return schedule_whatsapp_call(recipient, time_str, call_type, note)
    except Exception as e:
        return {"ok": False, "error": f"Failed to schedule WhatsApp call: {e}"}


def _handle_list_scheduled_calls(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import list_scheduled_calls
        return list_scheduled_calls()
    except Exception as e:
        return {"ok": False, "error": f"Failed to list scheduled calls: {e}"}


def _handle_cancel_scheduled_call(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import cancel_scheduled_call
        ident = str(args.get("identifier") or args.get("call_id") or args.get("recipient") or "").strip()
        if not ident:
            return {"ok": False, "error": "'identifier' is required to cancel a scheduled call."}
        return cancel_scheduled_call(ident)
    except Exception as e:
        return {"ok": False, "error": f"Failed to cancel scheduled call: {e}"}


BUILTIN_TOOL_DISPATCH: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "getCurrentTime": _handle_time,
    "getTime": _handle_time,
    "currentTime": _handle_time,
    "get_current_time": _handle_time,
    "runTerminalCommand": _handle_run_terminal_command,
    "patchCodeFile": _handle_patch_code_file,
    "gitAutomate": _handle_git_automate,
    "runUnitTests": _handle_run_unit_tests,
    "debugCodeFile": _handle_debug_code_file,
    "exportProjectStarter": _handle_export_project_starter,
    "exportWorkspaceZip": _handle_export_workspace_zip,
    "searchObsidianNotes": _handle_search_obsidian_notes,
    "readObsidianNote": _handle_read_obsidian_note,
    "writeObsidianNote": _handle_write_obsidian_note,
    "getWeather": _handle_get_weather,
    "morningBriefing": _handle_morning_briefing,
    "mediaControl": _handle_media_control,
    "spotifyControl": _handle_spotify_control,
    "quickNote": _handle_quick_note,
    "operatorControl": _handle_operator_control,
    "ambientVisionInspect": _handle_ambient_vision,
    "neuralMeshPair": _handle_neural_mesh_pair,
    "selfHealingAudit": _handle_self_healing_audit,
    "sendWhatsAppMessage": _handle_send_whatsapp,
    "sendWhatsApp": _handle_send_whatsapp,
    "whatsappSend": _handle_send_whatsapp,
    "saveWhatsAppContact": _handle_save_whatsapp_contact,
    "listWhatsAppContacts": _handle_list_whatsapp_contacts,
    "setupWhatsAppWeb": _handle_setup_whatsapp_web,
    "readWhatsAppChats": _handle_read_whatsapp_chats,
    "importWhatsAppContacts": _handle_import_whatsapp_contacts,
    "makeWhatsAppCall": _handle_make_whatsapp_call,
    "make_whatsapp_call": _handle_make_whatsapp_call,
    "whatsappCall": _handle_make_whatsapp_call,
    "callWhatsApp": _handle_make_whatsapp_call,
    "acceptWhatsAppCall": _handle_accept_whatsapp_call,
    "pickupWhatsAppCall": _handle_accept_whatsapp_call,
    "answerWhatsAppCall": _handle_accept_whatsapp_call,
    "rejectWhatsAppCall": _handle_reject_whatsapp_call,
    "declineWhatsAppCall": _handle_reject_whatsapp_call,
    "endWhatsAppCall": _handle_end_whatsapp_call,
    "hangupWhatsAppCall": _handle_end_whatsapp_call,
    "toggleWhatsAppCallMute": _handle_toggle_whatsapp_call_mute,
    "scheduleWhatsAppCall": _handle_schedule_whatsapp_call,
    "listScheduledWhatsAppCalls": _handle_list_scheduled_calls,
    "cancelScheduledWhatsAppCall": _handle_cancel_scheduled_call,
}


def execute_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool handler and return structured result."""
    args = args or {}

    if not isinstance(name, str):
        return {'ok': False, 'error': 'Tool name must be a string.'}

    # Normalize common aliases
    alias_map = {
        "getsystemstats": "systemInfo",
        "system_stats": "systemInfo",
        "get_system_stats": "systemInfo",
        "systeminfo": "systemInfo",
        "weather": "getWeather",
        "get_weather": "getWeather",
        "briefing": "morningBriefing",
        "morning_briefing": "morningBriefing",
    }
    if name.lower() in alias_map:
        name = alias_map[name.lower()]

    # --- Argument Normalization ---
    import os
    arg_mappings = {
        'createPythonFile': [('filename', 'path'), ('code', 'content')],
        'openFolder': [('folder', 'path')],
        'saveScreenshot': [('filename', 'name')],
        'patchCodeFile': [('path', 'file_path'), ('target', 'search_content'), ('replacement', 'replace_content')],
        'debugCodeFile': [('path', 'file_path'), ('trace', 'error_trace')],
        'runUnitTests': [('test_path', 'path')],
        'sendWhatsAppMessage': [('to', 'recipient'), ('contact', 'recipient'), ('phone', 'recipient'), ('text', 'message'), ('body', 'message')],
        'saveWhatsAppContact': [('phone', 'phone_number'), ('number', 'phone_number')],
    }
    for src, dst in arg_mappings.get(name, []):
        if src in args and dst not in args:
            args[dst] = args[src]

    if name == 'listFiles' and not args.get('path') and not args.get('name'):
        args['path'] = os.path.expanduser('~')

    if name in ('volumeUp', 'volumeDown') and 'amount' in args:
        amt = float(args['amount'])
        if amt > 1.0:
            args['amount'] = amt / 100.0

    if name == 'openApplication':
        target = str(args.get('name') or args.get('application') or '').strip().lower()
        try:
            from desktop_agent.tools_websites import SITE_URLS
            if target in SITE_URLS or '://' in target or target.startswith('www.') or any(target.endswith(ext) for ext in ('.com', '.org', '.net', '.io', '.ai', '.in', '.co')):
                name = 'openWebsite'
                args = {'url': target}
        except Exception:
            pass
    elif name == 'openWebsite':
        target = str(args.get('url') or args.get('name') or '').strip().lower()
        try:
            from desktop_agent.tools_applications import APP_COMMANDS
            from desktop_agent.tools_websites import SITE_URLS
            if target in APP_COMMANDS and target not in SITE_URLS and not any(target.endswith(ext) for ext in ('.com', '.org', '.net', '.io', '.ai', '.in')):
                name = 'openApplication'
                args = {'name': target}
            elif target in SITE_URLS:
                args['name'] = target
                args['url'] = SITE_URLS[target]
        except Exception:
            pass

    # 1. Check Built-in specialized handlers ($O(1)$)
    builtin_handler = BUILTIN_TOOL_DISPATCH.get(name)
    if not builtin_handler:
        # Case-insensitive fallback
        name_lower = name.lower()
        for k, v in BUILTIN_TOOL_DISPATCH.items():
            if k.lower() == name_lower:
                builtin_handler = v
                break

    if builtin_handler:
        return builtin_handler(args)

    # 2. Check Desktop Agent tools ($O(1)$)
    if name in TOOLS:
        handler = TOOLS[name]
        try:
            res = handler(args)
            if isinstance(res, dict) and list(res.keys()) == ['result']:
                res = res['result']
            return {"ok": True, "result": res}
        except ToolError as e:
            return {"ok": False, "error": e.message}
        except Exception as e:
            log.exception("Tool execution error in %s", name)
            return {"ok": False, "error": str(e)}

    # 3. Check Dynamic Plugin Registry
    if registry.has_tool(name):
        return registry.execute(name, args)

    return {"ok": False, "error": f"Tool '{name}' not found."}


def get_openai_tools() -> List[Dict[str, Any]]:
    """Return tool schemas formatted for OpenAI / Groq tool calling."""
    tools = []
    for spec in TOOL_SPECS:
        tools.append({
            "type": "function",
            "function": {
                "name": spec["name"],
                "description": spec["description"],
                "parameters": spec["parameters"],
            }
        })
    tools.extend(registry.get_tool_specs())
    return tools


def get_gemini_tools() -> List[Any]:
    """Return tool schemas formatted for Google Gemini function declarations."""
    decls = [
        {
            "name": spec["name"],
            "description": spec["description"],
            "parameters": spec["parameters"],
        }
        for spec in TOOL_SPECS
    ]
    decls.extend(registry.get_gemini_declarations())
    return [{"function_declarations": decls}]

# Initialize plugins
registry.scan_plugins()
