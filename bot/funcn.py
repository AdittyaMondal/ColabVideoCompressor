#    This file is part of the CompressorQueue distribution.
#    Copyright (c) 2021 Danish_00
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3.
#
#    This program is distributed in the hope that it will be useful, but
#    WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#    General Public License for more details.
#
# License can be found in <
# https://github.com/1Danish-00/CompressorQueue/blob/main/License> .

import asyncio
import threading
import time
import math
import os
import signal
import psutil
import requests
from pathlib import Path
from collections import defaultdict
from . import *
from .config import *

class ThreadSafeState:
    """Thread-safe state management for the bot"""
    def __init__(self):
        self._lock = threading.RLock()
        self._working = []
        self._queue = {}
        self._ok = {}
        self._retry_count = defaultdict(int)
        
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

# Global state instance
bot_state = ThreadSafeState()

# Legacy compatibility
WORKING = bot_state._working
QUEUE = bot_state._queue
OK = bot_state._ok

uptime = dt.now()

# Setup directories
def setup_directories():
    """Setup required directories with proper permissions"""
    dirs = ["downloads/", "encode/", "thumb/"]
    if IS_COLAB and COLAB_OUTPUT_DIR:
        dirs.append(COLAB_OUTPUT_DIR)
    
    for dir_path in dirs:
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            if IS_COLAB:
                os.chmod(dir_path, 0o755)

setup_directories()

# Download thumbnail
try:
    if not os.path.exists("thumb.jpg"):
        os.system(f"wget {THUMB} -O thumb.jpg")
except Exception as e:
    LOGS.info(f"Failed to download thumbnail: {e}")

tgp_client = TelegraphPoster(use_api=True, telegraph_api_url=TELEGRAPH_API)

def create_api_token():
    retries = 10
    telgrph_tkn_err_msg = (
        "Couldn't not successfully create api token required by telegraph to work"
        "\nAs such telegraph is therefore disabled!"
    )
    while retries:
        try:
            tgp_client.create_api_token("Mediainfo")
            break
        except (requests.exceptions.ConnectionError, ConnectionError) as e:
            retries -= 1
            if not retries:
                LOGS.info(telgrph_tkn_err_msg)
                break
            time.sleep(1)

create_api_token()

def validate_file_path(file_path):
    """Validate file path to prevent directory traversal attacks"""
    try:
        # Resolve the path and check if it's within allowed directories
        resolved_path = os.path.realpath(file_path)
        allowed_dirs = [
            os.path.realpath("downloads/"),
            os.path.realpath("encode/"),
            os.path.realpath("thumb/")
        ]
        
        if IS_COLAB and COLAB_OUTPUT_DIR:
            allowed_dirs.append(os.path.realpath(COLAB_OUTPUT_DIR))
        
        return any(resolved_path.startswith(allowed_dir) for allowed_dir in allowed_dirs)
    except Exception:
        return False

def get_file_size_mb(file_path):
    """Get file size in MB"""
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except Exception:
        return 0

def stdr(seconds: int) -> str:
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if len(str(minutes)) == 1:
        minutes = "0" + str(minutes)
    if len(str(hours)) == 1:
        hours = "0" + str(hours)
    if len(str(seconds)) == 1:
        seconds = "0" + str(seconds)
    dur = (
        ((str(hours) + ":") if hours else "00:")
        + ((str(minutes) + ":") if minutes else "00:")
        + ((str(seconds)) if seconds else "")
    )
    return dur

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
        + ((str(milliseconds) + "ms, ") if milliseconds else "")
    )
    return tmp[:-2]

def hbs(size):
    if not size:
        return ""
    power = 2**10
    raised_to_pow = 0
    dict_power_n = {0: "B", 1: "K", 2: "M", 3: "G", 4: "T", 5: "P"}
    while size > power:
        size /= power
        raised_to_pow += 1
    return str(round(size, 2)) + " " + dict_power_n[raised_to_pow] + "B"

No_Flood = {}

async def progress(current, total, event, start, type_of_ps, file=None):
    now = time.time()
    if No_Flood.get(event.chat_id):
        if No_Flood[event.chat_id].get(event.id):
            if (now - No_Flood[event.chat_id][event.id]) < 1.1:
                return
        else:
            No_Flood[event.chat_id].update({event.id: now})
    else:
        No_Flood.update({event.chat_id: {event.id: now}})
    
    diff = time.time() - start
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        time_to_completion = round((total - current) / speed) * 1000
        progress_str = "`[{0}{1}] {2}%`\n\n".format(
            "".join(["●" for i in range(math.floor(percentage / 5))]),
            "".join(["○" for i in range(20 - math.floor(percentage / 5))]),
            round(percentage, 2),
        )
        
        # Add GPU info if available
        gpu_info = f"\n`🚀 GPU: {GPU_TYPE.upper()}`" if GPU_TYPE != "cpu" else ""
        
        tmp = (
            progress_str
            + "`{0} of {1}`\n\n`✦ Speed: {2}/s`\n\n`✦ ETA: {3}`{4}\n\n".format(
                hbs(current),
                hbs(total),
                hbs(speed),
                ts(time_to_completion),
                gpu_info
            )
        )
        if file:
            await event.edit(
                "`✦ {}`\n\n`File Name: {}`\n\n{}".format(type_of_ps, file, tmp)
            )
        else:
            await event.edit("`✦ {}`\n\n{}".format(type_of_ps, tmp))

async def info(file, event=None):
    try:
        if not validate_file_path(file):
            LOGS.warning(f"Invalid file path: {file}")
            return None
            
        author = (await bot.get_me()).first_name
        author_url = f"https://t.me/{((await bot.get_me()).username)}"
        out = pymediainfo.MediaInfo.parse(file, output="HTML", full=False)
        if len(out) > 65536:
            out = (
                out[:65430]
                + "<strong>...<strong><br><br><strong>(TRUNCATED DUE TO CONTENT EXCEEDING MAX LENGTH)<strong>"
            )
        retries = 10
        while retries:
            try:
                page = tgp_client.post(
                    title="Mediainfo",
                    author=author,
                    author_url=author_url,
                    text=out,
                )
                break
            except (requests.exceptions.ConnectionError, ConnectionError) as e:
                retries -= 1
                if not retries:
                    raise e
                await asyncio.sleep(1)
        return page["url"]
    except Exception as e:
        LOGS.error(f"Error generating mediainfo: {e}")
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
        
        # Validate file paths
        if not validate_file_path(dl) or not validate_file_path(out):
            LOGS.warning("Invalid file paths in skip operation")
            return
        
        if bot_state.get_queue_item(int(id)):
            bot_state.clear_working()
            bot_state.pop_queue_item(int(id))
        
        await e.delete()
        
        # Safe file removal
        for file_path in [dl, out]:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                LOGS.error(f"Error removing file {file_path}: {e}")
        
        # Kill ffmpeg processes safely
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] == "ffmpeg":
                    proc.terminate()
                    proc.wait(timeout=5)
        except Exception as e:
            LOGS.error(f"Error terminating ffmpeg processes: {e}")
            
    except Exception as e:
        LOGS.error(f"Error in skip function: {e}")

async def fast_download(e, download_url, filename=None):
    def progress_callback(d, t):
        return (
            asyncio.get_event_loop().create_task(
                progress(
                    d,
                    t,
                    e,
                    time.time(),
                    f"Downloading from {download_url}",
                )
            ),
        )

    async def _maybe_await(value):
        if inspect.isawaitable(value):
            return await value
        else:
            return value

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url, timeout=None) as response:
                if not filename:
                    filename = download_url.rpartition("/")[-1]
                
                # Sanitize filename
                filename = "".join(c for c in filename if c.isalnum() or c in "._-")
                filename = os.path.join("downloads", filename)
                
                # Validate file path
                if not validate_file_path(filename):
                    raise ValueError("Invalid download path")
                
                total_size = int(response.headers.get("content-length", 0)) or None
                
                # Check file size limit
                if total_size and total_size > MAX_FILE_SIZE * 1024 * 1024:
                    raise ValueError(f"File too large: {hbs(total_size)} > {MAX_FILE_SIZE}MB")
                
                downloaded_size = 0
                with open(filename, "wb") as f:
                    async for chunk in response.content.iter_chunked(1024):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            await _maybe_await(
                                progress_callback(downloaded_size, total_size)
                            )
                return filename
    except Exception as e:
        LOGS.error(f"Download failed: {e}")
        raise

def cleanup_temp_files():
    """Clean up temporary files older than 1 hour"""
    try:
        for directory in ["downloads/", "encode/"]:
            if os.path.exists(directory):
                for file_path in Path(directory).glob("*"):
                    if file_path.is_file():
                        file_age = time.time() - file_path.stat().st_mtime
                        if file_age > 3600:  # 1 hour
                            file_path.unlink()
                            LOGS.info(f"Cleaned up old file: {file_path}")
    except Exception as e:
        LOGS.error(f"Error during cleanup: {e}")

# Schedule cleanup every hour
async def periodic_cleanup():
    while True:
        await asyncio.sleep(3600)  # 1 hour
        cleanup_temp_files()
