#!/usr/bin/env python3
"""
Google Colab Setup Script for Enhanced Compressor Bot
Automatically configures the environment for optimal GPU performance
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, check=True):
    """Run shell command with error handling"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {cmd}")
        print(f"Error: {e.stderr}")
        if check:
            sys.exit(1)
        return None

def setup_colab_environment():
    """Setup Google Colab environment for the bot"""
    print("🚀 Setting up Enhanced Compressor Bot for Google Colab...")
    
    # Check if running in Colab
    if not os.path.exists('/content'):
        print("❌ This script is designed for Google Colab environment")
        return False
    
    # Mount Google Drive
    print("📁 Mounting Google Drive...")
    try:
        from google.colab import drive
        drive.mount('/content/drive')
        print("✅ Google Drive mounted successfully")
    except Exception as e:
        print(f"⚠️ Drive mount failed: {e}")
    
    # Create bot directory structure
    bot_dir = "/content/CompressorBot"
    output_dir = "/content/drive/MyDrive/CompressorBot"
    
    for directory in [bot_dir, output_dir, f"{output_dir}/downloads", f"{output_dir}/encode"]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print(f"✅ Created directory structure")
    
    # Check GPU availability
    print("🔍 Checking GPU availability...")
    gpu_info = run_command("nvidia-smi", check=False)
    if gpu_info:
        print("✅ NVIDIA GPU detected:")
        print(run_command("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader"))
    else:
        print("⚠️ No NVIDIA GPU detected, will use CPU encoding")
    
    # Install system dependencies
    print("📦 Installing system dependencies...")
    system_deps = [
        "apt update -qq",
        "apt install -y -qq ffmpeg mediainfo wget curl",
        "apt install -y -qq vainfo intel-media-va-driver-non-free"  # For Intel GPU support
    ]
    
    for cmd in system_deps:
        run_command(cmd)
    
    print("✅ System dependencies installed")
    
    # Install Python dependencies
    print("🐍 Installing Python dependencies...")
    run_command("pip install -q -r requirements.txt")
    print("✅ Python dependencies installed")
    
    # Setup FFmpeg with GPU support
    print("⚡ Configuring FFmpeg for GPU acceleration...")
    ffmpeg_info = run_command("ffmpeg -encoders 2>/dev/null | grep nvenc", check=False)
    if ffmpeg_info:
        print("✅ NVIDIA hardware encoding available")
    else:
        print("⚠️ NVIDIA hardware encoding not available, using software encoding")
    
    # Create environment file template
    env_template = """# Enhanced Compressor Bot Configuration
# Copy this to .env and fill in your values

# Required Telegram API credentials
APP_ID=your_app_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
OWNER=your_telegram_user_id

# Optional settings
THUMBNAIL=https://envs.sh/F82.jpg
MAX_FILE_SIZE=2000
MAX_QUEUE_SIZE=10

# Security settings (set to true only if needed)
ENABLE_EVAL=false
ENABLE_BASH=false

# FFmpeg will be auto-configured based on available hardware
# FFMPEG=custom_ffmpeg_command_if_needed
"""
    
    with open(f"{bot_dir}/.env.template", "w") as f:
        f.write(env_template)
    
    print("✅ Environment template created")
    
    # Create startup script
    startup_script = f"""#!/bin/bash
# Enhanced Compressor Bot Startup Script for Colab

cd {bot_dir}

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Please create .env file from .env.template"
    echo "📝 Edit the .env file with your Telegram credentials"
    exit 1
fi

# Start the bot
echo "🚀 Starting Enhanced Compressor Bot..."
python3 -m bot
"""
    
    with open(f"{bot_dir}/start_bot.sh", "w") as f:
        f.write(startup_script)
    
    os.chmod(f"{bot_dir}/start_bot.sh", 0o755)
    print("✅ Startup script created")
    
    # Display setup completion message
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    print(f"📁 Bot directory: {bot_dir}")
    print(f"💾 Output directory: {output_dir}")
    print("\n📋 NEXT STEPS:")
    print("1. Copy your bot files to the bot directory")
    print("2. Create .env file from .env.template")
    print("3. Fill in your Telegram API credentials")
    print("4. Run: bash start_bot.sh")
    print("\n🚀 GPU acceleration will be automatically enabled if available!")
    print("="*60)
    
    return True

def check_gpu_performance():
    """Check GPU performance and provide optimization tips"""
    print("\n🔍 GPU Performance Check...")
    
    # Check GPU memory
    gpu_memory = run_command("nvidia-smi --query-gpu=memory.total,memory.used,memory.free --format=csv,noheader,nounits", check=False)
    if gpu_memory:
        total, used, free = map(int, gpu_memory.split(', '))
        print(f"📊 GPU Memory: {used}MB used / {total}MB total ({free}MB free)")
        
        if free < 1000:
            print("⚠️ Low GPU memory available. Consider:")
            print("   - Reducing MAX_FILE_SIZE")
            print("   - Processing smaller files")
            print("   - Restarting runtime to free memory")
    
    # Check GPU utilization
    gpu_util = run_command("nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits", check=False)
    if gpu_util:
        util = int(gpu_util)
        print(f"⚡ GPU Utilization: {util}%")
        
        if util > 90:
            print("🔥 High GPU utilization - performance is optimal!")
        elif util < 10:
            print("💡 Low GPU utilization - check if GPU encoding is enabled")

if __name__ == "__main__":
    if setup_colab_environment():
        check_gpu_performance()
