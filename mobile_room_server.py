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


@app.route("/api/command", methods=["POST"])
def api_command():
    """Execute raw voice or text command directly."""
    data = request.get_json(force=True, silent=True) or {}
    cmd = data.get("command", "").strip()
    if not cmd:
        return jsonify({"ok": False, "error": "Empty command."}), 400
    try:
        from ai_agent import agent
        reply = agent.process_message(cmd)
        return jsonify({"ok": True, "reply": reply})
    except Exception as e:
        logger.exception("Error executing command: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/gesture", methods=["POST"])
def api_gesture():
    """Handle touchless hand gesture commands (MediaPipe)."""
    data = request.get_json(force=True, silent=True) or {}
    gesture = str(data.get("gesture", "")).strip().lower()
    from tool_definitions import execute_tool

    if gesture in ("open_palm", "mute", "barge_in"):
        try:
            from voice_engine import voice
            voice.barge_in()
        except Exception:
            pass
        res = execute_tool("muteToggle", {})
        return jsonify({"ok": True, "gesture": gesture, "action": "barge_in_and_mute", "result": res})

    elif gesture in ("thumbs_up", "confirm", "proceed"):
        res = execute_tool("confirmAndSendWhatsAppDraft", {})
        return jsonify({"ok": True, "gesture": gesture, "action": "confirm_draft", "result": res})

    elif gesture in ("pinch", "rotate", "spread", "zoom"):
        return jsonify({"ok": True, "gesture": gesture, "action": "viewport_transform"})

    elif gesture in ("next_track", "swipe_right"):
        res = execute_tool("mediaControl", {"action": "next"})
        return jsonify({"ok": True, "gesture": gesture, "action": "media_next", "result": res})

    elif gesture in ("prev_track", "swipe_left"):
        res = execute_tool("mediaControl", {"action": "previous"})
        return jsonify({"ok": True, "gesture": gesture, "action": "media_prev", "result": res})

    return jsonify({"ok": False, "error": f"Unknown gesture: {gesture}"}), 400


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


@app.route("/api/hud/state")
def api_hud_state():
    """
    Consolidated HUD state endpoint providing live hardware, cognitive agent status,
    HER coral aura visualizer parameters, active durable plan, and Friday receipts.
    """
    import psutil
    try:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
    except Exception:
        cpu, mem = 0.0, 0.0

    # 1. Visualizer (HER Coral Breathing State)
    visualizer_data = {}
    try:
        from actions.her_companion import get_her_visualizer_state
        visualizer_data = get_her_visualizer_state()
    except Exception as e:
        visualizer_data = {"error": str(e)}

    # 2. Durable Task Plan
    active_plan = None
    try:
        from actions.friday_tasks import get_active_task_plan
        plan_res = get_active_task_plan()
        if plan_res.get("has_active_plan"):
            active_plan = plan_res.get("plan")
    except Exception:
        pass

    # 3. Recent Execution Receipts
    recent_receipts = []
    try:
        from actions.friday_receipts import get_execution_receipts
        rec_res = get_execution_receipts(limit=5)
        recent_receipts = rec_res.get("receipts", [])
    except Exception:
        pass

    # 4. User Preferences Memory (via Master Brain)
    preferences_count = 0
    try:
        from core.master_brain import prime_brain
        preferences_count = len(prime_brain._ram_cache)
    except Exception:
        pass

    from tool_definitions import TOOL_SPECS
    from config import config

    return jsonify({
        "ok": True,
        "status": "online",
        "timestamp": time.time(),
        "hardware": {
            "cpu_percent": cpu,
            "ram_percent": mem,
        },
        "ai": {
            "active_provider": config.get_active_provider(),
            "tools_count": len(TOOL_SPECS),
            "operator": "Pratik Thorat",
            "preferences_count": preferences_count,
        },
        "visualizer": visualizer_data,
        "active_plan": active_plan,
        "recent_receipts": recent_receipts,
    })


@app.route("/api/hud/stream")
def api_hud_stream():
    """Real-time SSE stream of HUD telemetry and HER breathing visualizer frames."""
    def hud_event_stream():
        import psutil
        try:
            from actions.her_companion import get_her_visualizer_state
            from actions.friday_tasks import get_active_task_plan
            from actions.friday_receipts import get_execution_receipts
            from config import config
            from tool_definitions import TOOL_SPECS

            while True:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory().percent
                vis = get_her_visualizer_state()
                plan_res = get_active_task_plan()
                active_plan = plan_res.get("plan") if plan_res.get("has_active_plan") else None
                rec_res = get_execution_receipts(limit=3)

                payload = {
                    "type": "hud_tick",
                    "time": time.time(),
                    "cpu": cpu,
                    "ram": mem,
                    "visualizer": vis,
                    "active_plan": active_plan,
                    "recent_receipts": rec_res.get("receipts", []),
                    "tools_count": len(TOOL_SPECS),
                    "provider": config.get_active_provider(),
                }
                yield f"data: {json.dumps(payload)}\n\n"
                time.sleep(1.5)
        except GeneratorExit:
            pass
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(stream_with_context(hud_event_stream()), mimetype="text/event-stream")


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
