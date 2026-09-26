"""
project_exporter.py — Project Exporter & Workspace Archiver for Prime AI.
Inherited from Pratik's IP-Codemaker-Agent (ip_agent_001).
Generates starter project packages and zips live workspaces on demand.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

STARTER_KITS = {
    "react_vite": {
        "name": "React 18 + Vite Starter Kit",
        "files": {
            "package.json": '{\n  "name": "react-app",\n  "private": true,\n  "version": "1.0.0",\n  "scripts": { "dev": "vite", "build": "vite build" },\n  "dependencies": { "react": "^18.3.1", "react-dom": "^18.3.1", "lucide-react": "^0.400.0" },\n  "devDependencies": { "@vitejs/plugin-react": "^4.3.1", "autoprefixer": "^10.4.19", "postcss": "^8.4.38", "tailwindcss": "^3.4.4", "vite": "^5.3.1" }\n}',
            "src/App.jsx": 'import React from "react";\nimport { Sparkles } from "lucide-react";\n\nexport default function App() {\n  return (\n    <div className="min-h-screen bg-slate-950 text-white flex flex-col items-center justify-center font-sans">\n      <h1 className="text-4xl font-bold flex items-center gap-3 text-cyan-400">\n        <Sparkles /> Prime AI React Starter\n      </h1>\n    </div>\n  );\n}',
            "src/main.jsx": 'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport App from "./App";\n\nReactDOM.createRoot(document.getElementById("root")).render(<App />);',
            "index.html": '<!DOCTYPE html>\n<html lang="en">\n<head><title>React App</title></head>\n<body><div id="root"></div><script type="module" src="/src/main.jsx"></script></body>\n</html>',
            "README.md": "# React Vite Starter Kit\n\nRun `npm install` and `npm run dev` to launch!"
        }
    },
    "fastapi_app": {
        "name": "FastAPI Autonomous Backend Starter",
        "files": {
            "main.py": 'from fastapi import FastAPI\nimport uvicorn\n\napp = FastAPI(title="Prime Autonomous API", version="1.0.0")\n\n@app.get("/")\ndef read_root():\n    return {"status": "ONLINE", "message": "FastAPI Server Ready"}\n\nif __name__ == "__main__":\n    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)',
            "requirements.txt": "fastapi>=0.111.0\nuvicorn>=0.30.0\npydantic>=2.7.0\n",
            "README.md": "# FastAPI Starter Kit\n\nRun `pip install -r requirements.txt` and `python main.py`!"
        }
    },
    "jarvis_voice": {
        "name": "JARVIS Python Voice Assistant Kit",
        "files": {
            "jarvis.py": 'import speech_recognition as sr\nimport pyttsx3\nimport datetime\n\nengine = pyttsx3.init("sapi5")\nengine.setProperty("rate", 185)\n\ndef speak(text):\n    print(f"JARVIS: {text}")\n    engine.say(text)\n    engine.runAndWait()\n\nif __name__ == "__main__":\n    speak("Jarvis Voice System Online, Sir.")',
            "requirements.txt": "pyttsx3\nSpeechRecognition\npyaudio\npygame\n",
            "README.md": "# Jarvis Voice Assistant Kit\n\nRun `pip install -r requirements.txt` and `python jarvis.py`!"
        }
    }
}


def export_project_starter(project_type: str, destination_dir: Optional[str] = None) -> Dict[str, Any]:
    """Generates a starter project and saves it as a zip archive."""
    p_type = project_type.lower().strip().replace("-", "_").replace(" ", "_")
    if p_type not in STARTER_KITS:
        return {
            "ok": False,
            "error": f"Unknown project type '{project_type}'. Available: {list(STARTER_KITS.keys())}"
        }

    kit = STARTER_KITS[p_type]
    out_dir = Path(destination_dir) if destination_dir else Path.cwd() / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    zip_filename = f"{p_type}_starter.zip"
    zip_path = out_dir / zip_filename

    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path, content in kit["files"].items():
            zf.writestr(file_path, content)

    return {
        "ok": True,
        "result": f"Exported {kit['name']} to: {zip_path.resolve()}",
        "zip_path": str(zip_path.resolve())
    }


def export_workspace_zip(output_path: Optional[str] = None) -> Dict[str, Any]:
    """Zips the current live workspace directory excluding binaries and git."""
    root_dir = Path.cwd()
    out_dir = Path(output_path).parent if output_path else root_dir / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    zip_file = Path(output_path) if output_path else out_dir / "prime_workspace_backup.zip"

    ignored_dirs = {".git", "node_modules", "__pycache__", "scratch", ".gemini", "exports", "tmp", ".venv", "venv", ".idea", ".vscode"}
    files_added = 0

    with zipfile.ZipFile(str(zip_file), "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for f in files:
                if f.endswith(".zip") or f == ".env":
                    continue  # Protect secrets and avoid recursion
                full_path = Path(root) / f
                rel_path = full_path.relative_to(root_dir)
                try:
                    zf.write(full_path, rel_path)
                    files_added += 1
                except Exception:
                    pass

    return {
        "ok": True,
        "result": f"Workspace packaged ({files_added} files) to: {zip_file.resolve()}"
    }
