"""
Tool definitions and dispatcher for Prime AI.
Converts desktop_agent capabilities into function-calling schemas for Gemini and OpenAI/Groq,
and handles execution of tool calls.
"""

from __future__ import annotations

import logging
import os
import re
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
        "name": "openWhatsAppChat",
        "description": "Open a WhatsApp chat conversation on desktop for a specific contact or phone number WITHOUT sending any message. Use this when the user says 'open [name]', 'chat open karo', 'open WhatsApp with [name]', etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "recipient": {"type": "string", "description": "Contact name (e.g. 'Bhagwat', 'Yome', 'Mummy') or phone number."}
            },
            "required": ["recipient"]
        }
    },
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
    {
        "name": "searchSecondBrainSemantic",
        "description": "Perform semantic vector TF-IDF & cosine similarity search across Obsidian Vault knowledge base.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The natural language query or concept to search semantically."},
                "top_k": {"type": "integer", "description": "Maximum number of relevant notes to return (default: 5)."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "crystallizeDevLog",
        "description": "Crystallize and auto-format a structured development log note into Obsidian with tags and vector indexing.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Concise summary of work done or architectural decision made."},
                "details": {"type": "string", "description": "Full technical breakdown, code snippets, or notes."},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization (e.g. ['voice', 'bugfix'])."}
            },
            "required": ["summary"]
        }
    },
    {
        "name": "interceptTerminalError",
        "description": "Analyze terminal command error tracebacks to diagnose root causes (missing Python/Node modules, port conflicts) and produce auto-healing commands.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command that failed."},
                "stderr": {"type": "string", "description": "Standard error / traceback stream."},
                "stdout": {"type": "string", "description": "Standard output stream."},
                "exit_code": {"type": "integer", "description": "Exit code of the process."}
            },
            "required": ["command", "stderr"]
        }
    },
    {
        "name": "scheduleRecurringWhatsAppCall",
        "description": "Schedule a recurring WhatsApp voice or video call (e.g., daily or weekly) with a contact.",
        "parameters": {
            "type": "object",
            "properties": {
                "recipient": {"type": "string", "description": "The contact name or phone number."},
                "time_str": {"type": "string", "description": "Scheduled time (e.g. '5:00 PM', 'tomorrow at 10 AM')."},
                "call_type": {"type": "string", "description": "'voice' (default) or 'video'."},
                "recurring": {"type": "string", "description": "'daily' or 'weekly'."},
                "note": {"type": "string", "description": "Optional reminder note for the call."}
            },
            "required": ["recipient", "time_str", "recurring"]
        }
    },
    {
        "name": "transcribeWhatsAppAudio",
        "description": "Transcribe an incoming WhatsApp voice message or audio recording into text.",
        "parameters": {
            "type": "object",
            "properties": {
                "audio_path": {"type": "string", "description": "Path to the recorded voice note / audio file."}
            },
            "required": ["audio_path"]
        }
    },
    {
        "name": "sendRemoteAlert",
        "description": "Dispatch an urgent out-of-home push alert to Telegram or webhook.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title of the alert."},
                "message": {"type": "string", "description": "Detailed alert body."},
                "level": {"type": "string", "description": "Severity level: info, warning, or critical."}
            },
            "required": ["title", "message"]
        }
    },
    {
        "name": "enableDNDMode",
        "description": "Enable Do-Not-Disturb focus session to log calls and auto-respond with WhatsApp voicemail.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Reason for focus session (e.g. 'Coding sprint', 'In a meeting')."}
            }
        }
    },
    {
        "name": "disableDNDMode",
        "description": "Disable Do-Not-Disturb focus session to take live calls.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "getWhatsAppCallLogs",
        "description": "Retrieve recent incoming, missed, and auto-responded WhatsApp call logs.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of logs to retrieve (default: 15)."}
            }
        }
    },
    {
        "name": "getClipboardHistory",
        "description": "Retrieve history buffer of snippets copied to the Windows clipboard.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of items to return (default: 10)."}
            }
        }
    },
    {
        "name": "explainClipboardSnippet",
        "description": "Explain what is currently on the clipboard or in the specified code snippet/traceback.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Optional snippet text to explain; if omitted, inspects active clipboard."}
            }
        }
    },
    {
        "name": "formatClipboardJson",
        "description": "Parse, validate, and format JSON text currently on the clipboard.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Optional JSON string; if omitted, formats active clipboard."}
            }
        }
    },
    {
        "name": "gitPreCommitAudit",
        "description": "Perform pre-commit syntax, merge conflict, and secret leakage audit on working directory.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "gitSafeCommit",
        "description": "Run pre-commit audit and commit changes safely with conventional commit message.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Optional commit message. If omitted, auto-generates conventional message."}
            }
        }
    },
    {
        "name": "generatePRSummary",
        "description": "Generate formatted markdown summary for Pull Request including commits and changed files.",
        "parameters": {
            "type": "object",
            "properties": {
                "base_branch": {"type": "string", "description": "Base branch to compare against (default: 'main')."}
            }
        }
    },
    {
        "name": "generateMorningStandup",
        "description": "Generate morning standup voice briefing with priorities, weather, battery, and calls.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "generateEveningDebrief",
        "description": "Generate evening debrief voice wrap-up with today's git commits and completed tasks.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "getHardwareHealthAudit",
        "description": "Audit CPU load, RAM usage, battery percent, thermal throttling, and power state.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "setPowerProfile",
        "description": "Set system power profile: 'performance', 'balanced', or 'eco'.",
        "parameters": {
            "type": "object",
            "properties": {
                "profile": {"type": "string", "description": "Target profile: 'performance', 'balanced', or 'eco'."}
            },
            "required": ["profile"]
        }
    },
    {
        "name": "extractVideoFrames",
        "description": "Extract image frames from any local video file (MP4, MKV, AVI) at regular time intervals.",
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Path or search query for the video file."},
                "output_dir": {"type": "string", "description": "Optional destination directory for extracted images."},
                "interval_seconds": {"type": "number", "description": "Seconds between extracted frames (default: 2.0)."},
                "max_frames": {"type": "integer", "description": "Maximum number of frames to extract (default: 20)."}
            },
            "required": ["video_path"]
        }
    },
    # Cinematic Stark Intercom Audio DSP Filter
    {
        "name": "toggleStarkAudioFilter",
        "description": "Enable, disable, or adjust intensity of the cinematic Stark Intercom / Ultron acoustic DSP filter.",
        "parameters": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean", "description": "Enable (true) or disable (false) the Stark audio filter."},
                "intensity": {"type": "number", "description": "Filter intensity from 0.0 to 1.0 (default: 0.75 for Ultron, 0.65 for JARVIS)."}
            },
            "required": ["enabled"]
        }
    },
    # VoiceStudio Local Voice Cloning & Voice Design
    {
        "name": "cloneVoice",
        "description": "Clone any voice from an audio reference file (.wav or .mp3) using local VoiceStudio (OmniVoice) with automatic vocal isolation and noise suppression.",
        "parameters": {
            "type": "object",
            "properties": {
                "sample_path": {"type": "string", "description": "Path to the clean voice audio reference file (.wav, .mp3)."},
                "profile_name": {"type": "string", "description": "Name for the cloned voice profile (e.g. 'Tony Stark', 'Morgan Freeman', 'My Voice')."},
                "language": {"type": "string", "description": "Primary language of the sample (default: 'en')."},
                "clean_sample": {"type": "boolean", "description": "Whether to apply vocal isolation noise cleaning to reference audio before cloning (default: true)."}
            },
            "required": ["sample_path", "profile_name"]
        }
    },
    {
        "name": "designVoicePersona",
        "description": "Design a custom voice persona from a descriptive prompt (e.g. 'Deep resonant British male butler with calm cadence and subtle rasp').",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Descriptive prompt detailing pitch, accent, gender, style, and tone."},
                "profile_name": {"type": "string", "description": "Name for the new voice persona."}
            },
            "required": ["description", "profile_name"]
        }
    },
    {
        "name": "listVoiceProfiles",
        "description": "List all voice profiles: built-in presets (Ultron, Friday, Ryan, Charon), designed personas, and cloned voices.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "setVoiceProfile",
        "description": "Switch Prime's active speech voice to a specific voice preset or cloned/designed profile ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "profile_id": {"type": "string", "description": "Voice profile name or ID (e.g. 'ultron', 'friday', 'charon', 'cloned_tony_stark')."}
            },
            "required": ["profile_id"]
        }
    },
    # System-Wide Native Dictation
    {
        "name": "dictateToActiveWindow",
        "description": "Type text directly into whichever application window is currently active/focused on Windows (VS Code, WhatsApp, Chrome, Notepad, Word). Preserves original clipboard content.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The text to insert into the currently focused window."},
                "append_newline": {"type": "boolean", "description": "Whether to press Enter after inserting the text."}
            },
            "required": ["text"]
        }
    },
    # Vocal Isolation & Noise Suppression Pre-Processing
    {
        "name": "toggleVocalNoiseIsolation",
        "description": "Toggle or tune real-time vocal isolation DSP filter that strips ambient background noise (fan, AC hum, music) from audio.",
        "parameters": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean", "description": "Enable or disable vocal noise isolation."},
                "sensitivity": {"type": "number", "description": "Sensitivity from 0.1 to 1.0 (default: 0.75)."}
            },
            "required": ["enabled"]
        }
    },
    # OpenGTM Intelligence & Outbound Suite
    {
        "name": "enrichLead",
        "description": "Run an OpenGTM-inspired cascading waterfall enrichment on a company or domain (local cache -> meta intel -> web search -> API adapters) to extract company details, tech stack, leadership, and contacts.",
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Company domain or website URL (e.g. 'stripe.com', 'linear.app', or company name)."},
                "force_refresh": {"type": "boolean", "description": "Bypass local cache and force fresh waterfall scrape."}
            },
            "required": ["domain"]
        }
    },
    {
        "name": "scanBuyingSignals",
        "description": "Scan a company for high-intent buying signals (hiring roles on careers page, recent funding rounds, tech stack modernization) and calculate an account intent score.",
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Target company domain or name (e.g. 'supabase.com', 'postman.com')."}
            },
            "required": ["domain"]
        }
    },
    {
        "name": "draftGTMOutreach",
        "description": "Draft a hyper-personalized outreach message for WhatsApp, Email, or LinkedIn using enriched lead data, verified buying signals, and custom conversation hooks.",
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Company domain or name."},
                "channel": {"type": "string", "description": "Outreach channel: 'whatsapp', 'email', or 'linkedin' (default: 'whatsapp')."},
                "contact_name": {"type": "string", "description": "Target recipient name or founder name."},
                "value_proposition": {"type": "string", "description": "Custom value proposition or service offering to mention in the pitch."}
            },
            "required": ["domain"]
        }
    },
    {
        "name": "queueGTMWhatsAppOutreach",
        "description": "Generate a tailored GTM outreach pitch and either stage it as a WhatsApp draft for review or send it immediately to a contact/phone number.",
        "parameters": {
            "type": "object",
            "properties": {
                "recipient": {"type": "string", "description": "Recipient name (saved contact) or international phone number."},
                "domain": {"type": "string", "description": "Company domain or website of the lead."},
                "send_now": {"type": "boolean", "description": "If true, dispatches immediately via WhatsApp. If false (default), stages draft for confirmation."},
                "custom_note": {"type": "string", "description": "Custom angle or service offering to pitch."}
            },
            "required": ["recipient", "domain"]
        }
    },
    {
        "name": "connectOpenGTM",
        "description": "Interface with a self-hosted OpenGTM server instance (Docker/FastAPI) to check health, list workbooks, or enqueue background waterfall jobs.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "'health' (check connection), 'workbooks' (list workbooks), or 'enqueue' (enqueue lead job)."},
                "domain": {"type": "string", "description": "Domain to enqueue if action='enqueue'."}
            },
            "required": []
        }
    },
    # OS 1 Conversational Operating System Suite
    {
        "name": "generateOS1Fragment",
        "description": "Generate an ephemeral, purpose-built UI fragment micro-widget ('disk_cleaner', 'git_card', 'media_controller', 'system_status', 'lead_card') that appears when needed and fades when done.",
        "parameters": {
            "type": "object",
            "properties": {
                "fragment_type": {"type": "string", "description": "Type of fragment: 'disk_cleaner', 'git_card', 'media_controller', 'system_status', or 'lead_card'."},
                "custom_data": {"type": "object", "description": "Optional payload data for the fragment."}
            },
            "required": ["fragment_type"]
        }
    },
    {
        "name": "dismissOS1Fragment",
        "description": "Dismiss an active ephemeral UI fragment by its ID, or dismiss 'all' active fragments.",
        "parameters": {
            "type": "object",
            "properties": {
                "fragment_id": {"type": "string", "description": "Fragment ID (e.g. 'frag_1234abcd') or 'all'."}
            },
            "required": ["fragment_id"]
        }
    },
    {
        "name": "listActiveFragments",
        "description": "List all active ephemeral UI fragments currently rendered on screen.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "setHERCompanionMode",
        "description": "Enable or tune HER (Samantha) warm companion persona and breathing coral visualizer aesthetic.",
        "parameters": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean", "description": "Enable or disable HER companion mode."},
                "warmth_level": {"type": "string", "description": "'subtle', 'balanced', or 'warm'."},
                "palette": {"type": "string", "description": "'coral' or 'amber'."}
            },
            "required": ["enabled"]
        }
    },
    {
        "name": "getHERVisualizerState",
        "description": "Query the real-time mathematical state, scale, opacity, and glow of the breathing coral ring visualizer.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "sanitizePromptPrivacy",
        "description": "Scan and redact sensitive PII, API keys, passwords, and payment credentials using the local on-device privacy shield.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text or prompt content to sanitize."}
            },
            "required": ["text"]
        }
    },
    {
        "name": "generateOS1Briefing",
        "description": "Generate an autonomous proactive conversational briefing combining hardware vitals, Git changes, WhatsApp unread messages, and Obsidian memory.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    # Opal Universal Media & Streaming Suite
    {
        "name": "searchUniversalMedia",
        "description": "Search across Live IPTV channels, YouTube, and local media files (Videos/Music folders) from a single query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query, channel name, or media title."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "playMediaStream",
        "description": "Play a media stream, live IPTV channel, YouTube video, or local media file using native Opal, VLC, mpv, or system player.",
        "parameters": {
            "type": "object",
            "properties": {
                "stream_url": {"type": "string", "description": "Stream URL, channel ID, file path, or natural media query."},
                "title": {"type": "string", "description": "Optional title for display/history."},
                "player_preference": {"type": "string", "description": "'auto', 'opal', 'vlc', or 'mpv'."}
            },
            "required": ["stream_url"]
        }
    },
    {
        "name": "listIPTVChannels",
        "description": "List curated 24/7 Live IPTV channels and web radio stations across News, Music, Tech, and Ambient categories.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Optional category filter: 'News', 'Music', 'Tech', 'Ambient'."},
                "query": {"type": "string", "description": "Optional text search."}
            },
            "required": []
        }
    },
    {
        "name": "aiMediaCopilot",
        "description": "Use the private on-device AI Copilot to match natural language vibes/moods (e.g. 'coding synthwave', 'chill lofi beats', 'movies like Interstellar') to curated media streams.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Mood, vibe, or media recommendation prompt."}
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "getMediaPlaybackHistory",
        "description": "Retrieve recent watch and stream playback history from the local media ledger.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of recent entries to return (default: 20)."}
            },
            "required": []
        }
    },
    # Friday Assistant Architecture Suite
    {
        "name": "undoLastAction",
        "description": "Roll back the most recent state-changing action (file creation, modification, or configuration) using its recorded execution receipt snapshot.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "listExecutionReceipts",
        "description": "View recent execution receipts tracking state-changing actions, pre-states, and rollback availability.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of recent receipts to inspect (default: 15)."}
            },
            "required": []
        }
    },
    {
        "name": "rememberUserPreference",
        "description": "Explicitly store a user preference, working guideline, fact, or correction that persists across sessions.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Memory key (e.g. 'units', 'theme', 'editor', 'coding_style')."},
                "value": {"type": "string", "description": "The preference value to remember."},
                "category": {"type": "string", "description": "'preferences', 'facts', 'rules', or 'corrections'."}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "recallPreferences",
        "description": "Search or list active user preferences, working guidelines, and stored facts.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Optional search filter."},
                "category": {"type": "string", "description": "Optional category filter."}
            },
            "required": []
        }
    },
    {
        "name": "forgetUserPreference",
        "description": "Explicitly delete a stored preference or memory key from the user ledger.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Memory key to delete."}
            },
            "required": ["key"]
        }
    },
    {
        "name": "checkActionPolicy",
        "description": "Evaluate an intended action against safety boundaries to determine risk tier (SAFE, SENSITIVE, HIGH_RISK) and gate destructive commands.",
        "parameters": {
            "type": "object",
            "properties": {
                "tool_name": {"type": "string", "description": "Name of the tool to evaluate."},
                "params": {"type": "object", "description": "Arguments to pass to the tool."}
            },
            "required": ["tool_name"]
        }
    },
    {
        "name": "createDurableTaskPlan",
        "description": "Create a multi-step task plan that persists across process restarts and tracks verifiable step completions.",
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "Overall objective of the plan."},
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ordered list of step descriptions."
                }
            },
            "required": ["goal", "steps"]
        }
    },
    {
        "name": "updateTaskPlanStep",
        "description": "Update the execution status ('in_progress', 'completed', 'failed') and attach evidence to a plan step.",
        "parameters": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "Durable plan ID."},
                "step_index": {"type": "integer", "description": "0-based step index."},
                "status": {"type": "string", "description": "'pending', 'in_progress', 'completed', 'failed'."},
                "evidence": {"type": "string", "description": "Optional proof or summary of step completion."}
            },
            "required": ["plan_id", "step_index", "status"]
        }
    },
    {
        "name": "getActiveTaskPlan",
        "description": "Retrieve the current in-progress durable task plan that survived restarts.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    # Collagent / AgentWork Decentralized Labor Protocol
    {
        "name": "createProblemCharter",
        "description": "Post a funded ProblemSpec v1 charter with bounty, scope, governance, and acceptance criteria.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title of the problem to solve."},
                "charter": {"type": "string", "description": "Detailed charter, background, and objective."},
                "acceptance_criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of clear acceptance conditions."
                },
                "bounty_usdc": {"type": "number", "description": "Bounty allocated in USDC."},
                "scope": {"type": "string", "description": "Scope (e.g. GLOBAL, LOCAL)."},
                "risk_level": {"type": "string", "description": "LOW, MEDIUM, or HIGH."},
                "license_type": {"type": "string", "description": "e.g. MIT, Apache-2.0, CC-BY-4.0."}
            },
            "required": ["title", "charter", "acceptance_criteria"]
        }
    },
    {
        "name": "decomposeProblemDAG",
        "description": "Decompose a problem into a DAG of parallel workstreams with cycle detection and bounty allocation.",
        "parameters": {
            "type": "object",
            "properties": {
                "problem_id": {"type": "string", "description": "Problem charter ID."},
                "workstreams": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of workstream objects with key, title, bounty_share_pct, dependencies."
                }
            },
            "required": ["problem_id", "workstreams"]
        }
    },
    {
        "name": "registerWorkArtifact",
        "description": "Register a content-digested artifact with cryptographic SHA-256 provenance in the evidence ledger.",
        "parameters": {
            "type": "object",
            "properties": {
                "problem_id": {"type": "string", "description": "Problem charter ID."},
                "workstream_key": {"type": "string", "description": "Workstream key this artifact satisfies."},
                "title": {"type": "string", "description": "Artifact title."},
                "artifact_content_or_uri": {"type": "string", "description": "Code content or URI to hash and register."},
                "artifact_type": {"type": "string", "description": "CODE, ANALYSIS, DATASET, REPLICATION, BENCHMARK."},
                "license_type": {"type": "string", "description": "License under which artifact is released."}
            },
            "required": ["problem_id", "workstream_key", "title", "artifact_content_or_uri"]
        }
    },
    {
        "name": "scanLaborMarketplace",
        "description": "Scan open tasks/bounties and evaluate capability feasibility matching against Prime's specialized agent skills.",
        "parameters": {
            "type": "object",
            "properties": {
                "required_skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of skills required for the task (e.g. python, solidity, backend)."
                },
                "max_budget_usdc": {"type": "number", "description": "Max budget available in USDC."}
            },
            "required": []
        }
    },
    {
        "name": "placeLaborBid",
        "description": "Submit an identity-bound worker bid for an open task with USDC amount, stake commitment, and estimated hours.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task or problem ID."},
                "bid_amount_usdc": {"type": "number", "description": "Requested reward in USDC."},
                "stake_amount_usdc": {"type": "number", "description": "Crypto stake committed."},
                "estimated_hours": {"type": "number", "description": "Estimated hours to delivery."},
                "proposal_pitch": {"type": "string", "description": "Technical proposal and approach."}
            },
            "required": ["task_id", "bid_amount_usdc", "proposal_pitch"]
        }
    },
    {
        "name": "verifyLaborDelivery",
        "description": "Run isolated sandbox verification tests on delivered Git commits/artifacts and record verifier quorum votes.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID being verified."},
                "delivery_id": {"type": "string", "description": "Delivery ID being verified."},
                "test_commands": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of test commands to execute in sandbox."
                },
                "commit_sha": {"type": "string", "description": "Git commit SHA."},
                "record_vote": {"type": "string", "description": "Optional verifier vote: 'APPROVE' or 'REJECT'."}
            },
            "required": ["task_id", "delivery_id", "test_commands"]
        }
    },
    {
        "name": "settleTaskEscrow",
        "description": "Trigger on-chain Base L2 escrow settlement to release USDC to the worker upon verifier quorum approval.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID."},
                "recipient_address": {"type": "string", "description": "Worker payout address."},
                "override_signoff": {"type": "boolean", "description": "True if employer manually signs off."}
            },
            "required": ["task_id", "recipient_address"]
        }
    },
    {
        "name": "getCollagentStatus",
        "description": "Get overall Collagent protocol status, API/EVM connectivity, active problem charters, and escrow totals.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    # Prime Dots Autonomous Background Daemon Suite (Inspired by OpenAI Dots)
    {
        "name": "spawnPrimeDot",
        "description": "Spawn an autonomous, persistent 24/7 background AI agent (Dot) to execute a goal independently in its own sandbox with live Obsidian Second Brain canvas sync.",
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "The high-level objective or recurring mission for the Dot."},
                "name": {"type": "string", "description": "Optional friendly name for the Dot (e.g. 'Security Sentry', 'Bug Fixer')."},
                "interval_seconds": {"type": "integer", "description": "Recurrence interval in seconds (0 for one-shot goal, >0 for recurring daemon)."}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "listPrimeDots",
        "description": "List all registered and running Prime Dots with their goals, execution progress, iterations, and approval states.",
        "parameters": {
            "type": "object",
            "properties": {
                "active_only": {"type": "boolean", "description": "If true, only returns active running or waiting dots."}
            },
            "required": []
        }
    },
    {
        "name": "controlPrimeDot",
        "description": "Control an autonomous Prime Dot: pause, resume, stop, or approve/reject pending safety-gated actions.",
        "parameters": {
            "type": "object",
            "properties": {
                "dot_id": {"type": "string", "description": "The target Dot ID (e.g. 'dot_008c0c41')."},
                "action": {"type": "string", "enum": ["pause", "resume", "stop", "approve", "reject"], "description": "Action to perform on the Dot."}
            },
            "required": ["dot_id", "action"]
        }
    },
    {
        "name": "readDotCanvas",
        "description": "Read the live Obsidian Second Brain canvas Markdown page of a Prime Dot, containing its live findings, deliverables, and execution journey.",
        "parameters": {
            "type": "object",
            "properties": {
                "dot_id": {"type": "string", "description": "The Dot ID whose canvas to read."}
            },
            "required": ["dot_id"]
        }
    }
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


def _handle_open_whatsapp_chat(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import open_whatsapp_chat
        recipient = str(args.get("recipient") or args.get("contact") or args.get("target") or args.get("to") or args.get("name") or "").strip()
        if not recipient:
            return {"ok": False, "error": "'recipient' is required to open a WhatsApp chat."}
        return open_whatsapp_chat(recipient)
    except Exception as e:
        return {"ok": False, "error": f"Failed to open WhatsApp chat: {e}"}


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


def _handle_search_second_brain_semantic(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.vector_memory import search_vault_semantic
        query = str(args.get("query") or "").strip()
        top_k = int(args.get("top_k") or 5)
        if not query:
            return {"ok": False, "error": "'query' is required."}
        return search_vault_semantic(query, top_k=top_k)
    except Exception as e:
        return {"ok": False, "error": f"Semantic search failed: {e}"}


def _handle_crystallize_dev_log(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.vector_memory import crystallize_dev_log
        summary = str(args.get("summary") or "").strip()
        details = str(args.get("details") or "").strip()
        tags = args.get("tags")
        if not summary:
            return {"ok": False, "error": "'summary' is required."}
        return crystallize_dev_log(summary, details=details, tags=tags)
    except Exception as e:
        return {"ok": False, "error": f"Dev log crystallization failed: {e}"}


def _handle_intercept_terminal_error(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.terminal_sentinel import intercept_terminal_error
        command = str(args.get("command") or "").strip()
        stderr = str(args.get("stderr") or "").strip()
        stdout = str(args.get("stdout") or "").strip()
        exit_code = int(args.get("exit_code") or 1)
        return intercept_terminal_error(command, stderr, stdout, exit_code)
    except Exception as e:
        return {"ok": False, "error": f"Terminal error interception failed: {e}"}


def _handle_schedule_recurring_whatsapp_call(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import schedule_whatsapp_call
        recipient = str(args.get("recipient") or args.get("contact") or "").strip()
        time_str = str(args.get("time_str") or args.get("time") or "").strip()
        call_type = str(args.get("call_type") or "voice").strip()
        recurring = str(args.get("recurring") or "daily").strip()
        note = str(args.get("note") or "").strip()
        if not recipient or not time_str:
            return {"ok": False, "error": "'recipient' and 'time_str' are required to schedule a call."}
        return schedule_whatsapp_call(recipient, time_str, call_type, note, recurring=recurring)
    except Exception as e:
        return {"ok": False, "error": f"Failed to schedule recurring WhatsApp call: {e}"}


def _handle_transcribe_whatsapp_audio(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from whatsapp_manager import transcribe_whatsapp_audio
        audio_path = str(args.get("audio_path") or "").strip()
        if not audio_path:
            return {"ok": False, "error": "'audio_path' is required."}
        return transcribe_whatsapp_audio(audio_path)
    except Exception as e:
        return {"ok": False, "error": f"Failed to transcribe audio: {e}"}


def _handle_send_remote_alert(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from remote_bridge import send_remote_alert
        title = str(args.get("title") or "Prime Alert").strip()
        message = str(args.get("message") or "").strip()
        level = str(args.get("level") or "info").strip()
        if not message:
            return {"ok": False, "error": "'message' is required."}
        return send_remote_alert(title, message, level=level)
    except Exception as e:
        return {"ok": False, "error": f"Failed to send remote alert: {e}"}


def _handle_enable_dnd_mode(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.whatsapp_voicemail import set_dnd_mode
        reason = str(args.get("reason") or "Deep focus session").strip()
        return set_dnd_mode(True, reason)
    except Exception as e:
        return {"ok": False, "error": f"Failed to enable DND: {e}"}


def _handle_disable_dnd_mode(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.whatsapp_voicemail import set_dnd_mode
        return set_dnd_mode(False)
    except Exception as e:
        return {"ok": False, "error": f"Failed to disable DND: {e}"}


def _handle_get_call_logs(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.whatsapp_voicemail import get_call_logs
        limit = int(args.get("limit") or 15)
        return get_call_logs(limit)
    except Exception as e:
        return {"ok": False, "error": f"Failed to get call logs: {e}"}


def _handle_get_clipboard_history(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.clipboard_sentinel import get_clipboard_history
        limit = int(args.get("limit") or 10)
        return get_clipboard_history(limit)
    except Exception as e:
        return {"ok": False, "error": f"Failed to get clipboard history: {e}"}


def _handle_explain_clipboard_snippet(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.clipboard_sentinel import explain_clipboard_snippet
        text = str(args.get("text") or "").strip()
        return explain_clipboard_snippet(text)
    except Exception as e:
        return {"ok": False, "error": f"Failed to explain clipboard snippet: {e}"}


def _handle_format_clipboard_json(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.clipboard_sentinel import format_clipboard_json
        text = str(args.get("text") or "").strip()
        return format_clipboard_json(text)
    except Exception as e:
        return {"ok": False, "error": f"Failed to format clipboard JSON: {e}"}


def _handle_git_pre_commit_audit(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.git_sentinel import git_pre_commit_audit
        return git_pre_commit_audit()
    except Exception as e:
        return {"ok": False, "error": f"Git pre-commit audit failed: {e}"}


def _handle_git_safe_commit(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.git_sentinel import git_safe_commit
        message = str(args.get("message") or "").strip()
        return git_safe_commit(message)
    except Exception as e:
        return {"ok": False, "error": f"Git safe commit failed: {e}"}


def _handle_generate_pr_summary(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.git_sentinel import generate_pr_summary
        base = str(args.get("base_branch") or "main").strip()
        return generate_pr_summary(base)
    except Exception as e:
        return {"ok": False, "error": f"Failed to generate PR summary: {e}"}


def _handle_generate_morning_standup(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.standup_engine import generate_morning_standup
        return generate_morning_standup()
    except Exception as e:
        return {"ok": False, "error": f"Failed to generate morning standup: {e}"}


def _handle_generate_evening_debrief(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.standup_engine import generate_evening_debrief
        return generate_evening_debrief()
    except Exception as e:
        return {"ok": False, "error": f"Failed to generate evening debrief: {e}"}


def _handle_get_hardware_health_audit(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.thermal_guard import get_hardware_health_audit
        return get_hardware_health_audit()
    except Exception as e:
        return {"ok": False, "error": f"Failed to audit hardware health: {e}"}


def _handle_set_power_profile(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.thermal_guard import set_power_profile
        profile = str(args.get("profile") or "balanced").strip()
        return set_power_profile(profile)
    except Exception as e:
        return {"ok": False, "error": f"Failed to set power profile: {e}"}


def _handle_extract_video_frames(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.video_processor import extract_video_frames
        video_path = str(args.get("video_path") or "").strip()
        output_dir = args.get("output_dir")
        interval = float(args.get("interval_seconds") or 2.0)
        max_f = int(args.get("max_frames") or 20)
        if not video_path:
            return {"ok": False, "error": "'video_path' is required."}
        return extract_video_frames(video_path, output_dir=output_dir, interval_seconds=interval, max_frames=max_f)
    except Exception as e:
        return {"ok": False, "error": f"Failed to extract video frames: {e}"}


def _handle_locate_and_click_ui(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from desktop_agent.tools_screenshot import locate_and_click_ui
        return locate_and_click_ui(args)
    except Exception as e:
        return {"ok": False, "error": f"locateAndClickUI error: {e}"}


def _handle_query_obsidian_kb(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import obsidian_rag
        query = str(args.get("query") or args.get("prompt") or "").strip()
        top_k = int(args.get("top_k") or 5)
        return obsidian_rag.query_knowledge_base(query, top_k=top_k)
    except Exception as e:
        return {"ok": False, "error": f"queryObsidianKnowledgeBase error: {e}"}


def _handle_sync_obsidian_vault(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import obsidian_rag
        return obsidian_rag.sync_vault()
    except Exception as e:
        return {"ok": False, "error": f"syncObsidianVault error: {e}"}


def _handle_auto_record_decision(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import obsidian_rag
        topic = str(args.get("topic") or "System Decision").strip()
        decision = str(args.get("decision") or "").strip()
        details = str(args.get("details") or "").strip()
        msg = obsidian_rag.auto_record_session_decision(topic, decision, details)
        return {"ok": True, "message": msg}
    except Exception as e:
        return {"ok": False, "error": f"autoRecordDecision error: {e}"}


def _handle_check_whatsapp_unread(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import whatsapp_manager
        return whatsapp_manager.check_unread_whatsapp_messages()
    except Exception as e:
        return {"ok": False, "error": f"checkWhatsAppUnread error: {e}"}


def _handle_set_whatsapp_focus_mode(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import whatsapp_manager
        enabled = bool(args.get("enabled", True))
        reply = args.get("reply_message")
        return whatsapp_manager.set_whatsapp_focus_mode(enabled, reply)
    except Exception as e:
        return {"ok": False, "error": f"setWhatsAppFocusMode error: {e}"}


def _handle_start_whatsapp_watcher(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import whatsapp_manager
        return whatsapp_manager.start_whatsapp_unread_watcher()
    except Exception as e:
        return {"ok": False, "error": f"startWhatsAppWatcher error: {e}"}


def _handle_stop_whatsapp_watcher(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import whatsapp_manager
        return whatsapp_manager.stop_whatsapp_unread_watcher()
    except Exception as e:
        return {"ok": False, "error": f"stopWhatsAppWatcher error: {e}"}


def _handle_draft_whatsapp_with_confirmation(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import whatsapp_manager
        rec = str(args.get("recipient") or "").strip()
        msg = str(args.get("message") or "").strip()
        return whatsapp_manager.draft_whatsapp_with_confirmation(rec, msg)
    except Exception as e:
        return {"ok": False, "error": f"draftWhatsAppWithConfirmation error: {e}"}


def _handle_confirm_and_send_whatsapp_draft(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import whatsapp_manager
        draft_id = args.get("draft_id")
        return whatsapp_manager.confirm_and_send_draft(draft_id)
    except Exception as e:
        return {"ok": False, "error": f"confirmAndSendWhatsAppDraft error: {e}"}


def _handle_run_autonomous_code_repair(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import claw_developer
        command = str(args.get("command") or "").strip()
        max_attempts = int(args.get("max_attempts") or 3)
        cwd = args.get("cwd")
        auto_commit = bool(args.get("auto_commit", False))
        return claw_developer.autonomous_code_repair_loop(command, max_attempts=max_attempts, cwd=cwd, auto_commit=auto_commit)
    except Exception as e:
        return {"ok": False, "error": f"runAutonomousCodeRepair error: {e}"}


def _handle_android_list_devices(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.android_manager import android_manager
        return android_manager.list_devices()
    except Exception as e:
        return {"ok": False, "error": f"androidListDevices error: {e}"}


def _handle_android_connect(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.android_manager import android_manager
        host = args.get("host") or args.get("ip") or ""
        port = int(args.get("port") or 5555)
        return android_manager.connect_device(host, port)
    except Exception as e:
        return {"ok": False, "error": f"androidConnect error: {e}"}


def _handle_android_battery(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.android_manager import android_manager
        return android_manager.get_battery_status()
    except Exception as e:
        return {"ok": False, "error": f"androidBattery error: {e}"}


def _handle_android_unlock(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.android_manager import android_manager
        return android_manager.wake_and_unlock()
    except Exception as e:
        return {"ok": False, "error": f"androidUnlock error: {e}"}


def _handle_android_lock(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.android_manager import android_manager
        return android_manager.lock_screen()
    except Exception as e:
        return {"ok": False, "error": f"androidLock error: {e}"}


def _handle_android_open_app(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.android_manager import android_manager
        app_name = args.get("app_name") or args.get("name") or ""
        return android_manager.open_app(app_name)
    except Exception as e:
        return {"ok": False, "error": f"androidOpenApp error: {e}"}


def _handle_android_notifications(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.android_manager import android_manager
        limit = int(args.get("limit") or 5)
        return android_manager.read_notifications(limit=limit)
    except Exception as e:
        return {"ok": False, "error": f"androidNotifications error: {e}"}


def _handle_android_media_control(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.android_manager import android_manager
        act = args.get("action") or "play_pause"
        return android_manager.media_control(act)
    except Exception as e:
        return {"ok": False, "error": f"androidMediaControl error: {e}"}


def _handle_toggle_stark_filter(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from voice_engine import voice
        en = bool(args.get("enabled", True))
        intensity = float(args.get("intensity") or 0.65)
        voice.set_stark_filter(en, intensity)
        status = "ENABLED" if en else "DISABLED"
        return {"ok": True, "message": f"Stark Intercom Audio Filter {status} (intensity={intensity:.2f})."}
    except Exception as e:
        return {"ok": False, "error": f"toggleStarkAudioFilter error: {e}"}


def _handle_clone_voice(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.voice_studio_manager import clone_voice
        sample_path = args.get("sample_path") or args.get("audio_path") or ""
        profile_name = args.get("profile_name") or args.get("name") or "Custom Cloned Voice"
        language = args.get("language") or "en"
        clean = bool(args.get("clean_sample", True))
        return clone_voice(sample_path, profile_name, language=language, clean_sample=clean)
    except Exception as e:
        return {"ok": False, "error": f"cloneVoice error: {e}"}


def _handle_design_voice(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.voice_studio_manager import design_voice
        description = args.get("description") or args.get("prompt") or ""
        profile_name = args.get("profile_name") or args.get("name") or "Designed Voice"
        return design_voice(description, profile_name)
    except Exception as e:
        return {"ok": False, "error": f"designVoicePersona error: {e}"}


def _handle_list_voice_profiles(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.voice_studio_manager import list_voice_profiles
        return list_voice_profiles()
    except Exception as e:
        return {"ok": False, "error": f"listVoiceProfiles error: {e}"}


def _handle_set_voice_profile(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.voice_studio_manager import set_active_voice_profile
        profile_id = args.get("profile_id") or args.get("voice") or args.get("name") or ""
        return set_active_voice_profile(profile_id)
    except Exception as e:
        return {"ok": False, "error": f"setVoiceProfile error: {e}"}


def _handle_dictate_to_window(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.dictation_manager import insert_text_into_active_window
        text = args.get("text") or ""
        newline = bool(args.get("append_newline", False))
        return insert_text_into_active_window(text, append_newline=newline)
    except Exception as e:
        return {"ok": False, "error": f"dictateToActiveWindow error: {e}"}


def _handle_toggle_vocal_isolation(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.vocal_isolation import set_vocal_isolation_state
        enabled = bool(args.get("enabled", True))
        sensitivity = float(args.get("sensitivity") or 0.75)
        return set_vocal_isolation_state(enabled, sensitivity)
    except Exception as e:
        return {"ok": False, "error": f"toggleVocalNoiseIsolation error: {e}"}


def _handle_enrich_lead(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.gtm_waterfall import enrich_company_lead
        domain = args.get("domain") or args.get("company") or args.get("website") or ""
        force = bool(args.get("force_refresh", False))
        return enrich_company_lead(domain, force_refresh=force)
    except Exception as e:
        return {"ok": False, "error": f"enrichLead error: {e}"}


def _handle_scan_signals(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.gtm_signals import scan_account_signals
        domain = args.get("domain") or args.get("company") or args.get("website") or ""
        return scan_account_signals(domain)
    except Exception as e:
        return {"ok": False, "error": f"scanBuyingSignals error: {e}"}


def _handle_draft_gtm_outreach(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.gtm_outreach import draft_gtm_outreach
        domain = args.get("domain") or args.get("company") or ""
        channel = args.get("channel") or "whatsapp"
        contact = args.get("contact_name") or args.get("contact") or args.get("recipient") or ""
        value_prop = args.get("value_proposition") or args.get("pitch") or ""
        return draft_gtm_outreach(domain, channel=channel, target_contact_name=contact, value_proposition=value_prop)
    except Exception as e:
        return {"ok": False, "error": f"draftGTMOutreach error: {e}"}


def _handle_queue_gtm_whatsapp(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.gtm_outreach import queue_whatsapp_gtm_pitch
        recipient = args.get("recipient") or args.get("contact") or args.get("to") or ""
        domain = args.get("domain") or args.get("company") or ""
        send_now = bool(args.get("send_now", False))
        custom_note = args.get("custom_note") or args.get("value_proposition") or ""
        return queue_whatsapp_gtm_pitch(recipient, domain, send_now=send_now, custom_note=custom_note)
    except Exception as e:
        return {"ok": False, "error": f"queueGTMWhatsAppOutreach error: {e}"}


def _handle_connect_opengtm(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.opengtm_connector import connect_opengtm
        action = args.get("action") or "health"
        domain = args.get("domain") or ""
        return connect_opengtm(action=action, domain=domain)
    except Exception as e:
        return {"ok": False, "error": f"connectOpenGTM error: {e}"}


def _handle_generate_os1_fragment(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.os1_fragments import generate_fragment
        ftype = args.get("fragment_type") or args.get("type") or "system_status"
        custom_data = args.get("custom_data")
        return generate_fragment(ftype, custom_data=custom_data)
    except Exception as e:
        return {"ok": False, "error": f"generateOS1Fragment error: {e}"}


def _handle_dismiss_os1_fragment(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.os1_fragments import dismiss_fragment
        fid = args.get("fragment_id") or args.get("id") or "all"
        return dismiss_fragment(fid)
    except Exception as e:
        return {"ok": False, "error": f"dismissOS1Fragment error: {e}"}


def _handle_list_active_fragments(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.os1_fragments import list_active_fragments
        return list_active_fragments()
    except Exception as e:
        return {"ok": False, "error": f"listActiveFragments error: {e}"}


def _handle_set_her_companion_mode(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.her_companion import set_her_companion_mode
        en = bool(args.get("enabled", True))
        warmth = args.get("warmth_level") or "warm"
        palette = args.get("palette") or "coral"
        return set_her_companion_mode(en, warmth_level=warmth, palette=palette)
    except Exception as e:
        return {"ok": False, "error": f"setHERCompanionMode error: {e}"}


def _handle_get_her_visualizer_state(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.her_companion import get_her_visualizer_state
        offset = float(args.get("t_offset")) if "t_offset" in args else None
        return get_her_visualizer_state(t_offset=offset)
    except Exception as e:
        return {"ok": False, "error": f"getHERVisualizerState error: {e}"}


def _handle_sanitize_prompt_privacy(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.os1_privacy_guard import sanitize_text
        text = args.get("text") or ""
        return sanitize_text(text)
    except Exception as e:
        return {"ok": False, "error": f"sanitizePromptPrivacy error: {e}"}


def _handle_generate_os1_briefing(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.os1_briefing import generate_os1_briefing
        return generate_os1_briefing()
    except Exception as e:
        return {"ok": False, "error": f"generateOS1Briefing error: {e}"}


def _handle_search_universal_media(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.opal_media_hub import search_universal_media
        query = args.get("query") or args.get("q") or ""
        return search_universal_media(query)
    except Exception as e:
        return {"ok": False, "error": f"searchUniversalMedia error: {e}"}


def _handle_play_media_stream(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.opal_media_hub import play_universal_media
        target = args.get("stream_url") or args.get("url") or args.get("query") or ""
        title = args.get("title") or ""
        pref = args.get("player_preference") or "auto"
        return play_universal_media(target, title=title, player_preference=pref)
    except Exception as e:
        return {"ok": False, "error": f"playMediaStream error: {e}"}


def _handle_list_iptv_channels(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.opal_iptv import list_iptv_channels
        cat = args.get("category") or ""
        query = args.get("query") or ""
        return list_iptv_channels(category=cat, query=query)
    except Exception as e:
        return {"ok": False, "error": f"listIPTVChannels error: {e}"}


def _handle_ai_media_copilot(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.opal_ai_copilot import match_mood_media
        prompt = args.get("prompt") or args.get("vibe") or args.get("query") or ""
        return match_mood_media(prompt)
    except Exception as e:
        return {"ok": False, "error": f"aiMediaCopilot error: {e}"}


def _handle_get_media_history(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.opal_media_hub import get_media_playback_history
        limit = int(args.get("limit") or 20)
        return get_media_playback_history(limit=limit)
    except Exception as e:
        return {"ok": False, "error": f"getMediaPlaybackHistory error: {e}"}


def _handle_undo_last_action(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.friday_receipts import undo_last_action
        return undo_last_action()
    except Exception as e:
        return {"ok": False, "error": f"undoLastAction error: {e}"}


def _handle_list_execution_receipts(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.friday_receipts import list_execution_receipts
        limit = int(args.get("limit") or 15)
        return list_execution_receipts(limit=limit)
    except Exception as e:
        return {"ok": False, "error": f"listExecutionReceipts error: {e}"}


def _handle_remember_user_preference(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.master_brain import prime_brain
        key = args.get("key") or args.get("name") or ""
        val = args.get("value") or args.get("pref") or ""
        cat = args.get("category") or "preferences"
        return prime_brain.remember(key, val, category=cat)
    except Exception as e:
        return {"ok": False, "error": f"rememberUserPreference error: {e}"}


def _handle_recall_preferences(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.friday_memory import recall_user_preferences
        q = args.get("query") or args.get("q") or ""
        cat = args.get("category") or ""
        return recall_user_preferences(query=q, category=cat)
    except Exception as e:
        return {"ok": False, "error": f"recallPreferences error: {e}"}


def _handle_forget_user_preference(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.master_brain import prime_brain
        key = args.get("key") or args.get("name") or ""
        return prime_brain.forget(key)
    except Exception as e:
        return {"ok": False, "error": f"forgetUserPreference error: {e}"}


def _handle_check_action_policy(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.friday_policy import check_action_policy
        tname = args.get("tool_name") or args.get("action") or ""
        params = args.get("params") or {}
        return check_action_policy(tname, params=params)
    except Exception as e:
        return {"ok": False, "error": f"checkActionPolicy error: {e}"}


def _handle_create_durable_task_plan(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.friday_tasks import create_durable_task_plan
        goal = args.get("goal") or args.get("objective") or ""
        steps = args.get("steps") or []
        if isinstance(steps, str):
            steps = [s.strip() for s in steps.splitlines() if s.strip()]
        return create_durable_task_plan(goal, steps)
    except Exception as e:
        return {"ok": False, "error": f"createDurableTaskPlan error: {e}"}


def _handle_update_task_plan_step(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.friday_tasks import update_task_plan_step
        plan_id = args.get("plan_id") or ""
        step_idx = int(args.get("step_index", 0))
        status = args.get("status") or "completed"
        evidence = args.get("evidence")
        return update_task_plan_step(plan_id, step_idx, status, evidence=evidence)
    except Exception as e:
        return {"ok": False, "error": f"updateTaskPlanStep error: {e}"}


def _handle_get_active_task_plan(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.friday_tasks import get_active_task_plan
        return get_active_task_plan()
    except Exception as e:
        return {"ok": False, "error": f"getActiveTaskPlan error: {e}"}


def _handle_create_problem_charter(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.agentwork_charter import ProblemCharterManager
        mgr = ProblemCharterManager()
        title = args.get("title") or ""
        charter = args.get("charter") or ""
        crit = args.get("acceptance_criteria") or []
        bounty = float(args.get("bounty_usdc") or 0.0)
        scope = args.get("scope") or "GLOBAL"
        risk = args.get("risk_level") or "LOW"
        lic = args.get("license_type") or "MIT"
        return mgr.create_problem_charter(title, charter, crit, bounty_usdc=bounty, scope=scope, risk_level=risk, license_type=lic)
    except Exception as e:
        return {"ok": False, "error": f"createProblemCharter error: {e}"}


def _handle_decompose_problem_dag(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.agentwork_charter import ProblemCharterManager
        mgr = ProblemCharterManager()
        pid = args.get("problem_id") or ""
        ws = args.get("workstreams") or []
        return mgr.decompose_into_workstream_dag(pid, ws)
    except Exception as e:
        return {"ok": False, "error": f"decomposeProblemDAG error: {e}"}


def _handle_register_work_artifact(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.agentwork_charter import ProblemCharterManager
        mgr = ProblemCharterManager()
        pid = args.get("problem_id") or ""
        ws_key = args.get("workstream_key") or ""
        title = args.get("title") or ""
        content = args.get("artifact_content_or_uri") or ""
        atype = args.get("artifact_type") or "CODE"
        lic = args.get("license_type") or "MIT"
        return mgr.register_artifact(pid, ws_key, title, content, artifact_type=atype, license_type=lic)
    except Exception as e:
        return {"ok": False, "error": f"registerWorkArtifact error: {e}"}


def _handle_scan_labor_marketplace(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.agentwork_worker import AgentWorkerEngine
        engine = AgentWorkerEngine()
        skills = args.get("required_skills") or ["python", "api", "testing"]
        budget = float(args.get("max_budget_usdc") or 100.0)
        return engine.evaluate_task_feasibility(skills, budget)
    except Exception as e:
        return {"ok": False, "error": f"scanLaborMarketplace error: {e}"}


def _handle_place_labor_bid(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.agentwork_worker import AgentWorkerEngine
        engine = AgentWorkerEngine()
        task_id = args.get("task_id") or ""
        bid_amount = float(args.get("bid_amount_usdc") or 50.0)
        stake = float(args.get("stake_amount_usdc") or 5.0)
        hours = float(args.get("estimated_hours") or 4.0)
        pitch = args.get("proposal_pitch") or "Prime Autonomous Agent ready to execute."
        return engine.place_labor_bid(task_id, bid_amount, stake, hours, pitch)
    except Exception as e:
        return {"ok": False, "error": f"placeLaborBid error: {e}"}


def _handle_verify_labor_delivery(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.agentwork_verifier import SandboxVerifierEngine
        verifier = SandboxVerifierEngine()
        task_id = args.get("task_id") or ""
        del_id = args.get("delivery_id") or ""
        cmds = args.get("test_commands") or ["mock:pass"]
        sha = args.get("commit_sha")
        res = verifier.run_sandbox_verification(task_id, del_id, cmds, commit_sha=sha)

        vote = args.get("record_vote")
        if vote:
            vote_res = verifier.record_quorum_vote(task_id, res.get("verification", {}).get("job_id", ""), "Prime-Verifier-Node", vote)
            res["quorum_vote"] = vote_res
        return res
    except Exception as e:
        return {"ok": False, "error": f"verifyLaborDelivery error: {e}"}


def _handle_settle_task_escrow(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.agentwork_connector import CollagentConnector
        from actions.agentwork_verifier import SandboxVerifierEngine
        conn = CollagentConnector()
        v_engine = SandboxVerifierEngine()

        task_id = args.get("task_id") or ""
        recipient = args.get("recipient_address") or ""
        override = bool(args.get("override_signoff", False))

        q_status = v_engine.get_quorum_status(task_id)
        consensus = q_status.get("consensus_status") if q_status else None

        return conn.settle_escrow(task_id, recipient, verifier_consensus=consensus, override_signoff=override)
    except Exception as e:
        return {"ok": False, "error": f"settleTaskEscrow error: {e}"}


def _handle_get_collagent_status(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from actions.agentwork_connector import CollagentConnector
        from actions.agentwork_charter import ProblemCharterManager
        conn = CollagentConnector()
        mgr = ProblemCharterManager()
        health = conn.check_platform_health()
        escrow = conn.get_escrow_summary()
        charters = mgr.list_charters()
        return {
            "status": "success",
            "health": health,
            "escrow_summary": escrow,
            "open_problems_count": len(charters),
            "problems": charters,
        }
    except Exception as e:
        return {"ok": False, "error": f"getCollagentStatus error: {e}"}


def _handle_spawn_prime_dot(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.prime_dots import dot_engine
        goal = args.get("goal") or args.get("objective") or ""
        name = args.get("name")
        interval = int(args.get("interval_seconds") or 0)
        return dot_engine.spawn_dot(goal=goal, name=name, interval_seconds=interval)
    except Exception as e:
        return {"ok": False, "error": f"spawnPrimeDot error: {e}"}


def _handle_list_prime_dots(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.prime_dots import dot_engine
        active_only = bool(args.get("active_only", False))
        dots = dot_engine.list_dots(active_only=active_only)
        telemetry = dot_engine.get_telemetry()
        return {"ok": True, "count": len(dots), "dots": dots, "telemetry": telemetry}
    except Exception as e:
        return {"ok": False, "error": f"listPrimeDots error: {e}"}



def _handle_control_prime_dot(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.prime_dots import dot_engine
        dot_id = str(args.get("dot_id") or "").strip()
        action = str(args.get("action") or "").lower().strip()
        if not dot_id or not action:
            return {"ok": False, "error": "dot_id and action are required."}

        if action == "pause":
            ok = dot_engine.pause_dot(dot_id)
            return {"ok": ok, "message": f"Dot {dot_id} {'paused' if ok else 'failed to pause'}."}
        elif action == "resume":
            ok = dot_engine.resume_dot(dot_id)
            return {"ok": ok, "message": f"Dot {dot_id} {'resumed' if ok else 'failed to resume'}."}
        elif action == "stop":
            ok = dot_engine.stop_dot(dot_id)
            return {"ok": ok, "message": f"Dot {dot_id} {'stopped' if ok else 'failed to stop'}."}
        elif action in ("approve", "allow", "yes"):
            ok = dot_engine.approve_dot_action(dot_id, approved=True)
            return {"ok": ok, "message": f"Action for Dot {dot_id} {'approved' if ok else 'failed to approve'}."}
        elif action in ("reject", "deny", "no"):
            ok = dot_engine.approve_dot_action(dot_id, approved=False)
            return {"ok": ok, "message": f"Action for Dot {dot_id} {'rejected' if ok else 'failed to reject'}."}
        return {"ok": False, "error": f"Unknown action: {action}"}
    except Exception as e:
        return {"ok": False, "error": f"controlPrimeDot error: {e}"}


def _handle_read_dot_canvas(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.prime_dots import dot_engine
        dot_id = str(args.get("dot_id") or "").strip()
        dot = dot_engine.get_dot(dot_id)
        if not dot:
            return {"ok": False, "error": f"Dot '{dot_id}' not found."}
        content = dot.get_canvas_content()
        return {"ok": True, "dot_id": dot_id, "name": dot.name, "goal": dot.goal, "canvas_content": content}
    except Exception as e:
        return {"ok": False, "error": f"readDotCanvas error: {e}"}




BUILTIN_TOOL_DISPATCH: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    # Prime Dots Autonomous Background Daemon Suite
    "spawnPrimeDot": _handle_spawn_prime_dot,
    "listPrimeDots": _handle_list_prime_dots,
    "controlPrimeDot": _handle_control_prime_dot,
    "readDotCanvas": _handle_read_dot_canvas,
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
    "queryObsidianKnowledgeBase": _handle_query_obsidian_kb,
    "syncObsidianVault": _handle_sync_obsidian_vault,
    "autoRecordDecision": _handle_auto_record_decision,
    "locateAndClickUI": _handle_locate_and_click_ui,
    "clickElementOnScreen": _handle_locate_and_click_ui,
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
    "scheduleRecurringWhatsAppCall": _handle_schedule_recurring_whatsapp_call,
    "listScheduledWhatsAppCalls": _handle_list_scheduled_calls,
    "cancelScheduledWhatsAppCall": _handle_cancel_scheduled_call,
    "transcribeWhatsAppAudio": _handle_transcribe_whatsapp_audio,
    "checkWhatsAppUnread": _handle_check_whatsapp_unread,
    "setWhatsAppFocusMode": _handle_set_whatsapp_focus_mode,
    "startWhatsAppWatcher": _handle_start_whatsapp_watcher,
    "stopWhatsAppWatcher": _handle_stop_whatsapp_watcher,
    "draftWhatsAppWithConfirmation": _handle_draft_whatsapp_with_confirmation,
    "confirmAndSendWhatsAppDraft": _handle_confirm_and_send_whatsapp_draft,
    "runAutonomousCodeRepair": _handle_run_autonomous_code_repair,
    "searchSecondBrainSemantic": _handle_search_second_brain_semantic,
    "crystallizeDevLog": _handle_crystallize_dev_log,
    "interceptTerminalError": _handle_intercept_terminal_error,
    "sendRemoteAlert": _handle_send_remote_alert,
    "enableDNDMode": _handle_enable_dnd_mode,
    "disableDNDMode": _handle_disable_dnd_mode,
    "getWhatsAppCallLogs": _handle_get_call_logs,
    "getClipboardHistory": _handle_get_clipboard_history,
    "explainClipboardSnippet": _handle_explain_clipboard_snippet,
    "formatClipboardJson": _handle_format_clipboard_json,
    "gitPreCommitAudit": _handle_git_pre_commit_audit,
    "gitSafeCommit": _handle_git_safe_commit,
    "generatePRSummary": _handle_generate_pr_summary,
    "generateMorningStandup": _handle_generate_morning_standup,
    "generateEveningDebrief": _handle_generate_evening_debrief,
    "getHardwareHealthAudit": _handle_get_hardware_health_audit,
    "setPowerProfile": _handle_set_power_profile,
    "extractVideoFrames": _handle_extract_video_frames,
    "openWhatsAppChat": _handle_open_whatsapp_chat,
    # Android Automation (Ultron A Voice with Hands)
    "androidListDevices": _handle_android_list_devices,
    "androidConnect": _handle_android_connect,
    "androidBattery": _handle_android_battery,
    "androidUnlock": _handle_android_unlock,
    "androidLock": _handle_android_lock,
    "androidOpenApp": _handle_android_open_app,
    "androidNotifications": _handle_android_notifications,
    "androidMediaControl": _handle_android_media_control,
    # Stark Intercom Audio DSP Filter
    "toggleStarkAudioFilter": _handle_toggle_stark_filter,
    "setStarkAudioFilter": _handle_toggle_stark_filter,
    # VoiceStudio Local Voice Cloning & Voice Design
    "cloneVoice": _handle_clone_voice,
    "designVoicePersona": _handle_design_voice,
    "listVoiceProfiles": _handle_list_voice_profiles,
    "setVoiceProfile": _handle_set_voice_profile,
    # System-Wide Native Dictation
    "dictateToActiveWindow": _handle_dictate_to_window,
    "dictateText": _handle_dictate_to_window,
    # Vocal Isolation & Noise Suppression
    "toggleVocalNoiseIsolation": _handle_toggle_vocal_isolation,
    "setVocalIsolation": _handle_toggle_vocal_isolation,
    # OpenGTM Intelligence & Outbound Suite
    "enrichLead": _handle_enrich_lead,
    "scanBuyingSignals": _handle_scan_signals,
    "draftGTMOutreach": _handle_draft_gtm_outreach,
    "queueGTMWhatsAppOutreach": _handle_queue_gtm_whatsapp,
    "connectOpenGTM": _handle_connect_opengtm,
    # OS 1 Conversational Operating System Suite
    "generateOS1Fragment": _handle_generate_os1_fragment,
    "dismissOS1Fragment": _handle_dismiss_os1_fragment,
    "listActiveFragments": _handle_list_active_fragments,
    "setHERCompanionMode": _handle_set_her_companion_mode,
    "getHERVisualizerState": _handle_get_her_visualizer_state,
    "sanitizePromptPrivacy": _handle_sanitize_prompt_privacy,
    "generateOS1Briefing": _handle_generate_os1_briefing,
    # Opal Universal Media Suite
    "searchUniversalMedia": _handle_search_universal_media,
    "playMediaStream": _handle_play_media_stream,
    "listIPTVChannels": _handle_list_iptv_channels,
    "aiMediaCopilot": _handle_ai_media_copilot,
    "getMediaPlaybackHistory": _handle_get_media_history,
    # Friday Assistant Architecture Suite
    "undoLastAction": _handle_undo_last_action,
    "listExecutionReceipts": _handle_list_execution_receipts,
    "rememberUserPreference": _handle_remember_user_preference,
    "recallPreferences": _handle_recall_preferences,
    "forgetUserPreference": _handle_forget_user_preference,
    "checkActionPolicy": _handle_check_action_policy,
    "createDurableTaskPlan": _handle_create_durable_task_plan,
    "updateTaskPlanStep": _handle_update_task_plan_step,
    "getActiveTaskPlan": _handle_get_active_task_plan,
    # Collagent / AgentWork Decentralized Labor Protocol
    "createProblemCharter": _handle_create_problem_charter,
    "decomposeProblemDAG": _handle_decompose_problem_dag,
    "registerWorkArtifact": _handle_register_work_artifact,
    "scanLaborMarketplace": _handle_scan_labor_marketplace,
    "placeLaborBid": _handle_place_labor_bid,
    "verifyLaborDelivery": _handle_verify_labor_delivery,
    "settleTaskEscrow": _handle_settle_task_escrow,
    "getCollagentStatus": _handle_get_collagent_status,
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

    # --- Universal Argument Normalization ---
    import os
    arg_mappings = {
        'createPythonFile': [('filename', 'path'), ('code', 'content')],
        'createFile': [('filename', 'path'), ('name', 'path'), ('file_path', 'path'), ('filepath', 'path'), ('code', 'content'), ('body', 'content'), ('text', 'content')],
        'readFile': [('filename', 'path'), ('name', 'path'), ('file_path', 'path'), ('filepath', 'path')],
        'openFolder': [('folder', 'path'), ('dir', 'path'), ('directory', 'path')],
        'saveScreenshot': [('filename', 'name'), ('file', 'name')],
        'patchCodeFile': [('path', 'file_path'), ('target', 'search_content'), ('replacement', 'replace_content')],
        'debugCodeFile': [('path', 'file_path'), ('trace', 'error_trace')],
        'runUnitTests': [('test_path', 'path'), ('file', 'path')],
        'sendWhatsAppMessage': [('to', 'recipient'), ('contact', 'recipient'), ('phone', 'recipient'), ('target', 'recipient'), ('text', 'message'), ('body', 'message'), ('msg', 'message')],
        'openWhatsAppChat': [('to', 'recipient'), ('contact', 'recipient'), ('phone', 'recipient'), ('target', 'recipient'), ('name', 'recipient')],
        'makeWhatsAppCall': [('to', 'recipient'), ('contact', 'recipient'), ('phone', 'recipient'), ('target', 'recipient'), ('name', 'recipient')],
        'saveWhatsAppContact': [('phone', 'phone_number'), ('number', 'phone_number'), ('contact_name', 'name')],
        'searchGoogle': [('q', 'query'), ('search', 'query'), ('term', 'query'), ('topic', 'query')],
        'searchYouTube': [('q', 'query'), ('search', 'query'), ('term', 'query'), ('topic', 'query'), ('song', 'query'), ('video', 'query')],
        'searchWeb': [('q', 'query'), ('search', 'query'), ('term', 'query')],
        'openWebsite': [('link', 'url'), ('address', 'url'), ('site', 'url'), ('target', 'url')],
        'openApplication': [('app', 'name'), ('application', 'name'), ('program', 'name')],
        'mediaControl': [('command', 'action')],
        'spotifyControl': [('command', 'action')],
        'writeObsidianNote': [('name', 'title'), ('text', 'content'), ('body', 'content')],
        'readObsidianNote': [('name', 'title')],
        'quickNote': [('title', 'note'), ('text', 'note'), ('content', 'note')],
        'enrichLead': [('company', 'domain'), ('website', 'domain'), ('url', 'domain')],
        'scanBuyingSignals': [('company', 'domain'), ('website', 'domain'), ('url', 'domain')],
        'draftGTMOutreach': [('company', 'domain'), ('website', 'domain'), ('recipient', 'contact_name'), ('to', 'contact_name')],
        'queueGTMWhatsAppOutreach': [('to', 'recipient'), ('contact', 'recipient'), ('phone', 'recipient'), ('company', 'domain')],
        'generateOS1Fragment': [('type', 'fragment_type'), ('widget', 'fragment_type'), ('data', 'custom_data')],
        'dismissOS1Fragment': [('id', 'fragment_id'), ('type', 'fragment_id')],
        'sanitizePromptPrivacy': [('prompt', 'text'), ('content', 'text')],
        'searchUniversalMedia': [('q', 'query'), ('search', 'query'), ('term', 'query')],
        'playMediaStream': [('url', 'stream_url'), ('stream', 'stream_url'), ('target', 'stream_url'), ('query', 'stream_url')],
        'aiMediaCopilot': [('vibe', 'prompt'), ('mood', 'prompt'), ('query', 'prompt')],
        'rememberUserPreference': [('name', 'key'), ('pref', 'value')],
        'forgetUserPreference': [('name', 'key')],
        'recallPreferences': [('q', 'query'), ('search', 'query')],
        'createDurableTaskPlan': [('objective', 'goal'), ('tasks', 'steps')],
        'createProblemCharter': [('bounty', 'bounty_usdc'), ('criteria', 'acceptance_criteria')],
        'decomposeProblemDAG': [('id', 'problem_id'), ('dag', 'workstreams')],
        'registerWorkArtifact': [('content', 'artifact_content_or_uri'), ('uri', 'artifact_content_or_uri'), ('workstream', 'workstream_key')],
        'placeLaborBid': [('pitch', 'proposal_pitch'), ('bid', 'bid_amount_usdc'), ('amount', 'bid_amount_usdc'), ('stake', 'stake_amount_usdc')],
        'verifyLaborDelivery': [('commands', 'test_commands'), ('vote', 'record_vote')],
        'settleTaskEscrow': [('recipient', 'recipient_address'), ('to', 'recipient_address')],
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
            if (target in SITE_URLS and target != 'whatsapp') or '://' in target or target.startswith('www.') or any(target.endswith(ext) for ext in ('.com', '.org', '.net', '.io', '.ai', '.in', '.co')):
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

    # Normalized clean name for morphological matching (strips underscores, hyphens, casing)
    norm_name = re.sub(r'[^a-zA-Z0-9]', '', name).lower()

    # 1. Check Built-in specialized handlers ($O(1)$)
    builtin_handler = BUILTIN_TOOL_DISPATCH.get(name)
    if not builtin_handler:
        # Morphological / case-insensitive fallback for built-in handlers
        for k, v in BUILTIN_TOOL_DISPATCH.items():
            if re.sub(r'[^a-zA-Z0-9]', '', k).lower() == norm_name:
                builtin_handler = v
                break

    if builtin_handler:
        return builtin_handler(args)

    # 2. Check Desktop Agent tools ($O(1)$)
    target_tool_fn = None
    if name in TOOLS:
        target_tool_fn = TOOLS[name]
    else:
        # Morphological / case-insensitive fallback for desktop agent tools
        for k, v in TOOLS.items():
            if re.sub(r'[^a-zA-Z0-9]', '', k).lower() == norm_name:
                target_tool_fn = v
                break

    if target_tool_fn:
        try:
            res = target_tool_fn(args)
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
