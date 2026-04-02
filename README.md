# ZentraAI

ZentraAI is a modular AI assistant that integrates with Gmail, Google Calendar, weather APIs, and your local system.  
It can create files, modify content, manage directory structures, control applications, read system information, and act as a fully capable personal assistant.  
You can run it locally with a GUI or remotely through Discord.  
Supports both **Ollama (local models)** and **API-based models** (Claude and OpenAI).

---

## Features

- Create files and manipulate file contents  
- Generate full folder structures  
- Open and close applications  
- View system specs and usage  
- Summarise Gmail  
- Manipulate Google Calendar  
- Personal AI assistant functions  
- GUI or Discord modes  
- Uses either local LLMs (Ollama) or cloud APIs (Claude/OpenAI)  
- More features coming soon  

---

## Installing(Ollama Discord Git Only)

To download the Ollama Discord Git:

```bash 
git clone https://github.com/Brobuiltathing/ZentraAI.git
```

### Pip Installations
```bash 
pip install discord.py requests psutil google-auth google-auth-oauthlib google-api-python-client
```

---

## Integration Modes

### 1. Ollama + Discord
Local LLM + Discord bot interface.  
Allows remote PC control (requires secure setup steps).

### 2. Ollama + GUI
Local GUI interface.  
Easiest setup but only runs on the user's PC.

### 3. API + Discord
Uses Claude or OpenAI through API + Discord bot.  
Allows remote control without a local LLM.

### 4. API + GUI
Uses Claude or OpenAI via API with a local GUI.  
Does not require Ollama installed.

---

## Ollama Setup

**Download Ollama:**  
https://ollama.com/download

**Official Website:**  
https://ollama.com/

After installing, download a model:
Then insert the model name into the config section in the code.

### Recommended Models
- **Qwen 7B** — strong coding performance  
- **Llama 3.2 Vision** — best for PC control and vision tasks  
- **DeepSeek 14B** — excellent reasoning if your hardware supports it  

---

## API Setup

### Claude (Anthropic)
**Website:**  
https://www.anthropic.com/

**Claude Console / API Keys:**  
https://console.anthropic.com/

### OpenAI
**Website:**  
https://openai.com/

**OpenAI API Keys:**  
https://platform.openai.com/account/api-keys

Generate your key and paste it into the config field in the program.

---

## Discord Bot Setup

To use ZentraAI with Discord, you need to create a bot and invite it to your server.

### 1. Create a Discord Application
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** and give it a name (e.g. `ZentraAI`)
3. Navigate to the **Bot** tab on the left sidebar
4. Click **Add Bot** → confirm with **Yes, do it!**

### 2. Enable Required Intents
Still on the **Bot** tab, scroll down to **Privileged Gateway Intents** and enable:
- **Message Content Intent** — allows the bot to read message content
- **Server Members Intent** — optional, but useful for member-based features

Click **Save Changes**.

### 3. Get Your Bot Token
On the **Bot** tab, click **Reset Token** and copy the token shown.  
Paste this token into the config field in the program.

```bash 
DISCORD_BOT_TOKEN = "#########################################" 
```

 ^^This line looks like this^^

> ⚠️ Never share or commit your bot token — treat it like a password.

### 4. Invite the Bot to Your Server
1. Go to the **OAuth2 → URL Generator** tab
2. Under **Scopes**, select `bot`
3. Under **Bot Permissions**, select:
   - `Send Messages`
   - `Read Message History`
4. Copy the generated URL, paste it into your browser, and select your server to invite the bot

The bot will now appear in your server and can read and send messages once the program is running.

---

## Google API Setup (Gmail & Google Calendar)

ZentraAI uses a `credentials.json` file to authenticate with Gmail and Google Calendar via OAuth 2.0.

### 1. Create a Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project → New Project**, give it a name, and click **Create**
3. Make sure your new project is selected in the top bar

### 2. Enable the Required APIs
1. Go to **APIs & Services → Library**
2. Search for and enable:
   - **Gmail API**
   - **Google Calendar API**

### 3. Configure the OAuth Consent Screen
1. Go to **APIs & Services → OAuth consent screen**
2. Select **External** and click **Create**
3. Fill in the required fields (App name, support email) and click **Save and Continue**
4. Skip the Scopes step for now and click **Save and Continue**
5. Add your Google account as a **Test User**, then click **Save and Continue**

### 4. Create OAuth 2.0 Credentials
1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Select **Desktop app** as the application type
4. Give it a name and click **Create**
5. Click **Download JSON** on the confirmation screen

### 5. Place the credentials.json File
Rename the downloaded file to `credentials.json` and place it in the **same folder as `main.py`**.

```
ZentraAI/
├── main.py
├── credentials.json   ← must be here
└── ...
```

> ⚠️ Never commit `credentials.json` to a public repository. Add it to your `.gitignore` file.

On first run, a browser window will open asking you to log in and authorise access. After completing this, a `token.json` file will be generated automatically and reused for future runs.
