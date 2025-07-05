from .FastTelethon import download_file, upload_file
from .funcn import *

async def stats(e):
    try:
        wah = e.pattern_match.group(1).decode("UTF-8")
        wh = decode(wah)
        if not wh:
            return await e.answer("Invalid stats request", cache_time=0, alert=True)
            
        out, dl, id = wh.split(";")
        
        if not validate_file_path(out) or not validate_file_path(dl):
            return await e.answer("Invalid file paths", cache_time=0, alert=True)
        
        if not os.path.exists(out) or not os.path.exists(dl):
            return await e.answer("Files not found, process may have completed or been cancelled.", cache_time=0, alert=True)
            
        ot = hbs(int(Path(out).stat().st_size))
        ov = hbs(int(Path(dl).stat().st_size))
        
        gpu_info = f"\n🚀 Using: {GPU_TYPE.upper()}"
        ans = f"Original: {ov}\nCompressed: {ot}{gpu_info}"
        await e.answer(ans, cache_time=0, alert=True)
    except Exception as er:
        LOGS.error(f"Stats error: {er}")
        await e.answer("Something went wrong 🤔\nResend Media", cache_time=0, alert=True)

async def dl_link(event):
    if not event.is_private:
        return
    if str(event.sender_id) not in OWNER:
        return
    
    parts = event.text.split(maxsplit=2)
    link, name = "", ""
    if len(parts) > 1:
        link = parts[1]
    if len(parts) > 2:
        name = parts[2]
    
    if not link:
        return await event.reply("❌ **Invalid command.**\n**Usage:** `/link <url> [custom_filename.ext]`")
    
    if not link.startswith(('http://', 'https://')):
        return await event.reply("❌ Invalid URL. It must start with `http://` or `https://`.")
    
    if bot_state.is_working() or bot_state.queue_size() > 0:
        if not bot_state.add_to_queue(link, name):
            return await event.reply(f"❌ Queue is full (max {MAX_QUEUE_SIZE})")
        return await event.reply(f"✅ Added to queue at position #{bot_state.queue_size()}")
    
    await process_link_download(event, link, name)

async def process_link_download(event, link, name):
    bot_state.set_working(True)
    s = dt.now()
    xxx = await event.reply(f"`Analysing link...`")

    try:
        dl = await fast_download(xxx, link, name)
        
        file_size_mb = get_file_size_mb(dl)
        if file_size_mb > MAX_FILE_SIZE:
            os.remove(dl)
            bot_state.clear_working()
            return await xxx.edit(f"❌ File too large: {file_size_mb:.1f}MB > {MAX_FILE_SIZE}MB")
        
        await process_compression(xxx, dl, s)
        
    except Exception as er:
        LOGS.error(f"Link download failed: {er}")
        await xxx.edit(f"❌ **Download failed:**\n`{str(er)}`")
    finally:
        bot_state.clear_working()


async def encod(event):
    try:
        if not event.is_private or not event.media or str(event.sender_id) not in OWNER:
            return

        if not hasattr(event.media, "document") or not event.media.document.mime_type.startswith("video"):
            return

        if event.fwd_from:
            me_id = (await event.client.get_me()).id
            if hasattr(event.fwd_from.from_id, 'user_id') and event.fwd_from.from_id.user_id == me_id:
                return await event.reply("`This video seems to be already compressed by me. 😑`")

        doc = event.media.document
        
        if doc.size > MAX_FILE_SIZE * 1024 * 1024:
            return await event.reply(f"❌ File is too large: {hbs(doc.size)}. Maximum allowed size is {MAX_FILE_SIZE}MB.")
        
        if bot_state.is_working() or bot_state.queue_size() > 0:
            if bot_state.is_in_queue(doc.id):
                return await event.reply("`This file is already in the queue.`")
            
            name = event.file.name or f"video_{doc.id}.mp4"
            
            if not bot_state.add_to_queue(doc.id, [name, doc]):
                return await event.reply(f"❌ Queue is full (max {MAX_QUEUE_SIZE}). Please wait.")
            
            return await event.reply(f"`✅ Added to queue at position #{bot_state.queue_size()}`")
        
        await process_file_encoding(event)
        
    except Exception as er:
        LOGS.error(f"Encoding handler error: {er}")
        bot_state.clear_working()


async def process_file_encoding(event):
    bot_state.set_working(True)
    xxx = await event.reply("`Preparing to download...`")
    s = dt.now()
    ttt = time.time()
    
    dl = None
    try:
        file = event.media.document
        filename = event.file.name or f"video_{file.id}.mp4"
        filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        dl = os.path.join("downloads/", filename)

        with open(dl, "wb") as f:
            await download_file(
                client=event.client,
                location=file,
                out=f,
                progress_callback=lambda d, t: progress(d, t, xxx, ttt, "Downloading File", filename)
            )
        
        await process_compression(xxx, dl, s)
        
    except Exception as er:
        LOGS.error(f"File encoding process failed: {er}")
        if xxx:
            await xxx.edit(f"❌ **Processing failed:**\n`{str(er)}`")
    finally:
        bot_state.clear_working()
        if dl and os.path.exists(dl) and validate_file_path(dl):
            os.remove(dl)


async def process_compression(event, dl, start_time):
    """Common compression processing logic with dynamic command building."""
    out = None
    try:
        # Mark download end time / compression start time
        compress_start_time = dt.now()
        original_name = Path(dl).stem
        os.makedirs("encode/", exist_ok=True)
        out = f"encode/{original_name}_compressed.mkv"
        
        dtime = ts(int((compress_start_time - start_time).total_seconds()) * 1000)
        
        unique_id = event.id
        hehe = f"{out};{dl};{unique_id}"
        wah = code(hehe)
        
        gpu_info = f" (🚀 {GPU_TYPE.upper()})" if GPU_TYPE != "cpu" else ""
        nn = await event.edit(
            f"`✅ Downloaded in {dtime}`\n\n`🔄 Compressing{gpu_info}...`",
            buttons=[
                [Button.inline("📊 STATS", data=f"stats{wah}")],
                [Button.inline("❌ CANCEL", data=f"skip{wah}")],
            ],
        )

        # === DYNAMIC FFMPEG COMMAND BUILDING ===
        scale_filter = f'-vf scale=-2:{V_SCALE}' if V_SCALE != -1 else ''
        
        if GPU_TYPE == "nvidia":
            cmd = (
                f'ffmpeg -y -hide_banner -loglevel error -hwaccel cuda -i "{dl}" '
                f'-c:v hevc_nvenc -preset {V_PRESET} -rc constqp -qp {V_QP} {scale_filter} '
                f'-c:a aac -b:a {A_BITRATE} -movflags +faststart "{out}"'
            )
        else: # Fallback for CPU
            cmd = (
                f'ffmpeg -y -hide_banner -loglevel error -i "{dl}" '
                f'-c:v libx264 -preset veryfast -crf {V_QP} {scale_filter} '
                f'-c:a aac -b:a {A_BITRATE} -movflags +faststart "{out}"'
            )
        # =========================================

        LOGS.info(f"Executing FFmpeg command: {cmd}")
        
        process = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()
        
        if process.returncode != 0:
            er = stderr.decode()
            LOGS.error(f"FFMPEG Error: {er}")
            await event.edit(f"❌ **COMPRESSION ERROR**\n\n```{er[:3500]}```")
            return

        if not os.path.exists(out) or os.path.getsize(out) == 0:
            await event.edit("❌ **COMPRESSION FAILED**\nOutput file not created or is empty.")
            return
        
        await upload_compressed_file(event, nn, dl, out, dtime, compress_start_time)
        
    except Exception as e:
        LOGS.error(f"Compression process error: {e}")
        await event.edit(f"❌ **COMPRESSION ERROR**: `{str(e)}`")
    finally:
        for f in [dl, out]:
            if f and os.path.exists(f) and validate_file_path(f):
                os.remove(f)

async def upload_compressed_file(event, nn, dl, out, dtime, compress_start_time):
    """Upload compressed file with progress tracking and accurate timing."""
    try:
        # Mark compression end time / upload start time
        compress_end_time = dt.now()
        comp_time = ts(int((compress_end_time - compress_start_time).total_seconds()) * 1000)
        
        await nn.delete()
        nnn = await event.client.send_message(event.chat_id, "`Preparing to upload...`")
        
        upload_name = Path(out).name
        upload_start_time = time.time()
        with open(out, "rb") as f:
            ok = await upload_file(
                client=event.client,
                file=f,
                name=upload_name,
                progress_callback=lambda d, t: progress(d, t, nnn, upload_start_time, "Uploading File", upload_name)
            )
        
        upload_time = ts(int((time.time() - upload_start_time) * 1000))
        await nnn.delete()

        if not os.path.exists("thumb.jpg"):
             os.system(f"wget {THUMB} -O thumb.jpg")

        thumb_path = "thumb.jpg" if os.path.exists("thumb.jpg") else None

        ds = await event.client.send_file(
            event.chat_id, file=ok, force_document=True, thumb=thumb_path, caption=f"`{upload_name}`"
        )
        
        org_size = os.path.getsize(dl)
        com_size = os.path.getsize(out)
        reduction = 100 - ((com_size / org_size) * 100) if org_size > 0 else 0
        
        info_before = await info(dl, event)
        info_after = await info(out, event)
        
        gpu_info = f"\n🚀 **Engine**: {GPU_TYPE.upper()}"
        
        stats_message = (
            f"✅ **COMPRESSION COMPLETE**\n\n"
            f"📁 **Original Size**: {hbs(org_size)}\n"
            f"📦 **Compressed Size**: {hbs(com_size)} ({reduction:.2f}% reduction)\n\n"
            f"⏱️ **Time Taken:**\n"
            f"  - **Download**: {dtime}\n"
            f"  - **Compress**: {comp_time}\n"
            f"  - **Upload**: {upload_time}{gpu_info}\n\n"
        )

        if info_before and info_after:
             stats_message += f"📋 **MediaInfo**: [Before]({info_before}) | [After]({info_after})"
        
        await ds.reply(stats_message, link_preview=False)
        
    except Exception as e:
        LOGS.error(f"Upload error: {e}")
        await event.edit(f"❌ **UPLOAD ERROR**: `{str(e)}`")

def cleanup_files(file_paths):
    """Safely cleanup files"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path) and validate_file_path(file_path):
                os.remove(file_path)
                LOGS.info(f"Cleaned up: {file_path}")
        except Exception as e:
            LOGS.error(f"Cleanup error for {file_path}: {e}")