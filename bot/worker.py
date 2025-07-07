import re
import os
import time
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path

from telethon import Button
from html_telegraph_poster import TelegraphPoster

from .FastTelethon import download_file, upload_file
from .funcn import bot_state, code, ts, hbs, progress, info, validate_file_path
from .config import LOGS, OWNER, GPU_TYPE
from .settings import settings_manager


def get_watermark_filter(user_id: int = None):
    """Constructs the watermark filter part of the FFmpeg command."""
    advanced_settings = settings_manager.get_setting("advanced_settings", user_id=user_id)
    LOGS.info(f"Advanced settings for user {user_id}: {advanced_settings}")

    watermark_enabled = advanced_settings.get("watermark_enabled", False)
    watermark_text = advanced_settings.get("watermark_text", "Compressed by Bot")
    watermark_position = advanced_settings.get("watermark_position", "bottom-right")

    LOGS.info(f"Watermark check - USER: {user_id}, ENABLED: {watermark_enabled}, TEXT: '{watermark_text}', POSITION: {watermark_position}")

    if not watermark_enabled:
        LOGS.info("Watermark is disabled, skipping filter creation")
        return ""

    position_map = {
        "top-left": "x=10:y=10",
        "top-right": "x=w-text_w-10:y=10",
        "bottom-left": "x=10:y=h-text_h-10",
        "bottom-right": "x=w-text_w-10:y=h-text_h-10",
        "center": "x=(w-text_w)/2:y=(h-text_h)/2"
    }
    position = position_map.get(watermark_position, "x=w-text_w-10:y=h-text_h-10")
    escaped_text = watermark_text.replace("\\", "\\\\").replace("'", "’").replace(":", "\\:").replace("%", "\\%")

    # Enhanced watermark with better visibility and styling
    watermark_filter = (
        f"drawtext=text='{escaped_text}'"
        f":fontcolor=white@0.9"
        f":fontsize=24"
        f":box=1"
        f":boxcolor=black@0.6"
        f":boxborderw=3"
        f":{position}"
    )

    LOGS.info(f"Watermark filter: {watermark_filter}")
    return watermark_filter


async def process_compression(event, dl, start_time):
    """Main compression logic with dynamic command building, watermarking, and renaming."""
    out = None
    process = None
    try:
        user_id = event.sender_id
        compress_start_time = datetime.now()
        original_name = Path(dl).stem
        os.makedirs("encode/", exist_ok=True)

        # Get dynamic settings for this user
        compression_settings = settings_manager.get_active_compression_settings(user_id)
        output_settings = settings_manager.get_setting("output_settings", user_id=user_id)

        filename_template = output_settings.get("filename_template", "{original_name} [{resolution} {codec}]")
        output_format = output_settings.get("output_format", "mkv")
        v_preset = compression_settings.get("v_preset", "medium")
        v_scale = compression_settings.get("v_scale", 1080)
        v_codec = compression_settings.get("v_codec", "libx264")

        filename_map = {
            'original_name': original_name, 'preset': v_preset,
            'resolution': f"{v_scale}p" if v_scale > 0 else "source",
            'codec': v_codec.replace('_nvenc', '').replace('lib', ''),
            'date': compress_start_time.strftime("%Y-%m-%d"),
            'time': compress_start_time.strftime("%H-%M-%S"),
        }
        new_filename_base = filename_template.format(**filename_map)
        sanitized_filename = re.sub(r'[\\/*?:"<>|]', "", new_filename_base)
        out = f"encode/{sanitized_filename}.{output_format}"
        
        dtime = ts(int((compress_start_time - start_time).total_seconds()) * 1000)

        wah = code(f"{out};{dl};{event.id}")

        # Enhanced compression status with more details
        gpu_info = f"🚀 {GPU_TYPE.upper()}" if GPU_TYPE != "cpu" else "💻 CPU"
        codec_info = v_codec.replace('_nvenc', ' (HW)').replace('lib', '').upper()

        advanced_settings = settings_manager.get_setting("advanced_settings", user_id=user_id)
        watermark_enabled = advanced_settings.get("watermark_enabled", False)

        status_parts = [f"📥 Downloaded in {dtime}", f"🔄 Compressing with {codec_info}", f"⚙️ Engine: {gpu_info}"]
        if watermark_enabled:
            status_parts.append(f"🏷️ Adding watermark")
        if v_scale > 0:
            status_parts.append(f"📐 Target: {v_scale}p")

        status_msg = "\n".join([f"`{part}`" for part in status_parts])

        await event.edit(
            status_msg,
            buttons=[[Button.inline("📊 STATS", data=f"stats{wah}"), Button.inline("❌ CANCEL", data=f"skip{wah}")]]
        )

        # Determine if the codec is hardware-accelerated
        is_hardware_codec = '_nvenc' in v_codec
        enable_hardware_acceleration = compression_settings.get("enable_hardware_acceleration", True)

        # FFmpeg Command Builder
        cmd_parts = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error']

        # Get all needed settings
        v_profile = compression_settings.get("v_profile", "high")
        v_level = compression_settings.get("v_level", "4.0")
        v_qp = compression_settings.get("v_qp", 26)
        v_fps = compression_settings.get("v_fps", 30)
        a_bitrate = compression_settings.get("a_bitrate", "192k")

        # Input options (before -i)
        if GPU_TYPE == "nvidia" and enable_hardware_acceleration and is_hardware_codec:
            cmd_parts.extend(['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda'])

        # Input file
        cmd_parts.extend(['-i', f'"{dl}"'])

        # Output options (after -i, before output file)
        filters = []
        if v_scale != -1:
            if GPU_TYPE == "nvidia" and enable_hardware_acceleration and is_hardware_codec:
                filters.append(f'scale_cuda=-2:{v_scale}')
            else:
                filters.append(f'scale=-2:{v_scale}:force_original_aspect_ratio=decrease')

        if watermark_enabled:
            watermark_filter = get_watermark_filter(user_id)
            if watermark_filter:  # Only add if watermark filter is valid
                if GPU_TYPE == "nvidia" and enable_hardware_acceleration and is_hardware_codec:
                    # For hardware acceleration, we need to download from GPU, apply watermark, then upload back
                    filters.append(f'hwdownload,format=nv12,{watermark_filter},hwupload_cuda')
                else:
                    # For software encoding, apply watermark directly
                    filters.append(watermark_filter)

        if filters:
            cmd_parts.extend(['-vf', f'"{",".join(filters)}"'])

        # Encoding parameters with custom settings
        cmd_parts.extend([
            '-c:v', v_codec,          # libx265
            '-preset', v_preset,      # p3
            '-profile:v', v_profile,  # high
            '-level:v', v_level,
            '-crf', str(v_qp),        # 26
            '-r', str(v_fps),         # 120
            '-c:a', 'aac',
            '-b:a', a_bitrate,        # 384k
            '-movflags', '+faststart',
            f'"{out}"'
        ])
        
        cmd = ' '.join(cmd_parts)
        LOGS.info(f"Executing FFmpeg command: {cmd}")
        process = await asyncio.create_subprocess_shell(cmd, stderr=asyncio.subprocess.PIPE)
        _, stderr = await process.communicate()
        
        stderr_output = stderr.decode(errors='ignore')
        if process.returncode != 0:
            error_message = f"❌ **COMPRESSION ERROR**\n`{stderr_output[:3500]}`"
            return await event.edit(error_message)
        
        if not os.path.exists(out) or os.path.getsize(out) == 0:
            return await event.edit(f"❌ **COMPRESSION FAILED**\nOutput file not created or empty.\n\n**FFmpeg Logs:**\n`{stderr_output[:3000]}`")
        
        # Generate thumbnail, preview, and screenshots
        thumbnail_path = await generate_thumbnail(out, user_id)
        preview_path, screenshots = None, []

        preview_settings = settings_manager.get_setting("preview_settings", user_id=user_id)
        enable_video_preview = preview_settings.get("enable_video_preview", False)
        enable_screenshots = preview_settings.get("enable_screenshots", False)

        LOGS.info(f"Preview settings - Video preview: {enable_video_preview}, Screenshots: {enable_screenshots}")

        if enable_video_preview:
            LOGS.info("Generating video preview...")
            preview_path = await generate_preview(out, user_id)
            LOGS.info(f"Preview generated: {preview_path}")

        if enable_screenshots:
            LOGS.info("Generating screenshots...")
            screenshots = await generate_screenshots(out, user_id)
            LOGS.info(f"Screenshots generated: {len(screenshots) if screenshots else 0} files")

        await upload_compressed_file(event, dl, out, dtime, compress_start_time, preview_path, screenshots, thumbnail_path)
        
    except Exception as e:
        LOGS.error(f"Compression process error: {e}", exc_info=True)
        await event.edit(f"❌ **FATAL COMPRESSION ERROR**: `{str(e)}`")
    finally:
        successful_compression = process and process.returncode == 0
        
        # Clean up output file
        if out and os.path.exists(out) and validate_file_path(out):
            try:
                os.remove(out)
            except OSError as e:
                LOGS.error(f"Failed to delete output file {out}: {e}")
        
        # Clean up original file based on settings
        if dl and os.path.exists(dl) and validate_file_path(dl):
            output_settings = settings_manager.get_setting("output_settings", user_id=event.sender_id)
            auto_delete_original = output_settings.get("auto_delete_original", False)
            if auto_delete_original and successful_compression:
                try:
                    os.remove(dl)
                except OSError as e:
                    LOGS.error(f"Failed to delete original file {dl}: {e}")


async def generate_preview(video_path, user_id: int = None):
    """Generate a preview compilation from multiple clips throughout the video"""
    try:
        preview_settings = settings_manager.get_setting("preview_settings", user_id=user_id)
        total_preview_duration = preview_settings.get("preview_duration", 10)
        preview_quality = preview_settings.get("preview_quality", 28)

        preview_output = f"encode/{Path(video_path).stem}_preview.mp4"
        temp_dir = "temp/preview_clips"
        os.makedirs(temp_dir, exist_ok=True)

        # Get video duration first
        duration_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{video_path}\""
        process = await asyncio.create_subprocess_shell(duration_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            LOGS.error(f"Failed to get video duration for preview: {stderr.decode(errors='ignore')}")
            return None

        duration = float(stdout.decode().strip())
        LOGS.info(f"Video duration: {duration:.2f} seconds")

        # Calculate clip parameters
        num_clips = min(8, max(3, int(duration / 120)))  # 3-8 clips based on video length
        clip_duration = total_preview_duration / num_clips  # Each clip duration

        # Skip first and last 5% of video to avoid intro/outro
        usable_duration = duration * 0.9
        start_offset = duration * 0.05

        # Calculate clip start times evenly distributed
        clip_starts = []
        for i in range(num_clips):
            position = start_offset + (i * usable_duration / (num_clips - 1)) if num_clips > 1 else start_offset + usable_duration / 2
            clip_starts.append(min(position, duration - clip_duration - 1))

        LOGS.info(f"Generating {num_clips} clips of {clip_duration:.1f}s each from {duration:.1f}s video")

        # Generate individual clips
        clip_files = []
        for i, start_time in enumerate(clip_starts):
            clip_file = f"{temp_dir}/clip_{i:02d}.mp4"

            cmd = (f"ffmpeg -y -ss {start_time:.2f} -i \"{video_path}\" -t {clip_duration:.2f} "
                   f"-c:v libx264 -crf {preview_quality} -preset veryfast "
                   f"-vf \"scale=-2:720:force_original_aspect_ratio=decrease\" "
                   f"-c:a aac -b:a 128k -avoid_negative_ts make_zero \"{clip_file}\"")

            process = await asyncio.create_subprocess_shell(cmd, stderr=asyncio.subprocess.PIPE)
            _, stderr = await process.communicate()

            if process.returncode == 0 and os.path.exists(clip_file):
                clip_files.append(clip_file)
                LOGS.info(f"Clip {i+1}/{num_clips} generated: {clip_file}")
            else:
                LOGS.error(f"Failed to generate clip {i+1}: {stderr.decode(errors='ignore')}")

        if not clip_files:
            LOGS.error("No clips were generated successfully")
            return None

        # Create concat file for FFmpeg
        concat_file = f"{temp_dir}/concat_list.txt"
        with open(concat_file, 'w') as f:
            for clip_file in clip_files:
                f.write(f"file '{os.path.abspath(clip_file)}'\n")

        # Concatenate clips into final preview
        concat_cmd = (f"ffmpeg -y -f concat -safe 0 -i \"{concat_file}\" "
                     f"-c copy -movflags +faststart \"{preview_output}\"")

        process = await asyncio.create_subprocess_shell(concat_cmd, stderr=asyncio.subprocess.PIPE)
        _, stderr = await process.communicate()

        # Cleanup temporary files
        for clip_file in clip_files:
            try:
                os.remove(clip_file)
            except:
                pass
        try:
            os.remove(concat_file)
            os.rmdir(temp_dir)
        except:
            pass

        if process.returncode == 0 and os.path.exists(preview_output):
            file_size = os.path.getsize(preview_output)
            LOGS.info(f"Preview compilation generated successfully: {preview_output} ({file_size} bytes)")
            return preview_output
        else:
            LOGS.error(f"Preview compilation failed: {stderr.decode(errors='ignore')}")
            return None

    except Exception as e:
        LOGS.error(f"Error generating preview compilation: {e}", exc_info=True)
        return None

async def generate_screenshots(video_path, user_id: int = None):
    """Generate multiple screenshots from video at different timestamps"""
    screenshots = []
    try:
        preview_settings = settings_manager.get_setting("preview_settings", user_id=user_id)
        screenshot_count = preview_settings.get("screenshot_count", 5)

        # Get video duration first
        duration_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{video_path}\""
        process = await asyncio.create_subprocess_shell(duration_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            LOGS.error(f"Failed to get video duration for screenshots: {stderr.decode(errors='ignore')}")
            return []

        duration = float(stdout.decode().strip())
        LOGS.info(f"Generating {screenshot_count} screenshots from {duration:.2f}s video")

        # Calculate timestamps for screenshots (avoid first and last 5% of video)
        start_offset = duration * 0.05  # Skip first 5%
        end_offset = duration * 0.95    # Skip last 5%
        usable_duration = end_offset - start_offset

        if usable_duration <= 0:
            LOGS.warning("Video too short for quality screenshots")
            usable_duration = duration
            start_offset = 0

        interval = usable_duration / screenshot_count

        for i in range(screenshot_count):
            timestamp = start_offset + (interval * i) + (interval / 2)  # Take from middle of each interval
            screenshot_path = f"encode/screenshot_{i+1}.jpg"

            # Generate screenshot with good quality and reasonable size
            cmd = (f"ffmpeg -y -ss {timestamp} -i \"{video_path}\" -vframes 1 "
                   f"-vf \"scale=1280:720:force_original_aspect_ratio=decrease\" "
                   f"-q:v 2 \"{screenshot_path}\"")

            process = await asyncio.create_subprocess_shell(cmd, stderr=asyncio.subprocess.PIPE)
            _, stderr = await process.communicate()

            if process.returncode == 0 and os.path.exists(screenshot_path):
                file_size = os.path.getsize(screenshot_path)
                LOGS.info(f"Screenshot {i+1} generated: {screenshot_path} ({file_size} bytes)")
                screenshots.append(screenshot_path)
            else:
                LOGS.error(f"Failed to generate screenshot {i+1} at {timestamp:.2f}s: {stderr.decode(errors='ignore')}")

        LOGS.info(f"Successfully generated {len(screenshots)}/{screenshot_count} screenshots")
        return screenshots

    except Exception as e:
        LOGS.error(f"Error generating screenshots: {e}", exc_info=True)
        return []


async def generate_thumbnail(video_path, user_id: int = None):
    """Generate a thumbnail image from video for Telegram upload"""
    try:
        thumbnail_settings = settings_manager.get_setting("thumbnail_settings", user_id=user_id)
        auto_generate = thumbnail_settings.get("auto_generate", True)
        custom_url = thumbnail_settings.get("custom_url", "")
        timestamp_str = thumbnail_settings.get("timestamp", "00:00:10")

        # Convert timestamp string to seconds
        try:
            time_parts = timestamp_str.split(":")
            timestamp_seconds = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])
        except:
            timestamp_seconds = 10  # Default to 10 seconds

        thumb_path = "thumb.jpg"

        # If custom URL is provided, try to download it first
        if custom_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(custom_url) as response:
                        if response.status == 200:
                            with open(thumb_path, 'wb') as f:
                                f.write(await response.read())
                            LOGS.info(f"Custom thumbnail downloaded: {thumb_path}")
                            return thumb_path
            except Exception as e:
                LOGS.error(f"Failed to download custom thumbnail: {e}")
                # Fall back to auto-generation if custom URL fails

        # Auto-generate thumbnail from video if no custom URL or custom URL failed
        if auto_generate or custom_url:  # Generate if auto_generate is True OR if custom URL failed
            # Get video duration first
            duration_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{video_path}\""
            process = await asyncio.create_subprocess_shell(duration_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, _ = await process.communicate()

            if process.returncode != 0:
                LOGS.error("Failed to get video duration for thumbnail")
                return None

            duration = float(stdout.decode().strip())
            # Use the specified timestamp, but ensure it's not beyond video duration
            timestamp = min(timestamp_seconds, duration - 1)

            # Generate thumbnail with specific size for Telegram (320x320 max, maintaining aspect ratio)
            cmd = f"ffmpeg -y -ss {timestamp} -i \"{video_path}\" -vframes 1 -vf \"scale=320:320:force_original_aspect_ratio=decrease\" -q:v 2 \"{thumb_path}\""
            process = await asyncio.create_subprocess_shell(cmd, stderr=asyncio.subprocess.PIPE)
            _, stderr = await process.communicate()

            if process.returncode == 0 and os.path.exists(thumb_path):
                LOGS.info(f"Thumbnail generated successfully: {thumb_path}")
                return thumb_path
            else:
                LOGS.error(f"Failed to generate thumbnail: {stderr.decode(errors='ignore')}")
                return None

        return None

    except Exception as e:
        LOGS.error(f"Error generating thumbnail: {e}", exc_info=True)
        return None


async def get_video_duration(video_path):
    """Get video duration in seconds"""
    try:
        duration_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{video_path}\""
        process = await asyncio.create_subprocess_shell(duration_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await process.communicate()

        if process.returncode == 0:
            duration = float(stdout.decode().strip())
            return duration
        else:
            LOGS.error("Failed to get video duration")
            return None
    except Exception as e:
        LOGS.error(f"Error getting video duration: {e}", exc_info=True)
        return None

async def upload_compressed_file(event, dl, out, dtime, compress_start_time, preview_path=None, screenshots=None, thumbnail_path=None):
    try:
        # Store user info before deleting event
        user_id = event.sender_id
        chat_id = event.chat_id
        client = event.client

        await event.delete()

        compress_end_time = datetime.now()
        comp_time = ts(int((compress_end_time - compress_start_time).total_seconds()) * 1000)

        nnn = await client.send_message(chat_id, "`Preparing to upload...`")

        # Get upload mode from settings
        output_settings = settings_manager.get_setting("output_settings", user_id=user_id)
        LOGS.info(f"Output settings for user {user_id}: {output_settings}")
        upload_mode = output_settings.get("default_upload_mode", "Document")
        LOGS.info(f"Upload mode for user {user_id}: {upload_mode}")
        
        upload_name = Path(out).name
        upload_start_time = time.time()
        with open(out, "rb") as f:
            uploaded_file = await upload_file(
                client=client, file=f, name=upload_name,
                progress_callback=lambda d, t: progress(d, t, nnn, upload_start_time, "Uploading File", upload_name)
            )
        
        upload_time = ts(int((time.time() - upload_start_time) * 1000))
        await nnn.delete()

        # Use generated thumbnail or fallback to existing thumb.jpg
        thumb_path = thumbnail_path if thumbnail_path and os.path.exists(thumbnail_path) else ("thumb.jpg" if os.path.exists("thumb.jpg") else None)
        LOGS.info(f"Thumbnail path: {thumb_path}, exists: {os.path.exists(thumb_path) if thumb_path else False}")

        force_document = upload_mode == "Document"
        LOGS.info(f"Upload settings - Mode: {upload_mode}, Force Document: {force_document}")
        
        # Get video duration for display
        video_duration = await get_video_duration(out)
        duration_str = f"{int(video_duration//60)}:{int(video_duration%60):02d}" if video_duration else "Unknown"

        # Create enhanced caption with duration
        caption = f"`{upload_name}`"
        if video_duration:
            caption += f"\n🎬 Duration: {duration_str}"

        final_message = await client.send_file(
            chat_id, file=uploaded_file, force_document=force_document, thumb=thumb_path, caption=caption
        )
        
        if preview_path and os.path.exists(preview_path):
            LOGS.info(f"Sending video preview: {preview_path}")
            await client.send_file(chat_id, file=preview_path, caption="**Video Preview**")
            os.remove(preview_path)
        else:
            LOGS.info(f"No preview to send - path: {preview_path}, exists: {os.path.exists(preview_path) if preview_path else False}")

        if screenshots and len(screenshots) > 0:
            LOGS.info(f"Sending {len(screenshots)} screenshots")
            await client.send_file(chat_id, file=screenshots, caption="**Screenshots**")
            for ss in screenshots:
                if os.path.exists(ss):
                    os.remove(ss)
        else:
            LOGS.info(f"No screenshots to send - count: {len(screenshots) if screenshots else 0}")
        
        org_size, com_size = os.path.getsize(dl), os.path.getsize(out)
        reduction = 100 - (com_size / org_size * 100) if org_size > 0 else 0
        
        info_before_html = await info(dl)
        info_after_html = await info(out)
        
        tgp_client = TelegraphPoster(use_api=True)
        info_before_url, info_after_url = None, None
        try:
            tgp_client.create_api_token("Mediainfo", author_name="CompressorBot")
            if info_before_html:
                info_before_url = tgp_client.post(title="Mediainfo (Before)", author="CompressorBot", text=info_before_html)["url"]
            if info_after_html:
                info_after_url = tgp_client.post(title="Mediainfo (After)", author="CompressorBot", text=info_after_html)["url"]
        except Exception as e:
            LOGS.error(f"Telegraph post failed: {e}")
            
        gpu_info = f"\n🚀 **Engine**: {GPU_TYPE.upper()}"
        stats_msg = (
            f"✅ **COMPRESSION COMPLETE**\n\n"
            f"📁 **Original Size**: {hbs(org_size)}\n"
            f"📦 **Compressed Size**: {hbs(com_size)} ({reduction:.2f}% reduction)\n"
            f"🎬 **Duration**: {duration_str}\n\n"
            f"⏱️ **Time Taken:**\n"
            f"  - **Download**: {dtime}\n"
            f"  - **Compress**: {comp_time}\n"
            f"  - **Upload**: {upload_time}{gpu_info}\n\n"
        )
        if info_before_url and info_after_url:
            stats_msg += f"📋 **MediaInfo**: [Before]({info_before_url}) | [After]({info_after_url})"
        
        await final_message.reply(stats_msg, link_preview=False)
        
    except Exception as e:
        LOGS.error(f"Upload error: {e}", exc_info=True)
        await event.client.send_message(event.chat_id, f"❌ **UPLOAD ERROR**: `{str(e)}`")


async def dl_link(event):
    if not event.is_private or str(event.sender_id) not in OWNER.split():
        return
    parts = event.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].startswith(('http://', 'https://')):
        return await event.reply("❌ **Usage:** `/link <url> [filename.ext]`")

    link = parts[1]

    # Get dynamic queue size setting
    output_settings = settings_manager.get_setting("output_settings", user_id=event.sender_id)
    max_queue_size = output_settings.get("max_queue_size", 15)

    if bot_state.is_working() or bot_state.queue_size() > 0:
        if not bot_state.add_to_queue(link, event):
            return await event.reply(f"❌ Queue is full (max {max_queue_size}) or item already exists.")
        return await event.reply(f"✅ Added to queue at position #{bot_state.queue_size()}")

    name = parts[2] if len(parts) > 2 else ""
    await process_link_download(event, link, name)


async def process_link_download(event, link, name):
    bot_state.set_working(True)
    xxx = await event.reply("`Analysing link...`")
    try:
        from .funcn import fast_download
        dl = await fast_download(xxx, link, name)
        await process_compression(xxx, dl, datetime.now())
    except Exception as er:
        LOGS.error(f"Link download failed: {er}", exc_info=True)
        await xxx.edit(f"❌ **Download failed:**\n`{str(er)}`")
    finally:
        bot_state.clear_working()


async def toggle_upload_mode(event):
    if not event.is_private or str(event.sender_id) not in OWNER.split():
        return
    
    current_mode = bot_state.get_upload_mode(event.sender_id)
    new_mode = "Document" if current_mode == "File" else "File"
    bot_state.set_upload_mode(event.sender_id, new_mode)
    
    await event.reply(f"☁️ Upload mode switched to **{new_mode}**.")


async def toggle_watermark(event):
    """Toggle watermark on/off"""
    if str(event.sender_id) not in OWNER.split():
        return

    user_id = event.sender_id
    advanced_settings = settings_manager.get_setting("advanced_settings", user_id=user_id)
    current_enabled = advanced_settings.get("watermark_enabled", False)
    watermark_text = advanced_settings.get("watermark_text", "Compressed by Bot")
    watermark_position = advanced_settings.get("watermark_position", "bottom-right")

    # Toggle the watermark setting
    new_enabled = not current_enabled
    settings_manager.set_setting("advanced_settings", "watermark_enabled", new_enabled, user_id)

    status = "✅ Enabled" if new_enabled else "❌ Disabled"
    await event.reply(
        f"🏷️ **Watermark Status Updated**\n\n"
        f"**Status**: {status}\n"
        f"**Text**: `{watermark_text}`\n"
        f"**Position**: `{watermark_position}`\n\n"
        f"Changes will apply to new compressions."
    )


async def custom_encoder(event):
    if not event.is_private or str(event.sender_id) not in OWNER.split():
        return
    
    if not event.reply_to_msg_id:
        return await event.reply("Reply to a video file to use custom encoding.")
        
    replied_msg = await event.get_reply_message()
    if not replied_msg.media or not getattr(replied_msg.media, 'document', None):
        return await event.reply("Reply to a video file to use custom encoding.")

    args = event.text.split()
    custom_settings = {}
    for i in range(1, len(args), 2):
        try:
            key = args[i][1:]
            value = args[i+1]
            custom_settings[key] = value
        except IndexError:
            break
            
    await process_file_encoding(replied_msg, custom_settings=custom_settings)


async def encod(event):
    if not event.is_private or not event.media or str(event.sender_id) not in OWNER.split():
        return

    doc_attr = getattr(event.media, 'document', None)
    if not (doc_attr and doc_attr.mime_type and doc_attr.mime_type.startswith("video")):
        return

    # Get dynamic file size setting
    output_settings = settings_manager.get_setting("output_settings", user_id=event.sender_id)
    max_file_size = output_settings.get("max_file_size", 4000)
    max_queue_size = output_settings.get("max_queue_size", 15)

    if doc_attr.size > max_file_size * 1024 * 1024:
        return await event.reply(f"❌ File too large: {hbs(doc_attr.size)} > {max_file_size}MB.")

    if bot_state.is_working() or bot_state.queue_size() > 0:
        if not bot_state.add_to_queue(doc_attr.id, event):
            return await event.reply(f"❌ Queue is full (max {max_queue_size}) or item already exists.")
        return await event.reply(f"`✅ Added to queue at position #{bot_state.queue_size()}`")

    await process_file_encoding(event)


async def process_file_encoding(event):
    bot_state.set_working(True)
    xxx = await event.reply("`Preparing to download...`")
    dl = None
    try:
        file = event.media.document
        filename = getattr(event.file, 'name', f"video_{file.id}.mp4")
        if not filename:
            filename = f"video_{file.id}.mp4"
        
        sanitized_filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
        
        os.makedirs("downloads/", exist_ok=True)
        dl = os.path.join("downloads/", sanitized_filename)
        
        with open(dl, "wb") as f:
            await download_file(
                client=event.client,
                location=file,
                out=f,
                progress_callback=lambda d, t: progress(d, t, xxx, time.time(), "Downloading File", sanitized_filename)
            )
        await process_compression(xxx, dl, datetime.now())
    except Exception as er:
        LOGS.error(f"File encoding failed: {er}", exc_info=True)
        if xxx:
            await xxx.edit(f"❌ **Processing failed:**\n`{str(er)}`")
    finally:
        bot_state.clear_working()
