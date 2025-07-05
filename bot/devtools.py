from .stuff import *

async def eval(event):
    """Eval command handler with enhanced security"""
    if str(event.sender_id) not in OWNER:
        return
    
    # Security check
    if not ENABLE_EVAL:
        return await event.reply("⚠️ Eval command is disabled for security reasons.")
    
    try:
        cmd = event.text.split(" ", maxsplit=1)[1]
    except IndexError:
        return await event.reply("❌ Please provide code to evaluate")
    
    # Security filtering
    dangerous_keywords = [
        'import os', 'import subprocess', 'exec(', 'eval(', '__import__', 
        'open(', 'file(', 'system(', 'delete(', 'remove('
    ]
    if any(keyword in cmd.lower() for keyword in dangerous_keywords):
        return await event.reply("⚠️ Command contains potentially dangerous operations.")
    
    msg = await event.reply("🔄 Processing...")
    
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    redirected_error = sys.stderr = io.StringIO()
    stdout, stderr, exc = None, None, None
    
    try:
        # Add timeout to prevent infinite loops
        with asyncio.timeout(30):  # 30 seconds timeout
            await aexec(cmd, event)
    except asyncio.TimeoutError:
        evaluation = "❌ Execution timed out (30s limit)"
    except Exception as e:
        exc = traceback.format_exc()
        evaluation = str(e)
    
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    
    if exc:
        evaluation = exc
    elif stderr:
        evaluation = stderr
    elif stdout:
        evaluation = stdout
    else:
        evaluation = "✅ Success"
    
    final_output = f"**📝 Code:**\n`{cmd}`\n\n**📤 Output:**\n`{evaluation}`"
    
    if len(final_output) > 4095:
        with io.BytesIO(str.encode(final_output)) as out_file:
            out_file.name = "eval_output.txt"
            await event.client.send_file(
                event.chat_id,
                out_file,
                force_document=True,
                allow_cache=False,
                caption="`Output too long, sent as file.`",
            )
            await msg.delete()
    else:
        await msg.edit(final_output)

async def aexec(code, event):
    """Execute async code"""
    exec(
        f'async def __aexec(event): ' +
        ''.join(f'\n {l}' for l in code.split('\n'))
    )
    return await locals()['__aexec'](event)

async def bash(event):
    """Bash command handler with enhanced security"""
    if str(event.sender_id) not in OWNER:
        return
    
    # Security check
    if not ENABLE_BASH:
        return await event.reply("⚠️ Bash command is disabled for security reasons.")
    
    try:
        cmd = event.text.split(" ", maxsplit=1)[1]
    except IndexError:
        return await event.reply("❌ Please provide a command to execute")
    
    # Security filtering
    dangerous_commands = [
        'rm -rf', 'mkfs', 'dd', 'fork', 'while true', ':(){:|:&};:', 
        'chmod 777', 'sudo', '> /dev/', 'mv /', 'cp /'
    ]
    if any(cmd in cmd.lower() for cmd in dangerous_commands):
        return await event.reply("⚠️ Command contains potentially dangerous operations.")
    
    msg = await event.reply("🔄 Executing...")
    
    try:
        # Add timeout to prevent hanging
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60  # 60 seconds timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            return await msg.edit("❌ Command execution timed out (60s limit)")
        
        err = stderr.decode().strip() or "No errors"
        out = stdout.decode().strip() or "No output"
        
        output = (
            f"**💻 Command:**\n`{cmd}`\n\n"
            f"**📤 Output:**\n`{out}`\n\n"
            f"**⚠️ Errors:**\n`{err}`\n\n"
            f"**🔄 Exit Code:**\n`{process.returncode}`"
        )
        
        if len(output) > 4095:
            with io.BytesIO(str.encode(output)) as out_file:
                out_file.name = "bash_output.txt"
                await event.client.send_file(
                    event.chat_id,
                    out_file,
                    force_document=True,
                    allow_cache=False,
                    caption="`Output too long, sent as file.`",
                )
                await msg.delete()
        else:
            await msg.edit(output)
            
    except Exception as e:
        await msg.edit(f"❌ **Error:**\n`{str(e)}`")
