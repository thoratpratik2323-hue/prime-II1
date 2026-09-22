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
]


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

    if name in ("getCurrentTime", "getTime", "currentTime", "get_current_time"):
        from datetime import datetime
        now_str = datetime.now().strftime("%A, %B %d, %Y %I:%M:%S %p")
        return {"ok": True, "result": f"Current system time is {now_str}"}

    # Handle Claw Code Developer Engine
    if name == "runTerminalCommand":
        try:
            import claw_developer
            cmd = args.get("command", "")
            cwd = args.get("cwd")
            return claw_developer.run_terminal_command(cmd, cwd=cwd)
        except Exception as e:
            return {"ok": False, "error": f"Terminal execution failed: {e}"}

    elif name == "patchCodeFile":
        try:
            import claw_developer
            fp = args.get("file_path", "")
            sc = args.get("search_content", "")
            rc = args.get("replace_content", "")
            return claw_developer.patch_file(fp, sc, rc)
        except Exception as e:
            return {"ok": False, "error": f"Patching failed: {e}"}

    elif name == "gitAutomate":
        try:
            import claw_developer
            act = args.get("action", "status")
            msg = args.get("message")
            cwd = args.get("cwd")
            return claw_developer.git_automate(act, message=msg, cwd=cwd)
        except Exception as e:
            return {"ok": False, "error": f"Git automation failed: {e}"}

    elif name == "runUnitTests":
        try:
            import claw_developer
            fw = args.get("framework", "pytest")
            path = args.get("path")
            cwd = args.get("cwd")
            return claw_developer.run_unit_tests(fw, path=path, cwd=cwd)
        except Exception as e:
            return {"ok": False, "error": f"Test runner failed: {e}"}

    elif name == "debugCodeFile":
        try:
            import claw_developer
            fp = args.get("file_path", "")
            et = args.get("error_trace")
            ins = args.get("instructions")
            return claw_developer.debug_file(fp, error_trace=et, instructions=ins)
        except Exception as e:
            return {"ok": False, "error": f"Debugging failed: {e}"}

    # Handle IP-Codemaker Project Exporter
    elif name == "exportProjectStarter":
        try:
            import project_exporter
            pt = args.get("project_type", "react_vite")
            dest = args.get("destination_dir")
            return project_exporter.export_project_starter(pt, destination_dir=dest)
        except Exception as e:
            return {"ok": False, "error": f"Project starter export failed: {e}"}

    elif name == "exportWorkspaceZip":
        try:
            import project_exporter
            op = args.get("output_path")
            return project_exporter.export_workspace_zip(output_path=op)
        except Exception as e:
            return {"ok": False, "error": f"Workspace zip export failed: {e}"}

    # Handle SAT / Obsidian / Morning Briefing / Weather actions
    elif name == "searchObsidianNotes":
        try:
            import obsidian_rag
            q = args.get("query", "")
            notes = obsidian_rag.search_notes(q)
            if not notes:
                return {"ok": True, "result": f"No notes found matching '{q}' in Obsidian Vault."}
            return {"ok": True, "result": notes}
        except Exception as e:
            return {"ok": False, "error": f"Obsidian search error: {e}"}

    elif name == "readObsidianNote":
        try:
            import obsidian_rag
            n = args.get("note_name", "")
            content = obsidian_rag.read_note(n)
            return {"ok": True, "result": content}
        except Exception as e:
            return {"ok": False, "error": f"Obsidian read error: {e}"}

    elif name == "writeObsidianNote":
        try:
            import obsidian_rag
            n = args.get("note_name", "")
            c = args.get("content", "")
            res = obsidian_rag.write_note(n, c)
            return {"ok": True, "result": res}
        except Exception as e:
            return {"ok": False, "error": f"Obsidian write error: {e}"}

    elif name == "getWeather":
        try:
            from actions.weather_report import weather_action
            city = args.get("city", "Pune")
            res = weather_action({"city": city})
            return {"ok": True, "result": res}
        except Exception as e:
            return {"ok": False, "error": f"Weather fetch error: {e}"}

    elif name == "morningBriefing":
        try:
            from actions.morning_briefer import morning_briefer
            res = morning_briefer({'action': args.get('action', 'briefing'), 'hour': args.get('hour', 8), 'minute': args.get('minute', 0)})
            return {"ok": True, "result": res}
        except Exception as e:
            return {"ok": False, "error": f"Morning briefing error: {e}"}

    # Handle IP-Prime action modules
    elif name == "mediaControl":
        try:
            from actions.media_controller import execute_media_control
            action = args.get("action", "play_pause")
            action_map = {'play_pause': 'play', 'previous': 'prev', 'stop': 'pause'}
            action = action_map.get(action.lower(), action.lower())
            res = execute_media_control(action)
            return {"ok": True, "result": res}
        except Exception as e:
            return {"ok": False, "error": f"Media control error: {e}"}

    elif name == "spotifyControl":
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

    elif name == "quickNote":
        try:
            from actions.computer_settings import add_note
            text = args.get("text", "")
            res = add_note(text)
            return {"ok": True, "result": f"Note saved: {text}"}
        except Exception as e:
            return {"ok": False, "error": f"Note save error: {e}"}

    elif name == "operatorControl":
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

    # Handle desktop_agent tools
    if name not in TOOLS:
        if registry.has_tool(name):
            return registry.execute(name, args)
        return {"ok": False, "error": f"Tool '{name}' not found."}

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
