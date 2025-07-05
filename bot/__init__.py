from telethon import TelegramClient

# Import from config which is now the base for LOGS and settings
from .config import (
    LOGS, APP_ID, API_HASH, BOT_TOKEN, OWNER, GPU_TYPE, V_CODEC, V_PRESET, V_QP,
    V_SCALE, V_FPS, A_BITRATE, WATERMARK_ENABLED, FILENAME_TEMPLATE,
    AUTO_DELETE_ORIGINAL, ENABLE_HARDWARE_ACCELERATION
)

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
    LOGS.info("--- Configuration ---")
    LOGS.info(f"GPU Detection: {GPU_TYPE.upper()} (HW Accel: {'Enabled' if ENABLE_HARDWARE_ACCELERATION else 'Disabled'})")
    LOGS.info(f"Encoding: {V_CODEC}, Preset: {V_PRESET}, Quality: {V_QP}")
    LOGS.info(f"Output: {V_SCALE}p @ {V_FPS}fps, Audio: {A_BITRATE}")
    LOGS.info(f"Watermark: {'Enabled' if WATERMARK_ENABLED else 'Disabled'}")
    LOGS.info(f"Filename Template: {FILENAME_TEMPLATE}")
    LOGS.info(f"Auto-delete Original: {AUTO_DELETE_ORIGINAL}")
    LOGS.info("---------------------")

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