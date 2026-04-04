

# Z E N T R A

**Your local AI assistant that actually controls your PC.**

Not another chatbot wrapper. Zentra runs on your machine, touches your files,  
launches your apps, reads your screen, manages your email, and automates your workflow.  
Everything local. Everything yours.

[Quickstart](#-quickstart-2-minutes) · [Features](#-what-can-zentra-do) · [Frontends](#-pick-your-frontend) · [Structure](#-project-structure) · [Discord Setup](#-discord-bot-setup) · [Google Setup](#-google-api-setup) · [Plugins](#-writing-plugins)

---

## Quickstart (2 minutes)

You need two things: **Python 3.10+** and **Ollama**.

### Step 1: Install Ollama

Download from [ollama.com](https://ollama.com/download), install it, then pull a model:

```bash
ollama pull qwen2.5-coder:7b
```

### Step 2: Clone and install

```bash
git clone https://github.com/Brobuiltathing/Zentra.git
cd Zentra
pip install requests python-dotenv rich pyperclip psutil
```

### Step 3: Run

```bash
python run_cli.py
```

That's it. You're talking to Zentra in your terminal. Type anything.

> **Want Discord instead?** See [Discord setup](#-discord-bot-setup) below, then `python run_discord.py`
>
> **Want the desktop GUI?** Run `pip install PySide6` then `python run_gui.py`

---

## What can Zentra do?

Talk to it like a person. It figures out what action to take.

### The basics


| You say                                         | Zentra does                                     |
| ----------------------------------------------- | ----------------------------------------------- |
| "create a flask server with a /health endpoint" | Writes the file to disk with correct extension  |
| "run npm test in my project"                    | Executes the command, returns output and errors |
| "open chrome, spotify, and discord"             | Launches all three applications                 |
| "show my system stats"                          | CPU, RAM, disk, GPU, network, top processes     |
| "commit and push my code"                       | `git add .`, `commit`, `push` in one shot       |


### Clipboard intelligence


| You say                            | Zentra does                             |
| ---------------------------------- | --------------------------------------- |
| "what's on my clipboard?"          | Reads and displays clipboard contents   |
| "explain the code on my clipboard" | Analyses it and explains what it does   |
| "fix the bugs on my clipboard"     | Fixes errors and copies the result back |


### Screen + context awareness


| You say                           | Zentra does                                                         |
| --------------------------------- | ------------------------------------------------------------------- |
| "what am I working on right now?" | Screenshots your screen, lists processes, suggests what to focus on |
| "click the submit button"         | Uses vision AI to find and click UI elements                        |


### Workflows (multi-step automation)


| You say                                   | Zentra does                           |
| ----------------------------------------- | ------------------------------------- |
| "run tests, if they pass commit and push" | Chains actions with conditional logic |
| "save that workflow as deploy"            | Saves it by name for later            |
| "replay deploy"                           | Runs the saved workflow again         |


### File watching


| You say                     | Zentra does                                         |
| --------------------------- | --------------------------------------------------- |
| "watch my Downloads folder" | Monitors for new/changed/deleted files in real-time |
| "stop watching Downloads"   | Stops the watcher                                   |


### Local knowledge base


| You say                                   | Zentra does                                        |
| ----------------------------------------- | -------------------------------------------------- |
| "index all my notes"                      | Reads and summarises your local documents          |
| "search my notes for that API key format" | Searches indexed docs and answers using your files |


### Scheduling


| You say                                   | Zentra does                        |
| ----------------------------------------- | ---------------------------------- |
| "remind me at 5pm to push my code"        | Sets a one-time reminder           |
| "every Monday at 9am summarise my emails" | Creates a recurring scheduled task |


### Email + Calendar (requires [Google setup](#-google-api-setup))


| You say                                                                                  | Zentra does                              |
| ---------------------------------------------------------------------------------------- | ---------------------------------------- |
| "summarise my unread emails"                                                             | AI-ranked digest with importance scoring |
| "send an email to [jake@example.com](mailto:jake@example.com) saying the report is done" | Composes and sends it                    |
| "what's on my calendar today?"                                                           | Shows events with conflict detection     |
| "add a meeting with Sarah on Friday at 2pm"                                              | Creates the calendar event               |


### And more

- **Export chat** as markdown or plain text
- **Plugin system** for adding custom actions (drop a .py file, done)
- **Shut down / restart / sleep** your PC remotely
- **Open files in VS Code** directly

---

## 🖥️ Pick your frontend

All three frontends share the same backend. Same features, same 40+ actions. Pick how you want to interact.


| Command                 | What you get                                                      |
| ----------------------- | ----------------------------------------------------------------- |
| `python run_cli.py`     | Terminal interface with rich formatting, slash commands, spinners |
| `python run_discord.py` | Discord bot you DM from anywhere (phone, laptop, etc.)            |
| `python run_gui.py`     | Desktop app with sidebar, chat bubbles, settings panel            |


### Frontend-specific dependencies

**CLI** (lightest):

```bash
pip install requests python-dotenv rich pyperclip psutil
```

**Discord** (adds discord.py):

```bash
pip install requests python-dotenv discord.py pyperclip psutil
```

**GUI** (adds PySide6):

```bash
pip install requests python-dotenv PySide6 pyperclip psutil
```

**Optional extras** (install if you want the feature):

```bash
pip install pyautogui Pillow                                          # screen automation + vision
pip install google-auth google-auth-oauthlib google-api-python-client  # Gmail + Calendar
```

**Or install everything at once:**

```bash
pip install -r requirements.txt
```

---

## 📁 Project Structure

```
Zentra/
│
├── run_cli.py               <- launch terminal version
├── run_discord.py           <- launch discord bot
├── run_gui.py               <- launch desktop GUI
│
├── zentra/                  <- SHARED BACKEND (one copy, all frontends use this)
│   ├── config.py               settings, model config, system prompt
│   ├── engine.py               core message processing
│   ├── dispatcher.py           routes 40+ actions to handlers
│   ├── memory.py               conversation memory
│   ├── ollama.py               LLM calls (chat, raw, vision)
│   ├── parser.py               JSON extraction from model output
│   ├── logger.py               logging setup
│   │
│   ├── actions/                one file per feature
│   │   ├── files.py               create, read, edit, run, scaffold files
│   │   ├── apps.py                open/close apps (80+ aliases built in)
│   │   ├── shell.py               direct terminal command execution
│   │   ├── git.py                 git add, commit, push
│   │   ├── system.py              system stats, PC shutdown/restart/sleep
│   │   ├── screen.py              screenshot + vision + mouse/keyboard
│   │   ├── clipboard.py           read, analyse, fix clipboard
│   │   ├── context.py             screen + processes + productivity suggestion
│   │   ├── workflow.py            multi-step automation chains
│   │   ├── watcher.py             folder monitoring
│   │   ├── knowledge.py           local document indexing + search
│   │   ├── scheduler.py           reminders + recurring tasks
│   │   ├── gmail.py               email summary + send
│   │   ├── calendar.py            calendar CRUD
│   │   ├── export.py              chat history export
│   │   ├── plugins.py             plugin loader
│   │   └── chat.py                plain conversation
│   │
│   ├── utils/
│   │   ├── __init__.py            path helpers, file I/O
│   │   ├── formatting.py          byte/uptime formatting, GPU info
│   │   ├── google_auth.py         Google OAuth + service builders
│   │   └── seen_emails.py         email tracking
│   │
│   └── plugins/                 drop custom .py plugins here
│       └── example_hello.py       example plugin template
│
├── frontends/               <- THIN WRAPPERS (just UI, no business logic)
│   ├── cli/main.py              terminal interface
│   ├── discord/main.py          discord bot
│   └── gui/                     desktop GUI
│       ├── main.py
│       ├── main_window.py
│       ├── chat_widget.py
│       ├── settings_panel.py
│       ├── theme.py
│       └── worker.py
│
├── gui_beta/                <- older standalone GUI (kept for reference)
├── requirements.txt
├── .env.example
├── .gitignore
└── LICENSE
```

### Why this structure matters

**One backend, three frontends.** When you fix a bug or add a feature in `zentra/`, every frontend gets it automatically. You never copy code between folders.

To add a new action:

1. Create a handler in `zentra/actions/`
2. Add one `elif` line in `zentra/dispatcher.py`
3. Add the action name to the system prompt in `zentra/config.py`

All three frontends immediately support it.

## Ollama Setup

Ollama runs AI models locally on your machine. No API keys, no cloud, no cost.

**Install:** [ollama.com/download](https://ollama.com/download)

**Pull a model:**

```bash
ollama pull qwen2.5-coder:7b
```

**For screen automation (vision):**

```bash
ollama pull llava:13b
```

### Recommended models


| Model               | Size   | Best for                                      |
| ------------------- | ------ | --------------------------------------------- |
| `qwen2.5-coder:7b`  | 4.7 GB | Coding + general assistant (default)          |
| `qwen2.5-coder:14b` | 9 GB   | Better reasoning, needs more RAM              |
| `deepseek-r1:14b`   | 9 GB   | Complex multi-step tasks                      |
| `llava:13b`         | 8 GB   | Vision (screen automation, context snapshots) |
| `llama3.2:3b`       | 2 GB   | Lightweight, weaker machines                  |


**Switch models anytime:**

- CLI: type `/model deepseek-r1:14b`
- Discord/GUI: ask "switch to deepseek-r1:14b"
- Or edit `OLLAMA_MODEL` in `zentra/config.py`

---

## Discord Bot Setup

### 1. Create the bot

Go to [discord.com/developers/applications](https://discord.com/developers/applications) and click **New Application**.

### 2. Get your token

Go to the **Bot** tab, click **Reset Token**, copy it.

### 3. Enable intents

Still on the **Bot** tab, scroll to **Privileged Gateway Intents** and enable **Message Content Intent**.

### 4. Invite to your server

Go to **OAuth2 > URL Generator**. Check `bot` under scopes, then `Send Messages` and `Read Message History` under permissions. Open the generated URL and select your server.

### 5. Configure Zentra

Edit `zentra/config.py`:

```python
DISCORD_BOT_TOKEN = "paste_your_token_here"
ALLOWED_USER_IDS = [your_discord_user_id]
```

Or create a `.env` file in the project root:

```
DISCORD_BOT_TOKEN=paste_your_token_here
```

> Find your user ID: enable Developer Mode in Discord settings, right-click your name, Copy User ID.

### 6. Run

```bash
pip install requests python-dotenv discord.py pyperclip psutil
python run_discord.py
```

DM the bot to start using it. The Discord version also includes automatic email polling, morning digests, and event reminders.

---

## Google API Setup

Required for Gmail and Calendar features. Skip this if you don't need email/calendar.

### 1. Create a project

Go to [console.cloud.google.com](https://console.cloud.google.com/) and create a new project.

### 2. Enable APIs

Go to **APIs & Services > Library** and enable:

- **Gmail API**
- **Google Calendar API**

### 3. OAuth consent screen

Go to **APIs & Services > OAuth consent screen**. Select **External**, fill in the basics, add your Google account as a test user.

### 4. Create credentials

Go to **APIs & Services > Credentials**. Click **Create Credentials > OAuth client ID**. Select **Desktop app**. Download the JSON file.

### 5. Place the file

Rename it to `credentials.json` and put it in the project root (same folder as `run_cli.py`).

### 6. Install the libraries

```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

On first run, a browser window opens for authentication. After that, a `google_token.pickle` is saved and reused.

---

## ⌨️ CLI Commands

When using the terminal version, these slash commands give you direct access without going through the AI:


| Command              | Action                                          |
| -------------------- | ----------------------------------------------- |
| `/help`              | Show all commands                               |
| `/clear`             | Wipe conversation memory                        |
| `/status`            | Check Ollama connection + list models           |
| `/model <n>`         | Hot-swap model without restarting               |
| `/clipboard`         | Read clipboard contents                         |
| `/fix`               | Fix code on clipboard, copy result back         |
| `/fix <instruction>` | Fix with specific instruction                   |
| `/snapshot`          | Screen + processes + AI productivity suggestion |
| `/export md`         | Export chat as markdown                         |
| `/export txt`        | Export chat as plain text                       |
| `/kb list`           | Show indexed documents                          |
| `/kb add <path>`     | Index files or folder                           |
| `/kb search <query>` | Search knowledge base                           |
| `/kb clear`          | Wipe the index                                  |
| `/schedule`          | List scheduled tasks                            |
| `/watch`             | List active file watchers                       |
| `/workflows`         | List saved workflows                            |
| `/plugins`           | List loaded plugins                             |
| `/reload`            | Hot-reload plugins                              |
| `/quit`              | Exit                                            |


Everything else you type goes straight to the AI.

---

## Writing Plugins

Create a `.py` file in `zentra/plugins/`:

```python
PLUGIN_NAME = "weather"
PLUGIN_DESCRIPTION = "Fetches current weather for a city"

import requests

def handle(data: dict) -> str:
    city = data.get("reply", "").strip() or "Sydney"
    try:
        r = requests.get(f"https://wttr.in/{city}?format=3", timeout=5)
        return r.text.strip()
    except Exception as exc:
        return f"Failed: {exc}"
```

Plugins auto-load on startup. Use `/reload` in the CLI to pick up new ones without restarting.

The `data` dict contains all the fields from the AI's JSON response (`reply`, `app`, `filename`, `content`, etc.), so your plugin can receive structured input.

---

## Configuration

All settings live in `zentra/config.py`. You can also override with a `.env` file in the project root:

```
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_VISION_MODEL=llava:13b
DISCORD_BOT_TOKEN=your_token_here
```

Key settings in `config.py`:


| Setting               | Default            | What it does                     |
| --------------------- | ------------------ | -------------------------------- |
| `OLLAMA_MODEL`        | `qwen2.5-coder:7b` | Which model handles chat         |
| `OLLAMA_VISION_MODEL` | `llava:13b`        | Which model handles screenshots  |
| `BASE_FOLDER`         | `./zentra_files`   | Where created files go           |
| `MEMORY_DEPTH`        | `8`                | How many exchanges to remember   |
| `RUN_TIMEOUT_SECONDS` | `30`               | Max time for code execution      |
| `ALLOWED_USER_IDS`    | `[]`               | Discord whitelist (empty = open) |


---

## Security

- **Never commit** `credentials.json`, `google_token.pickle`, or `.env` (already in `.gitignore`)
- Discord access is restricted to whitelisted user IDs
- All AI processing happens locally through Ollama
- Shell execution runs real commands on your machine, be mindful of what you ask
- Gmail/Calendar are the only features that talk to external servers

---

## Troubleshooting


| Problem                    | Fix                                                                                              |
| -------------------------- | ------------------------------------------------------------------------------------------------ |
| "Cannot connect to Ollama" | Ollama isn't running. Start with `ollama serve` or open the app                                  |
| "Model not found"          | Pull it: `ollama pull qwen2.5-coder:7b`                                                          |
| Calendar circular import   | Make sure there's no `calendar.py` in your project root                                          |
| Screen automation fails    | `pip install pyautogui Pillow` (Linux: `sudo apt install python3-tk scrot`)                      |
| Clipboard not working      | `pip install pyperclip` (Linux: `sudo apt install xclip`)                                        |
| Gmail/Calendar disabled    | `pip install google-auth google-auth-oauthlib google-api-python-client` + add `credentials.json` |
| GUI won't launch           | `pip install PySide6`                                                                            |


---

## Contributing

The monorepo structure makes contributing easy. Every feature is one file in `zentra/actions/`.

**Add a new action:**

1. Create `zentra/actions/your_feature.py` with a handler function
2. Import it in `zentra/dispatcher.py` and add an `elif`
3. Add the action to the system prompt in `zentra/config.py`

All three frontends get it automatically.

**Add a plugin:** drop a `.py` file in `zentra/plugins/`. No core changes needed.

---

Built by [@Brobuiltathing+@Planeman653](https://github.com/Brobuiltathing)