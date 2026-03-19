#!/usr/bin/env python3
"""
agent-code-tts — Instalador automático para Claude Code (Windows)

Autor: Nilson Guerra (github.com/niguerrac)
Proyecto: https://github.com/niguerrac/agent-code-tts

Copia los hooks a ~/.claude/hooks/ y actualiza ~/.claude/settings.json
para registrar los hooks de PreToolUse y Stop.
"""
import os, sys, json, shutil, subprocess

REPO_DIR    = os.path.dirname(os.path.abspath(__file__))
HOOKS_SRC   = os.path.join(REPO_DIR, "hooks")
CLAUDE_DIR  = os.path.join(os.path.expanduser("~"), ".claude")
HOOKS_DST   = os.path.join(CLAUDE_DIR, "hooks")
SETTINGS    = os.path.join(CLAUDE_DIR, "settings.json")

HOOK_FILES  = [
    "tts.py", "tts.sh",
    "tts_pretools.py", "tts_pretools.sh",
    "tts_worker.py",
    "tts_config.json",
]

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"

def ok(msg):   print(f"{GREEN}✔{RESET} {msg}")
def warn(msg): print(f"{YELLOW}⚠{RESET} {msg}")
def err(msg):  print(f"{RED}✘{RESET} {msg}")


def install_dependencies():
    print("\n📦 Instalando dependencias Python...")
    packages = ["edge-tts", "pygame", "playsound==1.2.2"]
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install"] + packages,
        capture_output=True, text=True
    )
    if result.returncode == 0:
        ok("Dependencias instaladas")
    else:
        warn("Algunas dependencias fallaron — instálalas manualmente:")
        print(f"  pip install {' '.join(packages)}")


def copy_hooks():
    print("\n📂 Copiando hooks a ~/.claude/hooks/ ...")
    os.makedirs(HOOKS_DST, exist_ok=True)
    for fname in HOOK_FILES:
        src = os.path.join(HOOKS_SRC, fname)
        dst = os.path.join(HOOKS_DST, fname)
        if not os.path.exists(src):
            warn(f"Archivo no encontrado: {fname}")
            continue
        if fname == "tts_config.json" and os.path.exists(dst):
            warn(f"tts_config.json ya existe, no se sobreescribe (edítalo manualmente)")
            continue
        shutil.copy2(src, dst)
        ok(f"Copiado: {fname}")


def update_settings():
    print("\n⚙️  Actualizando ~/.claude/settings.json ...")

    hooks_bash = HOOKS_DST.replace("\\", "/").replace("C:", "/c")

    new_pretool = {
        "matcher": "",
        "hooks": [{
            "type": "command",
            "command": f"{hooks_bash}/tts_pretools.sh",
            "async": False
        }]
    }
    new_stop = {
        "matcher": "",
        "hooks": [{
            "type": "command",
            "command": f"{hooks_bash}/tts.sh",
            "async": False
        }]
    }

    settings = {}
    if os.path.exists(SETTINGS):
        try:
            with open(SETTINGS, encoding="utf-8") as f:
                settings = json.load(f)
        except Exception:
            warn("No se pudo leer settings.json, se creará uno nuevo")

    hooks = settings.setdefault("hooks", {})

    def already_registered(hook_list, command):
        for entry in hook_list:
            for h in entry.get("hooks", []):
                if command in h.get("command", ""):
                    return True
        return False

    pretool_list = hooks.setdefault("PreToolUse", [])
    if not already_registered(pretool_list, "tts_pretools.sh"):
        pretool_list.append(new_pretool)
        ok("Hook PreToolUse registrado")
    else:
        warn("Hook PreToolUse ya estaba registrado")

    stop_list = hooks.setdefault("Stop", [])
    if not already_registered(stop_list, "tts.sh"):
        stop_list.append(new_stop)
        ok("Hook Stop registrado")
    else:
        warn("Hook Stop ya estaba registrado")

    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    ok(f"settings.json actualizado")


def main():
    print("=" * 50)
    print("  agent-code-tts — Instalador")
    print("  by Nilson Guerra (github.com/niguerrac)")
    print("=" * 50)

    if sys.platform != "win32":
        warn("Este instalador está pensado para Windows.")
        warn("En Linux/macOS ajusta las rutas manualmente.")

    install_dependencies()
    copy_hooks()
    update_settings()

    print(f"\n{GREEN}✔ Instalación completa.{RESET}")
    print("  Reinicia Claude Code para que los hooks surtan efecto.")
    print(f"\n  Voz activa: es-MX-DaliaNeural")
    print(f"  Config en: {os.path.join(HOOKS_DST, 'tts_config.json')}")
    print(f"  Log en:    {os.path.join(HOOKS_DST, 'tts.log')}")


if __name__ == "__main__":
    main()
