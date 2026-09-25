"""
PRIME AI :: AUTONOMOUS NEURAL COCKPIT
Cyberpunk CLI Interface with Real-Time Telemetry & Ambient Voice Link.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import winsound
except ImportError:
    winsound = None

import psutil
import speech_recognition as sr
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory

from ai_agent import agent
from config import config
import providers
from tool_definitions import TOOL_SPECS, execute_tool
from voice_engine import voice

# Force UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Cyberpunk Neon Theme
custom_theme = Theme({
    "info": "bold cyan",
    "warning": "bold yellow",
    "error": "bold red",
    "success": "bold green",
    "command": "bold magenta",
    "ai": "bold bright_cyan",
    "user": "bold bright_white",
    "tool": "bold bright_yellow",
    "dim": "dim cyan",
    "highlight": "bold bright_magenta",
    "neon_blue": "bold bright_blue",
    "neon_green": "bold bright_green",
    "neon_pink": "bold bright_magenta",
})
console = Console(theme=custom_theme)

# Session Telemetry
SESSION_START = time.time()
SESSION_STATS = {
    "queries": 0,
    "tool_calls": 0,
    "last_latency_ms": 0.0,
}

# Slash Commands Auto-completer
SLASH_COMMANDS = [
    "/menu",
    "/v", "/mic", "/voice",
    "/listen",
    "/hud",
    "/providers",
    "/switch",
    "/ping",
    "/key",
    "/stats",
    "/weather",
    "/briefing",
    "/notes",
    "/git",
    "/tools",
    "/agents", "/persona", "/activate", "/deactivate",
    "/goal", "/refine", "/lessons",
    "/system",
    "/speak",
    "/autostart",
    "/clear",
    "/help",
    "/exit", "quit"
]
completer = WordCompleter(SLASH_COMMANDS, ignore_case=True, sentence=True)

HISTORY_FILE = Path.home() / ".prime_history"
_session = None


def get_user_input(prompt_text: str = "⚡ PRIME ❯ ") -> str:
    """Safely get user input with prompt_toolkit or fallback to console.input."""
    global _session
    if _session is None:
        try:
            _session = PromptSession(history=FileHistory(str(HISTORY_FILE)), completer=completer)
        except Exception:
            _session = False  # Mark fallback

    if _session and _session is not False:
        try:
            return _session.prompt(prompt_text).strip()
        except KeyboardInterrupt:
            console.print("\n[dim yellow]^C (Session active. Press Ctrl+D or type /exit to quit)[/dim yellow]")
            return ""
        except EOFError:
            raise
        except Exception:
            pass

    try:
        return console.input(f"[bold cyan]{escape(prompt_text)}[/bold cyan]").strip()
    except KeyboardInterrupt:
        console.print("\n[dim yellow]^C[/dim yellow]")
        return ""


def format_bar(percent: float, width: int = 14) -> str:
    """ASCII progress meter with color grading."""
    filled = int(width * (percent / 100.0))
    filled = max(0, min(width, filled))
    empty = width - filled
    
    if percent < 60:
        bar_color = "bright_green"
    elif percent < 85:
        bar_color = "bright_yellow"
    else:
        bar_color = "bright_red"

    bar = f"[{bar_color}]{'█' * filled}[/{bar_color}][dim]{'░' * empty}[/dim]"
    return f"{bar} {percent:4.1f}%"


def get_waveform_visualizer() -> str:
    """Simulates a sleek audio frequency equalizer."""
    return "[bright_cyan] ▂[/bright_cyan][cyan]▃[/cyan][bright_blue]▅[/bright_blue][bright_magenta]▆[/bright_magenta][magenta]▇[/magenta][bright_magenta]▆[/bright_magenta][bright_blue]▅[/bright_blue][cyan]▃[/cyan][bright_cyan]▂ [/bright_cyan]"


def print_banner():
    """Renders the high-tech Cyberpunk HUD Cockpit Banner."""
    console.clear()

    ascii_logo = """
  ██████╗ ██████╗ ██╗███╗   ███╗███████╗     █████╗ ██╗
  ██╔══██╗██╔══██╗██║████╗ ████║██╔════╝    ██╔══██╗██║
  ██████╔╝██████╔╝██║██╔████╔██║█████╗      ███████║██║
  ██╔═══╝ ██╔══██╗██║██║╚██╔╝██║██╔══╝      ██╔══██║██║
  ██║     ██║  ██║██║██║ ╚═╝ ██║███████╗    ██║  ██║██║
  ╚═╝     ╚═╝  ╚═╝╚═╝╚═╝     ╚═╝╚══════╝    ╚═╝  ╚═╝╚═╝
    """

    logo_text = Text(ascii_logo, style="bold cyan")
    tagline = Text("  ⚡ AUTONOMOUS NEURAL COCKPIT :: ZERO GUI · 24/7 AMBIENT VOICE · PURE POWER  ", style="bold bright_white on dark_blue")

    header_group = Group(
        Align.center(logo_text),
        Align.center(tagline),
        Text(""),
    )
    console.print(header_group)

    # Telemetry Panel
    provider_id = config.get_active_provider()
    prov_info = providers.get_provider_by_id(provider_id)
    prov_display = prov_info["name"] if prov_info else provider_id.upper()
    tts_status = f"[bold bright_green]ONLINE[/bold bright_green] ({voice.current_voice})" if voice.tts_enabled else "[bold red]MUTED[/bold red]"
    
    # Left: AI Core & Neural State
    t_left = Table(show_header=False, box=None, padding=(0, 1))
    t_left.add_row("[bold cyan]Operator:[/bold cyan]", "[bold bright_white]Pratik Thorat[/bold bright_white]")
    t_left.add_row("[bold cyan]Neural Brain:[/bold cyan]", f"[bold bright_green]{config.default_model}[/bold bright_green] ([bold magenta]{prov_display}[/bold magenta])")
    t_left.add_row("[bold cyan]Spoken Voice:[/bold cyan]", f"{tts_status} {get_waveform_visualizer()}")
    t_left.add_row("[bold cyan]Tool Arsenal:[/bold cyan]", f"[bold bright_cyan]{len(TOOL_SPECS)} Active Modules[/bold bright_cyan] (Desktop + Code + SAT)")
    t_left.add_row("[bold cyan]Ambient Voice:[/bold cyan]", "[bold bright_green]● LIVE 24/7 (Always-On Mic)[/bold bright_green] [dim](Hands-free)[/dim]")
    persona_name = agent.active_persona["display_name"] if agent.active_persona else "Prime Core (Operator)"
    t_left.add_row("[bold cyan]Active Persona:[/bold cyan]", f"[bold bright_magenta]🎭 {persona_name}[/bold bright_magenta]")
    from prime_goal_harness import goal_tracker
    active_goal = goal_tracker.get_active_goal()
    if active_goal:
        goal_disp = f"[bold bright_yellow]{active_goal['objective'][:30]}[/bold bright_yellow] [dim]({active_goal['progress_percent']:.0f}%)[/dim]"
    else:
        goal_disp = "[dim]No active goal set (use /goal)[/dim]"
    t_left.add_row("[bold cyan]Active Goal:[/bold cyan]", f"🎯 {goal_disp}")

    # Right: Host Hardware Vitals
    cpu_pct = psutil.cpu_percent(interval=0.1)
    ram_pct = psutil.virtual_memory().percent
    disk_pct = psutil.disk_usage(".").percent

    bat_str = "A/C Mains"
    if hasattr(psutil, "sensors_battery"):
        bat = psutil.sensors_battery()
        if bat:
            bat_str = f"{bat.percent}% {'(⚡ Plugged)' if bat.power_plugged else '(🔋 Battery)'}"

    uptime_sec = int(time.time() - SESSION_START)
    uptime_str = f"{uptime_sec // 60}m {uptime_sec % 60}s"

    t_right = Table(show_header=False, box=None, padding=(0, 1))
    t_right.add_row("[bold cyan]CPU Load:[/bold cyan]", f"{format_bar(cpu_pct)}")
    t_right.add_row("[bold cyan]RAM Usage:[/bold cyan]", f"{format_bar(ram_pct)}")
    t_right.add_row("[bold cyan]Storage Usage:[/bold cyan]", f"{format_bar(disk_pct)}")
    t_right.add_row("[bold cyan]Power State:[/bold cyan]", f"[bold bright_cyan]{bat_str}[/bold bright_cyan]")
    t_right.add_row("[bold cyan]Cockpit Uptime:[/bold cyan]", f"[bold bright_white]{uptime_str}[/bold bright_white]")

    p_left = Panel(t_left, title="[bold bright_white]⚡ NEURAL CORE STATUS[/bold bright_white]", border_style="bright_cyan")
    p_right = Panel(t_right, title="[bold bright_white]🖥️ HOST TELEMETRY[/bold bright_white]", border_style="bright_cyan")

    console.print(Columns([p_left, p_right], expand=True))
    console.print(Rule(style="dim cyan"))
    console.print("[dim cyan]Type any prompt to talk, [bold bright_white]/menu[/bold bright_white] for command hub, [bold bright_white]/v[/bold bright_white] for mic, [bold bright_white]/providers[/bold bright_white] for free LLMs, or [bold bright_white]/help[/bold bright_white].[/dim cyan]\n")


def print_menu():
    """Interactive quick access menu."""
    table = Table(title="⚡ PRIME COMMAND COCKPIT MENU", border_style="bright_cyan", header_style="bold bright_cyan")
    table.add_column("Key", style="bold bright_magenta", justify="center", width=6)
    table.add_column("Quick Action", style="bold bright_white", width=32)
    table.add_column("Description", style="dim cyan")

    table.add_row("[1]", "🎙️  Start 24/7 Voice Mode", "Hands-free ambient voice assistant (open mic)")
    table.add_row("[2]", "⚡  Live Telemetry Cockpit (HUD)", "Real-time auto-refreshing CPU, RAM, Disk gauges")
    table.add_row("[3]", "🔄  Switch LLM Provider", "Select Groq, Cerebras, GitHub Models, Gemini, OpenRouter, etc.")
    table.add_row("[4]", "🔑  Configure API Keys", "Quickly save free provider API keys to .env")
    table.add_row("[5]", "🐙  Claw Code Git Control", "Autonomous Git commit, diff review & push")
    table.add_row("[6]", "📚  Obsidian Second Brain", "Search & browse markdown knowledge vault")
    table.add_row("[7]", "🛠️  Browse 44 Automation Tools", "Explore Desktop, Media, Filesystem & Dev tools")
    table.add_row("[8]", "🌅  Personalized Morning Briefing", "Trigger voice daily summary with weather & tasks")
    table.add_row("[9]", "🌦️  Live Weather Forecast", "Instant meteorological report for your city")
    table.add_row("[10]", "⏱️  Benchmark Provider Latency", "Test round-trip response speed of active AI core")
    table.add_row("[11]", "📊  Session Performance Stats", "View total queries, tool executions & uptime")
    table.add_row("[12]", "🧹  Clear & Redraw HUD", "Clean terminal buffer and render fresh cockpit")
    table.add_row("[13]", "🎙️  Mark-LIV Voice Matrix", "Switch between Charon (Mark-LIV JARVIS), Ryan, Puck, Fenrir")
    table.add_row("[0]", "🚪  Exit Prime AI", "Power down neural cockpit session")

    console.print(table)
    console.print("[dim cyan]Enter number [bold bright_white]1-13[/bold bright_white] or command name directly.[/dim cyan]\n")


def print_help():
    table = Table(title="⚡ PRIME COMMAND MATRIX", border_style="bright_cyan", header_style="bold bright_cyan")
    table.add_column("Command", style="bold bright_magenta", no_wrap=True)
    table.add_column("Action & Description", style="white")

    table.add_row("/menu", "Open interactive numbered command menu")
    table.add_row("/v, /mic", "One-shot voice command: records audio and executes immediately")
    table.add_row("/voice [name]", "Open Mark-LIV Voice Matrix or switch voice (e.g. /voice charon, /voice ryan)")
    table.add_row("/listen", "Start 24/7 continuous ambient listening loop in the current terminal")
    table.add_row("/hud", "Open full-screen live refreshing telemetry dashboard")
    table.add_row("/providers", "Browse 9 curated permanently free LLM providers (from awesome-free-llm-apis)")
    table.add_row("/switch [provider_id]", "Switch active LLM provider (e.g. /switch groq)")
    table.add_row("/ping", "Test round-trip response latency of the active AI model")
    table.add_row("/key <provider> <key>", "Store free API key into .env permanently")
    table.add_row("/stats", "Display session runtime metrics, queries, and tool invocations")
    table.add_row("/weather [city]", "Fetch instant live meteorological forecast for any city")
    table.add_row("/briefing", "Trigger comprehensive personalized morning voice briefing")
    table.add_row("/notes [query]", "Search user's Obsidian Vault Markdown second brain")
    table.add_row("/git [action]", "Run automated Git commands (status, diff, commit, push)")
    table.add_row("/tools [filter]", "Browse all 47 desktop & developer automation tools")
    table.add_row("/agents, /personas [filter]", "Browse 279 specialized agency persona profiles")
    table.add_row("/activate <persona>", "Adopt specialized expert persona (e.g. /activate frontend-developer)")
    table.add_row("/deactivate", "Restore default Prime Core autonomous persona")
    table.add_row("/goal [objective]", "View or set persistent autonomous objective")
    table.add_row("/goal progress <pct> [note]", "Update completion progress of active goal (e.g. /goal progress 75)")
    table.add_row("/refine <topic> = <insight>", "Record self-improving memory lesson / developer preference")
    table.add_row("/lessons", "Review all learned patterns and continual harness insights")
    table.add_row("/system", "Detailed hardware vitals report (CPU, RAM, Disks, Battery)")
    table.add_row("/speak on|off", "Toggle neural speech voice output (persisted to .env)")
    table.add_row("/wakeword on|off", "Toggle wake-word protection (must say 'Prime ...' vs open mic)")
    table.add_row("/autostart on|off", "Enable or disable automatic boot launch on Windows startup")
    table.add_row("/operator on|off", "Toggle proactive autonomous background operator & sentinels")
    table.add_row("/traces [limit]", "Inspect OpenJarvis execution reflection traces & latency")
    table.add_row("/mcp", "Inspect and manage Model Context Protocol (MCP) tool servers")
    table.add_row("/clear", "Clear terminal display and redraw HUD")
    table.add_row("/exit, quit", "Shutdown Prime AI session")

    console.print(table)


def print_tools(filter_kw: Optional[str] = None):
    table = Table(title=f"⚡ TOOL ARSENAL ({len(TOOL_SPECS)} Active Capabilities)", border_style="bright_cyan")
    table.add_column("Tool Name", style="bold bright_cyan", no_wrap=True)
    table.add_column("Category", style="bold bright_magenta")
    table.add_column("Capability Description", style="white")

    for spec in TOOL_SPECS:
        name = spec["name"]
        desc = spec["description"]

        if "Obsidian" in name:
            cat = "Knowledge"
        elif any(w in name for w in ("Terminal", "patch", "git", "Test", "debug")):
            cat = "Claw Dev"
        elif any(w in name for w in ("App", "Website", "Window")):
            cat = "Desktop"
        elif any(w in name for w in ("Volume", "Media", "spotify")):
            cat = "Audio"
        elif any(w in name for w in ("weather", "briefing")):
            cat = "Routines"
        elif any(w in name for w in ("File", "Directory")):
            cat = "Filesystem"
        else:
            cat = "Core"

        if filter_kw and filter_kw.lower() not in (name + desc + cat).lower():
            continue

        table.add_row(name, cat, desc)

    console.print(table)


def print_agency_agents(filter_kw: Optional[str] = None):
    import agency_roster
    agents = agency_roster.load_all_agency_agents()
    table = Table(title=f"⚡ AGENCY AGENTS ROSTER ({len(agents)} Specialist Personas Available)", border_style="bright_magenta")
    table.add_column("Agent ID", style="bold bright_magenta", no_wrap=True)
    table.add_column("Specialist Role", style="bold bright_white")
    table.add_column("Division", style="bold cyan")
    table.add_column("Description", style="dim white")

    shown = 0
    for aid, a in agents.items():
        if filter_kw:
            kw = filter_kw.lower()
            if kw not in (aid + a["display_name"] + a["category"] + a["description"]).lower():
                continue
        table.add_row(aid, a["display_name"], a["category"], a["description"][:100] + ("..." if len(a["description"]) > 100 else ""))
        shown += 1
        if not filter_kw and shown >= 35:
            break

    console.print(table)
    if not filter_kw:
        console.print(f"[dim cyan]Showing first 35 of {len(agents)} agents. Use [bold bright_white]/agents <division>[/bold bright_white] (e.g. /agents security, /agents engineering, /agents design) to search.[/dim cyan]")
    console.print("[dim cyan]To activate: [bold bright_white]/activate <agent_id>[/bold bright_white] or speak: [bold bright_white]\"Prime, activate Frontend Developer\"[/bold bright_white][/dim cyan]\n")


def print_providers():
    table = Table(title="⚡ FREE LLM PROVIDER DIRECTORY (Curated from awesome-free-llm-apis)", border_style="bright_cyan")
    table.add_column("ID", style="bold bright_magenta", no_wrap=True)
    table.add_column("Provider Name", style="bold bright_white")
    table.add_column("Status", justify="center")
    table.add_column("Inference Speed", style="dim bright_cyan")
    table.add_column("Free Tier Limits", style="dim white")
    table.add_column("Key Signup Link", style="bold yellow")

    active_provider = config.get_active_provider()

    for p in providers.get_providers_list():
        p_id = p["id"]
        is_active = (p_id == active_provider)
        is_cfg = providers.is_provider_configured(p_id)

        if is_active:
            status_badge = "[bold bright_green]● ACTIVE[/bold bright_green]"
        elif is_cfg:
            status_badge = "[bold green]✓ READY[/bold green]"
        else:
            status_badge = "[dim yellow]○ NO KEY[/dim yellow]"

        table.add_row(
            f"{p_id}",
            p["name"],
            status_badge,
            p.get("speed", "Fast"),
            p["free_tier"],
            p["signup_url"]
        )

    console.print(table)
    console.print("[dim cyan]To switch: [bold bright_white]/switch <provider_id>[/bold bright_white]  |  To add key: [bold bright_white]/key <provider_id> <api_key>[/bold bright_white][/dim cyan]\n")


def print_voice_menu():
    """Display Mark-LIV and Neural Voice Matrix."""
    table = Table(title="⚡ MARK-LIV NEURAL VOICE MATRIX", border_style="bright_cyan", header_style="bold bright_cyan")
    table.add_column("Voice Command", style="bold bright_magenta", no_wrap=True)
    table.add_column("Voice Name", style="bold bright_white")
    table.add_column("Engine", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Personality / Tone", style="dim white")

    curr = voice.current_voice.lower()
    voices = [
        ("charon", "Charon", "Gemini Live / Speech", "Mark-LIV Signature JARVIS (Deep, Authoritative Masculine)"),
        ("puck", "Puck", "Gemini Live / Speech", "Upbeat, energetic, and rapid male tone"),
        ("fenrir", "Fenrir", "Gemini Live / Speech", "Excitable and dynamic male voice"),
        ("kore", "Kore", "Gemini Live / Speech", "Firm, confident, and professional"),
        ("aoede", "Aoede", "Gemini Live / Speech", "Breezy, calm, and soothing"),
        ("ryan", "en-GB-RyanNeural", "Microsoft Edge-TTS", "British male butler / classic JARVIS tone"),
        ("guy", "en-US-GuyNeural", "Microsoft Edge-TTS", "Mark-LIV default offline fallback male"),
        ("christopher", "en-US-ChristopherNeural", "Microsoft Edge-TTS", "American broadcast news male"),
        ("david", "Microsoft David", "Windows SAPI5", "Local offline emergency backup"),
    ]

    for vid, vname, engine, desc in voices:
        is_active = (vid == curr or vname.lower() == curr)
        status = "[bold bright_green]● ACTIVE[/bold bright_green]" if is_active else "[dim]○ standby[/dim]"
        table.add_row(f"/voice {vid}", vname, engine, status, desc)

    console.print(table)
    console.print(f"[cyan]Current Voice: [bold bright_green]{voice.current_voice}[/bold bright_green][/cyan]")
    console.print("[dim cyan]To switch: [bold bright_white]/voice <name>[/bold bright_white] (e.g. /voice charon, /voice ryan, /voice puck) | Test: [bold bright_white]/voice test[/bold bright_white][/dim cyan]\n")


def ping_active_provider():
    """Benchmark the round-trip latency of the active LLM provider."""
    provider = config.get_active_provider()
    model = config.get_default_model(provider)
    console.print(f"[bold cyan]⚡ Measuring latency to [bold bright_white]{provider.upper()}[/bold bright_white] ({model})...[/bold cyan]")
    
    t0 = time.time()
    orig_tts = voice.tts_enabled
    voice.tts_enabled = False
    try:
        response = agent.process_message("ping - return only the single word: PONG")
        # Pop the benchmark out of history so it doesn't pollute ongoing conversation
        if agent.history and agent.history[-1].get("content") == response:
            agent.history.pop()
            if agent.history and "ping" in agent.history[-1].get("content", "").lower():
                agent.history.pop()
        latency = (time.time() - t0) * 1000.0
        SESSION_STATS["last_latency_ms"] = latency
        console.print(f"[bold bright_green]✓ Round-trip latency:[/bold bright_green] [bold bright_white]{latency:.1f} ms[/bold bright_white] | Response: [dim]{response.strip()[:40]}[/dim]")
    except Exception as e:
        console.print(f"[bold red]✗ Latency test failed:[/bold red] {e}")
    finally:
        voice.tts_enabled = orig_tts


def print_stats():
    """Display session performance stats."""
    uptime_sec = int(time.time() - SESSION_START)
    table = Table(title="⚡ PRIME SESSION METRICS", border_style="bright_cyan")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="bold bright_white")

    table.add_row("Session Uptime", f"{uptime_sec // 3600}h {(uptime_sec % 3600) // 60}m {uptime_sec % 60}s")
    table.add_row("Neural Queries Handled", str(SESSION_STATS["queries"]))
    table.add_row("Autonomous Tools Executed", str(SESSION_STATS["tool_calls"]))
    table.add_row("Last Round-trip Latency", f"{SESSION_STATS['last_latency_ms']:.1f} ms" if SESSION_STATS['last_latency_ms'] else "Not measured (use /ping)")
    table.add_row("Active LLM Core", f"{config.get_active_provider().upper()} ({config.default_model})")
    table.add_row("Voice Output State", f"ONLINE ({voice.current_voice})" if voice.tts_enabled else "MUTED")
    console.print(table)


def render_live_hud(duration: int = 10):
    """Full-screen live-refreshing hardware & telemetry HUD."""
    console.print(f"[bold cyan]Launching Live Telemetry Cockpit ({duration}s)... Press Ctrl+C to exit.[/bold cyan]")

    def generate_hud_table():
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage(".").percent

        t = Table(title=f"⚡ PRIME TELEMETRY COCKPIT — {datetime.now().strftime('%H:%M:%S')}", border_style="bright_cyan", expand=True)
        t.add_column("Telemetry Sensor", style="bold cyan")
        t.add_column("Current Metric", style="bold white")
        t.add_column("Visual Gauge", style="bold bright_green")

        t.add_row("CPU Load", f"{cpu:4.1f} %", format_bar(cpu, width=28))
        t.add_row("RAM Occupancy", f"{ram:4.1f} %", format_bar(ram, width=28))
        t.add_row("Storage Utilization", f"{disk:4.1f} %", format_bar(disk, width=28))

        if hasattr(psutil, "cpu_freq") and psutil.cpu_freq():
            freq = psutil.cpu_freq().current
            t.add_row("CPU Frequency", f"{freq:.0f} MHz", "[bold cyan]Active Dynamic Core[/bold cyan]")

        t.add_row("Active Arsenal", f"{len(TOOL_SPECS)} Tools", "[bold bright_green]100% Armed & Ready[/bold bright_green]")
        t.add_row("Audio Waveform", get_waveform_visualizer(), "[bold bright_cyan]Voice Bus Online[/bold bright_cyan]")
        return Panel(t, border_style="bright_cyan", padding=(1, 2))

    try:
        with Live(generate_hud_table(), refresh_per_second=2, console=console) as live:
            for _ in range(duration * 2):
                time.sleep(0.5)
                live.update(generate_hud_table())
    except KeyboardInterrupt:
        pass
    console.print("[dim cyan]Live Telemetry closed.[/dim cyan]\n")


def on_tool_call(name: str, args: dict):
    SESSION_STATS["tool_calls"] += 1
    arg_summary = ", ".join(f"[bold cyan]{k}[/bold cyan]={v!r}" for k, v in args.items()) if args else "no args"
    console.print(f" [bold bright_yellow]⚡ NEURAL TOOL EXECUTION[/bold bright_yellow] → [bold bright_white]{name}[/bold bright_white]({arg_summary})")


def on_tool_result(name: str, result: dict):
    if not isinstance(result, dict):
        result = {"ok": True, "result": str(result)}
    if result.get("ok"):
        res = result.get("result", {})
        msg = res.get("result", res) if isinstance(res, dict) else str(res)
        preview = str(msg).strip()
        if len(preview) > 180:
            preview = preview[:180] + "..."
        console.print(f" [bold bright_green]✓ COMPLETED[/bold bright_green] [bold cyan]{name}[/bold cyan] → [dim bright_white]{escape(preview)}[/dim bright_white]")
    else:
        err = result.get("error", "Action failed.")
        console.print(f" [bold red]✗ TOOL ERROR[/bold red] [bold cyan]{name}[/bold cyan] → [bold red]{escape(str(err))}[/bold red]")


def handle_user_query(query: str):
    if not query.strip():
        return

    SESSION_STATS["queries"] += 1
    console.print(f"\n[bold bright_cyan]❯ OPERATOR:[/bold bright_cyan] [bold bright_white]{escape(query)}[/bold bright_white]")

    t0 = time.time()
    with console.status("[bold bright_cyan]⚡ Prime Neural Brain is reasoning...[/bold bright_cyan]", spinner="dots12"):
        try:
            response = agent.process_message(
                query,
                on_tool_call=on_tool_call,
                on_tool_result=on_tool_result,
            )
        except Exception as e:
            response = f"I encountered an internal error: {e}"
            console.print(f"[bold red]AI execution error: {escape(str(e))}[/bold red]")
    elapsed = (time.time() - t0) * 1000.0
    SESSION_STATS["last_latency_ms"] = elapsed

    # Render response in a styled cyberpunk panel
    md = Markdown(response)
    panel = Panel(
        md,
        title=f"[bold bright_cyan]⚡ PRIME AI[/bold bright_cyan] [dim]({elapsed:.0f}ms)[/dim]",
        border_style="bright_cyan",
        padding=(1, 2),
    )
    console.print(panel)


_ambient_listener_thread = None
_ambient_stop_event = threading.Event()
_query_lock = threading.Lock()


def _ambient_voice_worker():
    """Background 24/7 ambient microphone listener that processes spoken commands automatically."""
    from voice_assistant import find_best_mic_index, clean_command, WAKE_WORDS, play_chime, get_require_wake_word
    mic_idx, mic_name = find_best_mic_index()

    r = sr.Recognizer()
    r.dynamic_energy_threshold = False
    r.energy_threshold = 220
    r.pause_threshold = 0.45
    r.non_speaking_duration = 0.2

    speaking_start_time = None

    try:
        with sr.Microphone(device_index=mic_idx) as source:
            req_ww = get_require_wake_word()
            mode_desc = "Say 'Prime ...' to command" if req_ww else "Speak commands anytime, hands-free"
            console.print(f"  [bold bright_green]● WAKE WORD LISTENER LIVE[/bold bright_green] [dim]— {mode_desc}[/dim]\n")
            try:
                r.adjust_for_ambient_noise(source, duration=0.5)
                r.energy_threshold = min(max(r.energy_threshold, 150), 350)
            except Exception:
                r.energy_threshold = 220
            while not _ambient_stop_event.is_set():
                try:
                    # Echo prevention: pause listening when Prime is speaking out loud
                    if voice.is_speaking or not voice.tts_queue.empty():
                        if speaking_start_time is None:
                            speaking_start_time = time.time()
                        elif time.time() - speaking_start_time > 60:
                            voice._is_speaking = False
                            speaking_start_time = None
                        time.sleep(0.12)
                        continue

                    if speaking_start_time is not None:
                        speaking_start_time = None
                        time.sleep(0.15)

                    try:
                        audio = r.listen(source, timeout=3, phrase_time_limit=12)
                    except sr.WaitTimeoutError:
                        continue

                    if voice.is_speaking or not voice.tts_queue.empty():
                        continue

                    # Try Google Web Speech with en-IN first (ultra-fast, understands Indian accents & Hinglish)
                    raw_text = None
                    try:
                        raw_text = r.recognize_google(audio, language="en-IN").strip()
                    except Exception:
                        try:
                            raw_text = r.recognize_google(audio, language="en-US").strip()
                        except Exception:
                            pass

                    # Fallback to local Faster-Whisper if Google was offline or failed
                    if not raw_text:
                        try:
                            from wake_word import wake_detector
                            raw_text = wake_detector.whisper.transcribe_audio_data(audio)
                        except Exception:
                            pass

                    if not raw_text:
                        continue

                    should_run, command = clean_command(raw_text)
                    if not should_run:
                        continue

                    with _query_lock:
                        play_chime("wake")
                        console.print(f"\n🎤 [bold bright_white]Heard:[/bold bright_white] \"{escape(raw_text)}\"")

                        # If user just called wake word
                        if not command or command.strip() in WAKE_WORDS:
                            ack = "Haan Pratik, boliye! I am listening."
                            console.print(f"[bold cyan]Prime:[/bold cyan] {ack}")
                            voice.speak(ack)
                            continue

                        # Check spoken voice change command
                        cmd_lower = command.lower()
                        if any(p in cmd_lower for p in ("change voice to", "switch voice to", "set voice to")):
                            available_voices = []
                            for v_list in voice.get_available_voices().values():
                                available_voices.extend(v_list)
                            for vname in [v.lower() for v in available_voices]:
                                if vname in cmd_lower:
                                    new_v = voice.set_voice(vname)
                                    ack = f"Voice matrix switched to {new_v}, Sir."
                                    console.print(f"[bold bright_green]Prime:[/bold bright_green] {ack}")
                                    voice.speak(ack)
                                    break
                            else:
                                voice.speak("Voice not recognized.")
                            continue

                        handle_user_query(command)
                        status_prompt = "● WAKE WORD LIVE — Say 'Prime' to command..." if get_require_wake_word() else "● AMBIENT MIC LIVE — Listening 24/7..."
                        console.print(f"\n[bold bright_green]{status_prompt}[/bold bright_green]")

                except Exception:
                    time.sleep(0.4)
    except Exception as e:
        console.print(f"[dim yellow]Ambient mic initialization note: {e}[/dim yellow]")


def start_ambient_mic():
    """Starts the 24/7 ambient microphone background thread."""
    global _ambient_listener_thread
    if _ambient_listener_thread is not None and _ambient_listener_thread.is_alive():
        return
    _ambient_stop_event.clear()
    _ambient_listener_thread = threading.Thread(target=_ambient_voice_worker, daemon=True, name="AmbientMic")
    _ambient_listener_thread.start()


def stop_ambient_mic():
    """Stops the ambient microphone thread if running."""
    _ambient_stop_event.set()


def listen_continuous():
    """Continuous ambient voice status."""
    console.print("\n[bold bright_green]● AMBIENT MIC IS ACTIVE 24/7 IN THE BACKGROUND[/bold bright_green]")
    console.print("[dim cyan]You can speak directly anytime without pressing any keys![/dim cyan]\n")


def get_prompt_text() -> str:
    """Builds a dynamic futuristic prompt string."""
    provider = config.get_active_provider().upper()
    persona_tag = f" :: 🎭 {agent.active_persona['display_name'].upper()}" if agent.active_persona else ""
    return f"╭─[⚡ PRIME :: {provider}{persona_tag}]─[🎙️ LIVE]─[🟢 READY]\n╰─❯ "


def main():
    from single_instance import acquire_single_instance, prevent_system_sleep
    if not acquire_single_instance():
        console.print("[bold yellow]⚠ Prime AI is already running in background.[/bold yellow]")
        console.print("[dim]Another instance is active. Exiting duplicate instance to prevent double-voice echo.[/dim]\n")
        sys.exit(0)

    prevent_system_sleep(True)

    print_banner()
    start_ambient_mic()
    try:
        from prime_operator import operator
        operator.start()
    except Exception:
        pass

    try:
        import tray_manager
        tray_manager.start_tray_icon()
    except Exception:
        pass

    from voice_assistant import get_dynamic_welcome_message
    welcome_msg = get_dynamic_welcome_message()
    console.print(f"  [bold cyan]Prime:[/bold cyan] [bold bright_white]\"{welcome_msg}\"[/bold bright_white]\n")
    voice.speak(welcome_msg)

    while True:
        try:
            prompt_str = get_prompt_text()
            user_input = get_user_input(prompt_str)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim cyan]Shutting down Prime AI cockpit. Systems offline.[/dim cyan]")
            stop_ambient_mic()
            try:
                from prime_operator import operator
                operator.stop()
            except Exception:
                pass
            break

        if not user_input:
            continue

        cmd_lower = user_input.lower().strip()

        # Normalize plain commands without leading slash (e.g. 'help' -> '/help')
        first_token = cmd_lower.split()[0] if cmd_lower else ""
        if not cmd_lower.startswith("/") and first_token in (
            "help", "menu", "tools", "hud", "stats", "providers", "ping", "system",
            "briefing", "notes", "git", "agents", "personas", "goal", "lessons", "voice",
            "listen", "weather", "speak", "clear", "cls", "autostart", "wakeword",
            "operator", "traces", "mcp"
        ):
            cmd_lower = "/" + cmd_lower

        # Numeric Menu Shortcuts
        if cmd_lower == "1":
            listen_continuous()
            continue
        elif cmd_lower == "2":
            render_live_hud(10)
            continue
        elif cmd_lower == "3":
            print_providers()
            continue
        elif cmd_lower == "4":
            prov = console.input("[bold cyan]Enter Provider ID (e.g. groq, cerebras, gemini): [/bold cyan]").strip().lower()
            key = console.input(f"[bold cyan]Enter API key for {prov}: [/bold cyan]").strip()
            if prov and key:
                config.set_api_key(prov, key)
                agent.init_provider()
                console.print(f"[bold green]✓ Saved API key for {prov}.[/bold green]")
            continue
        elif cmd_lower == "5":
            res = execute_tool("gitAutomate", {"action": "status"})
            output = res.get("result") or res.get("error") or str(res)
            console.print(Panel(str(output).strip(), title="[bold cyan]🐙 GIT STATUS[/bold cyan]", border_style="cyan"))
            continue
        elif cmd_lower == "6":
            query = console.input("[bold cyan]Enter search query for Obsidian Vault: [/bold cyan]").strip()
            if query:
                res = execute_tool("searchObsidianNotes", {"query": query})
                console.print(Panel(str(res.get("result", "")), title=f"[bold cyan]📚 OBSIDIAN RESULTS: '{query}'[/bold cyan]", border_style="cyan"))
            continue
        elif cmd_lower == "7":
            print_tools()
            continue
        elif cmd_lower == "8":
            with console.status("[bold cyan]Generating Morning Briefing...[/bold cyan]"):
                res = execute_tool("morningBriefing", {"action": "briefing"})
            console.print(Panel(res.get("result", ""), title="[bold cyan]🌅 MORNING BRIEFING[/bold cyan]", border_style="cyan"))
            continue
        elif cmd_lower == "9":
            city = console.input("[bold cyan]Enter city name (default Pune): [/bold cyan]").strip() or "Pune"
            res = execute_tool("getWeather", {"city": city})
            console.print(f"[bold bright_green]{res.get('result', res)}[/bold bright_green]")
            continue
        elif cmd_lower == "10":
            ping_active_provider()
            continue
        elif cmd_lower == "11":
            print_stats()
            continue
        elif cmd_lower == "12":
            print_banner()
            continue
        elif cmd_lower == "13":
            print_voice_menu()
            continue
        elif cmd_lower == "0":
            console.print("[bold cyan]Powering down Prime AI neural cockpit. Good day, Sir.[/bold cyan]")
            break

        # Command Routing
        if cmd_lower in ("/exit", "quit", "exit", "/quit"):
            console.print("[bold cyan]Shutting down Prime AI. Good day, Sir.[/bold cyan]")
            break

        elif cmd_lower in ("/clear", "cls"):
            print_banner()

        elif cmd_lower == "/menu":
            print_menu()

        elif cmd_lower == "/help":
            print_help()

        elif cmd_lower == "/stats":
            print_stats()

        elif cmd_lower == "/ping":
            ping_active_provider()

        elif cmd_lower.startswith("/tools"):
            parts = user_input.split(maxsplit=1)
            filter_kw = parts[1].strip() if len(parts) > 1 else None
            print_tools(filter_kw)

        elif cmd_lower == "/hud":
            render_live_hud(10)

        elif cmd_lower == "/listen":
            listen_continuous()

        elif cmd_lower.startswith(("/agents", "/personas")):
            parts = user_input.split(maxsplit=1)
            filter_kw = parts[1].strip() if len(parts) > 1 else None
            print_agency_agents(filter_kw)

        elif cmd_lower.startswith(("/activate", "/persona")):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                target = parts[1].strip().lower()
                if target in ("reset", "deactivate", "prime", "default"):
                    agent.deactivate_persona()
                    console.print("[bold cyan]✓ Deactivated specialist persona. Prime Neural Cockpit restored.[/bold cyan]")
                else:
                    activated = agent.activate_persona(target)
                    if activated:
                        console.print(f"[bold bright_magenta]✓ Activated Specialist Persona: {activated}[/bold bright_magenta]")
                    else:
                        console.print(f"[yellow]Could not find persona matching '{target}'. Use /agents to browse all 279 specialists.[/yellow]")
            else:
                curr = agent.active_persona["display_name"] if agent.active_persona else "Default Prime Cockpit"
                console.print(f"[cyan]Current Active Persona: [bold bright_magenta]{curr}[/bold bright_magenta][/cyan]")
                console.print("[dim cyan]Usage: [bold bright_white]/activate <name>[/bold bright_white] or [bold bright_white]/deactivate[/bold bright_white][/dim cyan]")

        elif cmd_lower in ("/deactivate", "/reset_persona"):
            agent.deactivate_persona()
            console.print("[bold cyan]✓ Deactivated specialist persona. Prime Neural Cockpit restored.[/bold cyan]")

        elif cmd_lower.startswith("/goal"):
            from prime_goal_harness import goal_tracker
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                arg = parts[1].strip()
                if arg.lower() in ("clear", "cancel", "reset"):
                    goal_tracker.clear_active_goal()
                    console.print("[yellow]Active goal cleared.[/yellow]")
                elif arg.lower() in ("done", "finish", "complete"):
                    g = goal_tracker.complete_active_goal("Goal completed by user.")
                    console.print(f"[bold bright_green]✓ Goal completed: {g['objective'] if g else ''}[/bold bright_green]")
                elif arg.lower().startswith("progress"):
                    p_parts = arg.split(maxsplit=2)
                    raw_pct = p_parts[1].rstrip("%") if len(p_parts) > 1 else "50"
                    try:
                        pct = float(raw_pct)
                    except ValueError:
                        console.print("[red]Invalid progress percentage. Please provide a number (e.g. /goal progress 75).[/red]")
                        continue
                    note = p_parts[2] if len(p_parts) > 2 else ""
                    g = goal_tracker.update_progress(pct, note=note)
                    if g:
                        console.print(f"[bold cyan]✓ Goal progress updated to {pct:.0f}%[/bold cyan]")
                    else:
                        console.print("[yellow]No active goal to update. Use /goal <objective> to set one.[/yellow]")
                else:
                    g = goal_tracker.set_goal(arg)
                    console.print(f"[bold bright_green]🎯 Persistent Goal Set:[/bold bright_green] [bold bright_white]{escape(g['objective'])}[/bold bright_white]")
            else:
                g = goal_tracker.get_active_goal()
                if g:
                    subtasks_text = ""
                    if g.get("subtasks"):
                        st_lines = []
                        for st in g["subtasks"]:
                            box = "[green]✓[/green]" if st.get("done") else "[dim]○[/dim]"
                            st_lines.append(f"  {box} {escape(st.get('title', ''))}")
                        subtasks_text = "\n[bold cyan]Subtasks:[/bold cyan]\n" + "\n".join(st_lines)
                    console.print(Panel(f"[bold white]{escape(g['objective'])}[/bold white]\n[cyan]Progress:[/cyan] [bold bright_green]{g['progress_percent']:.0f}%[/bold bright_green]\n[dim]Status: {g['status']}[/dim]{subtasks_text}", title="🎯 CURRENT PERSISTENT GOAL", border_style="bright_yellow"))
                else:
                    console.print("[dim]No active goal set. Type: [bold bright_white]/goal <your goal>[/bold bright_white][/dim]")

        elif cmd_lower.startswith("/refine"):
            from prime_goal_harness import continual_harness
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                text = parts[1].strip()
                if "=" in text:
                    topic, insight = text.split("=", 1)
                elif ":" in text:
                    topic, insight = text.split(":", 1)
                else:
                    topic, insight = "General", text
                l = continual_harness.record_lesson(topic.strip(), insight.strip(), source="operator_cli")
                console.print(f"[bold bright_green]✓ Learned Lesson Recorded:[/bold bright_green] [bold cyan]{l['topic']}[/bold cyan] → [dim bright_white]{l['insight']}[/dim bright_white]")
            else:
                console.print("[yellow]Usage: /refine <topic> = <insight / rule / preference>[/yellow]")

        elif cmd_lower == "/lessons":
            from prime_goal_harness import continual_harness
            lessons = continual_harness.get_lessons(limit=15)
            t = Table(title="⚡ CONTINUAL HARNESS LESSONS & LEARNED PATTERNS", border_style="bright_cyan")
            t.add_column("#", justify="center", style="dim")
            t.add_column("Topic", style="bold cyan")
            t.add_column("Learned Insight / Habit", style="white")
            for l in lessons:
                t.add_row(str(l.get("id", "-")), l.get("topic", ""), l.get("insight", ""))
            console.print(t)

        elif cmd_lower.startswith("/weather"):
            parts = user_input.split(maxsplit=1)
            city = parts[1].strip() if len(parts) > 1 else "Pune"
            res = execute_tool("getWeather", {"city": city})
            if res.get("ok"):
                console.print(f"[bold bright_green]{res.get('result')}[/bold bright_green]")
            else:
                console.print(f"[bold red]✗ Weather check failed: {res.get('error', 'City not found')}[/bold red]")

        elif cmd_lower == "/briefing":
            with console.status("[bold cyan]Generating Morning Briefing...[/bold cyan]"):
                res = execute_tool("morningBriefing", {"action": "briefing"})
            if res.get("ok"):
                console.print(Panel(str(res.get("result", "")), title="[bold cyan]🌅 MORNING BRIEFING[/bold cyan]", border_style="cyan"))
            else:
                console.print(f"[bold red]✗ Briefing failed: {res.get('error', 'Could not generate briefing')}[/bold red]")

        elif cmd_lower.startswith("/notes"):
            parts = user_input.split(maxsplit=1)
            query = parts[1].strip() if len(parts) > 1 else ""
            if not query:
                console.print("[yellow]Usage: /notes <search query>[/yellow]")
            else:
                res = execute_tool("searchObsidianNotes", {"query": query})
                if res.get("ok"):
                    console.print(Panel(str(res.get("result", "")), title=f"[bold cyan]📚 OBSIDIAN RESULTS: '{query}'[/bold cyan]", border_style="cyan"))
                else:
                    console.print(f"[bold red]✗ Notes search failed: {res.get('error', 'Vault note not found')}[/bold red]")

        elif cmd_lower.startswith("/git"):
            parts = user_input.split(maxsplit=1)
            action = parts[1].strip() if len(parts) > 1 else "status"
            res = execute_tool("gitAutomate", {"action": action})
            output = res.get("result") or res.get("error") or str(res)
            border_col = "green" if res.get("ok") else "red"
            console.print(Panel(str(output).strip(), title=f"[bold cyan]🐙 GIT: {action.upper()}[/bold cyan]", border_style=border_col))

        elif cmd_lower.startswith(("/v", "/mic")):
            console.print("[bold cyan]🎙️ Listening for single command... Speak now![/bold cyan]")
            audio_text = voice.listen_one_shot(timeout=7)
            if audio_text:
                console.print(f"[bold green]🎤 Recognized:[/bold green] \"{audio_text}\"")
                handle_user_query(audio_text)
            else:
                console.print("[dim yellow]No speech detected.[/dim yellow]")

        elif cmd_lower.startswith("/voice"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                arg = parts[1].strip()
                if arg.lower() in ("test", "sample", "check"):
                    console.print(f"[bold cyan]Testing voice [bold bright_magenta]{voice.current_voice}[/bold bright_magenta]...[/bold cyan]")
                    voice.speak(f"Mark-LIV voice matrix online, Sir. Active synthesizer is {voice.current_voice}. Ready for instructions.")
                elif arg.lower() in ("list", "menu", "matrix"):
                    print_voice_menu()
                else:
                    new_v = voice.set_voice(arg)
                    console.print(f"[bold bright_green]✓ Active Voice switched to: {new_v}[/bold bright_green]")
                    voice.speak(f"Voice synthesizer updated to {new_v}. Systems ready, Sir.")
            else:
                print_voice_menu()

        elif cmd_lower.startswith("/speak"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                arg = parts[1].lower().strip()
                if arg in ("on", "1", "true"):
                    voice.tts_enabled = True
                    try:
                        from dotenv import set_key
                        from config import ENV_PATH
                        set_key(str(ENV_PATH), "VOICE_OUTPUT", "true")
                    except Exception:
                        pass
                    console.print("[green]Speech audio enabled and saved to config.[/green]")
                elif arg in ("off", "0", "false"):
                    voice.tts_enabled = False
                    try:
                        from dotenv import set_key
                        from config import ENV_PATH
                        set_key(str(ENV_PATH), "VOICE_OUTPUT", "false")
                    except Exception:
                        pass
                    console.print("[yellow]Speech audio disabled (silent mode) and saved to config.[/yellow]")
            else:
                state = "ON" if voice.tts_enabled else "OFF"
                console.print(f"[cyan]Spoken voice is currently: [bold]{state}[/bold][/cyan]")

        elif cmd_lower == "/system":
            res = execute_tool("getSystemStats", {})
            console.print(Panel(str(res.get("result", "")), title="[bold cyan]🖥️ HARDWARE DIAGNOSTICS[/bold cyan]", border_style="cyan"))

        elif cmd_lower.startswith("/autostart"):
            parts = user_input.split(maxsplit=1)
            arg = parts[1].lower().strip() if len(parts) > 1 else ""
            if arg in ("on", "enable", "1", "true"):
                res = execute_tool("enableAutoStart", {})
                console.print(f"[bold green]✓ {res.get('result')}[/bold green]")
            elif arg in ("off", "disable", "0", "false"):
                res = execute_tool("disableAutoStart", {})
                console.print(f"[yellow]{res.get('result')}[/yellow]")
            else:
                res = execute_tool("getAutoStartStatus", {})
                col = "green" if res.get("enabled") else "yellow"
                console.print(f"[{col}]● {res.get('result')}[/{col}]")
                console.print("[dim cyan]Usage: [bold bright_white]/autostart on[/bold bright_white] | [bold bright_white]/autostart off[/bold bright_white] | [bold bright_white]/autostart status[/bold bright_white][/dim cyan]")

        elif cmd_lower.startswith("/wakeword"):
            from voice_assistant import get_require_wake_word, set_require_wake_word
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                arg = parts[1].lower().strip()
                if arg in ("on", "enable", "1", "true"):
                    set_require_wake_word(True)
                    console.print("[bold green]✓ Wake-Word Protection ENABLED.[/bold green] [dim]Prime will only respond when 'Prime' is spoken in the sentence.[/dim]")
                elif arg in ("off", "disable", "0", "false"):
                    set_require_wake_word(False)
                    console.print("[yellow]! Wake-Word Protection DISABLED.[/yellow] [dim]Prime will respond to all room speech (open-mic mode).[/dim]")
                else:
                    state = "ENABLED (Must say 'Prime ...')" if get_require_wake_word() else "DISABLED (Open mic)"
                    console.print(f"[cyan]Wake-word requirement is: [bold]{state}[/bold][/cyan]")
            else:
                state = "ENABLED (Must say 'Prime ...')" if get_require_wake_word() else "DISABLED (Open mic)"
                console.print(f"[cyan]Wake-word requirement is: [bold]{state}[/bold][/cyan]")
                console.print("[dim cyan]Usage: [bold bright_white]/wakeword on[/bold bright_white] | [bold bright_white]/wakeword off[/bold bright_white][/dim cyan]")

        elif cmd_lower.startswith("/operator"):
            from prime_operator import operator
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                arg = parts[1].lower().strip()
                if arg in ("on", "enable", "1", "true"):
                    operator.set_enabled(True)
                    console.print("[bold green]✓ Proactive Autonomous Operator ENABLED.[/bold green] [dim]Background sentinels active.[/dim]")
                elif arg in ("off", "disable", "0", "false"):
                    operator.set_enabled(False)
                    console.print("[yellow]! Proactive Autonomous Operator DISABLED.[/yellow]")
                else:
                    st = operator.get_status()
                    console.print(Panel(f"[cyan]Enabled:[/cyan] {st['enabled']}\n[cyan]Running:[/cyan] {st['running']}\n[cyan]RAM Load:[/cyan] {st['ram_percent']}%\n[cyan]Battery:[/cyan] {st['battery']}\n[cyan]Sentinels:[/cyan] {', '.join(st['sentinels'])}", title="🤖 PROACTIVE OPERATOR STATUS", border_style="bright_cyan"))
            else:
                st = operator.get_status()
                console.print(Panel(f"[cyan]Enabled:[/cyan] {st['enabled']}\n[cyan]Running:[/cyan] {st['running']}\n[cyan]RAM Load:[/cyan] {st['ram_percent']}%\n[cyan]Battery:[/cyan] {st['battery']}\n[cyan]Sentinels:[/cyan] {', '.join(st['sentinels'])}", title="🤖 PROACTIVE OPERATOR STATUS", border_style="bright_cyan"))
                console.print("[dim cyan]Usage: [bold bright_white]/operator on[/bold bright_white] | [bold bright_white]/operator off[/bold bright_white] | [bold bright_white]/operator status[/bold bright_white][/dim cyan]")

        elif cmd_lower.startswith("/traces"):
            from prime_traces import trace_logger
            parts = user_input.split(maxsplit=1)
            limit = 8
            if len(parts) > 1 and parts[1].strip().isdigit():
                limit = int(parts[1].strip())
            console.print(trace_logger.render_traces_table(limit=limit))

        elif cmd_lower.startswith("/mcp"):
            from mcp_bridge import mcp_bridge
            parts = user_input.split(maxsplit=2)
            if len(parts) > 1 and parts[1].lower() in ("enable", "disable"):
                action = parts[1].lower()
                target_server = parts[2].strip() if len(parts) > 2 else ""
                if target_server:
                    ok = mcp_bridge.enable_server(target_server, enable=(action == "enable"))
                    if ok:
                        console.print(f"[bold green]✓ MCP server '{target_server}' updated: {action.upper()}[/bold green]")
                    else:
                        console.print(f"[yellow]Server '{target_server}' not found in mcp_servers.json[/yellow]")
                else:
                    console.print("[yellow]Usage: /mcp enable <server_name> | /mcp disable <server_name>[/yellow]")
            else:
                console.print(mcp_bridge.render_mcp_table())
                console.print("[dim cyan]Usage: [bold bright_white]/mcp enable <server>[/bold bright_white] | [bold bright_white]/mcp disable <server>[/bold bright_white][/dim cyan]")

        elif cmd_lower == "/providers":
            print_providers()

        elif cmd_lower.startswith("/switch"):
            parts = user_input.split()
            if len(parts) >= 2:
                prov = parts[1].lower().replace("/", "")
                key = parts[2].strip() if len(parts) > 2 else ""
                p_info = providers.get_provider_by_id(prov)
                if not p_info:
                    console.print(f"[yellow]Unknown provider '{prov}'. Type /providers to see available options.[/yellow]")
                else:
                    if key:
                        config.set_api_key(prov, key)
                    config.set_active_provider(prov)
                    agent.init_provider()
                    console.print(f"[bold green]✓ Switched AI Provider to: {p_info['name']} (Model: {config.get_default_model(prov)})[/bold green]")
            else:
                print_providers()
                console.print("[dim cyan]Type [bold bright_white]/switch <id>[/bold bright_white] to activate a provider.[/dim cyan]")

        elif cmd_lower.startswith("/key"):
            parts = user_input.split()
            if len(parts) >= 3:
                prov = parts[1].lower()
                val = parts[2].strip()
                p_check = providers.get_provider_by_id(prov)
                if not p_check and prov not in ("gemini", "openai", "groq", "cerebras", "github", "openrouter", "mistral", "deepseek"):
                    console.print(f"[yellow]Unknown provider ID '{prov}'. Type /providers to view valid provider IDs.[/yellow]")
                    continue
                config.set_api_key(prov, val)
                agent.init_provider()
                console.print(f"[bold green]✓ API key for '{prov}' saved permanently to .env.[/bold green]")
            else:
                console.print("[yellow]Usage: /key <provider_id> <your_key> (e.g. /key groq gsk_...)[/yellow]")

        else:
            # Standard conversational AI query
            handle_user_query(user_input)


if __name__ == "__main__":
    main()
