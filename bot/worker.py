import re
import os
import time
import asyncio
from datetime import datetime
from pathlib import Path

from telethon import Button
from html_telegraph_poster import TelegraphPoster

from .FastTelethon import download_file, upload_file
from .funcn import bot_state, code, ts, hbs, progress, info, validate_file_path
from .config import (
    LOGS, OWNER, MAX_FILE_SIZE, MAX_QUEUE_SIZE, FILENAME_TEMPLATE, AUTO_DELETE_ORIGINAL,
    GPU_TYPE, V_CODEC, V_PRESET, V_PROFILE, V_LEVEL, V_QP, V_SCALE, V_FPS, A_BITRATE,
    WATERMARK_ENABLED, WATERMARK_TEXT, WATERMARK_POSITION, ENABLE_HARDWARE_ACCELERATION,
    DEFAULT_UPLOAD_MODE
)


def get_watermark_filter():
    """Constructs the watermark filter part of the FFmpeg command."""
    if not WATERMARK_ENABLED:
        return ""

    position_map = {
        "top-left": "x=10:y=10",
        "top-right": "x=w-text_w-10:y=10",
        "bottom-left": "x=10:y=h-text_h-10",
        "bottom-right": "x=w-text_w-10:y=h-text_h-10",
        "center": "x=(w-text_w)/2:y=(h-text_h)/2"
    }
    position = position_map.get(WATERMARK_POSITION, "x=w-text_w-10:y=h-text_h-10")
    escaped_text = WATERMARK_TEXT.replace("\\", "\\\\").replace("'", "’").replace(":", "\\:").replace("%", "\\%")
    
    return f"drawtext=text='{escaped_text}':fontcolor=white@0.8:fontsize=24:box=1:boxcolor=black@0.4:boxborderw=5:{position}"


async def process_compression(event, dl, start_time):
    """Main compression logic with dynamic command building, watermarking, and renaming."""
    out = None
    process = None
    try:
        compress_start_time = datetime.now()
        original_name = Path(dl).stem
        os.makedirs("encode/", exist_ok=True)
        
        filename_map = {
            'original_name': original_name, 'preset': V_PRESET,
            'resolution': f"{V_SCALE}p" if V_SCALE > 0 else "source",
            'codec': V_CODEC.replace('_nvenc', '').replace('lib', ''),
            'date': compress_start_time.strftime("%Y-%m-%d"),
            'time': compress_start_time.strftime("%H-%M-%S"),
        }
        new_filename_base = FILENAME_TEMPLATE.format(**filename_map)
        sanitized_filename = re.sub(r'[\\/*?:"<>|]', "", new_filename_base)
        out = f"encode/{sanitized_filename}.mkv"
        
        dtime = ts(int((compress_start_time - start_time).total_seconds()) * 1000)
        
        wah = code(f"{out};{dl};{event.id}")
        
        gpu_info = f" (🚀 {GPU_TYPE.upper()})" if GPU_TYPE != "cpu" else ""
        await event.edit(
            f"`✅ Downloaded in {dtime}`\n\n`🔄 Compressing{gpu_info}...`",
            buttons=[[Button.inline("📊 STATS", data=f"stats{wah}"), Button.inline("❌ CANCEL", data=f"skip{wah}")]]
        )

        # Determine if the codec is hardware-accelerated
        is_hardware_codec = '_nvenc' in V_CODEC

        # FFmpeg Command Builder
        cmd_parts = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error']
        
        # Input options (before -i)
        if GPU_TYPE == "nvidia" and ENABLE_HARDWARE_ACCELERATION and is_hardware_codec:
            cmd_parts.extend(['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda'])
        
        # Input file
        cmd_parts.extend(['-i', f'"{dl}"'])
        
        # Output options (after -i, before output file)
        filters = []
        if V_SCALE != -1:
            if GPU_TYPE == "nvidia" and ENABLE_HARDWARE_ACCELERATION and is_hardware_codec:
                filters.append(f'scale_cuda=-2:{V_SCALE}')
            else:
                filters.append(f'scale=-2:{V_SCALE}:force_original_aspect_ratio=decrease')
        
        if WATERMARK_ENABLED:
            watermark_filter = get_watermark_filter()
            if GPU_TYPE == "nvidia" and ENABLE_HARDWARE_ACCELERATION and is_hardware_codec:
                filters.append(f'hwdownload,format=nv12,{watermark_filter},hwupload_cuda')
            else:
                filters.append(watermark_filter)
        
        if filters:
            cmd_parts.extend(['-vf', f'"{",".join(filters)}"'])
        
        # Encoding parameters with custom settings
        cmd_parts.extend([
            '-c:v', V_CODEC,          # libx265
            '-preset', V_PRESET,      # p3
            '-profile:v', V_PROFILE,  # high
            '-level:v', V_LEVEL,
            '-crf', str(V_QP),        # 26
            '-r', str(V_FPS),         # 120
            '-c:a', 'aac',
            '-b:a', A_BITRATE,        # 384k
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
        
        await upload_compressed_file(event, dl, out, dtime, compress_start_time)
        
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
            if AUTO_DELETE_ORIGINAL and successful_compression:
                try:
                    os.remove(dl)
                except OSError as e:
                    LOGS.error(f"Failed to delete original file {dl}: {e}")


async def upload_compressed_file(event, dl, out, dtime, compress_start_time):
    try:
        await event.delete()
        
        compress_end_time = datetime.now()
        comp_time = ts(int((compress_end_time - compress_start_time).total_seconds()) * 1000)
        
        nnn = await event.client.send_message(event.chat_id, "`Preparing to upload...`")
        
        upload_mode = bot_state.get_upload_mode(event.sender_id)
        
        upload_name = Path(out).name
        upload_start_time = time.time()
        with open(out, "rb") as f:
            uploaded_file = await upload_file(
                client=event.client, file=f, name=upload_name,
                progress_callback=lambda d, t: progress(d, t, nnn, upload_start_time, "Uploading File", upload_name)
            )
        
        upload_time = ts(int((time.time() - upload_start_time) * 1000))
        await nnn.delete()

        thumb_path = "thumb.jpg" if os.path.exists("thumb.jpg") else None
        
        force_document = upload_mode == "Document"
        
        final_message = await event.client.send_file(
            event.chat_id, file=uploaded_file, force_document=force_document, thumb=thumb_path, caption=f"`{upload_name}`"
        )
        
        org_size, com_size = os.path.getsize(dl), os.path.getsize(out)
        reduction = 100 - (com_size / org_size * 100) if org_size > 0 else 0
        
        info_before_html = await info(dl)
        info_after_html = await info(out)
        
        tgp_client = TelegraphPoster(use_api=True)
        info_before_url, info_after_url = None, None
        try:
            tgp_client.create_api_token("Mediainfo", author_name="CompressorBot")
            if info_before_html:
                info_before_url = tgp_client.post(title="Mediainfo (Before)", text=info_before_html)["url"]
            if info_after_html:
                info_after_url = tgp_client.post(title="Mediainfo (After)", text=info_after_html)["url"]
        except Exception as e:
            LOGS.error(f"Telegraph post failed: {e}")
            
        gpu_info = f"\n🚀 **Engine**: {GPU_TYPE.upper()}"
        stats_msg = (
            f"✅ **COMPRESSION COMPLETE**\n\n"
            f"📁 **Original Size**: {hbs(org_size)}\n"
            f"📦 **Compressed Size**: {hbs(com_size)} ({reduction:.2f}% reduction)\n\n"
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
    
    if bot_state.is_working() or bot_state.queue_size() > 0:
        if not bot_state.add_to_queue(link, event):
            return await event.reply(f"❌ Queue is full (max {MAX_QUEUE_SIZE}) or item already exists.")
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

    if doc_attr.size > MAX_FILE_SIZE * 1024 * 1024:
        return await event.reply(f"❌ File too large: {hbs(doc_attr.size)} > {MAX_FILE_SIZE}MB.")
    
    if bot_state.is_working() or bot_state.queue_size() > 0:
        if not bot_state.add_to_queue(doc_attr.id, event):
            return await event.reply(f"❌ Queue is full (max {MAX_QUEUE_SIZE}) or item already exists.")
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
