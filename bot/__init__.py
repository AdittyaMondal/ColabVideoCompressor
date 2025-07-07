from telethon import TelegramClient

# Import from config which is now the base for LOGS and settings
from .config import LOGS, APP_ID, API_HASH, BOT_TOKEN, OWNER, GPU_TYPE

try:
    if not all([APP_ID, API_HASH, BOT_TOKEN, OWNER]):
        LOGS.critical("One or more required environment variables (APP_ID, API_HASH, BOT_TOKEN, OWNER) are missing.")
        exit(1)
    bot = TelegramClient(None, APP_ID, API_HASH)
except Exception as e:
    LOGS.error("Could not create Bot client.", exc_info=True)
    exit(1)

async def startup():
    """Send startup message to bot owners and log config"""
    # Initialize settings manager
    from .settings import settings_manager
    import sys

    print("⚙️ Initializing bot configuration...")  # Immediate output
    sys.stdout.flush()
    LOGS.info("--- Configuration ---")
    print(f"🖥️ GPU Detection: {GPU_TYPE.upper()}")  # Immediate output
    LOGS.info(f"GPU Detection: {GPU_TYPE.upper()}")
    print("🎛️ Settings System: Dynamic settings enabled")  # Immediate output
    LOGS.info(f"Settings System: Dynamic settings enabled")
    default_preset = settings_manager.get_setting('active_preset') or 'balanced'
    print(f"🎯 Default Preset: {default_preset}")  # Immediate output
    LOGS.info(f"Default Preset: {default_preset}")
    LOGS.info("---------------------")
    sys.stdout.flush()

    owners = [owner_id.strip() for owner_id in OWNER.split()]
    for x in owners:
        if not x: continue
        try:
            await bot.send_message(
                int(x),
                "**🚀 Enhanced Video Compressor Bot Started**\n"
                f"🖥️ Using {GPU_TYPE.upper()} for encoding"
            )
        except Exception as e:
            LOGS.warning(f"Failed to send startup message to {x}: {e}")