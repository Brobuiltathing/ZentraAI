

# Z E N T R A

**Your local AI assistant that actually controls your PC.**

Not another chatbot wrapper. Zentra runs on your machine, touches your files,  
launches your apps, reads your screen, searches the web, talks to your Arduino,  
manages your email, and automates your workflow. Everything local. Everything yours.

[Quickstart](#-quickstart) · [Features](#-features) · [Frontends](#-choose-your-frontend) · [Ollama](#-ollama-setup) · [Discord](#-discord-bot-setup) · [Google APIs](#-google-api-setup-gmail--calendar) · [Arduino](#-arduino-hardware-assistant) · [Structure](#-project-structure) · [Plugins](#-writing-plugins) · [CLI Reference](#-cli-commands-reference) · [Troubleshooting](#%EF%B8%8F-troubleshooting)

---

## Quickstart

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

For **all features including screen automation, Arduino, and Google integrations**:

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

## Features

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


### Web search + content fetching 🆕


| You say                                                                                       | What happens                                                  |
| --------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| "search for the latest react 19 features"                                                     | Searches DuckDuckGo, AI-summarises top results with citations |
| "what's happening with AI regulation in the EU"                                               | Current information with source links                         |
| "fetch [https://arxiv.org/abs/2312.00752](https://arxiv.org/abs/2312.00752) and summarise it" | Downloads the page, strips clutter, extracts main points      |
| "read this blog post and tell me the key takeaways"                                           | URL-based content analysis                                    |


**No API key needed.** Uses DuckDuckGo's HTML endpoint and sends results to your local Ollama model for summarisation.

### Arduino hardware assistant 🆕

See the [Arduino section below](#-arduino-hardware-assistant) for the full walkthrough. Quick examples:


| You say                                                 | What happens                                         |
| ------------------------------------------------------- | ---------------------------------------------------- |
| "what pins does the esp32 have"                         | Full pinout, I2C/SPI/UART pins, voltage warnings     |
| "which library for dht22"                               | Tells you the exact library name and install command |
| "what arduino ports are connected"                      | Lists USB serial devices, flags likely Arduinos      |
| "generate an esp32 sketch that reads a dht22 on gpio 4" | Complete working .ino file with wiring table         |
| "start serial monitor on COM3 at 115200"                | Opens live serial connection                         |


### Clipboard intelligence


| You say                            | What happens                                                 |
| ---------------------------------- | ------------------------------------------------------------ |
| "what's on my clipboard?"          | Reads and displays clipboard contents                        |
| "explain the code on my clipboard" | AI analyses and explains it                                  |
| "fix the bugs on my clipboard"     | Fixes errors, copies the corrected version back to clipboard |


### Screen and context awareness


| You say                           | What happens                                                     |
| --------------------------------- | ---------------------------------------------------------------- |
| "what am I working on right now?" | Screenshots, lists processes, shows active window, AI suggestion |
| "click the submit button"         | Vision AI finds and clicks UI elements                           |


### Workflow chains (multi-step automation)


| You say                                                            | What happens                          |
| ------------------------------------------------------------------ | ------------------------------------- |
| "run tests, if they pass commit and push, then email me a summary" | Chains actions with conditional logic |
| "save that workflow as deploy"                                     | Saves named workflow for replay       |
| "replay deploy"                                                    | Runs the saved workflow again         |


### File watching


| You say                                   | What happens                              |
| ----------------------------------------- | ----------------------------------------- |
| "watch my Downloads folder for new files" | Real-time monitoring, notifies on changes |


### Local knowledge base


| You say                                   | What happens                                    |
| ----------------------------------------- | ----------------------------------------------- |
| "add all my notes to the knowledge base"  | Indexes local documents with AI summaries       |
| "search my notes for that API key format" | Searches indexed docs, answers using your files |


### Scheduled tasks and reminders


| You say                                   | What happens          |
| ----------------------------------------- | --------------------- |
| "remind me at 5pm to push my code"        | One-time reminder     |
| "every Monday at 9am summarise my emails" | Recurring weekly task |


### Gmail + Calendar


| You say                                                                                  | What happens                             |
| ---------------------------------------------------------------------------------------- | ---------------------------------------- |
| "summarise my unread emails"                                                             | AI-ranked digest with importance scoring |
| "send an email to [jake@example.com](mailto:jake@example.com) saying the report is done" | Composes and sends                       |
| "what's on my calendar today?"                                                           | Shows events with conflict detection     |
| "add a meeting with Sarah on Friday at 2pm"                                              | Creates event from natural language      |


Requires [Google API setup](#-google-api-setup-gmail--calendar).

### Other features

- **Git push** - `git add .`, `commit`, `push` in one shot
- **Export chat** - as markdown or plain text
- **Plugin system** - drop a .py file, new action available
- **Shell commands** - direct terminal execution

---

## Choose your frontend

All three frontends share the same backend. Pick your interface.


| Command                 | Interface                                 | Best for                     |
| ----------------------- | ----------------------------------------- | ---------------------------- |
| `python run_cli.py`     | Terminal, rich formatting, slash commands | Fast local use, developers   |
| `python run_discord.py` | Discord bot via DMs                       | Remote control from phone/PC |
| `python run_gui.py`     | Desktop app                               | Visual preference            |


### Frontend dependencies

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

**Everything:**

```bash
pip install -r requirements.txt
```

---

## Ollama Setup

Ollama runs AI models locally. No API keys, no cloud costs.

**Install:** [ollama.com/download](https://ollama.com/download)

**Pull your models:**

```bash
ollama pull qwen2.5-coder:7b
ollama pull llava:13b
```

**Verify:**

```bash
ollama list
```

### Recommended models


| Model             | Size   | Best for                          |
| ----------------- | ------ | --------------------------------- |
| qwen2.5-coder:7b  | 4.7 GB | Coding + general tasks (default)  |
| qwen2.5-coder:14b | 9 GB   | Better reasoning, needs 16GB+ RAM |
| deepseek-r1:14b   | 9 GB   | Complex multi-step reasoning      |
| llava:13b         | 8 GB   | Vision, screen automation         |
| llama3.2:3b       | 2 GB   | Lightweight, low-spec machines    |


**Switch models anytime:**

- CLI: type `/model deepseek-r1:14b`
- Discord/GUI: ask "switch to deepseek-r1:14b"

---

## Discord Bot Setup

### 1. Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application**, give it a name, click **Create**

### 2. Create the Bot

1. Click **Bot** in the left sidebar
2. Click **Add Bot**, confirm with **Yes, do it!**

### 3. Enable Intents

Scroll to **Privileged Gateway Intents** and enable:

- **Message Content Intent**
- **Server Members Intent** (optional)

Click **Save Changes**.

### 4. Get Your Token

Click **Reset Token** and copy it.

### 5. Add to Zentra

Edit `zentra/config.py`:

```python
DISCORD_BOT_TOKEN = "your_token_here"
ALLOWED_USER_IDS = [your_discord_user_id]
```

Or create `.env`:

```
DISCORD_BOT_TOKEN=your_token_here
```

> Find your user ID: enable Developer Mode in Discord settings, right-click your name, Copy User ID.

### 6. Invite the Bot

1. Go to **OAuth2 > URL Generator**
2. Scopes: `bot`
3. Permissions: `Send Messages`, `Read Message History`
4. Open the generated URL and select your server

### 7. Run

```bash
python run_discord.py
```

DM the bot to start. Discord version has exclusive background features:

- Morning digest at 8am (email + calendar)
- Critical email alerts every 5 min
- Event reminders 30 min before meetings
- File watcher notifications

---

## Google API Setup (Gmail + Calendar)

Optional - skip if you don't need email/calendar.

### 1. Create Google Cloud Project

[console.cloud.google.com](https://console.cloud.google.com/) → **New Project**

### 2. Enable APIs

**APIs & Services > Library** → enable:

- Gmail API
- Google Calendar API

### 3. OAuth Consent Screen

**APIs & Services > OAuth consent screen** → External → add yourself as test user

### 4. Create Credentials

**APIs & Services > Credentials > Create Credentials > OAuth client ID** → Desktop app → Download JSON

### 5. Place File

Rename to `credentials.json` and put in the project root.

### 6. Install

```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

First run opens a browser for authentication. A `google_token.pickle` is saved and reused.

---

## 🔧 Arduino Hardware Assistant

Zentra has a dedicated Arduino/ESP toolkit for hardware projects. Not just compile-and-upload - it solves the real friction points.

### What it does

**Board database** - Detailed specs for 6 boards built in (Arduino Uno, Nano, Mega, ESP32, ESP8266, Raspberry Pi Pico). Every pin, every interface, every warning, no Googling.

**Library lookup** - 30+ common components mapped to the correct libraries. Ask "which library for mpu6050" and get the exact library name, include statement, and install instructions.

**Port detection** - Finds your board on USB automatically, flags likely Arduinos by their USB-to-serial chipset (CH340, CP210, FTDI, Silicon Labs).

**Code generation** - Generates complete .ino sketches from natural language, using the correct pins for your specific board. Includes wiring table, library list, and notes.

**Compile + Upload** - Wraps arduino-cli with the right FQBN for your chosen board.

**Live serial monitor** - Opens a connection in a background thread, buffers 200 lines, lets you read output and send commands back without alt-tabbing.

### Setup

Install pyserial:

```bash
pip install pyserial
```

For real compile/upload (optional, everything else works without it):

1. Install arduino-cli: [arduino.github.io/arduino-cli/latest/installation](https://arduino.github.io/arduino-cli/latest/installation/)
2. Install the core for your board:
  ```bash
   arduino-cli core install arduino:avr      # Uno, Nano, Mega
   arduino-cli core install esp32:esp32      # ESP32
   arduino-cli core install esp8266:esp8266  # ESP8266
   arduino-cli core install rp2040:rp2040    # Pi Pico
  ```

### Example workflow

Building a temperature logger with an ESP32 and DHT22:

```
You: what pins does the esp32 have
Zentra: [shows full ESP32 pinout with I2C, SPI, ADC, avoid_pins warnings, etc]

You: which library for dht22
Zentra: DHT22 - temperature + humidity
        Library: DHT sensor library
        Include: #include <DHT.h>
        Install via Arduino IDE Library Manager...

You: generate an esp32 sketch that reads a dht22 on gpio 4 and prints to serial every 2 seconds
Zentra: Arduino Sketch Generated
        Target: ESP32 DevKit
        Saved to: ./zentra_files/arduino/esp32_dht22.ino
        
        Wiring:
        DHT22 VCC  -> ESP32 3.3V
        DHT22 GND  -> ESP32 GND
        DHT22 DATA -> ESP32 GPIO 4
        (10K pullup resistor between VCC and DATA)
        
        Libraries needed: DHT sensor library, Adafruit Unified Sensor
        [shows full working code]

You: what ports are connected
Zentra: Detected Ports
        COM4 [ARDUINO?]
          USB-SERIAL CH340
          Manufacturer: wch.cn
          VID:PID = 1A86:7523

You: compile esp32_dht22.ino for esp32
Zentra: Compiled successfully for esp32:esp32:esp32
        Sketch uses 238,765 bytes (18%) of program storage...

You: upload it to COM4 for esp32
Zentra: Uploaded to COM4 (esp32:esp32:esp32)

You: start monitor on COM4 at 115200
Zentra: Monitoring COM4 @ 115200 baud

You: read the serial output
Zentra: Serial output from COM4 (last 5 lines)
        [14:32:01] Temperature: 22.4 C  Humidity: 45.2%
        [14:32:03] Temperature: 22.4 C  Humidity: 45.1%
        [14:32:05] Temperature: 22.5 C  Humidity: 45.3%
```

### Supported boards


| Key       | Board             |
| --------- | ----------------- |
| `uno`     | Arduino Uno R3    |
| `nano`    | Arduino Nano      |
| `mega`    | Arduino Mega 2560 |
| `esp32`   | ESP32 DevKit      |
| `esp8266` | ESP8266 NodeMCU   |
| `pi_pico` | Raspberry Pi Pico |


### Component library (30+ built in)

Sensors: `dht11`, `dht22`, `ds18b20`, `bmp280`, `bme280`, `mpu6050`, `hc-sr04`, `ultrasonic`  
Displays: `lcd`, `oled`, `ssd1306`, `tft`  
Storage: `sd`, `rtc`, `ds3231`  
Motors: `servo`, `stepper`, `28byj-48`  
Wireless: `nrf24`, `wifi`, `bluetooth`, `ble`, `esp-now`  
Other: `rfid`, `mfrc522`, `neopixel`, `ws2812`, `ir`, `keypad`, `buzzer`, `joystick`, `potentiometer`, `relay`, `button`, `led`

---

## Project Structure

```
Zentra/
│
├── run_cli.py               <- type: python run_cli.py
├── run_discord.py           <- type: python run_discord.py
├── run_gui.py               <- type: python run_gui.py
│
├── zentra/                  <- SHARED BACKEND (all frontends use this)
│   ├── config.py
│   ├── engine.py
│   ├── dispatcher.py
│   ├── memory.py
│   ├── ollama.py
│   ├── parser.py
│   ├── logger.py
│   │
│   ├── actions/             <- one file per feature
│   │   ├── files.py
│   │   ├── apps.py
│   │   ├── shell.py
│   │   ├── git.py
│   │   ├── system.py
│   │   ├── screen.py
│   │   ├── clipboard.py
│   │   ├── context.py
│   │   ├── workflow.py
│   │   ├── watcher.py
│   │   ├── knowledge.py
│   │   ├── scheduler.py
│   │   ├── gmail.py
│   │   ├── calendar.py
│   │   ├── export.py
│   │   ├── plugins.py
│   │   ├── web.py           <- web search + fetch
│   │   ├── arduino.py       <- arduino hardware assistant
│   │   └── chat.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── formatting.py
│   │   ├── google_auth.py
│   │   └── seen_emails.py
│   │
│   └── plugins/             <- drop custom .py plugins here
│       └── example_hello.py
│
├── frontends/               <- UI WRAPPERS (no business logic)
│   ├── cli/main.py
│   ├── discord/main.py
│   └── gui/
│
├── gui_beta/                <- older standalone GUI
├── requirements.txt
├── .env.example
├── .gitignore
└── LICENSE
```

### Adding a new feature

1. Create `zentra/actions/your_feature.py`
2. Add one `elif` in `zentra/dispatcher.py`
3. Add the action to the system prompt in `zentra/config.py`

All three frontends get it instantly.

---

## CLI Commands Reference


| Command              | Action                          |
| -------------------- | ------------------------------- |
| `/help`              | Show all commands               |
| `/clear`             | Wipe conversation memory        |
| `/status`            | Check Ollama connection         |
| `/model <n>`         | Switch model                    |
| `/clipboard`         | Read clipboard contents         |
| `/fix`               | Fix clipboard, copy back        |
| `/snapshot`          | Screen + processes + suggestion |
| `/export md`         | Export chat as markdown         |
| `/export txt`        | Export chat as plain text       |
| `/kb list`           | Show knowledge base             |
| `/kb add <path>`     | Index files/folder              |
| `/kb search <query>` | Search KB                       |
| `/schedule`          | List scheduled tasks            |
| `/watch`             | List file watchers              |
| `/workflows`         | List saved workflows            |
| `/plugins`           | List loaded plugins             |
| `/reload`            | Hot-reload plugins              |
| `/quit`              | Exit                            |


Everything else goes to the AI.

---

## Writing Plugins

Drop a `.py` file in `zentra/plugins/`:

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

Auto-loads on startup. Use `/reload` to pick up new plugins without restarting.

---

## Configuration

Edit `zentra/config.py` or create a `.env` file:

```
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_VISION_MODEL=llava:13b
DISCORD_BOT_TOKEN=your_token_here
```


| Setting               | Default          | Controls                      |
| --------------------- | ---------------- | ----------------------------- |
| `OLLAMA_MODEL`        | qwen2.5-coder:7b | Chat model                    |
| `OLLAMA_VISION_MODEL` | llava:13b        | Vision model                  |
| `BASE_FOLDER`         | ./zentra_files   | Where files are saved         |
| `MEMORY_DEPTH`        | 8                | Conversation turns remembered |
| `ALLOWED_USER_IDS`    | []               | Discord whitelist             |


---

## Security Notes

- Never commit `credentials.json`, `google_token.pickle`, or `.env`
- All AI runs locally via Ollama (web_search uses DuckDuckGo, no data stored)
- Shell commands run real commands on your machine
- Discord access is whitelisted via `ALLOWED_USER_IDS`

---

## Troubleshooting


| Problem                      | Fix                                                                                      |
| ---------------------------- | ---------------------------------------------------------------------------------------- |
| "Cannot connect to Ollama"   | Start Ollama: `ollama serve` or check system tray                                        |
| "Model not found"            | `ollama pull qwen2.5-coder:7b`                                                           |
| `No module named 'discord'`  | `pip install discord.py`                                                                 |
| `No module named 'rich'`     | `pip install rich`                                                                       |
| `No module named 'pyserial'` | `pip install pyserial`                                                                   |
| `No module named 'PySide6'`  | `pip install PySide6`                                                                    |
| Calendar circular import     | No `calendar.py` in project root, only in `zentra/actions/`                              |
| Screen automation fails      | `pip install pyautogui Pillow` (Linux: `sudo apt install python3-tk scrot`)              |
| Clipboard not working        | `pip install pyperclip` (Linux: `sudo apt install xclip`)                                |
| Gmail/Calendar disabled      | Install google libs + add `credentials.json` to root                                     |
| arduino-cli not found        | [Install from official docs](https://arduino.github.io/arduino-cli/latest/installation/) |
| Bot shows "Not authorised"   | Add your Discord user ID to `ALLOWED_USER_IDS`                                           |
| GUI won't launch             | `pip install PySide6`                                                                    |


---

## Contributing

The monorepo structure makes contributing simple.

**Add an action:**

1. Create `zentra/actions/your_feature.py`
2. Add `elif` in `zentra/dispatcher.py`
3. Add to system prompt in `zentra/config.py`

**Add a plugin:** drop a `.py` file in `zentra/plugins/`. No core changes.

---

Built by [@Brobuiltathing & @Planeman653](https://github.com/Brobuiltathing)