#!/usr/bin/env python3
"""
agent-code-tts MCP Server
Expone herramientas TTS para clientes MCP (Claude Cowork, Cursor, etc.)
Comparte la misma cola y worker que los hooks de Claude Code.

Author: Nilson Guerra
"""
import json, os, re, sys, subprocess

HOOKS_DIR   = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HOOKS_DIR, "tts_config.json")
QUEUE_PATH  = os.path.join(HOOKS_DIR, "tts_queue.jsonl")
PID_PATH    = os.path.join(HOOKS_DIR, "tts_worker.pid")


def load_config():
    defaults = {
        "voice": "es-MX-DaliaNeural",
        "rate": "+0%", "volume": "+0%", "pitch": "+0Hz",
        "max_chars": 1500, "enabled": True
    }
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            defaults.update(json.load(f))
    except Exception:
        pass
    return defaults


def clean_text(text: str) -> str:
    text = re.sub(r'```[\s\S]*?```', ' código ', text)
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'#+\s+', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'[-*]\s+', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def enqueue(text: str):
    with open(QUEUE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"text": text}) + "\n")


def worker_alive() -> bool:
    if not os.path.exists(PID_PATH):
        return False
    try:
        with open(PID_PATH) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except Exception:
        try:
            os.unlink(PID_PATH)
        except Exception:
            pass
        return False


def ensure_worker():
    if worker_alive():
        return
    worker_script = os.path.join(HOOKS_DIR, "tts_worker.py")
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        ["python", worker_script],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **kwargs
    )


def queue_length() -> int:
    try:
        with open(QUEUE_PATH, encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


# --- MCP Server ---
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("agent-code-tts")


@mcp.tool()
def tts_speak(text: str) -> str:
    """Habla el texto dado usando Edge TTS. Pasa por la cola del worker."""
    cfg = load_config()
    if not cfg.get("enabled", True):
        return "TTS desactivado"
    cleaned = clean_text(text)
    if not cleaned:
        return "Texto vacío"
    if len(cleaned) > cfg["max_chars"]:
        cleaned = cleaned[:cfg["max_chars"]] + "... texto truncado"
    enqueue(cleaned)
    ensure_worker()
    return f"Encolado: {len(cleaned)} caracteres"


@mcp.tool()
def tts_status() -> str:
    """Devuelve el estado actual del sistema TTS (worker, cola, configuración)."""
    cfg = load_config()
    return json.dumps({
        "enabled": cfg.get("enabled", True),
        "worker_alive": worker_alive(),
        "queue_length": queue_length(),
        "voice": cfg.get("voice"),
        "rate": cfg.get("rate"),
        "volume": cfg.get("volume"),
        "pitch": cfg.get("pitch"),
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def tts_configure(
    voice: str = None,
    rate: str = None,
    volume: str = None,
    pitch: str = None,
    enabled: bool = None,
    max_chars: int = None
) -> str:
    """
    Actualiza la configuración del TTS en tiempo real.
    voice: nombre de voz Edge TTS (ej: es-MX-DaliaNeural, es-ES-ElviraNeural)
    rate: velocidad (ej: +10%, -20%)
    volume: volumen (ej: +0%, +50%)
    pitch: tono (ej: +10Hz, -5Hz)
    enabled: activar/desactivar TTS
    max_chars: máximo de caracteres por mensaje
    """
    cfg = load_config()
    changed = []
    if voice is not None:      cfg["voice"] = voice;             changed.append(f"voice={voice}")
    if rate is not None:       cfg["rate"] = rate;               changed.append(f"rate={rate}")
    if volume is not None:     cfg["volume"] = volume;           changed.append(f"volume={volume}")
    if pitch is not None:      cfg["pitch"] = pitch;             changed.append(f"pitch={pitch}")
    if enabled is not None:    cfg["enabled"] = enabled;         changed.append(f"enabled={enabled}")
    if max_chars is not None:  cfg["max_chars"] = max_chars;     changed.append(f"max_chars={max_chars}")

    if not changed:
        return "Sin cambios"

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    return f"Actualizado: {', '.join(changed)}"


if __name__ == "__main__":
    mcp.run()
