import os
import re
from decouple import config, Csv

# --- CORE API & BOT SETTINGS ---
APP_ID = config("APP_ID", cast=int)
API_HASH = config("API_HASH")
BOT_TOKEN = config("BOT_TOKEN")
OWNER = config("OWNER")
THUMBNAIL = config("THUMBNAIL", default="https://graph.org/file/75ee20ec8d8c8bba84f02.jpg")

# --- FILE & QUEUE SETTINGS ---
MAX_FILE_SIZE = config("MAX_FILE_SIZE", default=4000, cast=int)
MAX_QUEUE_SIZE = config("MAX_QUEUE_SIZE", default=15, cast=int)
FILENAME_TEMPLATE = config("FILENAME_TEMPLATE", default="{original_name} [{preset}]")
AUTO_DELETE_ORIGINAL = config("AUTO_DELETE_ORIGINAL", default=False, cast=bool)

# --- HARDWARE & PERFORMANCE ---
ENABLE_HARDWARE_ACCELERATION = config("ENABLE_HARDWARE_ACCELERATION", default=True, cast=bool)
PROGRESS_UPDATE_INTERVAL = config("PROGRESS_UPDATE_INTERVAL", default=5, cast=int)

def detect_gpu():
    """Detect NVIDIA GPU, respecting the hardware acceleration toggle."""
    if not ENABLE_HARDWARE_ACCELERATION:
        return "cpu"
    try:
        # A quick check for nvidia-smi's existence and return code
        if os.system("nvidia-smi -L >/dev/null 2>&1") == 0:
            return "nvidia"
    except Exception:
        pass
    return "cpu"

GPU_TYPE = detect_gpu()

# --- ENCODING PARAMETERS (from Colab Notebook) ---
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

# --- FILENAME PLACEHOLDERS (for dynamic naming) ---
FILENAME_PRESET = config("FILENAME_PRESET", default="Preset")
FILENAME_RESOLUTION = config("FILENAME_RESOLUTION", default="1080p")
FILENAME_CODEC = config("FILENAME_CODEC", default="h264")
FILENAME_DATE = config("FILENAME_DATE", default="2024-01-01")
FILENAME_TIME = config("FILENAME_TIME", default="12-00-00")

# --- LOGGING & DEBUG ---
IS_COLAB = os.path.exists('/content')
COLAB_OUTPUT_DIR = "/content/drive/MyDrive/CompressorBot" if IS_COLAB else None
TELEGRAPH_API = config("TELEGRAPH_API", default="https://api.telegra.ph")

print("✅ Configuration Loaded Successfully")
print(f"GPU Detection: {GPU_TYPE} (Hardware Acceleration: {'Enabled' if ENABLE_HARDWARE_ACCELERATION else 'Disabled'})")
print(f"Video Codec: {V_CODEC}, Preset: {V_PRESET}, Quality (QP/CRF): {V_QP}")
print(f"Output: {V_SCALE}p @ {V_FPS}fps, Audio: {A_BITRATE}")
print(f"Watermark: {'Enabled' if WATERMARK_ENABLED else 'Disabled'}")
print(f"Filename Template: {FILENAME_TEMPLATE}")