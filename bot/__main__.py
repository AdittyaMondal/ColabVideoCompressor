import signal
import sys
from . import *
from .devtools import *

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

@bot.on(events.callbackquery.CallbackQuery(data=re.compile(b"stats(.*)")))
async def _(e):
    await stats(e)

@bot.on(events.callbackquery.CallbackQuery(data=re.compile(b"skip(.*)")))
async def _(e):
    await skip(e)

@bot.on(events.callbackquery.CallbackQuery(data=re.compile("ihelp")))
async def _(e):
    await ihelp(e)

@bot.on(events.callbackquery.CallbackQuery(data=re.compile("beck")))
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

@bot.on(events.NewMessage(incoming=True))
async def _(e):
    await encod(e)

async def queue_processor():
    """Enhanced queue processing with better error handling"""
    while True:
        try:
            if not bot_state.is_working() and bot_state.queue_size() > 0:
                user = int(OWNER.split()[0])
                e = await bot.send_message(user, "`🔄 Processing Queue Files...`")
                
                key, item = bot_state.get_first_queue_item()
                if not key or not item:
                    await asyncio.sleep(3)
                    continue
                
                bot_state.set_working(True)
                s = dt.now()
                
                try:
                    if isinstance(item, str):
                        # URL download
                        dl = await fast_download(e, key, item)
                    else:
                        # File download
                        dl, file = item
                        tt = time.time()
                        dl = "downloads/" + dl
                        
                        # Sanitize filename
                        dl = "downloads/" + "".join(c for c in dl.split("/")[-1] if c.isalnum() or c in "._-")
                        
                        with open(dl, "wb") as f:
                            await download_file(
                                client=bot,
                                location=file,
                                out=f,
                                progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                                    progress(d, t, e, tt, "Downloading")
                                ),
                            )
                    
                    # Check file size
                    file_size_mb = get_file_size_mb(dl)
                    if file_size_mb > MAX_FILE_SIZE:
                        await e.edit(f"❌ File too large: {file_size_mb:.1f}MB > {MAX_FILE_SIZE}MB")
                        cleanup_files([dl])
                        bot_state.pop_first_queue_item()
                        bot_state.clear_working()
                        continue
                    
                    await process_compression(e, dl, s)
                    bot_state.pop_first_queue_item()
                    bot_state.clear_working()
                    
                except Exception as r:
                    LOGS.error(f"Queue processing error: {r}")
                    retry_count = bot_state.increment_retry(key)
                    
                    if retry_count >= MAX_RETRIES:
                        await e.edit(f"❌ Failed after {MAX_RETRIES} attempts: {str(r)}")
                        bot_state.pop_first_queue_item()
                        bot_state.clear_retry(key)
                    else:
                        await e.edit(f"⚠️ Attempt {retry_count} failed, retrying...")
                        await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    
                    bot_state.clear_working()
                    if 'dl' in locals():
                        cleanup_files([dl])
            else:
                await asyncio.sleep(3)
                
        except Exception as err:
            LOGS.error(f"Queue processor error: {err}")
            bot_state.clear_working()
            await asyncio.sleep(5)

########### Start ############

async def main():
    """Main bot execution with proper error handling"""
    try:
        # Start periodic cleanup
        cleanup_task = asyncio.create_task(periodic_cleanup())
        
        # Start queue processor
        queue_task = asyncio.create_task(queue_processor())
        
        LOGS.info("Bot has started successfully.")
        LOGS.info(f"Using {GPU_TYPE.upper()} for encoding")
        
        # Send startup notification
        await startup()
        
        # Keep the bot running
        await asyncio.gather(cleanup_task, queue_task)
        
    except KeyboardInterrupt:
        LOGS.info("Bot stopped by user")
    except Exception as e:
        LOGS.error(f"Bot crashed: {e}")
    finally:
        # Cleanup on exit
        bot_state.clear_working()
        cleanup_temp_files()
        LOGS.info("Bot shutdown complete")

if __name__ == "__main__":
    with bot:
        bot.loop.run_until_complete(main())
