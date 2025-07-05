#    This file is part of the Compressor distribution.
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

import subprocess
import os
from decouple import config

def detect_gpu():
    """Detect available GPU and return appropriate FFmpeg encoder"""
    try:
        # Check for NVIDIA GPU
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        if result.returncode == 0:
            return "nvidia"
    except FileNotFoundError:
        pass
    
    try:
        # Check for AMD GPU (Linux)
        if os.path.exists('/dev/dri'):
            result = subprocess.run(['vainfo'], capture_output=True, text=True)
            if result.returncode == 0 and 'VAProfileH264' in result.stdout:
                return "vaapi"
    except FileNotFoundError:
        pass
    
    # Check if running in Google Colab
    if os.path.exists('/content'):
        return "nvidia"  # Colab typically has NVIDIA GPUs
    
    return "cpu"

def get_ffmpeg_command(gpu_type="cpu"):
    """Get optimized FFmpeg command based on available hardware"""
    base_params = "-y -hide_banner -loglevel error"
    
    if gpu_type == "nvidia":
        return f'ffmpeg {base_params} -hwaccel cuda -hwaccel_output_format cuda -i "{{}}" -c:v h264_nvenc -preset fast -crf 23 -c:a aac -b:a 128k -movflags +faststart "{{}}"'
    elif gpu_type == "vaapi":
        return f'ffmpeg {base_params} -hwaccel vaapi -hwaccel_device /dev/dri/renderD128 -hwaccel_output_format vaapi -i "{{}}" -c:v h264_vaapi -qp 23 -c:a aac -b:a 128k -movflags +faststart "{{}}"'
    else:
        return f'ffmpeg {base_params} -i "{{}}" -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k -movflags +faststart "{{}}"'

try:
    APP_ID = config("APP_ID", default=6, cast=int)
    API_HASH = config("API_HASH", default="eb06d4abfb49dc3eeb1aeb98ae0f581e")
    BOT_TOKEN = config("BOT_TOKEN")
    DEV = 1322549723
    OWNER = config("OWNER")
    
    # GPU Detection and optimized FFmpeg command
    GPU_TYPE = detect_gpu()
    FFMPEG = config("FFMPEG", default=get_ffmpeg_command(GPU_TYPE))
    
    # Security settings
    ENABLE_EVAL = config("ENABLE_EVAL", default=False, cast=bool)
    ENABLE_BASH = config("ENABLE_BASH", default=False, cast=bool)
    MAX_FILE_SIZE = config("MAX_FILE_SIZE", default=2000, cast=int)  # MB
    MAX_QUEUE_SIZE = config("MAX_QUEUE_SIZE", default=10, cast=int)
    
    TELEGRAPH_API = config("TELEGRAPH_API", default="https://api.telegra.ph")
    THUMB = config(
        "THUMBNAIL", default="https://graph.org/file/75ee20ec8d8c8bba84f02.jpg"
    )
    
    # Colab specific settings
    IS_COLAB = os.path.exists('/content')
    COLAB_OUTPUT_DIR = "/content/drive/MyDrive/CompressorBot" if IS_COLAB else None
    
    print(f"GPU Detection: {GPU_TYPE}")
    print(f"Running in Colab: {IS_COLAB}")
    
except Exception as e:
    print("Environment vars Missing")
    print("something went wrong")
    print(str(e))
    exit()
