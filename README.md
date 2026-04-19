# 🤖 FRIDAY — Windows AI Agent

> **F**ast **R**easoning **I**ntelligent **D**esktop **A**utomation **Y**ield

A fully modular, Windows-native AI agent that can control your computer, browse the web, generate images, run shell commands, and reason over tasks — all from a single terminal.

---

## ✨ Features

| Capability | Module | Description |
|---|---|---|
| 🖱️ **System Control** | `modules/system_control.py` | Click, type, drag, scroll, open apps, manage windows |
| 📸 **Screen Awareness** | `modules/screen_context.py` | Screenshots, OCR, GPT-4o Vision analysis |
| 🔍 **Web Search** | `modules/web_search.py` | DuckDuckGo (free) or Tavily API |
| 🎨 **Image Generation** | `modules/image_gen.py` | DALL-E 3 (cloud) or Stable Diffusion (local) |
| 🧠 **LLM Brain** | `core/llm_brain.py` | GPT-4o or local Llama 3 via Ollama, rolling memory |
| ⚙️ **Code Executor** | `core/executor.py` | Sandboxed Python runner with all FRIDAY tools |
| 📋 **Task Planner** | `core/planner.py` | Decomposes goals → ordered steps, auto-retry on error |
| 🛑 **Kill-Switch** | `core/safety.py` | Move mouse to top-left corner to stop instantly |
| 📝 **Logging** | `core/logger.py` | Rotating file + rich console logs |
| 🔔 **Notifications** | `modules/utils.py` | Windows toast notifications |

---

## 📁 Project Structure

```
Frieday/
│
├── friday.py                   ← Main entry point (REPL)
├── config.py                   ← All settings & API keys
├── setup.py                    ← One-time setup wizard
├── requirements.txt            ← pip dependencies
├── .env.example                ← API key template
├── .env                        ← Your actual keys (gitignored)
│
├── core/
│   ├── logger.py               ← Centralised logging
│   ├── safety.py               ← Kill-switch watcher
│   ├── llm_brain.py            ← LLM reasoning + memory
│   ├── executor.py             ← Safe Python code runner
│   └── planner.py              ← Multi-step task planner
│
├── modules/
│   ├── system_control.py       ← Mouse, keyboard, windows, apps
│   ├── screen_context.py       ← Screenshots, OCR, Vision
│   ├── web_search.py           ← DuckDuckGo / Tavily search
│   ├── image_gen.py            ← DALL-E 3 / Stable Diffusion
│   └── utils.py                ← Clipboard, files, notifications
│
├── screenshots/                ← Auto-saved screenshots
├── generated_images/           ← AI-generated images
└── logs/                       ← friday.log (rotating)
```

---

## 🚀 Quick Start

### 1 — Prerequisites

- **Python 3.10+** (3.11 recommended)
- **Windows 10 / 11**
- An **OpenAI API key** (for GPT-4o + DALL-E) *or* **Ollama** running locally

### 2 — Setup

```powershell
# Clone / download the project, then:
cd Frieday

# Run the one-time setup wizard (installs packages, creates dirs, copies .env)
python setup.py
```

### 3 — Configure API Keys

```powershell
# Edit .env with your real keys
notepad .env
```

```ini
OPENAI_API_KEY=sk-your-real-key-here
```

### 4 — Run FRIDAY

```powershell
# Standard mode
python friday.py

# Require confirmation before executing any generated code (safer)
python friday.py --confirm

# Use a local Ollama model instead of OpenAI
python friday.py --provider ollama
```

---

## 💬 Usage Examples

Once FRIDAY is running, type naturally:

```
You ❯ Open Chrome and go to github.com
You ❯ Search the web for Python best practices 2025
You ❯ Take a screenshot and tell me what's on the screen
You ❯ Generate an image of a futuristic city at sunset
You ❯ Type "Hello World" in the current window
You ❯ Open Notepad, type a grocery list, and save the file
```

### Built-in Slash Commands

```
/help              Show all commands
/screen            Capture + describe the current screen
/search <query>    Quick web search
/image <prompt>    Generate an image right now
/windows           List all open windows
/open <app>        Launch an application (chrome, notepad, vscode…)
/shell <command>   Run a PowerShell/CMD command
/status            Show agent status (model, memory, kill-switch)
/reset             Clear conversation memory
/kill              Manually trigger the kill-switch
/quit              Exit FRIDAY
```

---

## 🛑 Safety — Kill-Switch

> **Move your mouse to the TOP-LEFT corner of the screen at any time.**

This immediately:
1. Sets a global `_killed` flag that all modules check
2. Terminates the process via `sys.exit(0)`

PyAutoGUI's built-in `FAILSAFE` is **also** enabled — it triggers on the same corner automatically.

To change the corner, edit `config.py`:

```python
KILL_SWITCH_ACTIVE_CORNER = "top_right"   # or bottom_left, bottom_right
```

---

## ⚙️ Configuration (`config.py`)

| Setting | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `"openai"` | `"openai"` or `"ollama"` |
| `OPENAI_MODEL` | `"gpt-4o"` | Model name |
| `OLLAMA_MODEL` | `"llama3"` | Local model name |
| `IMAGE_PROVIDER` | `"dalle"` | `"dalle"` or `"stable_diffusion"` |
| `SEARCH_PROVIDER` | `"duckduckgo"` | `"duckduckgo"` or `"tavily"` |
| `KILL_SWITCH_ACTIVE_CORNER` | `"top_left"` | Corner that triggers kill |
| `PYAUTOGUI_PAUSE` | `0.3` | Seconds between automated actions |
| `AGENT_HISTORY_LIMIT` | `20` | Max conversation turns kept in memory |

---

## 🔌 Using Ollama (Local / Free)

1. Download & install Ollama: https://ollama.com
2. Pull a model:
   ```powershell
   ollama pull llama3
   ```
3. Run FRIDAY with local mode:
   ```powershell
   python friday.py --provider ollama
   ```

---

## 🎨 Local Image Generation (Stable Diffusion)

Uncomment the SD packages in `requirements.txt`, then install:

```powershell
pip install diffusers transformers accelerate torch
```

Then in `config.py`:
```python
IMAGE_PROVIDER = "stable_diffusion"
```

> ⚠️ A CUDA-capable GPU is strongly recommended for acceptable speed.

---

## 🔒 Security Notes

| Risk | Mitigation |
|---|---|
| LLM executes arbitrary code | Use `--confirm` flag for human review |
| API keys in code | Stored in `.env` only — never hardcode |
| Mouse automation | Kill-switch + `PYAUTOGUI_FAILSAFE = True` |
| Sensitive windows | Always review generated code before approving |

---

## 📦 Tech Stack

| Layer | Library |
|---|---|
| Automation | PyAutoGUI, PyGetWindow |
| Vision | Pillow, pytesseract, GPT-4o Vision |
| LLM | OpenAI GPT-4o, Ollama (Llama 3) |
| Search | duckduckgo-search, Tavily |
| Image Gen | DALL-E 3, Stable Diffusion (diffusers) |
| CLI | Rich |
| HTTP | httpx |

---

## 📄 License

MIT — use freely, modify, extend. FRIDAY is yours.
