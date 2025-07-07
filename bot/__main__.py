import signal
import sys
import asyncio
import re
from datetime import datetime as dt
from telethon import events

# Import from the correct, specific modules
from .config import LOGS, BOT_TOKEN, OWNER, MAX_QUEUE_SIZE, GPU_TYPE
from . import bot, startup
from .funcn import bot_state, uptime, cleanup_temp_files, periodic_cleanup, ts, skip, stats
from .worker import (
    process_link_download, process_file_encoding, encod, dl_link,
    toggle_upload_mode, custom_encoder, toggle_watermark
)
from .stuff import start, up, help, usage, ihelp, beck
from .settings_menu import settings_menu
from .settings_handlers import settings_handlers

LOGS.info("Starting Enhanced Video Compressor Bot...")

# Graceful shutdown handler
def signal_handler(signum, frame):
    LOGS.info("Received shutdown signal, cleaning up...")
    if bot_state.is_working():
        bot_state.clear_working()
    cleanup_temp_files()
    LOGS.info("Cleanup complete. Exiting.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Connect to Telegram
try:
    bot.start(bot_token=BOT_TOKEN)
    LOGS.info("Bot connected successfully")
except Exception as er:
    LOGS.error(f"Bot connection failed: {er}")
    sys.exit(1)

# --- Command Handlers ---

@bot.on(events.NewMessage(pattern="/start"))
async def _(e): await start(e)

@bot.on(events.NewMessage(pattern="/ping"))
async def _(e): await up(e)

@bot.on(events.NewMessage(pattern="/help"))
async def _(e): await help(e)

@bot.on(events.NewMessage(pattern="/link"))
async def _(e): await dl_link(e)

@bot.on(events.NewMessage(pattern="/toggle_upload_mode"))
async def _(e): await toggle_upload_mode(e)

@bot.on(events.NewMessage(pattern="/watermark"))
async def _(e): await toggle_watermark(e)

@bot.on(events.NewMessage(pattern="/custom"))
async def _(e): await custom_encoder(e)

@bot.on(events.NewMessage(pattern="/settings"))
async def _(e): await settings_menu.show_main_menu(e, e.sender_id)

@bot.on(events.NewMessage(pattern="/status"))
async def _(e):
    if str(e.sender_id) not in OWNER.split(): return
    status_msg = (
        f"🤖 **Bot Status**\n\n"
        f"🔧 **Working**: {'Yes' if bot_state.is_working() else 'No'}\n"
        f"📋 **Queue Size**: {bot_state.queue_size()}/{MAX_QUEUE_SIZE}\n"
        f"🚀 **GPU Type**: {GPU_TYPE.upper()}\n"
        f"⏰ **Uptime**: {ts(int((dt.now() - uptime).total_seconds() * 1000))}"
    )
    await e.reply(status_msg)

@bot.on(events.NewMessage(pattern="/usage"))
async def _(e): await usage(e)

# --- Callback Handlers ---

@bot.on(events.CallbackQuery(data=re.compile(b"stats(.*)")))
async def _(e): await stats(e)

@bot.on(events.CallbackQuery(data=re.compile(b"skip(.*)")))
async def _(e): await skip(e)

@bot.on(events.CallbackQuery(data=re.compile(b"ihelp")))
async def _(e): await ihelp(e)

@bot.on(events.CallbackQuery(data=re.compile(b"beck")))
async def _(e): await beck(e)

@bot.on(events.CallbackQuery())
async def _(e):
    """Handle settings and other callback queries"""
    try:
        data = e.data.decode()
        if data.startswith("settings_") or data.startswith("preset_") or data.startswith("custom_") or \
           data.startswith("output_") or data.startswith("preview_") or data.startswith("advanced_") or \
           data.startswith("thumb_") or data.startswith("set_") or data.startswith("confirm_"):
            await settings_handlers.handle_settings_callback(e)
        else:
            # Let other handlers process their callbacks
            pass
    except Exception as er:
        LOGS.error(f"Settings callback error: {er}", exc_info=True)

# --- Text Input Handler for Settings ---

@bot.on(events.NewMessage(incoming=True, func=lambda e: not e.media and not e.text.startswith('/') and str(e.sender_id) in OWNER.split()))
async def _(e):
    """Handle text input for settings configuration"""
    if await settings_handlers.handle_text_input(e, e.sender_id):
        return  # Text was processed as settings input

# --- Media Handler ---

@bot.on(events.NewMessage(incoming=True, func=lambda e: e.media and str(e.sender_id) in OWNER.split()))
async def _(e): await encod(e)

# --- Queue Processor ---

async def queue_processor():
    while True:
        try:
            if not bot_state.is_working() and bot_state.queue_size() > 0:
                key, original_event = bot_state.pop_first_queue_item()
                if not original_event:
                    await asyncio.sleep(3)
                    continue
                
                LOGS.info(f"Processing item '{key}' from queue.")

                if hasattr(original_event, 'text') and original_event.text and original_event.text.startswith('/link'):
                    parts = original_event.text.split(maxsplit=2)
                    if len(parts) < 2:
                        await original_event.reply("❌ Invalid link command in queue. Skipping.")
                        continue
                    link = parts[1]
                    name = parts[2] if len(parts) > 2 else ""
                    await process_link_download(original_event, link, name)
                elif hasattr(original_event, 'media'):
                    await process_file_encoding(original_event)
                else:
                    LOGS.warning(f"Unknown item type in queue: {key}. Skipping.")
            
            await asyncio.sleep(3)
        except Exception as err:
            LOGS.error(f"Queue processor error: {err}", exc_info=True)
            if bot_state.is_working():
                bot_state.clear_working()
            await asyncio.sleep(5)

# --- Main Execution ---

async def main():
    try:
        cleanup_task = asyncio.create_task(periodic_cleanup())
        queue_task = asyncio.create_task(queue_processor())
        
        await startup()
        
        LOGS.info("Bot has started successfully and is listening for commands.")
        
        await asyncio.gather(cleanup_task, queue_task)
        
    except Exception as e:
        LOGS.error(f"Bot crashed in main loop: {e}", exc_info=True)
    finally:
        bot_state.clear_working()
        cleanup_temp_files()
        LOGS.info("Bot shutdown complete.")

if __name__ == "__main__":
    with bot:
        bot.loop.run_until_complete(main())
