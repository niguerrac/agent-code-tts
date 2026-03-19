# 🔊 agent-code-tts — Automatic TTS Voice for Claude Code

> **Make Claude Code speak its responses aloud in real time**, including intermediate messages between tool calls.
> Uses Microsoft Edge TTS (free, no API key needed) with natural neural voices in Spanish and English.

Built for **Claude Code** · Compatible with **OpenCode** and **Kimi Code** *(coming soon)*

**By [Nilson Guerra](https://github.com/niguerrac)**

---

## ✨ Features

- 🗣️ **Reads every response aloud** — including short messages Claude writes between tool calls
- ⚡ **Queue-based architecture** — a background worker speaks items in order, no overlapping audio
- 🌍 **40+ neural voices** — Spanish (MX, ES, AR...), English, and more via Edge TTS
- 🔧 **Easy config** — edit one JSON file to change voice, speed, pitch, and volume
- 🔕 **Toggle on/off** — via `/tts` command in Claude Code
- 🪟 **Windows native** — works out of the box on Windows 10/11

---

## 🚀 Quick Install (Windows)

**1. Clone and install:**
```bash
git clone https://github.com/niguerrac/agent-code-tts.git
cd agent-code-tts
python install.py
```

**2. Restart Claude Code.**

That's it. Dalia will start speaking automatically.

---

## 📦 Manual Install

### 1. Install Python dependencies
```bash
pip install edge-tts pygame playsound==1.2.2
```

### 2. Copy hooks to Claude Code
Copy the contents of the `hooks/` folder to `~/.claude/hooks/`:
```
~/.claude/hooks/
├── tts.py              ← Stop hook (speaks final response)
├── tts.sh              ← Bash wrapper for Stop hook
├── tts_pretools.py     ← PreToolUse hook (speaks intermediate messages)
├── tts_pretools.sh     ← Bash wrapper for PreToolUse hook
├── tts_worker.py       ← Background worker (queue processor)
└── tts_config.json     ← Configuration file
```

### 3. Register hooks in `~/.claude/settings.json`
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/c/Users/YOUR_USER/.claude/hooks/tts_pretools.sh",
            "async": false
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/c/Users/YOUR_USER/.claude/hooks/tts.sh",
            "async": false
          }
        ]
      }
    ]
  }
}
```
> Replace `YOUR_USER` with your Windows username.

---

## ⚙️ Configuration

Edit `~/.claude/hooks/tts_config.json`:

```json
{
  "voice": "es-MX-DaliaNeural",
  "rate": "+0%",
  "volume": "+0%",
  "pitch": "+10Hz",
  "max_chars": 1500,
  "enabled": true
}
```

| Parameter | Description | Examples |
|-----------|-------------|---------|
| `voice` | Edge TTS neural voice | `es-MX-DaliaNeural`, `en-US-JennyNeural` |
| `rate` | Speech speed | `+20%` faster, `-15%` slower |
| `volume` | Volume | `+10%`, `-10%` |
| `pitch` | Pitch | `+10Hz` higher, `-5Hz` lower |
| `max_chars` | Max characters per chunk | `1500` |
| `enabled` | Enable/disable TTS | `true`, `false` |

### List available voices
```bash
edge-tts --list-voices
# Filter by language:
edge-tts --list-voices | grep "^es-"   # Spanish
edge-tts --list-voices | grep "^en-"   # English
```

### Recommended Spanish voices
| Voice | Region | Gender |
|-------|--------|--------|
| `es-MX-DaliaNeural` | Mexico | Female ⭐ |
| `es-MX-JorgeNeural` | Mexico | Male |
| `es-ES-ElviraNeural` | Spain | Female |
| `es-ES-AlvaroNeural` | Spain | Male |
| `es-AR-ElenaNeural` | Argentina | Female |

---

## 🔕 Toggle TTS on/off

Create `~/.claude/skills/tts.md` to enable the `/tts` command:

```markdown
# TTS Toggle

Toggle or configure the agent-code-tts voice.

## Instructions

Read `~/.claude/hooks/tts_config.json`.

Based on the args:
- No args or "toggle": flip `enabled` (true→false or false→true), save and report.
- "on" / "activar": set `enabled` to true.
- "off" / "desactivar": set `enabled` to false.
- "status" / "estado": report current state without changing anything.
- "config KEY VALUE": update that parameter (e.g. "config pitch +15Hz").

Always respond in one line.
```

Usage:
```
/tts          → toggle on/off
/tts on       → enable
/tts off      → disable
/tts status   → check current state
/tts config rate +20%  → change a parameter
```

---

## 🏗️ Architecture

```
Claude writes text
      ↓
PreToolUse hook fires (before each tool call)
      ↓
tts_pretools.py extracts NEW text from current turn only
      ↓
Saves enqueued UUIDs to tts_state.json (prevents duplicates)
      ↓
Appends text to tts_queue.jsonl
      ↓
Starts tts_worker.py (if not running)
      ↓
Worker speaks items one by one in order
      ↓
Stop hook fires (end of turn)
      ↓
tts.py enqueues any remaining text, waits for worker to finish
      ↓
tts_state.json cleared for next turn
```

**Why a queue?** When Claude makes multiple tool calls rapidly, hooks can fire faster than audio plays. The queue ensures every message is spoken once, in order, without overlap.

---

## 📁 Files

| File | Purpose |
|------|---------|
| `hooks/tts.py` | Stop hook — enqueues final text, waits for worker |
| `hooks/tts.sh` | Bash wrapper for Stop hook |
| `hooks/tts_pretools.py` | PreToolUse hook — enqueues intermediate messages |
| `hooks/tts_pretools.sh` | Bash wrapper for PreToolUse hook |
| `hooks/tts_worker.py` | Background worker — speaks queue items in order |
| `hooks/tts_config.json` | User configuration |
| `install.py` | Automatic installer |

**Runtime files** (auto-managed, do not edit):
- `tts_queue.jsonl` — pending audio queue
- `tts_state.json` — enqueued UUIDs for current turn
- `tts_worker.pid` — worker process ID
- `tts.log` — debug log

---

## 🔮 Roadmap

- [ ] Linux / macOS support
- [ ] OpenCode integration
- [ ] Kimi Code integration
- [ ] Multi-language auto-detection

---

## 📄 License

MIT © [Nilson Guerra](https://github.com/niguerrac)
