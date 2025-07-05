import asyncio
import threading
import time
import math
import os
import signal
import psutil
import requests
import aiohttp
import inspect
import re
from pathlib import Path
from collections import defaultdict
from . import *
from .config import *
from datetime import datetime as dt
from telethon import errors, Button
from html_telegraph_poster import TelegraphPoster
import pymediainfo

class ThreadSafeState:
    """Thread-safe state management for the bot"""
    def __init__(self):
        self._lock = threading.RLock()
        self._working = []
        self._queue = {}
        self._ok = {}
        self._retry_count = defaultdict(int)
        self.last_progress_update = {}

    def is_working(self):
        with self._lock:
            return bool(self._working)
    
    def set_working(self, value=True):
        with self._lock:
            if value:
                self._working.append(1)
            else:
                self._working.clear()
    
    def clear_working(self):
        with self._lock:
            self._working.clear()
    
    def add_to_queue(self, key, value):
        with self._lock:
            if len(self._queue) >= MAX_QUEUE_SIZE:
                return False
            self._queue[key] = value
            return True
    
    def get_queue_item(self, key):
        with self._lock:
            return self._queue.get(key)
    
    def pop_queue_item(self, key):
        with self._lock:
            return self._queue.pop(key, None)
    
    def get_first_queue_item(self):
        with self._lock:
            if self._queue:
                key = list(self._queue.keys())[0]
                return key, self._queue[key]
            return None, None
    
    def pop_first_queue_item(self):
        with self._lock:
            if self._queue:
                key = list(self._queue.keys())[0]
                return key, self._queue.pop(key)
            return None, None
    
    def queue_size(self):
        with self._lock:
            return len(self._queue)
    
    def is_in_queue(self, key):
        with self._lock:
            return key in self._queue
    
    def add_ok(self, data):
        with self._lock:
            self._ok[len(self._ok)] = data
            return str(len(self._ok) - 1)
    
    def get_ok(self, key):
        with self._lock:
            return self._ok.get(int(key))
    
    def increment_retry(self, key):
        with self._lock:
            self._retry_count[key] += 1
            return self._retry_count[key]
    
    def get_retry_count(self, key):
        with self._lock:
            return self._retry_count.get(key, 0)
    
    def clear_retry(self, key):
        with self._lock:
            self._retry_count.pop(key, None)

bot_state = ThreadSafeState()
uptime = dt.now()

def setup_directories():
    """Setup required directories with proper permissions"""
    dirs = ["downloads/", "encode/", "thumb/"]
    if IS_COLAB and COLAB_OUTPUT_DIR:
        dirs.append(COLAB_OUTPUT_DIR)
    
    for dir_path in dirs:
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            if IS_COLAB:
                os.chmod(dir_path, 0o777)

setup_directories()

try:
    if not os.path.exists("thumb.jpg"):
        os.system(f"wget {THUMB} -O thumb.jpg")
except Exception as e:
    LOGS.info(f"Failed to download thumbnail: {e}")

tgp_client = TelegraphPoster(use_api=True)
if TELEGRAPH_API:
    tgp_client.telegraph_api_url = TELEGRAPH_API

def validate_file_path(file_path):
    try:
        resolved_path = Path(file_path).resolve()
        allowed_dirs = [Path(d).resolve() for d in ["downloads/", "encode/", "thumb/"]]
        if IS_COLAB and COLAB_OUTPUT_DIR:
            allowed_dirs.append(Path(COLAB_OUTPUT_DIR).resolve())
        return any(resolved_path.is_relative_to(d) for d in allowed_dirs)
    except Exception:
        return False

def get_file_size_mb(file_path):
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except Exception:
        return 0

def ts(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
        ((str(days) + "d, ") if days else "")
        + ((str(hours) + "h, ") if hours else "")
        + ((str(minutes) + "m, ") if minutes else "")
        + ((str(seconds) + "s, ") if seconds else "")
    )
    return tmp[:-2] if tmp else "0s"

def hbs(size):
    if not size:
        return ""
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
    
    if message_id in bot_state.last_progress_update and (now - bot_state.last_progress_update[message_id]) < 3:
        if current != total:
             return
    
    bot_state.last_progress_update[message_id] = now
    
    diff = time.time() - start
    if diff == 0:
        return
        
    percentage = current * 100 / total
    speed = current / diff if diff > 0 else 0
    time_to_completion = round((total - current) / speed) if speed > 0 else 0
    
    progress_str = "`[{0}{1}] {2}%`\n".format(
        "".join(["●" for _ in range(math.floor(percentage / 10))]),
        "".join(["○" for _ in range(10 - math.floor(percentage / 10))]),
        round(percentage, 2),
    )
    
    gpu_info = f"\n`🚀 GPU: {GPU_TYPE.upper()}`" if GPU_TYPE != "cpu" else ""
    
    tmp = (
        f"{progress_str}"
        f"`{hbs(current)} of {hbs(total)}`\n"
        f"`Speed: {hbs(speed)}/s`\n"
        f"`ETA: {ts(time_to_completion * 1000)}`{gpu_info}\n"
    )
    
    try:
        text = f"`{type_of_ps}`\n"
        if file:
            text += f"`File: {file}`\n"
        text += f"\n{tmp}"
        await event.edit(text)
    except errors.MessageNotModifiedError:
        pass
    except errors.FloodWaitError as e:
        LOGS.warning(f"Flood wait of {e.seconds}s in progress bar. Sleeping.")
        await asyncio.sleep(e.seconds + 1)
    except Exception as e:
        LOGS.error(f"Error in progress bar update: {e}")

async def info(file, event=None):
    try:
        if not validate_file_path(file):
            return None
        me = await bot.get_me()
        author, author_url = me.first_name, f"https://t.me/{me.username}"
        out = pymediainfo.MediaInfo.parse(file, output="HTML", full=False)
        page = tgp_client.post(title="Mediainfo", author=author, author_url=author_url, text=out)
        return page["url"]
    except Exception:
        return None

def code(data):
    return bot_state.add_ok(data)

def decode(key):
    return bot_state.get_ok(key)

async def skip(e):
    try:
        wah = e.pattern_match.group(1).decode("UTF-8")
        wh = decode(wah)
        if not wh:
            return
        out, dl, id = wh.split(";")
        if not validate_file_path(dl) or not validate_file_path(out):
            return
        if bot_state.get_queue_item(int(id)):
            bot_state.pop_queue_item(int(id))
        bot_state.clear_working()
        await e.edit("`Process cancelled by user.`", buttons=None)
        for f in [dl, out]:
            if os.path.exists(f):
                os.remove(f)
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] == "ffmpeg" and dl in ' '.join(proc.info['cmdline']):
                proc.terminate()
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
                       await progress(downloaded_size, total_size, e, start_time, "Downloading Link")
            return filepath

def cleanup_temp_files():
    try:
        for directory in ["downloads/", "encode/"]:
            for file_path in Path(directory).glob("*"):
                if file_path.is_file() and (time.time() - file_path.stat().st_mtime > 3600):
                    file_path.unlink()
    except Exception as e:
        LOGS.error(f"Error during scheduled cleanup: {e}")

async def periodic_cleanup():
    while True:
        await asyncio.sleep(3600)
        cleanup_temp_files()