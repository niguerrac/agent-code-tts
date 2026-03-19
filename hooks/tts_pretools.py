#!/usr/bin/env python3
"""
agent-code-tts — PreToolUse Hook
Encola el texto escrito por el asistente antes de cada herramienta,
limitado al turno actual para evitar repetición de historial.

Autor: Nilson Guerra (github.com/niguerrac)
Proyecto: https://github.com/niguerrac/agent-code-tts
Licencia: MIT
"""
import sys, json, os, re, subprocess

HOOKS_DIR   = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HOOKS_DIR, "tts_config.json")
STATE_PATH  = os.path.join(HOOKS_DIR, "tts_state.json")
QUEUE_PATH  = os.path.join(HOOKS_DIR, "tts_queue.jsonl")
PID_PATH    = os.path.join(HOOKS_DIR, "tts_worker.pid")
LOG         = os.path.join(HOOKS_DIR, "tts.log")


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[pretools] {msg}\n")


def load_config():
    defaults = {"enabled": True, "max_chars": 1500}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            defaults.update(json.load(f))
    except Exception:
        pass
    return defaults


def load_state(session_id):
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)
        if state.get("session_id") == session_id:
            return state
    except Exception:
        pass
    return {"session_id": session_id, "enqueued_uuids": []}


def save_state(state):
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception as e:
        log(f"Error guardando estado: {e}")


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


def is_real_user_message(entry):
    if entry.get("type") != "user" or entry.get("isMeta"):
        return False
    content = entry.get("message", {}).get("content", "")
    if isinstance(content, list):
        if all(b.get("type") == "tool_result" for b in content if isinstance(b, dict)):
            return False
    return True


def get_new_text(transcript_path, enqueued_uuids):
    """Devuelve texto del turno actual aún no encolado."""
    try:
        with open(transcript_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        log(f"Error leyendo transcript: {e}")
        return [], []

    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except Exception:
            continue

    # Inicio del turno = después del último mensaje real del usuario
    last_user_idx = 0
    for i, entry in enumerate(entries):
        if is_real_user_message(entry):
            last_user_idx = i

    enqueued_set = set(enqueued_uuids)
    texts, new_uuids = [], []

    for entry in entries[last_user_idx + 1:]:
        if entry.get("type") != "assistant":
            continue
        uuid = entry.get("uuid", "")
        if uuid in enqueued_set:
            continue
        content = entry.get("message", {}).get("content", [])
        for block in content:
            if block.get("type") == "text":
                text = block.get("text", "").strip()
                if text:
                    texts.append(text)
                    new_uuids.append(uuid)
                    break

    return texts, new_uuids


def enqueue(text):
    with open(QUEUE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"text": text}) + "\n")


def worker_alive():
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


def main():
    try:
        cfg = load_config()
        if not cfg.get("enabled", True):
            return

        raw = sys.stdin.read()
        data = json.loads(raw)
        session_id      = data.get("session_id", "")
        transcript_path = data.get("transcript_path", "")

        if not transcript_path or not os.path.exists(transcript_path):
            log(f"transcript no encontrado: {transcript_path!r}")
            return

        state = load_state(session_id)
        texts, new_uuids = get_new_text(transcript_path, state.get("enqueued_uuids", []))

        if not texts:
            log("no hay texto nuevo")
            return

        # Guardar estado ANTES de encolar (evita doble encola en hooks rápidos)
        state["enqueued_uuids"] = state.get("enqueued_uuids", []) + new_uuids
        save_state(state)

        combined = clean_text(" ".join(texts))
        if not combined:
            return

        if len(combined) > cfg["max_chars"]:
            combined = combined[:cfg["max_chars"]] + "... texto truncado"

        log(f"encolando {len(combined)} chars")
        enqueue(combined)
        ensure_worker()

    except Exception as e:
        log(f"ERROR: {e}")


if __name__ == "__main__":
    main()
