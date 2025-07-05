import re
import os
import time
from datetime import datetime
from pathlib import Path
from .FastTelethon import download_file, upload_file
from .funcn import *
from html_telegraph_poster import TelegraphPoster

def get_watermark_filter():
    """Constructs the watermark filter part of the ffmpeg command."""
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
    # Escape special characters for FFmpeg's drawtext filter
    escaped_text = WATERMARK_TEXT.replace("\\", "\\\\").replace("'", "’").replace(":", "\\:").replace("%", "\\%")
    
    return f"drawtext=text='{escaped_text}':fontcolor=white@0.8:fontsize=24:box=1:boxcolor=black@0.4:boxborderw=5:{position}"

async def process_compression(event, dl, start_time):
    """Main compression logic with dynamic command building, watermarking, and renaming."""
    out = None
    process = None
    try:
        compress_start_time = dt.now()
        original_name = Path(dl).stem
        os.makedirs("encode/", exist_ok=True)
        
        filename_map = {
            'original_name': original_name, 'preset': FILENAME_PRESET,
            'resolution': FILENAME_RESOLUTION, 'codec': FILENAME_CODEC,
            'date': FILENAME_DATE, 'time': FILENAME_TIME,
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

        video_filters = []
        if V_SCALE != -1: video_filters.append(f"scale=-2:{V_SCALE}")
        
        watermark_filter = get_watermark_filter()
        if watermark_filter: video_filters.append(watermark_filter)
        
        vf_string = f'-vf "{",".join(video_filters)}"' if video_filters else ""

        cmd = f'ffmpeg -y -hide_banner -loglevel error'
        if GPU_TYPE == "nvidia": cmd += ' -hwaccel cuda'
        
        cmd += f' -i "{dl}" -c:v {V_CODEC} -preset {V_PRESET} -profile:v {V_PROFILE} -level:v {V_LEVEL}'
        
        if 'nvenc' in V_CODEC: cmd += f' -rc constqp -qp {V_QP}'
        else: cmd += f' -crf {V_QP}'
            
        cmd += f' -r {V_FPS} -c:a aac -b:a {A_BITRATE} {vf_string} -movflags +faststart "{out}"'

        LOGS.info(f"Executing FFmpeg command: {cmd}")
        process = await asyncio.create_subprocess_shell(cmd, stderr=asyncio.subprocess.PIPE)
        _, stderr = await process.communicate()
        
        if process.returncode != 0:
            return await event.edit(f"❌ **COMPRESSION ERROR**\n```{stderr.decode(errors='ignore')[:3500]}```")
        if not os.path.exists(out) or os.path.getsize(out) == 0:
            return await event.edit("❌ **COMPRESSION FAILED**\nOutput file not created or empty.")
        
        await upload_compressed_file(event, dl, out, dtime, compress_start_time)
        
    except Exception as e:
        LOGS.error(f"Compression process error: {e}", exc_info=True)
        await event.edit(f"❌ **COMPRESSION ERROR**: `{str(e)}`")
    finally:
        files_to_delete = []
        if out and os.path.exists(out): files_to_delete.append(out)
        if dl and os.path.exists(dl):
            if AUTO_DELETE_ORIGINAL or (process and process.returncode == 0):
                files_to_delete.append(dl)

        for f in files_to_delete:
            if validate_file_path(f):
                try: os.remove(f)
                except OSError as e: LOGS.error(f"Failed to delete file {f}: {e}")

async def upload_compressed_file(event, dl, out, dtime, compress_start_time):
    try:
        await event.delete()
        
        compress_end_time = dt.now()
        comp_time = ts(int((compress_end_time - compress_start_time).total_seconds()) * 1000)
        
        nnn = await event.client.send_message(event.chat_id, "`Preparing to upload...`")
        
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
        final_message = await event.client.send_file(
            event.chat_id, file=uploaded_file, force_document=True, thumb=thumb_path, caption=f"`{upload_name}`"
        )
        
        org_size, com_size = os.path.getsize(dl), os.path.getsize(out)
        reduction = 100 - (com_size / org_size * 100) if org_size > 0 else 0
        
        info_before_html = await info(dl)
        info_after_html = await info(out)
        
        tgp_client = TelegraphPoster(use_api=True)
        try:
            tgp_client.create_api_token("Mediainfo", author_name="CompressorBot")
            info_before_url = tgp_client.post(title="Mediainfo (Before)", text=info_before_html)["url"] if info_before_html else None
            info_after_url = tgp_client.post(title="Mediainfo (After)", text=info_after_html)["url"] if info_after_html else None
        except Exception as e:
            LOGS.error(f"Telegraph post failed: {e}")
            info_before_url, info_after_url = None, None

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