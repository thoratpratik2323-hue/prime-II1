"""
Prime AI — 24/7 Always-On Hands-Free Voice Assistant.
Continuously listens to microphone with high sensitivity,
processes commands directly without requiring typing,
executes desktop tools, and speaks back in realistic male voice.
"""

from __future__ import annotations

import os
import re
import sys
import time
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

try:
    import winsound
except ImportError:
    winsound = None

import speech_recognition as sr
from ai_agent import agent
from config import config
from tool_definitions import TOOL_SPECS
from voice_engine import voice

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()

# Wake-Word enforcement: only respond when the user addresses 'Prime'.
REQUIRE_WAKE_WORD = os.getenv("REQUIRE_WAKE_WORD", "true").lower() in ("true", "1", "yes")

# Keywords that trigger Prime (strictly focused on Prime + common variants)
WAKE_WORDS = sorted(
    [
        'hey prime', 'okay prime', 'ok prime', 'hello prime',
        'hi prime', 'suno prime', 'oye prime', 'ip prime', 'bhai prime',
        'prime', 'prem', 'jarvis', 'saturday', 'crime', 'pram'
    ],
    key=len, reverse=True
)


def set_require_wake_word(val: bool) -> None:
    """Toggle wake word requirement and persist to .env."""
    global REQUIRE_WAKE_WORD
    REQUIRE_WAKE_WORD = bool(val)
    try:
        from dotenv import set_key
        from config import ENV_PATH
        set_key(str(ENV_PATH), "REQUIRE_WAKE_WORD", "true" if val else "false")
    except Exception:
        pass


def get_require_wake_word() -> bool:
    """Return whether wake word is required."""
    return REQUIRE_WAKE_WORD


def get_dynamic_welcome_message() -> str:
    """Generate dynamic, randomized welcome greeting for Pratik Thorat."""
    import random
    from datetime import datetime

    hour = datetime.now().hour
    if 5 <= hour < 12:
        time_greeting = "Good morning, Sir."
    elif 12 <= hour < 17:
        time_greeting = "Good afternoon, Pratik."
    elif 17 <= hour < 22:
        time_greeting = "Good evening, Sir."
    else:
        time_greeting = "Late night operations active, Pratik."

    templates = [
        "Welcome back, Sir! What is today's plan? Prime is standing by.",
        f"{time_greeting} Welcome back! All neural systems online. What are we building today?",
        "Welcome back, Pratik! Cockpit primed and ready. What's on our agenda today?",
        f"{time_greeting} Systems online and awaiting instructions. What is today's mission, Sir?",
        "Welcome back, Sir! Neural cores calibrated and listening. What's our plan for today?",
        f"{time_greeting} Welcome back, Pratik! Prime is ready for action, say Prime to command.",
    ]
    return random.choice(templates)


def play_chime(kind: str = "wake"):
    """Audible high-tech feedback tones."""
    try:
        if winsound:
            if kind == "wake":
                winsound.Beep(988, 70)
                winsound.Beep(1318, 100)
            elif kind == "done":
                winsound.Beep(1318, 70)
                winsound.Beep(988, 90)
    except Exception:
        pass


def print_voice_header(mic_name: str):
    os.system("cls" if os.name == "nt" else "clear")

    ascii_banner = (
        "==========================================================\n"
        "    PRIME AI  ::  AUTONOMOUS NEURAL COCKPIT\n"
        "      [ Zero GUI · 24/7 Voice Driven · Pure Power ]\n"
        "=========================================================="
    )
    console.print(f"[bold cyan]{ascii_banner}[/bold cyan]")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("[bold cyan]System:[/bold cyan]", "[bold bright_white]Autonomous Digital Cockpit (Built for Pratik Thorat)[/bold bright_white]")
    table.add_row("[bold cyan]Status:[/bold cyan]", "[bold green]● LIVE 24/7 (Always Listening, Zero Typing)[/bold green]")
    table.add_row("[bold cyan]Voice:[/bold cyan]", f"[bold bright_magenta]Mark-LIV Neural Voice ({voice.current_voice})[/bold bright_magenta]")
    table.add_row("[bold cyan]AI Brain:[/bold cyan]", f"[bold]{config.get_default_model(config.get_active_provider())}[/bold]")
    trigger_mode = "[green]Wake-Word Protected (Say 'Prime ...')[/green]" if REQUIRE_WAKE_WORD else "[green]Open-Mic (Speak any command directly)[/green]"
    table.add_row("[bold cyan]Trigger Mode:[/bold cyan]", trigger_mode)
    table.add_row("[bold cyan]Tools Active:[/bold cyan]", f"{len(TOOL_SPECS)} desktop & system automation tools")

    console.print(Panel(table, border_style="cyan", title="[bold bright_white]System Cockpit Online[/bold bright_white]"))
    if REQUIRE_WAKE_WORD:
        console.print("[bold yellow]Wake Word Protected:[/bold yellow] [dim]Say \"Prime open YouTube\", \"Prime kya time hua hai\", \"Prime volume up\"[/dim]\n")
    else:
        console.print("[bold yellow]Simply speak into your mic:[/bold yellow] [dim]\"Open Chrome\", \"What's my CPU usage?\", \"Volume up\"[/dim]\n")


GHOST_FILLER_WORDS = {
    "you", "ah", "yeah", "okay", "um", "oh", "hm", "mhm", "uh", "so", "like", 
    "the", "a", "an", "ok", "yep", "nope", "hey", "well", "right", "i", "me"
}
ACTION_KEYWORDS = {
    "open", "play", "mute", "unmute", "pause", "stop", "help", "status", "lock", 
    "sleep", "restart", "close", "kya", "batao", "chalao", "band", "time", "date",
    "weather", "cpu", "ram", "volume", "take", "click", "type", "press", "search"
}

def clean_command(text: str) -> tuple[bool, str]:
    """Extract command, stripping wake word and filtering ambient ghost words/noise."""
    lower = text.lower().strip()
    has_wake_word = False
    clean = lower

    for kw in WAKE_WORDS:
        pattern = rf'\b{re.escape(kw)}\b[\s,:.\.?!]*'
        if re.search(pattern, lower):
            has_wake_word = True
            clean = re.sub(pattern, '', lower, count=1).strip()
            break

    # If wake word was spoken, user is explicitly talking to Prime
    if has_wake_word:
        return True, clean

    # If wake word is required but was not heard
    if REQUIRE_WAKE_WORD:
        return False, ''

    # Open-Mic Mode: Filter ambient noises, breath fragments, and isolated filler utterances
    words = re.findall(r'\b[a-zA-Z0-9_\u0900-\u097F]+\b', lower)
    if not words:
        return False, ''

    # Filter out pure filler sounds (e.g. "you", "yeah yeah", "okay okay", "ah")
    meaningful = [w for w in words if w not in GHOST_FILLER_WORDS]
    if not meaningful:
        return False, ''

    # If short phrase (<=3 words), must have at least 2 meaningful words OR start with an action keyword
    if len(words) <= 3:
        if len(meaningful) < 2 and words[0] not in ACTION_KEYWORDS and words[-1] not in ACTION_KEYWORDS:
            return False, ''

    return True, lower


def on_tool_call(name: str, args: dict):
    arg_summary = ", ".join(f"{k}={v!r}" for k, v in args.items()) if args else ""
    console.print(f"  [cyan]⚡ Executing:[/cyan] [bold bright_white]{name}[/bold bright_white]({arg_summary})")


def on_tool_result(name: str, result: dict):
    if not isinstance(result, dict):
        result = {'ok': True, 'result': str(result)}
    if result.get("ok"):
        res = result.get("result", {})
        msg = res.get("result", res) if isinstance(res, dict) else str(res)
        console.print(f"  [green]✓ Done:[/green] [dim]{msg}[/dim]")
    else:
        err = result.get("error", "Failed")
        console.print(f"  [red]✗ Error:[/red] [bold red]{err}[/bold red]")


def find_best_mic_index() -> tuple[Optional[int], str]:
    """Find the best active microphone on the system, verifying it has input channels and can open."""
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        input_devices = []
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0:
                    name = info.get("name", "")
                    input_devices.append((i, name))
            except Exception:
                pass
        p.terminate()
    except Exception:
        input_devices = []

    # Check for connected bluetooth headset/mic in verified INPUT devices
    for idx, name in input_devices:
        name_lower = name.lower()
        if "output" in name_lower:
            continue
        if any(h in name_lower for h in ("headset", "bluetooth", "airbass", "ptron", "wireless", "airlits", "hands-free", "vivo")):
            try:
                with sr.Microphone(device_index=idx) as test_source:
                    return idx, name
            except Exception:
                continue

    # Default to Windows System Default Recording Device (device_index=None)
    return None, "System Default (Windows Audio Mapper)"


def run_voice_loop():
    from single_instance import acquire_single_instance, prevent_system_sleep
    if not acquire_single_instance():
        console.print("[bold yellow]⚠ Prime AI is already active in another window or background process.[/bold yellow]")
        console.print("[dim]Exiting duplicate instance to avoid audio echo and mic capture conflicts.[/dim]\n")
        return

    prevent_system_sleep(True)

    mic_idx, mic_name = find_best_mic_index()
    print_voice_header(mic_name)

    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = False
    recognizer.energy_threshold = 250
    recognizer.pause_threshold = 0.6
    recognizer.non_speaking_duration = 0.3

    # Dynamic personalized welcome announcement in Charon voice
    welcome_msg = get_dynamic_welcome_message()
    console.print(f"  [bold cyan]Prime:[/bold cyan] [bold bright_white]\"{welcome_msg}\"[/bold bright_white]\n")
    voice.speak(welcome_msg)

    listen_msg = "[bold green]● WAKE WORD LISTENER LIVE...[/bold green] [dim](Say 'Prime ...' anytime)[/dim]\n" if REQUIRE_WAKE_WORD else "[bold green]● LISTENING 24/7...[/bold green] [dim](Say a command anytime)[/dim]\n"
    console.print(listen_msg)

    speaking_start_time = None
    with sr.Microphone(device_index=mic_idx) as source:
        try:
            recognizer.adjust_for_ambient_noise(source, duration=0.6)
            recognizer.energy_threshold = min(max(recognizer.energy_threshold, 150), 350)
        except Exception:
            recognizer.energy_threshold = 250
        while True:
            try:
                # Barge-in support: if speaking, still check for interruption keywords
                if voice.is_speaking:
                    try:
                        audio = recognizer.listen(source, timeout=2, phrase_time_limit=4)
                        text = None
                        try:
                            text = recognizer.recognize_google(audio, language="en-IN").strip()
                        except Exception:
                            try:
                                from wake_word import wake_detector
                                text = wake_detector.whisper.transcribe_audio_data(audio)
                            except Exception:
                                pass

                        if text and any(w in text.lower() for w in ("stop", "quiet", "cancel", "chup", "ruko", "halt", "pause")):
                            voice.stop_speaking()
                            console.print("\n[bold yellow]⏹️ Barge-In: Speech interrupted by operator.[/bold yellow]\n")
                    except Exception:
                        pass
                    continue

                if speaking_start_time is not None:
                    speaking_start_time = None
                    time.sleep(0.3)

                audio = recognizer.listen(source, timeout=8, phrase_time_limit=14)

                if voice.is_speaking or not voice.tts_queue.empty():
                    continue

                console.print("  [dim cyan]⚡ Sound detected... transcribing[/dim cyan]", end="\r")

                # Try Google Web Speech with en-IN first for ultra-fast, accurate accented Hindi/English recognition
                raw_text = None
                try:
                    raw_text = recognizer.recognize_google(audio, language="en-IN").strip()
                except Exception:
                    try:
                        raw_text = recognizer.recognize_google(audio, language="en-US").strip()
                    except Exception:
                        pass

                # Fallback to local Faster-Whisper if Google fails or is offline
                if not raw_text:
                    try:
                        from wake_word import wake_detector
                        raw_text = wake_detector.whisper.transcribe_audio_data(audio)
                    except Exception:
                        pass
                if not raw_text:
                    continue

                # Process spoken text
                should_run, command = clean_command(raw_text)

                if not should_run:
                    continue

                play_chime("wake")
                console.print(f"\n[bold bright_white]🎤 User:[/bold bright_white] \"{raw_text}\"")

                # If user just said "Prime"
                if not command or command.strip() in WAKE_WORDS:
                    acknowledgement = "Haan Pratik, boliye! I am listening."
                    console.print(f"[bold cyan]Prime:[/bold cyan] {acknowledgement}")
                    voice.speak(acknowledgement)
                    continue

                # Check if user commanded to switch voices
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

                # Process command through AI Agent + Tools
                with console.status("[bold cyan]Prime is processing...[/bold cyan]", spinner="dots"):
                    response = agent.process_message(
                        command,
                        on_tool_call=on_tool_call,
                        on_tool_result=on_tool_result,
                    )

                console.print(f"[bold cyan]Prime:[/bold cyan]")
                console.print(Panel(response, border_style="blue", expand=False))
                console.print("\n[bold green]● LISTENING 24/7...[/bold green]\n")

            except sr.WaitTimeoutError:
                continue
            except (KeyboardInterrupt, SystemExit):
                console.print("\n[yellow]Prime Voice Assistant pausing. Goodbye![/yellow]")
                voice.speak("Voice assistant offline.")
                time.sleep(1.0)
                break
            except Exception as e:
                console.print(f"[red]Voice loop exception: {e}[/red]")
                voice.speak("I encountered an error processing that command.")
                time.sleep(1.0)


if __name__ == "__main__":
    run_voice_loop()
