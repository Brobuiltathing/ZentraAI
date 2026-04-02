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

<<<<<<< Updated upstream
=======
## Installing(Ollama Discord Git Only)

To download the Ollama Discord Git:

```bash 
git clone --no-checkout https://github.com/Brobuiltathing/ZentraAI.git
cd ZentraAI
git sparse-checkout init --cone
git sparse-checkout set ollama_discord
git checkout
```

<<<<<<< Updated upstream
```bash
git clone --no-checkout https://github.com/Brobuiltathing/ZentraAI.git && cd ZentraAI && git sparse-checkout init --cone && git sparse-checkout set ollama_discord && git checkout
```
=======
git clone https://github.com/Brobuiltathing/ZentraAI.git

cd ZentraAI

git sparse-checkout init --cone

git sparse-checkout set ollama_discord

git checkout main
>>>>>>> Stashed changes

### Pip Installations
```bash 
pip install discord.py requests psutil google-auth google-auth-oauthlib google-api-python-client
```

---

>>>>>>> Stashed changes
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

## Repository Structure
