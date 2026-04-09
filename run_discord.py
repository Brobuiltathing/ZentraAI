from frontends.discord.main import client
from zentra.config import DISCORD_BOT_TOKEN, APP_NAME, APP_VERSION
from zentra.logger import log

if __name__ == "__main__":
    if DISCORD_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Set DISCORD_BOT_TOKEN in zentra/config.py or .env")
        raise SystemExit(1)
    log.info(f"Starting {APP_NAME} v{APP_VERSION} (Discord)...")
    client.run(DISCORD_BOT_TOKEN)
