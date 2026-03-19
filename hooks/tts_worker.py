#!/usr/bin/env python3
"""
agent-code-tts — TTS Worker
Proceso background que habla items de la cola en orden, uno a la vez.

Autor: Nilson Guerra (github.com/niguerrac)
Proyecto: https://github.com/niguerrac/agent-code-tts
Licencia: MIT
"""
import json, asyncio, tempfile, os, re, time, sys

HOOKS_DIR   = os.path.dirname(os.path.abspath(__file__))
QUEUE_PATH  = os.path.join(HOOKS_DIR, "tts_queue.jsonl")
PID_PATH    = os.path.join(HOOKS_DIR, "tts_worker.pid")
CONFIG_PATH = os.path.join(HOOKS_DIR, "tts_config.json")
LOG         = os.path.join(HOOKS_DIR, "tts.log")


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[worker] {msg}\n")


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


def pop_queue():
    if not os.path.exists(QUEUE_PATH):
        return None
    try:
        with open(QUEUE_PATH, encoding="utf-8") as f:
            lines = [l for l in f.readlines() if l.strip()]
        if not lines:
            return None
        item = json.loads(lines[0])
        with open(QUEUE_PATH, "w", encoding="utf-8") as f:
            f.writelines(lines[1:])
        return item
    except Exception as e:
        log(f"Error en pop_queue: {e}")
        return None


async def generate_mp3(text: str, cfg: dict) -> str:
    import edge_tts
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    communicate = edge_tts.Communicate(
        text, cfg["voice"],
        rate=cfg["rate"], volume=cfg["volume"], pitch=cfg["pitch"]
    )
    await communicate.save(tmp)
    return tmp


def play_audio(path: str):
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        pygame.mixer.quit()
    except Exception:
        try:
            from playsound import playsound
            playsound(path)
        except Exception:
            pass


def main():
    with open(PID_PATH, "w") as f:
        f.write(str(os.getpid()))
    log(f"iniciado PID={os.getpid()}")

    try:
        idle_cycles = 0
        while idle_cycles < 10:
            cfg = load_config()
            item = pop_queue()
            if item is None:
                idle_cycles += 1
                time.sleep(0.1)
                continue

            idle_cycles = 0
            text = item.get("text", "")
            if not text:
                continue

            log(f"hablando {len(text)} chars")
            try:
                tmp = asyncio.run(generate_mp3(text, cfg))
                try:
                    play_audio(tmp)
                finally:
                    try:
                        os.unlink(tmp)
                    except Exception:
                        pass
            except Exception as e:
                log(f"Error hablando: {e}")
    finally:
        try:
            os.unlink(PID_PATH)
        except Exception:
            pass
        log("terminado")


if __name__ == "__main__":
    main()
