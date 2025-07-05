import asyncio
import threading
import time
import math
import os
import re
from pathlib import Path
from collections import defaultdict
from . import *
from .config import *
from datetime import datetime as dt
from telethon import errors, Button
from html_telegraph_poster import TelegraphPoster
import pymediainfo
import psutil
import aiohttp

class ThreadSafeState:
    """Thread-safe state management for the bot."""
    def __init__(self):
        self._lock = threading.RLock()
        self._working = []
        self._queue = {}
        self._ok = {}
        self._retry_count = defaultdict(int)
        self.last_progress_update = {}
    
    def is_working(self):
        with self._lock: return bool(self._working)
    def set_working(self, value=True):
        with self._lock:
            if value: self._working.append(1)
            else: self._working.clear()
    def clear_working(self):
        with self._lock: self._working.clear()
    def add_to_queue(self, key, value):
        with self._lock:
            if len(self._queue) >= MAX_QUEUE_SIZE: return False
            self._queue[key] = value
            return True
    def pop_first_queue_item(self):
        with self._lock:
            if self._queue:
                key = list(self._queue.keys())[0]
                return key, self._queue.pop(key)
            return None, None
    def queue_size(self):
        with self._lock: return len(self._queue)
    def is_in_queue(self, key):
        with self._lock: return key in self._queue
    def add_ok(self, data):
        with self._lock:
            self._ok[len(self._ok)] = data
            return str(len(self._ok) - 1)
    def get_ok(self, key):
        with self._lock: return self._ok.get(int(key))

bot_state = ThreadSafeState()
uptime = dt.now()

def setup_directories():
    """Setup required directories with proper permissions"""
    dirs = ["downloads/", "encode/", "thumb/", "temp", "logs"]
    if IS_COLAB and COLAB_OUTPUT_DIR: dirs.append(COLAB_OUTPUT_DIR)
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)

setup_directories()

def validate_file_path(file_path):
    try:
        if not file_path: return False
        resolved_path = Path(file_path).resolve()
        base_path = Path("/content").resolve()
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
        if not wh: return
        out, dl, _ = wh.split(";")
        bot_state.clear_working()
        await e.edit("`Process cancelled by user.`", buttons=None)
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] == "ffmpeg" and dl in ' '.join(proc.info.get('cmdline', [])):
                proc.terminate()
        
        for f in [dl, out]:
            if f and os.path.exists(f): os.remove(f)
    except Exception as ex:
        LOGS.error(f"Error in skip function: {ex}")

async def fast_download(e, download_url, filename=None):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    start_time = time.time()
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(download_url, timeout=None, allow_redirects=True) as response:
            if response.status != 200:
                raise Exception(f"Download failed: Status {response.status}")

            if not filename:
                content_disposition = response.headers.get('Content-Disposition')
                if content_disposition and (res := re.findall("filename=\"?(.+)\"?", content_disposition)):
                    filename = res[0]
                else:
                    filename = download_url.rpartition("/")[-1].split('?')[0]
            
            filepath = os.path.join("downloads", "".join(c for c in filename if c.isalnum() or c in "._- "))
            if not validate_file_path(filepath):
                raise ValueError("Invalid download path")
            
            total_size = int(response.headers.get("content-length", 0))
            if total_size and total_size > MAX_FILE_SIZE * 1024 * 1024:
                raise ValueError(f"File too large: {hbs(total_size)} > {MAX_FILE_SIZE}MB")
            
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
    for directory in ["downloads/", "encode/", "temp/"]:
        if not os.path.isdir(directory): continue
        for file_path in Path(directory).glob("*"):
            try:
                if file_path.is_file() and (time.time() - file_path.stat().st_mtime > 3600):
                    file_path.unlink()
            except (OSError, FileNotFoundError) as e:
                LOGS.warning(f"Failed to cleanup old file {file_path}: {e}")

async def periodic_cleanup():
    while True:
        await asyncio.sleep(3600)
        cleanup_temp_files()