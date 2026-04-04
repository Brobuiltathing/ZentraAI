

# Z E N T R A

**Your local AI assistant that actually controls your PC.**

Not another chatbot wrapper. Zentra runs on your machine, touches your files,  
launches your apps, reads your screen, manages your email, and automates your workflow.  
Everything local. Everything yours.

[Quickstart](#-quickstart) · [Features](#-features) · [Frontends](#-choose-your-frontend) · [Ollama](#-ollama-setup) · [Discord](#-discord-bot-setup) · [Google APIs](#-google-api-setup-gmail--calendar) · [Structure](#-project-structure) · [Plugins](#-writing-plugins) · [CLI Reference](#-cli-commands-reference) · [Troubleshooting](#%EF%B8%8F-troubleshooting)

---

## 🚀 Quickstart

### What you need

- **Python 3.10+** ([python.org](https://www.python.org/downloads/))
- **Ollama** ([ollama.com](https://ollama.com/download))
- **Git** ([git-scm.com](https://git-scm.com/downloads))

### Step 1 - Install Ollama and pull a model

Download and install Ollama from [ollama.com/download](https://ollama.com/download).

Once installed, open a terminal and pull the default model:

```bash
ollama pull qwen2.5-coder:7b
```

If you want screen automation and vision features, also pull:

```bash
ollama pull llava:13b
```

Make sure Ollama is running. On Windows/Mac it runs as a background app. On Linux, start it with:

```bash
ollama serve
```

### Step 2 - Clone the repo

```bash
git clone https://github.com/Brobuiltathing/Zentra.git
cd Zentra
```

### Step 3 - Install Python dependencies

For the **terminal version** (fastest to get going):

```bash
pip install requests python-dotenv rich pyperclip psutil
```

For **all features including screen automation and Google integrations**:

```bash
pip install -r requirements.txt
```

### Step 4 - Run it

```bash
python run_cli.py
```

You should see the Zentra banner with your model info. Type anything and press enter.

> **That's it.** The terminal version works out of the box with zero configuration.
>
> For Discord or GUI, keep reading below.

---

## 💡 Features

Talk to Zentra in natural language. It decides which action to take and executes it on your machine.

### File and code operations


| You say                                                | What happens                                  |
| ------------------------------------------------------ | --------------------------------------------- |
| "create a python flask server with a /health endpoint" | Writes the file to disk                       |
| "run npm test in my project folder"                    | Executes the shell command, returns output    |
| "read main.py and explain what it does"                | Reads the file and analyses it                |
| "edit server.js and change the port to 8080"           | Applies a surgical find-and-replace patch     |
| "scaffold a react project with router and auth"        | Generates a full multi-file project structure |


### Application and system control


| You say                             | What happens                                  |
| ----------------------------------- | --------------------------------------------- |
| "open chrome, spotify, and discord" | Launches all three (80+ built-in app aliases) |
| "close steam"                       | Finds and terminates the process              |
| "show my system stats"              | CPU, RAM, disk, GPU, network, top processes   |
| "shut down my pc in 10 seconds"     | Executes shutdown command                     |
| "open my project in vscode"         | Launches VS Code with the folder              |


### Clipboard intelligence


| You say                            | What happens                                                 |
| ---------------------------------- | ------------------------------------------------------------ |
| "what's on my clipboard?"          | Reads and displays clipboard contents                        |
| "explain the code on my clipboard" | AI analyses and explains it                                  |
| "fix the bugs on my clipboard"     | Fixes errors, copies the corrected version back to clipboard |


### Screen and context awareness


| You say                           | What happens                                                                                              |
| --------------------------------- | --------------------------------------------------------------------------------------------------------- |
| "what am I working on right now?" | Takes a screenshot, lists running processes, shows active window, gives you an AI productivity suggestion |
| "click the submit button"         | Screenshots the screen, uses vision AI to locate the button, clicks it                                    |
| "scroll down and click settings"  | Multi-step screen automation with re-evaluation after each action                                         |


### Workflow chains (multi-step automation)


| You say                                                               | What happens                                                                |
| --------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| "run my tests, if they pass commit and push, then email me a summary" | Chains multiple actions with conditional logic (stop/skip/retry on failure) |
| "save that workflow as deploy"                                        | Saves a named workflow you can replay later                                 |
| "replay deploy"                                                       | Runs the saved workflow again                                               |
| "list my workflows"                                                   | Shows all saved workflows                                                   |


### File watching


| You say                                   | What happens                                         |
| ----------------------------------------- | ---------------------------------------------------- |
| "watch my Downloads folder for new files" | Starts real-time monitoring, notifies you on changes |
| "stop watching Downloads"                 | Stops the watcher                                    |
| "list my watchers"                        | Shows all active watchers                            |


### Local knowledge base


| You say                                           | What happens                                                |
| ------------------------------------------------- | ----------------------------------------------------------- |
| "add all my notes to the knowledge base"          | Indexes your local text/code/config files with AI summaries |
| "search my notes for that API key format I saved" | Searches indexed docs and answers using only your files     |
| "list my knowledge base"                          | Shows all indexed documents                                 |
| "clear the knowledge base"                        | Wipes the index                                             |


Supported file types: `.txt`, `.md`, `.py`, `.js`, `.ts`, `.json`, `.yaml`, `.yml`, `.toml`, `.cfg`, `.ini`, `.html`, `.css`, `.csv`, `.log`, `.sh`, `.bat`, `.ps1`, `.env`, `.xml`, `.rst`, `.tex`

### Scheduled tasks and reminders


| You say                                   | What happens                      |
| ----------------------------------------- | --------------------------------- |
| "remind me at 5pm to push my code"        | One-time reminder                 |
| "every Monday at 9am summarise my emails" | Recurring weekly task             |
| "list my scheduled tasks"                 | Shows all pending tasks with IDs  |
| "cancel task_1"                           | Cancels a specific scheduled task |


Supports one-time, hourly, daily, and weekly schedules.

### Gmail integration


| You say                                                                                  | What happens                             |
| ---------------------------------------------------------------------------------------- | ---------------------------------------- |
| "summarise my unread emails"                                                             | AI-ranked digest with importance scoring |
| "check for emails from Jake"                                                             | Filtered search by sender or keyword     |
| "send an email to [jake@example.com](mailto:jake@example.com) saying the report is done" | Composes and sends the email             |


The Discord version also includes automatic email polling that DMs you when critical emails arrive, and a daily morning briefing digest.

Requires [Google API setup](#-google-api-setup-gmail--calendar).

### Google Calendar integration


| You say                                     | What happens                                                              |
| ------------------------------------------- | ------------------------------------------------------------------------- |
| "what's on my calendar today?"              | Shows events with times, locations, meeting links, and conflict detection |
| "show my week"                              | Full weekly agenda grouped by day                                         |
| "add a meeting with Sarah on Friday at 2pm" | Creates the event with natural language parsing                           |
| "delete the dentist appointment"            | Finds and deletes by name                                                 |
| "search my calendar for standup"            | Searches upcoming events by keyword                                       |


The Discord version includes automatic event reminders 30 minutes before each meeting.

Requires [Google API setup](#-google-api-setup-gmail--calendar).

### Other features


| You say                                | What happens                              |
| -------------------------------------- | ----------------------------------------- |
| "commit and push my code"              | `git add .`, `commit`, `push` in one shot |
| "export this conversation as markdown" | Saves chat history to a .md or .txt file  |
| "list my plugins"                      | Shows loaded custom plugins               |


### Plugin system

Drop a Python file in `zentra/plugins/` and it becomes a new action. No core code changes needed. See [Writing Plugins](#-writing-plugins).

---

## 🖥️ Choose your frontend

All three frontends use the exact same backend. Same 40+ actions, same features. Pick your interface.


| Command                 | Interface                                               | Best for                                |
| ----------------------- | ------------------------------------------------------- | --------------------------------------- |
| `python run_cli.py`     | Terminal with rich formatting, spinners, slash commands | Fast local use, developers              |
| `python run_discord.py` | Discord bot, interact via DMs                           | Remote control from phone or another PC |
| `python run_gui.py`     | Desktop app with sidebar, chat bubbles, settings panel  | Visual preference, non-terminal users   |


### Install dependencies per frontend

**Terminal only:**

```bash
pip install requests python-dotenv rich pyperclip psutil
```

**Discord only:**

```bash
pip install requests python-dotenv discord.py pyperclip psutil
```

**GUI only:**

```bash
pip install requests python-dotenv PySide6 pyperclip psutil
```

**Everything (all frontends + all optional features):**

```bash
pip install -r requirements.txt
```

---

## 🤖 Ollama Setup

Ollama runs AI models locally. No API keys, no cloud costs, no data leaving your machine.

### Install Ollama

Download from [ollama.com/download](https://ollama.com/download) and run the installer.

### Pull your models

Open a terminal and run:

```bash
ollama pull qwen2.5-coder:7b
```

For vision/screen features:

```bash
ollama pull llava:13b
```

### Verify it's working

```bash
ollama list
```

You should see your downloaded models listed.

### Make sure Ollama is running

- **Windows/Mac**: Ollama runs as a background service after installation. Check your system tray.
- **Linux**: Start it manually with `ollama serve`

### Recommended models


| Model             | Download                        | Size   | Best for                                     |
| ----------------- | ------------------------------- | ------ | -------------------------------------------- |
| qwen2.5-coder:7b  | `ollama pull qwen2.5-coder:7b`  | 4.7 GB | Coding and general tasks (default)           |
| qwen2.5-coder:14b | `ollama pull qwen2.5-coder:14b` | 9 GB   | Better reasoning, needs 16GB+ RAM            |
| deepseek-r1:14b   | `ollama pull deepseek-r1:14b`   | 9 GB   | Complex multi-step reasoning                 |
| llava:13b         | `ollama pull llava:13b`         | 8 GB   | Vision, screen automation, context snapshots |
| llama3.2:3b       | `ollama pull llama3.2:3b`       | 2 GB   | Lightweight, low-spec machines               |


### Switching models

You can change the model anytime without restarting:

- **CLI**: type `/model deepseek-r1:14b`
- **Discord or GUI**: ask Zentra "switch to deepseek-r1:14b"
- **Permanently**: edit `OLLAMA_MODEL` in `zentra/config.py`

---

## 💬 Discord Bot Setup

This section walks you through creating a Discord bot from scratch and connecting it to Zentra. If you've never made a Discord bot before, follow every step.

### 1. Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click the **New Application** button in the top right
3. Give it a name (e.g. `ZentraAI`) and click **Create**
4. You'll land on the General Information page. You can optionally add a description and icon here.

### 2. Create the Bot User

1. In the left sidebar, click **Bot**
2. Click **Add Bot**, then confirm with **Yes, do it!**
3. You now have a bot user attached to your application

### 3. Enable Required Intents

Still on the **Bot** page, scroll down to **Privileged Gateway Intents** and turn on:

- **Message Content Intent** (required, lets the bot read what you type)
- **Server Members Intent** (optional but useful)

Click **Save Changes** at the bottom.

### 4. Get Your Bot Token

Still on the **Bot** page:

1. Click **Reset Token**
2. Confirm, then **copy the token** that appears

This token is like a password for your bot. Keep it secret.

> If you accidentally leak your token, go back here and reset it immediately.

### 5. Add the Token to Zentra

**Option A** - Edit the config file directly:

Open `zentra/config.py` and find this line near the top:

```python
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
```

Replace `YOUR_BOT_TOKEN_HERE` with your actual token:

```python
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "MTIzNDU2Nzg5MDEy...")
```

**Option B** - Use a `.env` file (recommended, keeps secrets out of code):

Create a file called `.env` in the project root (same folder as `run_discord.py`):

```
DISCORD_BOT_TOKEN=MTIzNDU2Nzg5MDEy...
```

The `.gitignore` already prevents `.env` from being committed.

### 6. Add Your User ID to the Whitelist

This ensures only you can talk to the bot.

First, get your Discord user ID:

1. Open Discord
2. Go to **Settings > Advanced** and enable **Developer Mode**
3. Close settings
4. Right-click your own username anywhere in Discord
5. Click **Copy User ID**

Then open `zentra/config.py` and find:

```python
ALLOWED_USER_IDS: list = []
```

Add your ID:

```python
ALLOWED_USER_IDS: list = [123456789012345678]
```

Replace `123456789012345678` with your actual ID.

If you leave the list empty, anyone who can DM the bot can use it.

### 7. Invite the Bot to Your Server

1. In the Developer Portal, go to **OAuth2 > URL Generator** in the left sidebar
2. Under **Scopes**, check `bot`
3. Under **Bot Permissions**, check:
  - `Send Messages`
  - `Read Message History`
4. Copy the generated URL at the bottom of the page
5. Paste it into your browser
6. Select your server from the dropdown and click **Authorize**

The bot will now appear in your server's member list (it will show as offline until you start the program).

### 8. Install Dependencies and Run

```bash
pip install requests python-dotenv discord.py pyperclip psutil
python run_discord.py
```

You should see logs like:

```
ZENTRA v9.0 -- Discord Bot
Bot user    : ZentraAI#1234 (ID 9876543210)
Ready -- waiting for DMs
```

### 9. Start Using It

Open Discord and **send a Direct Message** to your bot. Don't type in a server channel, use DMs.

Type anything, like:

- "hello"
- "show my system stats"
- "create a python hello world file"

The bot will respond in the DM.

### Discord-exclusive features

The Discord version has background tasks that the CLI and GUI versions don't:

- **Morning digest** - Every day at 8:00 AM, Zentra DMs you a briefing with unread emails and today's calendar (requires Google setup)
- **Email polling** - Checks for important emails every 5 minutes and DMs you immediately if something critical arrives
- **Event reminders** - DMs you 30 minutes before each calendar event with the meeting link
- **File watcher alerts** - If you have active file watchers, changes get sent to your DMs
- **Scheduled task execution** - Reminders and recurring tasks fire as DMs

These run automatically in the background as long as the bot is online.

---

## 📧 Google API Setup (Gmail + Calendar)

Gmail and Calendar features are optional. Skip this entire section if you don't need them. Zentra will work fine without them and just disable those specific actions.

### 1. Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. If you've never used Google Cloud, you may need to agree to terms of service
3. Click the project dropdown at the top of the page and click **New Project**
4. Give it a name (e.g. `ZentraAI`) and click **Create**
5. Make sure your new project is selected in the dropdown at the top

### 2. Enable the APIs

1. In the left sidebar, go to **APIs & Services > Library**
2. Search for **Gmail API** and click on it, then click **Enable**
3. Go back to the Library
4. Search for **Google Calendar API** and click on it, then click **Enable**

### 3. Configure the OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. Select **External** and click **Create**
3. Fill in:
  - **App name**: ZentraAI (or anything)
  - **User support email**: your Gmail address
  - **Developer contact email**: your Gmail address
4. Click **Save and Continue**
5. On the **Scopes** page, click **Save and Continue** (skip for now)
6. On the **Test users** page, click **Add Users**
7. Enter your Gmail address and click **Save**
8. Click **Save and Continue**, then **Back to Dashboard**

### 4. Create OAuth 2.0 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials** at the top, select **OAuth client ID**
3. For **Application type**, select **Desktop app**
4. Give it a name (e.g. `ZentraDesktop`) and click **Create**
5. On the confirmation screen, click **Download JSON**

### 5. Place the Credentials File

1. Rename the downloaded file to exactly `credentials.json`
2. Move it to the Zentra project root (the same folder as `run_cli.py`)

```
Zentra/
├── credentials.json   <-- put it here
├── run_cli.py
├── run_discord.py
└── ...
```

### 6. Install the Libraries

```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

### 7. First Run Authentication

The first time you use a Gmail or Calendar command, a browser window will open asking you to log in to your Google account and grant access.

After you approve, a `google_token.pickle` file is created in the project folder. This stores your authentication so you don't have to log in again.

> **Never commit `credentials.json` or `google_token.pickle` to Git.** Both are already in the `.gitignore`.

---

## 📁 Project Structure

```
Zentra/
│
├── run_cli.py               <- type: python run_cli.py
├── run_discord.py           <- type: python run_discord.py
├── run_gui.py               <- type: python run_gui.py
│
├── zentra/                  <- THE SHARED BACKEND
│   ├── config.py               all settings, tokens, model names, system prompt
│   ├── engine.py               processes a user message end-to-end
│   ├── dispatcher.py           reads the AI's chosen action, calls the right handler
│   ├── memory.py               stores and loads conversation history
│   ├── ollama.py               sends prompts to Ollama and gets responses
│   ├── parser.py               extracts JSON from the model's raw output
│   ├── logger.py               logging config
│   │
│   ├── actions/                every feature is one file here
│   │   ├── files.py               create / read / edit / run / scaffold files
│   │   ├── apps.py                open / close apps (80+ built-in aliases)
│   │   ├── shell.py               run any terminal command directly
│   │   ├── git.py                 git add + commit + push
│   │   ├── system.py              system stats, shutdown / restart / sleep PC
│   │   ├── screen.py              screenshot + vision AI + mouse/keyboard control
│   │   ├── clipboard.py           read / analyse / fix clipboard contents
│   │   ├── context.py             screen + processes + active window + suggestion
│   │   ├── workflow.py            multi-step automation with conditionals
│   │   ├── watcher.py             real-time folder monitoring
│   │   ├── knowledge.py           local document indexing and search
│   │   ├── scheduler.py           reminders and recurring tasks
│   │   ├── gmail.py               email summary and send
│   │   ├── calendar.py            calendar view / add / delete / search
│   │   ├── export.py              export chat as markdown or text
│   │   ├── plugins.py             loads custom plugins from the plugins folder
│   │   └── chat.py                plain conversational responses
│   │
│   ├── utils/
│   │   ├── __init__.py            file path resolution, write helpers
│   │   ├── formatting.py          byte formatting, uptime, GPU info
│   │   ├── google_auth.py         Google OAuth flow, service builders, retry logic
│   │   └── seen_emails.py         tracks processed email IDs
│   │
│   └── plugins/                 your custom plugins go here
│       └── example_hello.py       working example to copy from
│
├── frontends/               <- UI WRAPPERS (no business logic, just interface)
│   ├── cli/
│   │   └── main.py              terminal: rich panels, slash commands, spinners
│   ├── discord/
│   │   └── main.py              discord: bot events, typing indicator, scheduler
│   └── gui/
│       ├── main.py              app entry point
│       ├── main_window.py       window layout, sidebar, input handling
│       ├── chat_widget.py       message bubbles, welcome screen, quick actions
│       ├── settings_panel.py    live settings editor
│       ├── theme.py             dark theme stylesheet
│       └── worker.py            background thread for AI calls
│
├── gui_beta/                <- older standalone GUI version (kept for reference)
│
├── requirements.txt         <- pip install -r requirements.txt for everything
├── .env.example             <- template for your .env file
├── .gitignore               <- keeps secrets and generated files out of git
└── LICENSE
```

### How to add a new feature

This is the whole point of the structure. You edit **one place** and all three frontends get it.

1. Create `zentra/actions/your_feature.py` with a `handle_your_feature(data: dict) -> str` function
2. Open `zentra/dispatcher.py`, import your function, add one `elif action == "your_feature":` line
3. Open `zentra/config.py`, add `your_feature` to the system prompt's action list so the AI knows about it

Done. CLI, Discord, and GUI all support the new action immediately.

---

## ⚙️ Configuration

### Config file

All settings are in `zentra/config.py`:


| Setting               | Default                  | What it controls                |
| --------------------- | ------------------------ | ------------------------------- |
| `OLLAMA_ENDPOINT`     | `http://localhost:11434` | Where Ollama is running         |
| `OLLAMA_MODEL`        | `qwen2.5-coder:7b`       | Model for chat/actions          |
| `OLLAMA_VISION_MODEL` | `llava:13b`              | Model for screen/vision         |
| `BASE_FOLDER`         | `./zentra_files`         | Where generated files are saved |
| `MEMORY_DEPTH`        | `8`                      | Conversation turns to remember  |
| `RUN_TIMEOUT_SECONDS` | `30`                     | Max seconds for code execution  |
| `DISCORD_BOT_TOKEN`   | `YOUR_BOT_TOKEN_HERE`    | Your Discord bot token          |
| `ALLOWED_USER_IDS`    | `[]`                     | Discord user whitelist          |


### Environment variables

Instead of editing `config.py`, you can create a `.env` file in the project root:

```
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_VISION_MODEL=llava:13b
DISCORD_BOT_TOKEN=your_token_here
```

The `.env` file is already in `.gitignore` so it won't be committed.

Requires `python-dotenv` (included in all install commands above).

---

## ⌨️ CLI Commands Reference

Direct slash commands in the terminal version (bypass the AI for instant execution):


| Command              | What it does                                                    |
| -------------------- | --------------------------------------------------------------- |
| `/help`              | Show all commands                                               |
| `/clear`             | Wipe conversation memory and start fresh                        |
| `/status`            | Check Ollama connection, list available models                  |
| `/model <name>`      | Switch model without restarting (e.g. `/model deepseek-r1:14b`) |
| `/clipboard`         | Read and display current clipboard contents                     |
| `/fix`               | Fix code/text on clipboard, copy corrected version back         |
| `/fix <instruction>` | Fix with specific instruction (e.g. `/fix add type hints`)      |
| `/snapshot`          | Context snapshot: screenshot + processes + AI suggestion        |
| `/export md`         | Export conversation as markdown file                            |
| `/export txt`        | Export conversation as plain text file                          |
| `/kb list`           | Show all indexed knowledge base documents                       |
| `/kb add <path>`     | Index a file or folder into the knowledge base                  |
| `/kb search <query>` | Search the knowledge base                                       |
| `/kb clear`          | Wipe the entire knowledge base index                            |
| `/schedule`          | List all scheduled tasks and reminders                          |
| `/watch`             | List all active file watchers                                   |
| `/workflows`         | List all saved workflow chains                                  |
| `/plugins`           | List all loaded plugins                                         |
| `/reload`            | Hot-reload plugins without restarting Zentra                    |
| `/quit`              | Exit Zentra                                                     |


Anything that doesn't start with `/` gets sent to the AI as a natural language request.

---

## 🔌 Writing Plugins

Plugins let you add custom actions without touching any core code.

### Create a plugin

Make a new `.py` file in `zentra/plugins/`:

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

### How it works

- `PLUGIN_NAME` becomes the action name the AI can call
- `PLUGIN_DESCRIPTION` is shown in plugin listings
- `handle(data)` receives the AI's parsed JSON with fields like `reply`, `app`, `filename`, `content`
- Return a string with your result

### Loading

Plugins load automatically when Zentra starts. In the CLI, use `/reload` to pick up new plugins without restarting.

### Using plugins

Ask the AI: "run the weather plugin for Tokyo"

Or in the CLI: `/plugins` to see what's loaded.

An example plugin (`example_hello.py`) is included to copy from.

---

## 🔒 Security Notes


| What                  | Rule                                                                              |
| --------------------- | --------------------------------------------------------------------------------- |
| `credentials.json`    | Never commit. Contains your Google OAuth client secret.                           |
| `google_token.pickle` | Never commit. Contains your authenticated Google session.                         |
| `.env`                | Never commit. Contains your Discord token and other secrets.                      |
| `DISCORD_BOT_TOKEN`   | Treat like a password. Reset immediately if leaked.                               |
| `ALLOWED_USER_IDS`    | Set this to restrict who can control your PC via Discord.                         |
| Shell commands        | Zentra runs real commands on your machine. Be careful what you ask.               |
| Data privacy          | All AI runs locally via Ollama. Gmail/Calendar are the only external connections. |


The `.gitignore` already covers all sensitive files.

---

## 🛠️ Troubleshooting


| Problem                                            | Solution                                                                                                                  |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| "Cannot connect to Ollama"                         | Ollama isn't running. Start with `ollama serve` (Linux) or check your system tray (Windows/Mac).                          |
| "Model not found"                                  | Pull it first: `ollama pull qwen2.5-coder:7b`                                                                             |
| `ModuleNotFoundError: No module named 'discord'`   | Run: `pip install discord.py`                                                                                             |
| `ModuleNotFoundError: No module named 'rich'`      | Run: `pip install rich`                                                                                                   |
| `ModuleNotFoundError: No module named 'PySide6'`   | Run: `pip install PySide6`                                                                                                |
| `ModuleNotFoundError: No module named 'pyperclip'` | Run: `pip install pyperclip`                                                                                              |
| Calendar circular import error                     | Make sure there's no file called `calendar.py` in the project root. The action file must stay inside `zentra/actions/`.   |
| Screen automation not working                      | `pip install pyautogui Pillow`. On Linux also: `sudo apt install python3-tk python3-dev scrot`                            |
| Clipboard not working on Linux                     | `sudo apt install xclip`                                                                                                  |
| Gmail/Calendar shows as disabled                   | `pip install google-auth google-auth-oauthlib google-api-python-client` and place `credentials.json` in the project root. |
| Bot is online but not responding                   | Make sure you're DMing the bot, not typing in a server channel. Check that your user ID is in `ALLOWED_USER_IDS`.         |
| Bot shows "Not authorised"                         | Add your Discord user ID to `ALLOWED_USER_IDS` in `zentra/config.py`.                                                     |
| Google auth browser doesn't open                   | Make sure `credentials.json` is in the project root (same folder as `run_cli.py`).                                        |
| Token expired / auth error                         | Delete `google_token.pickle` and restart. It will re-authenticate.                                                        |


---

## 🤝 Contributing

The monorepo makes contributing simple. Every feature is one file.

**Add a new action:**

1. Create `zentra/actions/your_feature.py`
2. Add an `elif` in `zentra/dispatcher.py`
3. Add the action to the system prompt in `zentra/config.py`

All three frontends get it instantly.

**Add a plugin:** drop a `.py` file in `zentra/plugins/`. Zero core changes.

**Fix a bug:** find the relevant file in `zentra/actions/` or `zentra/utils/`, fix it once. Every frontend benefits.

---

Built by [@Brobuiltathing](https://github.com/Brobuiltathing)