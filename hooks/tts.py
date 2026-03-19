#!/usr/bin/env python3
"""
agent-code-tts — Stop Hook
Encola el texto final de la respuesta y espera a que el worker
termine de hablar todo antes de liberar el turno.

Autor: Nilson Guerra (github.com/niguerrac)
Proyecto: https://github.com/niguerrac/agent-code-tts
Licencia: MIT
"""
import sys, json, os, re, subprocess, time

HOOKS_DIR   = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HOOKS_DIR, "tts_config.json")
STATE_PATH  = os.path.join(HOOKS_DIR, "tts_state.json")
QUEUE_PATH  = os.path.join(HOOKS_DIR, "tts_queue.jsonl")
PID_PATH    = os.path.join(HOOKS_DIR, "tts_worker.pid")
LOG         = os.path.join(HOOKS_DIR, "tts.log")


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[stop] {msg}\n")


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


def clear_state():
    try:
        if os.path.exists(STATE_PATH):
            os.unlink(STATE_PATH)
    except Exception:
        pass


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
    try:
        with open(transcript_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        log(f"Error leyendo transcript: {e}")
        return []

    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except Exception:
            continue

    last_user_idx = 0
    for i, entry in enumerate(entries):
        if is_real_user_message(entry):
            last_user_idx = i

    enqueued_set = set(enqueued_uuids)
    texts = []

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
                    break

    return texts


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


def wait_for_worker(timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        queue_empty = not os.path.exists(QUEUE_PATH) or os.path.getsize(QUEUE_PATH) == 0
        if queue_empty and not worker_alive():
            break
        time.sleep(0.2)


def main():
    try:
        cfg = load_config()
        raw = sys.stdin.read()
        data = json.loads(raw)
        session_id      = data.get("session_id", "")
        transcript_path = data.get("transcript_path", "")

        if not cfg.get("enabled", True):
            log("TTS desactivado")
            clear_state()
            return

        state = load_state(session_id)
        texts = []

        if transcript_path and os.path.exists(transcript_path):
            texts = get_new_text(transcript_path, state.get("enqueued_uuids", []))

        if not texts:
            fallback = data.get("last_assistant_message", "")
            if fallback and not state.get("enqueued_uuids"):
                texts = [fallback]
                log("usando fallback last_assistant_message")

        clear_state()

        if texts:
            combined = clean_text(" ".join(texts))
            if combined:
                if len(combined) > cfg["max_chars"]:
                    combined = combined[:cfg["max_chars"]] + "... respuesta truncada"
                log(f"encolando texto final {len(combined)} chars")
                enqueue(combined)

        ensure_worker()
        log("esperando al worker...")
        wait_for_worker()
        log("worker terminado, fin del turno")

    except Exception as e:
        log(f"ERROR: {e}")


if __name__ == "__main__":
    main()
