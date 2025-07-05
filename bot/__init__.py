import asyncio
import glob
import inspect
import io
import itertools
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime as dt
from logging import DEBUG, INFO, basicConfig, getLogger, warning
from pathlib import Path

import aiohttp
import psutil
import pymediainfo
import requests
from html_telegraph_poster import TelegraphPoster
from telethon import Button, TelegramClient, errors, events, functions, types
from telethon.sessions import StringSession
from telethon.utils import pack_bot_file_id

from .config import *

basicConfig(format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=INFO)
LOGS = getLogger(__name__)

try:
    bot = TelegramClient(None, APP_ID, API_HASH)
    LOGS.info("Bot client created successfully")
except Exception as e:
    LOGS.info("Environment vars are missing! Kindly recheck.")
    LOGS.info("Bot is quiting...")
    LOGS.info(str(e))
    exit()

async def startup():
    """Send startup message to bot owners and log config"""
    LOGS.info("--- Configuration ---")
    LOGS.info(f"GPU Detection: {GPU_TYPE.upper()} (HW Accel: {'Enabled' if ENABLE_HARDWARE_ACCELERATION else 'Disabled'})")
    LOGS.info(f"Encoding: {V_CODEC}, Preset: {V_PRESET}, Quality: {V_QP}")
    LOGS.info(f"Output: {V_SCALE}p @ {V_FPS}fps, Audio: {A_BITRATE}")
    LOGS.info(f"Watermark: {'Enabled' if WATERMARK_ENABLED else 'Disabled'}")
    LOGS.info(f"Filename Template: {FILENAME_TEMPLATE}")
    LOGS.info(f"Auto-delete Original: {AUTO_DELETE_ORIGINAL}")
    LOGS.info("---------------------")

    for x in OWNER.split():
        try:
            await bot.send_message(
                int(x),
                "**🚀 Enhanced Video Compressor Bot Started**\n"
                f"🖥️ Using {GPU_TYPE.upper()} for encoding"
            )
        except Exception as e:
            LOGS.warning(f"Failed to send startup message to {x}: {e}")