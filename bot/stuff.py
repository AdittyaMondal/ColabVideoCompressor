from .worker import *

async def up(event):
    """Ping command handler"""
    if not event.is_private:
        return
    stt = dt.now()
    msg = await event.reply("Pinging...")
    ed = dt.now()
    ms = (ed - stt).microseconds / 1000
    p = f"🏓 **Pong!**\n⚡ `{ms}ms`\n🚀 Using {GPU_TYPE.upper()}"
    await msg.edit(p)

async def usage(event):
    """System usage command handler"""
    if str(event.sender_id) not in OWNER:
        return
    
    total, used, free = shutil.disk_usage(".")
    cpuUsage = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    upload = hbs(psutil.net_io_counters().bytes_sent)
    down = hbs(psutil.net_io_counters().bytes_recv)
    
    stats = (
        "**💻 System Statistics**\n\n"
        f"**CPU Usage:** `{cpuUsage}%`\n"
        f"**RAM Usage:** `{memory}%`\n"
        f"**Storage Used:** `{disk}%`\n"
        f"**Upload:** `{upload}`\n"
        f"**Download:** `{down}`\n\n"
        "**Storage Info**\n"
        f"**Total:** `{hbs(total)}`\n"
        f"**Used:** `{hbs(used)}`\n"
        f"**Free:** `{hbs(free)}`\n"
    )
    
    if GPU_TYPE != "cpu":
        try:
            gpu_util = subprocess.check_output(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"]).decode().strip()
            gpu_mem = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"]).decode().strip().split(", ")
            stats += (
                "\n**GPU Info**\n"
                f"**GPU Usage:** `{gpu_util}%`\n"
                f"**GPU Memory:** `{gpu_mem[0]}MB / {gpu_mem[1]}MB`"
            )
        except:
            pass
    
    await event.reply(stats)

async def start(event):
    """Start command handler"""
    await event.reply(
        "**🚀 Enhanced Video Compressor Bot**\n\n"
        "A powerful bot that can compress videos with GPU acceleration.\n"
        "Features:\n"
        "• GPU-accelerated encoding\n"
        "• Queue system for multiple files\n"
        "• Real-time progress tracking\n"
        "• Supports URL downloads\n"
        "• Automatic hardware detection",
        buttons=[
            [Button.inline("ℹ️ HELP", data="ihelp")],
            [Button.inline("📊 STATUS", data="stats")]
        ],
    )

async def help(event):
    """Help command handler"""
    await event.reply(
        "**📖 Help Guide**\n\n"
        "**Commands:**\n"
        "• `/start` - Start the bot\n"
        "• `/help` - Show this help message\n"
        "• `/ping` - Check bot response\n"
        "• `/status` - Show bot status\n"
        "• `/link` - Process video from URL\n"
        "• `/usage` - Show system stats\n\n"
        "**How to use:**\n"
        "1. Send or forward a video file\n"
        "2. Bot will compress it using GPU (if available)\n"
        "3. Multiple files are handled via queue\n"
        "4. Progress and stats are shown in real-time"
    )

async def ihelp(event):
    """Inline help button handler"""
    await event.edit(
        "**📖 Help Guide**\n\n"
        "**Commands:**\n"
        "• `/start` - Start the bot\n"
        "• `/help` - Show this help message\n"
        "• `/ping` - Check bot response\n"
        "• `/status` - Show bot status\n"
        "• `/link` - Process video from URL\n"
        "• `/usage` - Show system stats\n\n"
        "**Features:**\n"
        "• GPU-accelerated encoding\n"
        "• Queue system\n"
        "• Progress tracking\n"
        "• URL support\n"
        "• Hardware detection",
        buttons=[Button.inline("🔙 BACK", data="beck")]
    )

async def beck(event):
    """Back button handler"""
    await event.edit(
        "**🚀 Enhanced Video Compressor Bot**\n\n"
        "A powerful bot that can compress videos with GPU acceleration.\n"
        "Features:\n"
        "• GPU-accelerated encoding\n"
        "• Queue system for multiple files\n"
        "• Real-time progress tracking\n"
        "• Supports URL downloads\n"
        "• Automatic hardware detection",
        buttons=[
            [Button.inline("ℹ️ HELP", data="ihelp")],
            [Button.inline("📊 STATUS", data="stats")]
        ],
    )
