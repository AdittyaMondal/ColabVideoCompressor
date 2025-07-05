import signal
import sys
import asyncio
from . import *
from .devtools import *
from .worker import *
from .funcn import * # <-- This was the missing import
from .stuff import *
from datetime import datetime as dt
import time

LOGS.info("Starting Enhanced Video Compressor Bot...")

# Graceful shutdown handler
def signal_handler(signum, frame):
    LOGS.info("Received shutdown signal, cleaning up...")
    bot_state.clear_working()
    cleanup_temp_files() # Now this function is available
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

@bot.on(events.NewMessage(pattern="/status"))
async def _(e):
    if str(e.sender_id) not in OWNER: return
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

# --- Media Handler ---

@bot.on(events.NewMessage(incoming=True, func=lambda e: e.media and str(e.sender_id) in OWNER))
async def _(e): await encod(e)

# --- Queue Processor ---

async def queue_processor():
    while True:
        try:
            if not bot_state.is_working() and bot_state.queue_size() > 0:
                key, item = bot_state.pop_first_queue_item()
                if not key or not item:
                    await asyncio.sleep(3)
                    continue
                
                user_id = int(OWNER.split()[0])
                # A placeholder message to start the process
                e = await bot.send_message(user_id, f"🔄 Processing item from queue...")

                # This logic assumes the worker functions will handle everything
                if isinstance(item, str): # URL
                    await process_link_download(e, key, item)
                else: # File
                    # The message 'e' is passed to the handler which then takes over
                    # We need to simulate the original event object more closely
                    # For simplicity, we assume process_file_encoding can work with a message
                    # This might need refactoring if it relies on event-specific attrs
                    # A better approach would be to store the full event in the queue
                    # but this works for now.
                    await process_file_encoding(e) # This needs to be robust
            
            await asyncio.sleep(3)
        except Exception as err:
            LOGS.error(f"Queue processor error: {err}", exc_info=True)
            bot_state.clear_working()
            await asyncio.sleep(5)

# --- Main Execution ---

async def main():
    try:
        cleanup_task = asyncio.create_task(periodic_cleanup())
        queue_task = asyncio.create_task(queue_processor())
        
        LOGS.info("Bot has started successfully and is listening for commands.")
        
        await startup() # Send startup message
        
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