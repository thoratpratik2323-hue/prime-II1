"""
room_server.py — Prime AI Mobile & Web Voice Cockpit Server
Allows connecting any phone, tablet, or secondary device over local WiFi
to talk to Prime hands-free with zero cloud subscriptions.

Run: python room_server.py
Then open http://YOUR_PC_IP:8765 on your phone.
"""

from __future__ import annotations

import io
import json
import logging
import os
import socket
import sys
import tempfile
import time
import uuid
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file, send_from_directory

from ai_agent import agent
from config import config
from tool_definitions import TOOL_SPECS
from voice_engine import voice

# Configure Flask app
app = Flask(__name__, static_folder=".")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prime.room_server")

AUDIO_CACHE_DIR = Path(tempfile.gettempdir()) / "prime_mobile_audio"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_local_ip() -> str:
    """Detect LAN IP address of this computer."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@app.route("/")
def index():
    """Serve the Prime Mobile Voice Cockpit UI."""
    return send_from_directory(".", "room_client.html")


@app.route("/api/status")
def get_status():
    """Return live status of Prime assistant."""
    import psutil
    return jsonify({
        "status": "online",
        "system": "Prime AI :: Autonomous Neural Cockpit",
        "voice": config.tts_voice,
        "tools_count": len(TOOL_SPECS),
        "cpu_percent": psutil.cpu_percent(),
        "ram_percent": psutil.virtual_memory().percent,
        "local_ip": get_local_ip(),
        "port": 8765,
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """Process a voice or text command from the mobile device."""
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"ok": False, "error": "No input provided."}), 400

    logger.info(f"Mobile command received: '{text}'")

    # Run AI reasoning and tool execution
    reply_text = agent.process_message(text)

    # Generate TTS audio file for phone playback
    audio_id = str(uuid.uuid4().hex[:12])
    audio_path = AUDIO_CACHE_DIR / f"{audio_id}.mp3"

    try:
        import asyncio
        import edge_tts

        async def generate_edge_audio():
            clean = voice._clean_text_for_speech(reply_text)
            communicate = edge_tts.Communicate(clean, config.tts_voice)
            await communicate.save(str(audio_path))

        asyncio.run(generate_edge_audio())
        has_audio = audio_path.exists()
    except Exception as e:
        logger.warning(f"Failed to generate mobile audio: {e}")
        has_audio = False

    return jsonify({
        "ok": True,
        "user_query": text,
        "reply": reply_text,
        "audio_url": f"/api/audio/{audio_id}" if has_audio else None,
    })


@app.route("/api/audio/<audio_id>")
def get_audio(audio_id: str):
    """Stream generated TTS audio to mobile browser."""
    audio_path = AUDIO_CACHE_DIR / f"{audio_id}.mp3"
    if audio_path.exists():
        return send_file(audio_path, mimetype="audio/mpeg")
    return jsonify({"error": "Audio not found"}), 404


@app.route("/token")
def get_livekit_token():
    """Optional LiveKit token generator if credentials are provided."""
    livekit_url = os.getenv("LIVEKIT_URL", "")
    livekit_key = os.getenv("LIVEKIT_API_KEY", "")
    livekit_secret = os.getenv("LIVEKIT_API_SECRET", "")

    if not (livekit_url and livekit_key and livekit_secret):
        return jsonify({
            "configured": False,
            "message": "LiveKit Cloud credentials not set. Mobile Room is running in Direct Neural Web Mode."
        })

    try:
        from livekit.api import AccessToken, VideoGrants
        identity = request.args.get("identity", f"mobile-user-{uuid.uuid4().hex[:4]}")
        token = AccessToken(livekit_key, livekit_secret)
        token.with_identity(identity)
        token.with_name(identity)
        token.with_grants(VideoGrants(room_join=True, room="prime-ai-room", can_publish=True, can_subscribe=True))
        return jsonify({
            "configured": True,
            "token": token.to_jwt(),
            "url": livekit_url,
            "room": "prime-ai-room",
            "identity": identity,
        })
    except Exception as e:
        return jsonify({"configured": False, "error": str(e)})


def run_server():
    ip = get_local_ip()
    port = 8765
    print("==========================================================")
    print("    PRIME AI  ::  MOBILE VOICE COCKPIT SERVER")
    print("      [ Zero GUI · 24/7 Voice Driven · Pure Power ]")
    print("==========================================================")
    print(f"[*] PC LAN IP Address : {ip}")
    print(f"[*] Access URL on PC  : http://localhost:{port}")
    print(f"[*] Access on Phone   : http://{ip}:{port}")
    print("----------------------------------------------------------")
    print("Make sure your phone is connected to the same WiFi network!")
    print("==========================================================\n")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    run_server()
