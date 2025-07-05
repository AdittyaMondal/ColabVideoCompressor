import signal
import sys
import asyncio
from . import *
from .devtools import *
from .worker import *
from .funcn import *
from .stuff import *
from datetime import datetime as dt
import time

LOGS.info("Starting Enhanced Video Compressor Bot...")
LOGS.info(f"GPU Detection: {GPU_TYPE}")
LOGS.info(f"Running in Colab: {IS_COLAB}")

# Graceful shutdown handler
def signal_handler(signum, frame):
    LOGS.info("Received shutdown signal, cleaning up...")
    bot_state.clear_working()
    cleanup_temp_files()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

######## Connect ########

try:
    bot.start(bot_token=BOT_TOKEN)
    LOGS.info("Bot connected successfully")
except Exception as er:
    LOGS.error(f"Bot connection failed: {er}")
    sys.exit(1)

####### GENERAL CMDS ########

@bot.on(events.NewMessage(pattern="/start"))
async def _(e):
    await start(e)

@bot.on(events.NewMessage(pattern="/ping"))
async def _(e):
    await up(e)

@bot.on(events.NewMessage(pattern="/help"))
async def _(e):
    await help(e)

@bot.on(events.NewMessage(pattern="/link"))
async def _(e):
    await dl_link(e)

@bot.on(events.NewMessage(pattern="/status"))
async def _(e):
    if str(e.sender_id) not in OWNER:
        return
    
    queue_size = bot_state.queue_size()
    is_working = bot_state.is_working()
    
    status_msg = (
        f"🤖 **Bot Status**\n\n"
        f"🔧 **Working**: {'Yes' if is_working else 'No'}\n"
        f"📋 **Queue Size**: {queue_size}/{MAX_QUEUE_SIZE}\n"
        f"🚀 **GPU Type**: {GPU_TYPE.upper()}\n"
        f"☁️ **Colab Mode**: {'Yes' if IS_COLAB else 'No'}\n"
        f"⏰ **Uptime**: {ts(int((dt.now() - uptime).total_seconds() * 1000))}"
    )
    await e.reply(status_msg)

######## Callbacks #########

@bot.on(events.CallbackQuery(data=re.compile(b"stats(.*)")))
async def _(e):
    await stats(e)

@bot.on(events.CallbackQuery(data=re.compile(b"skip(.*)")))
async def _(e):
    await skip(e)

@bot.on(events.CallbackQuery(data=re.compile(b"ihelp")))
async def _(e):
    await ihelp(e)

@bot.on(events.CallbackQuery(data=re.compile(b"beck")))
async def _(e):
    await beck(e)

########## Direct ###########

@bot.on(events.NewMessage(pattern="/eval"))
async def _(e):
    await eval(e)

@bot.on(events.NewMessage(pattern="/bash"))
async def _(e):
    await bash(e)

@bot.on(events.NewMessage(pattern="/usage"))
async def _(e):
    await usage(e)

########## AUTO ###########

@bot.on(events.NewMessage(incoming=True, func=lambda e: e.media and str(e.sender_id) in OWNER))
async def _(e):
    await encod(e)

def cleanup_files(file_paths):
    """Safely cleanup a list of files."""
    for file_path in file_paths:
        if file_path and os.path.exists(file_path) and validate_file_path(file_path):
            try:
                os.remove(file_path)
                LOGS.info(f"Cleaned up file: {file_path}")
            except Exception as e:
                LOGS.error(f"Failed to clean up {file_path}: {e}")

async def queue_processor():
    """Enhanced queue processing with better error handling"""
    while True:
        try:
            if not bot_state.is_working() and bot_state.queue_size() > 0:
                user_id = int(OWNER.split()[0])
                key, item = bot_state.pop_first_queue_item()
                if not key or not item:
                    await asyncio.sleep(3)
                    continue

                bot_state.set_working(True)
                e = await bot.send_message(user_id, f"`🔄 Processing item #{bot_state.queue_size() + 1} from queue...`")
                s = dt.now()
                dl = None

                try:
                    if isinstance(item, str): # URL download
                        await process_link_download(e, key, item)
                    else: # File download
                        await process_file_encoding(e)
                    
                except Exception as r:
                    LOGS.error(f"Queue processing error for key {key}: {r}")
                    await e.edit(f"❌ **Queue Error**\nAn unexpected error occurred while processing an item from the queue.\n`{str(r)}`")
                    bot_state.clear_working()
                    cleanup_files([dl] if 'dl' in locals() else [])
            
            else:
                await asyncio.sleep(3)
                
        except Exception as err:
            LOGS.error(f"Fatal queue processor error: {err}")
            bot_state.clear_working()
            await asyncio.sleep(5)

########### Start ############

async def main():
    """Main bot execution with proper error handling"""
    try:
        cleanup_task = asyncio.create_task(periodic_cleanup())
        queue_task = asyncio.create_task(queue_processor())
        
        LOGS.info("Bot has started successfully.")
        LOGS.info(f"Using {GPU_TYPE.upper()} for encoding")
        
        await startup()
        
        await asyncio.gather(cleanup_task, queue_task)
        
    except KeyboardInterrupt:
        LOGS.info("Bot stopped by user")
    except Exception as e:
        LOGS.error(f"Bot crashed: {e}")
    finally:
        bot_state.clear_working()
        cleanup_temp_files()
        LOGS.info("Bot shutdown complete")

if __name__ == "__main__":
    with bot:
        bot.loop.run_until_complete(main())