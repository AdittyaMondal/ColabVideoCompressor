import asyncio
import threading
import time
import math
import os
import re
from pathlib import Path
from collections import OrderedDict
from datetime import datetime as dt
import psutil
import aiohttp
import pymediainfo
from telethon import errors, Button
from html_telegraph_poster import TelegraphPoster

# Import explicitly from config module
from .config import (
    LOGS, MAX_QUEUE_SIZE, IS_COLAB, COLAB_OUTPUT_DIR, GPU_TYPE,
    MAX_FILE_SIZE, PROGRESS_UPDATE_INTERVAL, DEFAULT_UPLOAD_MODE
)

class BotState:
    """State management for the bot."""
    def __init__(self):
        self._is_working = False
        self._queue = OrderedDict()
        self._ok = {}  # For callback data
        self.last_progress_update = {}
        self.user_upload_modes = {}
    
    def is_working(self): return self._is_working
    def set_working(self, value=True): self._is_working = value
    def clear_working(self): self._is_working = False
    
    def add_to_queue(self, key, value):
        with threading.Lock():
            if len(self._queue) >= MAX_QUEUE_SIZE: return False
            if key in self._queue: return False # Prevent duplicates
            self._queue[key] = value
            return True
    
    def pop_first_queue_item(self):
        with threading.Lock():
            if self._queue:
                return self._queue.popitem(last=False)
            return None, None

    def queue_size(self): return len(self._queue)
    def is_in_queue(self, key): return key in self._queue
    
    def add_ok(self, data):
        key = str(len(self._ok))
        self._ok[key] = data
        return key
        
    def get_ok(self, key):
        return self._ok.get(str(key))

    def set_upload_mode(self, user_id, mode):
        self.user_upload_modes[user_id] = mode

    def get_upload_mode(self, user_id):
        return self.user_upload_modes.get(user_id, DEFAULT_UPLOAD_MODE)

bot_state = BotState()
uptime = dt.now()

def setup_directories():
    """Setup required directories"""
    dirs = ["downloads/", "encode/", "thumb/", "temp", "logs"]
    if IS_COLAB and COLAB_OUTPUT_DIR: dirs.append(COLAB_OUTPUT_DIR)
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)

setup_directories()

def validate_file_path(file_path):
    """Ensure file path is within the project directory to prevent traversal attacks."""
    try:
        if not file_path: return False
        base_path = Path.cwd().resolve()
        resolved_path = Path(file_path).resolve()
        return str(resolved_path).startswith(str(base_path))
    except Exception:
        return False

def ts(milliseconds: int) -> str:
    seconds, _ = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ""
    if days: tmp += f"{days}d, "
    if hours: tmp += f"{hours}h, "
    if minutes: tmp += f"{minutes}m, "
    if seconds or not tmp: tmp += f"{seconds}s"
    return tmp.strip(', ')

def hbs(size):
    if not size: return "0 B"
    power = 1024
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size >= power and n < len(power_labels) - 1:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}"

async def progress(current, total, event, start, type_of_ps, file=None):
    message_id = event.id
    now = time.time()
    
    if message_id in bot_state.last_progress_update and (now - bot_state.last_progress_update[message_id]) < PROGRESS_UPDATE_INTERVAL:
        if current != total: return
    
    bot_state.last_progress_update[message_id] = now
    
    diff = now - start
    if diff == 0: return
        
    percentage = current * 100 / total
    speed = current / diff
    eta = ts(round((total - current) / speed) * 1000) if speed > 0 else "N/A"
    
    progress_bar = "●" * math.floor(percentage / 10) + "○" * (10 - math.floor(percentage / 10))
    gpu_info = f"\n`🚀 GPU: {GPU_TYPE.upper()}`" if GPU_TYPE != "cpu" else ""
    
    text = (
        f"`{type_of_ps}`\n"
        f"`File: {file}`\n\n"
        f"`[{progress_bar}] {percentage:.2f}%`\n"
        f"`{hbs(current)} of {hbs(total)}`\n"
        f"`Speed: {hbs(speed)}/s`\n"
        f"`ETA: {eta}`{gpu_info}\n"
    )
    
    try:
        await event.edit(text)
    except (errors.MessageNotModifiedError, errors.MessageIdInvalidError):
        pass
    except errors.FloodWaitError as e:
        await asyncio.sleep(e.seconds + 2)
    except Exception as e:
        LOGS.error(f"Progress bar error: {e}")

async def info(file_path):
    try:
        if not validate_file_path(file_path):
            LOGS.warning(f"Skipping mediainfo for invalid path: {file_path}")
            return None
        return pymediainfo.MediaInfo.parse(file_path, output="HTML", full=False)
    except Exception as e:
        LOGS.error(f"Pymediainfo failed for {file_path}: {e}")
        return None

def code(data):
    return bot_state.add_ok(data)

def decode(key):
    return bot_state.get_ok(key)

async def skip(e):
    try:
        wah = e.pattern_match.group(1).decode("UTF-8")
        wh = decode(wah)
        if not wh: return await e.answer("Process already cancelled or finished.", alert=True)
        
        out, dl, _ = wh.split(";")
        bot_state.clear_working()
        await e.edit("`⛔ Process cancelled by user.`", buttons=None)
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] == "ffmpeg" and dl in ' '.join(proc.info.get('cmdline', [])):
                LOGS.info(f"Terminating ffmpeg process {proc.pid} for {dl}")
                proc.terminate()
        
        for f in [dl, out]:
            if f and os.path.exists(f) and validate_file_path(f):
                try: os.remove(f)
                except OSError as ex: LOGS.error(f"Error removing file {f} on skip: {ex}")
    except Exception as ex:
        LOGS.error(f"Error in skip function: {ex}", exc_info=True)
        await e.answer(f"Error cancelling: {ex}", alert=True)

async def stats(e):
    """Callback handler for the stats button during compression."""
    try:
        wah = e.pattern_match.group(1).decode("UTF-8")
        wh = decode(wah)
        if not wh:
            return await e.answer("Status expired or invalid.", alert=True)
        
        out_path, dl_path, _ = wh.split(";")
        
        original_size = os.path.getsize(dl_path) if os.path.exists(dl_path) and validate_file_path(dl_path) else 0
        current_size = os.path.getsize(out_path) if os.path.exists(out_path) and validate_file_path(out_path) else 0
        
        reduction = (100 - (current_size / original_size * 100)) if original_size > 0 else 0
        
        await e.answer(
            f"📊 Compression Stats 📊\n\n"
            f"Original: {hbs(original_size)}\n"
            f"Compressed: {hbs(current_size)}\n"
            f"Reduction: {reduction:.2f}%",
            alert=True
        )
    except Exception as ex:
        LOGS.error(f"Error getting stats: {ex}", exc_info=True)
        await e.answer(f"Error getting stats: {ex}", alert=True)

async def fast_download(e, download_url, filename=None):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    start_time = time.time()
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(download_url, timeout=None, allow_redirects=True) as response:
            if response.status != 200:
                raise Exception(f"Download failed: Status {response.status}")

            total_size = int(response.headers.get("content-length", 0))
            if total_size and total_size > MAX_FILE_SIZE * 1024 * 1024:
                raise ValueError(f"File too large: {hbs(total_size)} > {MAX_FILE_SIZE}MB")

            if not filename:
                content_disposition = response.headers.get('Content-Disposition')
                if content_disposition and (res := re.findall("filename=\"?(.+)\"?", content_disposition)):
                    filename = res[0]
                else:
                    filename = os.path.basename(download_url.split('?')[0])

            filepath = os.path.join("downloads", "".join(c for c in filename if c.isalnum() or c in "._- "))
            if not validate_file_path(filepath):
                raise ValueError("Invalid download path detected")
            
            downloaded_size = 0
            with open(filepath, "wb") as f:
                async for chunk in response.content.iter_chunked(1024 * 1024):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size:
                       await progress(downloaded_size, total_size, e, start_time, "Downloading Link", filename)
            return filepath

def cleanup_temp_files():
    """Clean up temporary files older than 1 hour"""
    LOGS.info("Running periodic cleanup of temporary files...")
    now = time.time()
    for directory in ["downloads/", "encode/", "temp/"]:
        if not os.path.isdir(directory): continue
        for file_path in Path(directory).glob("*"):
            try:
                if file_path.is_file() and (now - file_path.stat().st_mtime > 3600):
                    LOGS.info(f"Deleting old temp file: {file_path}")
                    file_path.unlink()
            except (OSError, FileNotFoundError) as e:
                LOGS.warning(f"Failed to cleanup old file {file_path}: {e}")

async def periodic_cleanup():
    while True:
        await asyncio.sleep(3600) # Run every hour
        cleanup_temp_files()