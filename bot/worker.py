#    This file is part of the CompressorQueue distribution.
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

from .FastTelethon import download_file, upload_file
from .funcn import *

MAX_RETRIES = 3

async def stats(e):
    try:
        wah = e.pattern_match.group(1).decode("UTF-8")
        wh = decode(wah)
        if not wh:
            return await e.answer("Invalid stats request", cache_time=0, alert=True)
            
        out, dl, id = wh.split(";")
        
        # Validate file paths
        if not validate_file_path(out) or not validate_file_path(dl):
            return await e.answer("Invalid file paths", cache_time=0, alert=True)
        
        if not os.path.exists(out) or not os.path.exists(dl):
            return await e.answer("Files not found", cache_time=0, alert=True)
            
        ot = hbs(int(Path(out).stat().st_size))
        ov = hbs(int(Path(dl).stat().st_size))
        
        # Add GPU info
        gpu_info = f"\n🚀 Using: {GPU_TYPE.upper()}"
        ans = f"Downloaded:\n{ov}\n\nCompressing:\n{ot}{gpu_info}"
        await e.answer(ans, cache_time=0, alert=True)
    except Exception as er:
        LOGS.error(f"Stats error: {er}")
        await e.answer("Something went wrong 🤔\nResend Media", cache_time=0, alert=True)

async def dl_link(event):
    if not event.is_private:
        return
    if str(event.sender_id) not in OWNER:
        return
    
    link, name = "", ""
    try:
        link = event.text.split()[1]
        name = event.text.split()[2] if len(event.text.split()) > 2 else ""
    except BaseException:
        pass
    
    if not link:
        return await event.reply("❌ Please provide a valid link")
    
    # Validate URL
    if not link.startswith(('http://', 'https://')):
        return await event.reply("❌ Invalid URL format")
    
    if bot_state.is_working() or bot_state.queue_size() > 0:
        if not bot_state.add_to_queue(link, name):
            return await event.reply(f"❌ Queue is full (max {MAX_QUEUE_SIZE})")
        return await event.reply(f"✅ Added {link} to queue #{bot_state.queue_size()}")
    
    await process_link_download(event, link, name)

async def process_link_download(event, link, name):
    """Process link download with retry mechanism"""
    bot_state.set_working(True)
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        try:
            s = dt.now()
            xxx = await event.reply(f"`🔄 Downloading... (Attempt {retry_count + 1}/{MAX_RETRIES})`")
            
            dl = await fast_download(xxx, link, name)
            
            # Check file size
            file_size_mb = get_file_size_mb(dl)
            if file_size_mb > MAX_FILE_SIZE:
                os.remove(dl)
                bot_state.clear_working()
                return await xxx.edit(f"❌ File too large: {file_size_mb:.1f}MB > {MAX_FILE_SIZE}MB")
            
            await process_compression(xxx, dl, s, is_link=True)
            bot_state.clear_working()
            return
            
        except Exception as er:
            retry_count += 1
            LOGS.error(f"Download attempt {retry_count} failed: {er}")
            
            if retry_count >= MAX_RETRIES:
                bot_state.clear_working()
                return await xxx.edit(f"❌ Download failed after {MAX_RETRIES} attempts: {str(er)}")
            
            await asyncio.sleep(2 ** retry_count)  # Exponential backoff

async def encod(event):
    try:
        if not event.is_private:
            return
        if str(event.sender_id) not in OWNER:
            return
        if not event.media:
            return
        
        if hasattr(event.media, "document"):
            if not event.media.document.mime_type.startswith(
                ("video", "application/octet-stream")
            ):
                return
        else:
            return
        
        # Check for already compressed files
        try:
            oc = event.fwd_from.from_id.user_id
            occ = (await event.client.get_me()).id
            if oc == occ:
                return await event.reply(
                    "`This Video File is already Compressed 😑😑.`"
                )
        except BaseException:
            pass
        
        doc = event.media.document
        
        # Check file size
        if doc.size > MAX_FILE_SIZE * 1024 * 1024:
            return await event.reply(f"❌ File too large: {hbs(doc.size)} > {MAX_FILE_SIZE}MB")
        
        if bot_state.is_working() or bot_state.queue_size() > 0:
            xxx = await event.reply("`Adding To Queue`")
            
            if bot_state.is_in_queue(doc.id):
                return await xxx.edit("`THIS FILE ALREADY IN QUEUE`")
            
            name = event.file.name
            if not name:
                name = "video_" + dt.now().isoformat("_", "seconds") + ".mp4"
            
            if not bot_state.add_to_queue(doc.id, [name, doc]):
                return await xxx.edit(f"❌ Queue is full (max {MAX_QUEUE_SIZE})")
            
            return await xxx.edit(f"`✅ Added to Queue #{bot_state.queue_size()}`")
        
        await process_file_encoding(event)
        
    except Exception as er:
        LOGS.error(f"Encoding error: {er}")
        bot_state.clear_working()

async def process_file_encoding(event):
    """Process file encoding with retry mechanism"""
    bot_state.set_working(True)
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        try:
            xxx = await event.reply(f"`🔄 Downloading... (Attempt {retry_count + 1}/{MAX_RETRIES})`")
            s = dt.now()
            ttt = time.time()
            dir = f"downloads/"
            
            if hasattr(event.media, "document"):
                file = event.media.document
                filename = event.file.name
                if not filename:
                    filename = "video_" + dt.now().isoformat("_", "seconds") + ".mp4"
                
                # Sanitize filename
                filename = "".join(c for c in filename if c.isalnum() or c in "._-")
                dl = os.path.join(dir, filename)
                
                with open(dl, "wb") as f:
                    await download_file(
                        client=event.client,
                        location=file,
                        out=f,
                        progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                            progress(d, t, xxx, ttt, "Downloading")
                        ),
                    )
            else:
                dl = await event.client.download_media(
                    event.media,
                    dir,
                    progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                        progress(d, t, xxx, ttt, "Downloading")
                    ),
                )
            
            await process_compression(xxx, dl, s)
            bot_state.clear_working()
            return
            
        except Exception as er:
            retry_count += 1
            LOGS.error(f"Encoding attempt {retry_count} failed: {er}")
            
            if retry_count >= MAX_RETRIES:
                bot_state.clear_working()
                if 'dl' in locals() and os.path.exists(dl):
                    os.remove(dl)
                return await xxx.edit(f"❌ Processing failed after {MAX_RETRIES} attempts: {str(er)}")
            
            await asyncio.sleep(2 ** retry_count)  # Exponential backoff

async def process_compression(event, dl, start_time, is_link=False):
    """Common compression processing logic"""
    try:
        es = dt.now()
        kk = dl.split("/")[-1]
        aa = kk.split(".")[-1]
        rr = "encode"
        bb = kk.replace(f".{aa}", "_compressed.mkv")
        out = f"{rr}/{bb}"
        thum = "thumb.jpg"
        dtime = ts(int((es - start_time).seconds) * 1000)
        
        hehe = f"{out};{dl};0"
        wah = code(hehe)
        
        # Add GPU info to compression message
        gpu_info = f" (🚀 {GPU_TYPE.upper()})" if GPU_TYPE != "cpu" else ""
        nn = await event.edit(
            f"`🔄 Compressing{gpu_info}...`",
            buttons=[
                [Button.inline("📊 STATS", data=f"stats{wah}")],
                [Button.inline("❌ CANCEL", data=f"skip{wah}")],
            ],
        )
        
        # Use GPU-optimized FFmpeg command
        cmd = FFMPEG.format(dl, out)
        LOGS.info(f"Compression command: {cmd}")
        
        process = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        er = stderr.decode()
        
        if er and process.returncode != 0:
            await event.edit(f"❌ **COMPRESSION ERROR**\n```{er[:1000]}```\n\nContact @danish_00")
            cleanup_files([dl, out])
            return
        
        if not os.path.exists(out):
            await event.edit("❌ **COMPRESSION FAILED** - Output file not created")
            cleanup_files([dl])
            return
        
        await upload_compressed_file(event, nn, dl, out, dtime, start_time)
        
    except Exception as e:
        LOGS.error(f"Compression error: {e}")
        cleanup_files([dl, out] if 'out' in locals() else [dl])
        await event.edit(f"❌ **COMPRESSION ERROR**: {str(e)}")

async def upload_compressed_file(event, nn, dl, out, dtime, start_time):
    """Upload compressed file with progress tracking"""
    try:
        ees = dt.now()
        ttt = time.time()
        await nn.delete()
        nnn = await event.client.send_message(event.chat_id, "`📤 Uploading...`")
        
        with open(out, "rb") as f:
            ok = await upload_file(
                client=event.client,
                file=f,
                name=out,
                progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                    progress(d, t, nnn, ttt, "Uploading")
                ),
            )
        
        fname = out.split("/")[1]
        ds = await event.client.send_file(
            event.chat_id, file=ok, force_document=True, thumb="thumb.jpg", caption=f"`{fname}`"
        )
        await nnn.delete()
        
        # Calculate compression stats
        org = int(Path(dl).stat().st_size)
        com = int(Path(out).stat().st_size)
        pe = 100 - ((com / org) * 100)
        per = str(f"{pe:.2f}") + "%"
        
        eees = dt.now()
        x = dtime
        xx = ts(int((ees - ees).seconds) * 1000)
        xxx = ts(int((eees - ees).seconds) * 1000)
        
        # Generate mediainfo
        a1 = await info(dl, event)
        a2 = await info(out, event)
        
        # Add GPU info to final message
        gpu_info = f"\n🚀 **Accelerated by**: {GPU_TYPE.upper()}"
        
        stats_message = (
            f"📊 **COMPRESSION COMPLETE**\n\n"
            f"📁 **Original Size**: {hbs(org)}\n"
            f"📦 **Compressed Size**: {hbs(com)}\n"
            f"📉 **Compression**: {per}\n\n"
            f"⏱️ **Downloaded in**: {x}\n"
            f"⚡ **Compressed in**: {xx}\n"
            f"📤 **Uploaded in**: {xxx}{gpu_info}\n\n"
            f"📋 **MediaInfo**: [Before]({a1}) // [After]({a2})"
        )
        
        await ds.reply(stats_message, link_preview=False)
        
        # Cleanup
        cleanup_files([dl, out])
        
    except Exception as e:
        LOGS.error(f"Upload error: {e}")
        cleanup_files([dl, out])
        await event.edit(f"❌ **UPLOAD ERROR**: {str(e)}")

def cleanup_files(file_paths):
    """Safely cleanup files"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path) and validate_file_path(file_path):
                os.remove(file_path)
                LOGS.info(f"Cleaned up: {file_path}")
        except Exception as e:
            LOGS.error(f"Cleanup error for {file_path}: {e}")
