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
    """Process link download with retry mechanism"""
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

        # Check for already compressed files
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
    """Process file encoding with retry mechanism"""
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
    """Common compression processing logic"""
    out = None
    try:
        es = dt.now()
        original_name = Path(dl).stem
        out = f"encode/{original_name}_compressed.mkv"
        
        dtime = ts(int((es - start_time).total_seconds()) * 1000)
        
        # Using event.id to ensure the button payload is unique to the message
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
        
        cmd = FFMPEG.format(dl, out)
        LOGS.info(f"Executing FFmpeg command: {cmd}")
        
        process = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            er = stderr.decode()
            LOGS.error(f"FFMPEG Error: {er}")
            await event.edit(f"❌ **COMPRESSION ERROR**\n\n```{er[:3500]}```")
            return

        if not os.path.exists(out) or os.path.getsize(out) == 0:
            await event.edit("❌ **COMPRESSION FAILED** - Output file not created or is empty.")
            return
        
        await upload_compressed_file(event, nn, dl, out, dtime, start_time)
        
    except Exception as e:
        LOGS.error(f"Compression process error: {e}")
        await event.edit(f"❌ **COMPRESSION ERROR**: `{str(e)}`")
    finally:
        # Cleanup both files
        for f in [dl, out]:
            if f and os.path.exists(f) and validate_file_path(f):
                os.remove(f)

async def upload_compressed_file(event, nn, dl, out, dtime, start_time):
    """Upload compressed file with progress tracking"""
    try:
        ees = dt.now()
        ttt = time.time()
        await nn.delete()
        nnn = await event.client.send_message(event.chat_id, "`Preparing to upload...`")
        
        upload_name = Path(out).name
        with open(out, "rb") as f:
            ok = await upload_file(
                client=event.client,
                file=f,
                name=upload_name,
                progress_callback=lambda d, t: progress(d, t, nnn, ttt, "Uploading File", upload_name)
            )
        
        await nnn.delete()

        # Download thumbnail if it doesn't exist
        if not os.path.exists("thumb.jpg"):
             os.system(f"wget {THUMB} -O thumb.jpg")

        thumb_path = "thumb.jpg" if os.path.exists("thumb.jpg") else None

        ds = await event.client.send_file(
            event.chat_id, file=ok, force_document=True, thumb=thumb_path, caption=f"`{upload_name}`"
        )
        
        # Calculate stats
        org_size = os.path.getsize(dl)
        com_size = os.path.getsize(out)
        reduction = 100 - ((com_size / org_size) * 100) if org_size > 0 else 0
        
        eees = dt.now()
        ctime = ts(int((ees - ees).total_seconds()) * 1000) # This seems incorrect, let's fix
        comp_time = ts(int((ees - start_time).total_seconds() * 1000) - int(dtime.replace('s',''))*1000)
        upload_time = ts(int((dt.now() - ees).total_seconds()) * 1000)

        # Generate mediainfo links
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