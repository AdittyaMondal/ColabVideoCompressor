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
from pathlib import Path
from collections import defaultdict
from . import *
from .config import *
from datetime import datetime as dt

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

# Global state instance
bot_state = ThreadSafeState()

# Legacy compatibility (best to phase these out)
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
                os.chmod(dir_path, 0o777) # Use 777 for colab to avoid permission issues

setup_directories()

# Download thumbnail
try:
    if not os.path.exists("thumb.jpg"):
        # The original link was dead, using a new one
        os.system(f"wget {THUMB} -O thumb.jpg")
except Exception as e:
    LOGS.info(f"Failed to download thumbnail: {e}")

tgp_client = TelegraphPoster(use_api=True)
if TELEGRAPH_API:
    tgp_client.telegraph_api_url = TELEGRAPH_API

def create_api_token():
    retries = 5
    while retries:
        try:
            tgp_client.create_api_token("Mediainfo")
            LOGS.info("Telegraph API token created.")
            break
        except Exception as e:
            retries -= 1
            LOGS.warning(f"Couldn't create Telegraph API token, retrying... ({e})")
            if not retries:
                LOGS.error("Failed to create Telegraph API token. Mediainfo will not be posted.")
                break
            time.sleep(2)

create_api_token()

def validate_file_path(file_path):
    """Validate file path to prevent directory traversal attacks"""
    try:
        resolved_path = Path(file_path).resolve()
        allowed_dirs = [
            Path("downloads/").resolve(),
            Path("encode/").resolve(),
            Path("thumb/").resolve()
        ]
        
        if IS_COLAB and COLAB_OUTPUT_DIR:
            allowed_dirs.append(Path(COLAB_OUTPUT_DIR).resolve())
        
        return any(resolved_path.is_relative_to(allowed_dir) for allowed_dir in allowed_dirs)
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
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

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
    return tmp[:-2] if tmp else "0s"

def hbs(size):
    if not size:
        return ""
    power = 1024
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power and n < len(power_labels) -1 :
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}"

async def progress(current, total, event, start, type_of_ps, file=None):
    """A reliable progress bar that updates every 3 seconds to avoid flood waits."""
    message_id = event.id
    now = time.time()
    
    # Update only if 3 seconds have passed since the last update for this message
    if message_id in bot_state.last_progress_update and (now - bot_state.last_progress_update[message_id]) < 3:
        if current != total:
             return
    
    bot_state.last_progress_update[message_id] = now
    
    diff = time.time() - start
    if diff == 0:
        return # Avoid division by zero
        
    percentage = current * 100 / total
    speed = current / diff
    time_to_completion = round((total - current) / speed) if speed > 0 else 0
    
    progress_str = "`[{0}{1}] {2}%`\n".format(
        "".join(["●" for i in range(math.floor(percentage / 10))]),
        "".join(["○" for i in range(10 - math.floor(percentage / 10))]),
        round(percentage, 2),
    )
    
    gpu_info = f"\n`🚀 GPU: {GPU_TYPE.upper()}`" if GPU_TYPE != "cpu" else ""
    
    tmp = (
        progress_str
        + "`{0} of {1}`\n"
        + "`Speed: {2}/s`\n"
        + "`ETA: {3}`{4}\n".format(
            hbs(current),
            hbs(total),
            hbs(speed),
            ts(time_to_completion * 1000),
            gpu_info
        )
    )
    
    try:
        if file:
            await event.edit(
                "`{}`\n`File: {}`\n\n{}".format(type_of_ps, file, tmp)
            )
        else:
            await event.edit("`{}`\n\n{}".format(type_of_ps, tmp))
    except errors.MessageNotModifiedError:
        pass # Ignore if the message content is the same
    except errors.FloodWaitError as e:
        LOGS.warning(f"Flood wait of {e.seconds}s in progress bar. Sleeping.")
        await asyncio.sleep(e.seconds + 1)
    except Exception as e:
        LOGS.error(f"Error in progress bar update: {e}")

async def info(file, event=None):
    try:
        if not validate_file_path(file):
            LOGS.warning(f"Invalid file path for mediainfo: {file}")
            return None
            
        me = await bot.get_me()
        author = me.first_name
        author_url = f"https://t.me/{me.username}"
        
        out = pymediainfo.MediaInfo.parse(file, output="HTML", full=False)
        if len(out) > 65536:
            out = (
                out[:65430]
                + "<strong>...<strong><br><br><strong>(TRUNCATED DUE TO CONTENT EXCEEDING MAX LENGTH)<strong>"
            )

        retries = 3
        while retries:
            try:
                page = tgp_client.post(
                    title="Mediainfo",
                    author=author,
                    author_url=author_url,
                    text=out,
                )
                return page["url"]
            except Exception as e:
                retries -= 1
                LOGS.warning(f"Mediainfo post failed, retrying... ({e})")
                if not retries:
                    LOGS.error(f"Failed to post mediainfo: {e}")
                    return None
                await asyncio.sleep(2)
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
        
        if not validate_file_path(dl) or not validate_file_path(out):
            LOGS.warning("Invalid file paths in skip operation")
            return
        
        if bot_state.get_queue_item(int(id)):
            bot_state.pop_queue_item(int(id))
        
        bot_state.clear_working()
        await e.edit("`Process cancelled by user.`", buttons=None)
        
        for file_path in [dl, out]:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as ex:
                LOGS.error(f"Error removing file {file_path}: {ex}")
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] == "ffmpeg" and dl in ' '.join(proc.info['cmdline']):
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except psutil.NoSuchProcess:
                    pass
                except Exception as ex:
                    LOGS.error(f"Error terminating ffmpeg process {proc.pid}: {ex}")

    except Exception as ex:
        LOGS.error(f"Error in skip function: {ex}")

async def fast_download(e, download_url, filename=None):
    """Fixed fast_download with User-Agent header."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    start_time = time.time()
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(download_url, timeout=None, allow_redirects=True) as response:
            if response.status != 200:
                raise Exception(f"Download failed with status: {response.status} {response.reason}")

            if not filename:
                filename = download_url.rpartition("/")[-1]
            
            filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            filepath = os.path.join("downloads", filename)
            
            if not validate_file_path(filepath):
                raise ValueError("Invalid download path")
            
            total_size = int(response.headers.get("content-length", 0))
            if not total_size:
                LOGS.warning("Content-Length not found. Progress will not be shown accurately.")

            if total_size and total_size > MAX_FILE_SIZE * 1024 * 1024:
                raise ValueError(f"File too large: {hbs(total_size)} > {MAX_FILE_SIZE}MB")
            
            downloaded_size = 0
            with open(filepath, "wb") as f:
                async for chunk in response.content.iter_chunked(1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size:
                           await progress(downloaded_size, total_size, e, start_time, "Downloading Link")

            return filepath

def cleanup_temp_files():
    """Clean up temporary files older than 1 hour"""
    try:
        for directory in ["downloads/", "encode/"]:
            if os.path.exists(directory):
                for file_path in Path(directory).glob("*"):
                    try:
                        if file_path.is_file():
                            file_age = time.time() - file_path.stat().st_mtime
                            if file_age > 3600:  # 1 hour
                                file_path.unlink()
                                LOGS.info(f"Cleaned up old file: {file_path}")
                    except Exception as e:
                        LOGS.error(f"Error cleaning up file {file_path}: {e}")
    except Exception as e:
        LOGS.error(f"Error during scheduled cleanup: {e}")

async def periodic_cleanup():
    while True:
        await asyncio.sleep(3600)  # 1 hour
        cleanup_temp_files()