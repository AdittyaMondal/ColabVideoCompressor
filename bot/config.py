import os
import re
import subprocess
from decouple import config
from logging import INFO, basicConfig, getLogger

# --- LOGGING SETUP ---
# Define logger here to be importable by all other modules without circular deps
basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s",
    level=INFO,
    datefmt="%d-%b-%y %H:%M:%S"
)
LOGS = getLogger("CompressorBot")

# --- CORE API & BOT SETTINGS ---
APP_ID = config("APP_ID", cast=int)
API_HASH = config("API_HASH")
BOT_TOKEN = config("BOT_TOKEN")
OWNER = config("OWNER", default="")

# --- FILE & QUEUE SETTINGS ---
MAX_FILE_SIZE = config("MAX_FILE_SIZE", default=4000, cast=int)
MAX_QUEUE_SIZE = config("MAX_QUEUE_SIZE", default=15, cast=int)
FILENAME_TEMPLATE = config("FILENAME_TEMPLATE", default="{original_name} [{resolution} {codec}]")
AUTO_DELETE_ORIGINAL = config("AUTO_DELETE_ORIGINAL", default=False, cast=bool)

# --- HARDWARE & PERFORMANCE ---
ENABLE_HARDWARE_ACCELERATION = config("ENABLE_HARDWARE_ACCELERATION", default=True, cast=bool)
PROGRESS_UPDATE_INTERVAL = config("PROGRESS_UPDATE_INTERVAL", default=5, cast=int)

def detect_gpu():
    if not ENABLE_HARDWARE_ACCELERATION:
        return "cpu"
    try:
        if subprocess.run(["nvidia-smi"], capture_output=True, check=False).returncode == 0:
            return "nvidia"
    except (FileNotFoundError, Exception):
        pass
    return "cpu"

GPU_TYPE = detect_gpu()

# --- ENCODING PARAMETERS ---
V_CODEC = config("V_CODEC", default="h264_nvenc" if GPU_TYPE == "nvidia" else "libx264")
V_PRESET = config("V_PRESET", default="p3")
V_PROFILE = config("V_PROFILE", default="high")
V_LEVEL = config("V_LEVEL", default="4.0")
V_QP = config("V_QP", default=26, cast=int)
V_SCALE = config("V_SCALE", default=1080, cast=int)
V_FPS = config("V_FPS", default=30, cast=int)
A_BITRATE = config("A_BITRATE", default="192k")

# --- WATERMARK SETTINGS ---
WATERMARK_ENABLED = config("WATERMARK_ENABLED", default=False, cast=bool)
WATERMARK_TEXT = config("WATERMARK_TEXT", default="Compressed by Bot")
WATERMARK_POSITION = config("WATERMARK_POSITION", default="bottom-right")

# --- LOGGING & DEBUG ---
IS_COLAB = os.path.exists('/content')
COLAB_OUTPUT_DIR = "/content/drive/MyDrive/CompressorBot" if IS_COLAB else None
TELEGRAPH_API = config("TELEGRAPH_API", default="https://api.telegra.ph")

# --- DEV TOOLS ---
ENABLE_EVAL = config("ENABLE_EVAL", default=False, cast=bool)
ENABLE_BASH = config("ENABLE_BASH", default=False, cast=bool)

LOGS.info("✅ Configuration Loaded Successfully")