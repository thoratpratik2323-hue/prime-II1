"""
mobile_room_server.py — Prime AI Mobile Remote Voice Cockpit Server.
Serves the mobile-friendly holographic voice UI on port 8765.
Allows Pratik to control Prime AI directly from any smartphone or tablet on local WiFi.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
import time
import uuid
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

load_dotenv()

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent
STATIC_FILE = PROJECT_ROOT / "mobile_room.html"

app = Flask(__name__, static_folder=str(PROJECT_ROOT))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prime.mobile_room")

# LiveKit support (optional)
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
ROOM_NAME = "prime-ai-room"


def get_local_ip() -> str:
    """Detect LAN IPv4 address for phone connectivity."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


@app.route("/")
def index():
    """Serve the Prime Mobile Voice Cockpit UI."""
    if STATIC_FILE.exists():
        return STATIC_FILE.read_text(encoding="utf-8")
    return "<h3>mobile_room.html not found</h3>", 404


@app.route("/token")
def token():
    """Generate LiveKit token if configured, or report direct mode."""
    if not (LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET):
        return jsonify({
            "mode": "direct",
            "url": None,
            "token": None,
            "room": ROOM_NAME,
            "message": "LiveKit credentials not configured. Using direct neural API mode."
        })

    identity = f"operator-{str(uuid.uuid4())[:8]}"
    try:
        import jwt as pyjwt
        now = int(time.time())
        payload = {
            "iss": LIVEKIT_API_KEY,
            "sub": identity,
            "iat": now,
            "exp": now + 3600,
            "nbf": now,
            "jti": str(uuid.uuid4()),
            "video": {
                "room": ROOM_NAME,
                "roomJoin": True,
                "canPublish": True,
                "canSubscribe": True,
                "canPublishData": True,
            }
        }
        tok = pyjwt.encode(payload, LIVEKIT_API_SECRET, algorithm="HS256")
        token_str = tok if isinstance(tok, str) else tok.decode("utf-8")
        return jsonify({
            "mode": "livekit",
            "url": LIVEKIT_URL,
            "token": token_str,
            "room": ROOM_NAME,
            "identity": identity,
        })
    except Exception as e:
        logger.warning("Could not generate LiveKit token: %s", e)
        return jsonify({"mode": "direct", "error": str(e)})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    Direct Neural API endpoint for mobile voice/text input.
    Executes commands on the PC using Prime AI Agent and returns the response.
    """
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"ok": False, "error": "Empty message."}), 400

    try:
        from ai_agent import agent

        tool_logs = []

        def on_tool(name, args):
            tool_logs.append(f"Ran tool: {name}")

        reply = agent.process_message(message, on_tool_call=on_tool)
        return jsonify({
            "ok": True,
            "reply": reply,
            "tools": tool_logs,
        })
    except Exception as e:
        logger.exception("Error processing mobile chat: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


from flask import Flask, jsonify, request, send_from_directory, Response, stream_with_context
from neural_mesh_bridge import mesh_bridge

# Start background PC clipboard watcher
mesh_bridge.start_clipboard_sync()

@app.route("/api/mesh/pair")
def api_mesh_pair():
    """Return local LAN pairing credentials."""
    ip = get_local_ip()
    return jsonify({
        "ok": True,
        "token": mesh_bridge.auth_token,
        "lan_ip": ip,
        "port": 8765,
        "connect_url": f"http://{ip}:8765/?pin={mesh_bridge.auth_token}",
    })

@app.route("/api/mesh/clipboard", methods=["GET", "POST"])
def api_mesh_clipboard():
    """Bidirectional clipboard endpoint for mobile synchronization."""
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        text = data.get("text", "")
        if text:
            success = mesh_bridge.set_pc_clipboard(text)
            return jsonify({"ok": success})
        return jsonify({"ok": False, "error": "Empty text"}), 400
    else:
        text = mesh_bridge._get_pc_clipboard()
        return jsonify({"ok": True, "text": text})

@app.route("/api/mesh/action", methods=["POST"])
def api_mesh_action():
    """Execute quick hardware actions remotely from phone."""
    data = request.get_json(force=True, silent=True) or {}
    action = data.get("action", "")
    params = data.get("params", {})
    res = mesh_bridge.execute_remote_action(action, params)
    return jsonify(res)

@app.route("/api/mesh/events")
def api_mesh_events():
    """Real-time Server-Sent Events (SSE) stream to connected mobile devices."""
    def event_stream():
        q = mesh_bridge.subscribe_events()
        try:
            # Yield initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'token_valid': True})}\n\n"
            while True:
                try:
                    event = q.get(timeout=25.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except Exception:
                    # Keep-alive heartbeat
                    yield f"data: {json.dumps({'type': 'heartbeat', 'time': time.time()})}\n\n"
        finally:
            mesh_bridge.unsubscribe_events(q)

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")


@app.route("/api/status")
def api_status():
    """Telemetry endpoint for mobile cockpit status."""
    import psutil
    try:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        from tool_definitions import TOOL_SPECS
        return jsonify({
            "status": "online",
            "cpu_percent": cpu,
            "ram_percent": mem,
            "tools_count": len(TOOL_SPECS),
            "operator": "Pratik Thorat",
            "mesh_token": mesh_bridge.auth_token,
        })
    except Exception as e:
        return jsonify({"status": "unknown", "error": str(e)})


def run_server(port: int = 8765):
    ip = get_local_ip()
    print("=" * 60)
    print("  PRIME AI :: MOBILE VOICE COCKPIT SERVER ONLINE")
    print(f"  Phone/Tablet URL:  http://{ip}:{port}")
    print(f"  Local PC URL:      http://localhost:{port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8765
    run_server(port_arg)
