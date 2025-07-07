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
from .settings import settings_manager

print("🚀 Starting Enhanced Video Compressor Bot...")  # Immediate output
LOGS.info("Starting Enhanced Video Compressor Bot...")
import sys
sys.stdout.flush()  # Force flush

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
    print("🔗 Connecting to Telegram...")  # Immediate output
    sys.stdout.flush()
    bot.start(bot_token=BOT_TOKEN)
    print("✅ Bot connected successfully")  # Immediate output
    LOGS.info("Bot connected successfully")
    sys.stdout.flush()
except Exception as er:
    print(f"❌ Bot connection failed: {er}")  # Immediate output
    LOGS.error(f"Bot connection failed: {er}")
    sys.stdout.flush()
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
async def _(e):
    """Handle settings command with detailed logging and error handling"""
    try:
        LOGS.info(f"Settings command received from user {e.sender_id}")

        # --- FIX: Added explicit check for OWNER variable ---
        if not OWNER:
            LOGS.warning("OWNER variable is not set. Settings command is disabled.")
            return await e.reply("❌ **Configuration Error:**\nBot owner not configured. The `/settings` command is disabled.")

        owner_list = OWNER.split()
        if str(e.sender_id) not in owner_list:
            LOGS.info(f"User {e.sender_id} is not an owner. Owner list: {owner_list}")
            return await e.reply("❌ You don't have permission to access settings.\n\nPlease ensure your User ID is listed in the `OWNER` variable in the bot's configuration.")

        LOGS.info("User is owner, proceeding to show settings menu")

        # Test basic message sending first
        LOGS.info("Testing basic message reply...")
        test_msg = await e.reply("🔄 Loading settings menu...")
        LOGS.info("Basic reply successful, proceeding with settings menu")

        if not hasattr(settings_menu, 'settings_manager') or settings_menu.settings_manager is None:
            LOGS.error("Settings manager not initialized")
            return await test_msg.edit("❌ Settings system not initialized. Please restart the bot and try again.")

        LOGS.info("Settings manager is initialized, displaying main menu")
        await settings_menu.show_main_menu(test_msg, e.sender_id)
        LOGS.info("Settings menu displayed successfully")
    except Exception as er:
        LOGS.error(f"Settings command error: {er}", exc_info=True)
        try:
            await e.reply(f"❌ Error accessing settings: {str(er)}\n\nPlease check bot logs or contact the developer.")
        except Exception as reply_error:
            LOGS.error(f"Failed to send error reply: {reply_error}")

@bot.on(events.NewMessage(pattern="/status"))
async def _(e):
    if not OWNER or str(e.sender_id) not in OWNER.split(): return
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

@bot.on(events.NewMessage(pattern="/debug"))
async def _(e):
    """Debug command to check user permissions and settings"""
    try:
        user_id = e.sender_id
        is_owner = OWNER and str(user_id) in OWNER.split()

        debug_info = (
            f"🔍 **Debug Information**\n\n"
            f"**Your User ID**: `{user_id}`\n"
            f"**Are you an Owner?**: `{'✅ Yes' if is_owner else '❌ No'}`\n"
            f"**Configured Owner List**: `{OWNER.split() if OWNER else 'Not configured'}`\n"
            f"**Settings Manager**: `{'✅ Initialized' if hasattr(settings_menu, 'settings_manager') and settings_menu.settings_manager else '❌ Not initialized'}`"
        )

        await e.reply(debug_info)
    except Exception as er:
        LOGS.error(f"Debug command error: {er}", exc_info=True)
        await e.reply(f"❌ Debug error: {er}")

@bot.on(events.NewMessage(pattern="/test"))
async def _(e):
    """Simple test command to verify bot responsiveness"""
    await e.reply("✅ Bot is responding! Test successful.")

@bot.on(events.NewMessage(pattern="/test_buttons"))
async def _(e):
    """Test button functionality"""
    try:
        from telethon import Button
        LOGS.info("Testing button creation...")

        test_buttons = [
            [Button.inline("Test Button 1", data="test_1")],
            [Button.inline("Test Button 2", data="test_2")]
        ]

        await e.reply("🧪 **Button Test**\n\nTesting inline buttons:", buttons=test_buttons)
        LOGS.info("Button test successful")
    except Exception as er:
        LOGS.error(f"Button test error: {er}", exc_info=True)
        await e.reply(f"❌ Button test failed: {str(er)}")

@bot.on(events.NewMessage(pattern="/test_settings"))
async def _(e):
    """Test settings functionality"""
    try:
        user_id = e.sender_id
        LOGS.info(f"Testing settings for user {user_id}")

        # Test setting a value
        success = settings_manager.set_setting("advanced_settings", "watermark_enabled", True, user_id)
        LOGS.info(f"Set watermark_enabled=True: {success}")

        # Test getting the value
        value = settings_manager.get_setting("advanced_settings", "watermark_enabled", user_id)
        LOGS.info(f"Got watermark_enabled: {value}")

        # Test upload mode
        upload_mode = settings_manager.get_setting("output_settings", "default_upload_mode", user_id)
        LOGS.info(f"Upload mode: {upload_mode}")

        # Test thumbnail settings
        thumb_settings = settings_manager.get_setting("thumbnail_settings", user_id=user_id)
        LOGS.info(f"Thumbnail settings: {thumb_settings}")

        await e.reply(f"🧪 **Settings Test**\n\n"
                     f"**Watermark Enabled**: `{value}`\n"
                     f"**Upload Mode**: `{upload_mode}`\n"
                     f"**Thumbnail Settings**: `{thumb_settings}`\n\n"
                     f"Check logs for detailed info.")

    except Exception as er:
        LOGS.error(f"Settings test error: {er}", exc_info=True)
        await e.reply(f"❌ Settings test failed: {str(er)}")

# --- Callback Handlers ---

@bot.on(events.CallbackQuery(data=re.compile(b"stats(.*)")))
async def _(e): await stats(e)

@bot.on(events.CallbackQuery(data=re.compile(b"skip(.*)")))
async def _(e): await skip(e)

@bot.on(events.CallbackQuery(data=re.compile(b"ihelp")))
async def _(e): await ihelp(e)

@bot.on(events.CallbackQuery(data=re.compile(b"test_(.*)")))
async def _(e):
    """Handle test button callbacks"""
    try:
        data = e.data.decode()
        await e.answer(f"✅ Button {data} clicked successfully!")
        LOGS.info(f"Test button callback: {data}")
    except Exception as er:
        LOGS.error(f"Test button callback error: {er}")
        await e.answer("❌ Button test failed")

@bot.on(events.CallbackQuery(data=re.compile(b"beck")))
async def _(e): await beck(e)

@bot.on(events.CallbackQuery())
async def _(e):
    """Handle settings and other callback queries"""
    try:
        data = e.data.decode()
        LOGS.info(f"Callback received: {data} from user {e.sender_id}")

        if data.startswith("settings_") or data.startswith("preset_") or data.startswith("custom_") or \
           data.startswith("output_") or data.startswith("preview_") or data.startswith("advanced_") or \
           data.startswith("thumb_") or data.startswith("set_") or data.startswith("confirm_"):
            LOGS.info(f"Processing settings callback: {data}")
            await settings_handlers.handle_settings_callback(e)
        else:
            # Let other handlers process their callbacks
            LOGS.info(f"Non-settings callback: {data}")
            pass
    except Exception as er:
        LOGS.error(f"Callback error: {er}", exc_info=True)
        try:
            await e.answer("❌ Error processing button", alert=True)
        except:
            pass

# --- Text Input Handler for Settings ---

@bot.on(events.NewMessage(incoming=True, func=lambda e: not e.media and not e.text.startswith('/') and OWNER and str(e.sender_id) in OWNER.split()))
async def _(e):
    """Handle text input for settings configuration"""
    if await settings_handlers.handle_text_input(e, e.sender_id):
        return  # Text was processed as settings input

# --- Media Handler ---

@bot.on(events.NewMessage(incoming=True, func=lambda e: e.media and OWNER and str(e.sender_id) in OWNER.split()))
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

        print("🎉 Bot has started successfully and is listening for commands.")  # Immediate output
        LOGS.info("Bot has started successfully and is listening for commands.")
        sys.stdout.flush()
        
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