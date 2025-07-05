import re
from .FastTelethon import download_file, upload_file
from .funcn import *

async def stats(e):
    try:
        wah = e.pattern_match.group(1).decode("UTF-8")
        wh = decode(wah)
        if not wh:
            return await e.answer("Invalid stats request", cache_time=0, alert=True)
            
        out, dl, _ = wh.split(";")
        
        if not (validate_file_path(out) and validate_file_path(dl)):
            return await e.answer("Invalid file paths", cache_time=0, alert=True)
        
        if not (os.path.exists(out) and os.path.exists(dl)):
            return await e.answer("Files not found.", cache_time=0, alert=True)
            
        ot = hbs(os.path.getsize(out))
        ov = hbs(os.path.getsize(dl))
        
        gpu_info = f"\n🚀 Using: {GPU_TYPE.upper()}"
        ans = f"Original: {ov}\nCompressed: {ot}{gpu_info}"
        await e.answer(ans, cache_time=0, alert=True)
    except Exception as er:
        LOGS.error(f"Stats error: {er}")
        await e.answer("Something went wrong 🤔", cache_time=0, alert=True)

async def dl_link(event):
    if not event.is_private or str(event.sender_id) not in OWNER:
        return
    
    parts = event.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].startswith(('http://', 'https://')):
        return await event.reply("❌ **Usage:** `/link <url> [filename.ext]`")
    
    link, name = parts[1], parts[2] if len(parts) > 2 else ""
    
    if bot_state.is_working() or bot_state.queue_size() > 0:
        if not bot_state.add_to_queue(link, name):
            return await event.reply(f"❌ Queue is full (max {MAX_QUEUE_SIZE})")
        return await event.reply(f"✅ Added to queue at position #{bot_state.queue_size()}")
    
    await process_link_download(event, link, name)

async def process_link_download(event, link, name):
    bot_state.set_working(True)
    xxx = await event.reply("`Analysing link...`")
    try:
        dl = await fast_download(xxx, link, name)
        await process_compression(xxx, dl, dt.now())
    except Exception as er:
        LOGS.error(f"Link download failed: {er}")
        await xxx.edit(f"❌ **Download failed:**\n`{str(er)}`")
    finally:
        bot_state.clear_working()

async def encod(event):
    if not event.is_private or not event.media or str(event.sender_id) not in OWNER:
        return
    if not (hasattr(event.media, "document") and event.media.document.mime_type.startswith("video")):
        return

    doc = event.media.document
    if doc.size > MAX_FILE_SIZE * 1024 * 1024:
        return await event.reply(f"❌ File too large: {hbs(doc.size)} > {MAX_FILE_SIZE}MB.")
    
    if bot_state.is_working() or bot_state.queue_size() > 0:
        if bot_state.is_in_queue(doc.id):
            return await event.reply("`This file is already in the queue.`")
        name = event.file.name or f"video_{doc.id}.mp4"
        if not bot_state.add_to_queue(doc.id, [name, doc]):
            return await event.reply(f"❌ Queue is full (max {MAX_QUEUE_SIZE}).")
        return await event.reply(f"`✅ Added to queue at position #{bot_state.queue_size()}`")
    
    await process_file_encoding(event)

async def process_file_encoding(event):
    bot_state.set_working(True)
    xxx = await event.reply("`Preparing to download...`")
    dl = None
    try:
        file = event.media.document
        filename = event.file.name or f"video_{file.id}.mp4"
        filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
        dl = os.path.join("downloads/", filename)
        with open(dl, "wb") as f:
            await download_file(
                client=event.client,
                location=file,
                out=f,
                progress_callback=lambda d, t: progress(d, t, xxx, time.time(), "Downloading File", filename)
            )
        await process_compression(xxx, dl, dt.now())
    except Exception as er:
        LOGS.error(f"File encoding failed: {er}", exc_info=True)
        if xxx: await xxx.edit(f"❌ **Processing failed:**\n`{str(er)}`")
    finally:
        bot_state.clear_working()
        if dl and os.path.exists(dl): os.remove(dl)

async def process_compression(event, dl, start_time):
    out = None
    try:
        compress_start_time = dt.now()
        original_name = Path(dl).stem
        os.makedirs("encode/", exist_ok=True)
        
        new_filename_base = FILENAME_TEMPLATE.format(original_name=original_name)
        sanitized_filename = re.sub(r'[\\/*?:"<>|]', "", new_filename_base)
        out = f"encode/{sanitized_filename}.mkv"
        
        dtime = ts(int((compress_start_time - start_time).total_seconds()) * 1000)
        
        unique_id = event.id
        wah = code(f"{out};{dl};{unique_id}")
        
        gpu_info = f" (🚀 {GPU_TYPE.upper()})" if GPU_TYPE != "cpu" else ""
        nn = await event.edit(
            f"`✅ Downloaded in {dtime}`\n\n`🔄 Compressing{gpu_info}...`",
            buttons=[[Button.inline("📊 STATS", data=f"stats{wah}"), Button.inline("❌ CANCEL", data=f"skip{wah}")]]
        )

        scale_filter = f'-vf scale=-2:{V_SCALE}' if V_SCALE != -1 else ''
        
        if GPU_TYPE == "nvidia":
            cmd = (
                f'ffmpeg -y -hide_banner -loglevel error -hwaccel cuda -i "{dl}" '
                f'-c:v hevc_nvenc -preset {V_PRESET} -rc constqp -qp {V_QP} {scale_filter} '
                f'-c:a aac -b:a {A_BITRATE} -movflags +faststart "{out}"'
            )
        else: # CPU fallback
            cmd = (
                f'ffmpeg -y -hide_banner -loglevel error -i "{dl}" '
                f'-c:v libx264 -preset veryfast -crf {V_QP} {scale_filter} '
                f'-c:a aac -b:a {A_BITRATE} -movflags +faststart "{out}"'
            )

        LOGS.info(f"Executing FFmpeg command: {cmd}")
        process = await asyncio.create_subprocess_shell(cmd, stderr=asyncio.subprocess.PIPE)
        _, stderr = await process.communicate()
        
        if process.returncode != 0:
            return await event.edit(f"❌ **COMPRESSION ERROR**\n\n```{stderr.decode()[:3500]}```")
        if not os.path.exists(out) or os.path.getsize(out) == 0:
            return await event.edit("❌ **COMPRESSION FAILED**\nOutput file not created or is empty.")
        
        await upload_compressed_file(event, nn, dl, out, dtime, compress_start_time)
        
    except Exception as e:
        LOGS.error(f"Compression process error: {e}", exc_info=True)
        await event.edit(f"❌ **COMPRESSION ERROR**: `{str(e)}`")
    finally:
        for f in [dl, out]:
            if f and os.path.exists(f): os.remove(f)

async def upload_compressed_file(event, nn, dl, out, dtime, compress_start_time):
    try:
        compress_end_time = dt.now()
        comp_time = ts(int((compress_end_time - compress_start_time).total_seconds()) * 1000)
        
        await nn.delete()
        nnn = await event.client.send_message(event.chat_id, "`Preparing to upload...`")
        
        upload_name = Path(out).name
        upload_start_time = time.time()
        with open(out, "rb") as f:
            ok = await upload_file(
                client=event.client, file=f, name=upload_name,
                progress_callback=lambda d, t: progress(d, t, nnn, upload_start_time, "Uploading File", upload_name)
            )
        
        upload_time = ts(int((time.time() - upload_start_time) * 1000))
        await nnn.delete()

        thumb_path = "thumb.jpg" if os.path.exists("thumb.jpg") else None
        ds = await event.client.send_file(
            event.chat_id, file=ok, force_document=True, thumb=thumb_path, caption=f"`{upload_name}`"
        )
        
        org_size, com_size = os.path.getsize(dl), os.path.getsize(out)
        reduction = 100 - (com_size / org_size * 100) if org_size > 0 else 0
        info_before, info_after = await info(dl), await info(out)
        
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
        if info_before and info_after:
            stats_msg += f"📋 **MediaInfo**: [Before]({info_before}) | [After]({info_after})"
        
        await ds.reply(stats_msg, link_preview=False)
        
    except Exception as e:
        LOGS.error(f"Upload error: {e}", exc_info=True)
        await event.edit(f"❌ **UPLOAD ERROR**: `{str(e)}`")