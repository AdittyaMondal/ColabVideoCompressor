import subprocess
import os
import re
from decouple import config

def detect_gpu():
    """Detect available GPU. Prioritize Colab's environment."""
    if os.path.exists('/content'):
        try:
            if subprocess.run(['nvidia-smi'], capture_output=True).returncode == 0:
                return "nvidia"
        except FileNotFoundError:
            return "cpu"
    
    try:
        if subprocess.run(['nvidia-smi'], capture_output=True).returncode == 0:
            return "nvidia"
    except FileNotFoundError:
        pass
    
    return "cpu"

try:
    APP_ID = config("APP_ID", cast=int)
    API_HASH = config("API_HASH")
    BOT_TOKEN = config("BOT_TOKEN")
    OWNER = config("OWNER")
    
    # Bot settings
    MAX_FILE_SIZE = config("MAX_FILE_SIZE", default=4000, cast=int)
    MAX_QUEUE_SIZE = config("MAX_QUEUE_SIZE", default=10, cast=int)
    THUMB = config("THUMBNAIL", default="https://graph.org/file/75ee20ec8d8c8bba84f02.jpg")
    
    # Filename Template
    FILENAME_TEMPLATE = config("FILENAME_TEMPLATE", default="{original_name}_compressed")

    # Hardware and Encoding settings
    GPU_TYPE = detect_gpu()
    V_PRESET = config("V_PRESET", default="p2")
    V_QP = config("V_QP", default=28, cast=int)
    V_SCALE = config("V_SCALE", default=720, cast=int)
    A_BITRATE = config("A_BITRATE", default="128k")

    # Other settings
    IS_COLAB = os.path.exists('/content')
    COLAB_OUTPUT_DIR = "/content/drive/MyDrive/CompressorBot" if IS_COLAB else None
    TELEGRAPH_API = config("TELEGRAPH_API", default="https://api.telegra.ph")
    MAX_RETRIES = config("MAX_RETRIES", default=3, cast=int)

    print(f"GPU Detection: {GPU_TYPE}")
    print(f"Running in Colab: {IS_COLAB}")
    print(f"Filename Template: {FILENAME_TEMPLATE}")
    print(f"Encoding params: Preset={V_PRESET}, QP={V_QP}, Scale={V_SCALE}, Audio={A_BITRATE}")

except Exception as e:
    print(f"FATAL: Environment variables missing or invalid: {e}")
    exit()