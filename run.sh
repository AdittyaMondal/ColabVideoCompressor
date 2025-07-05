#!/bin/bash

# Enhanced Compressor Bot Startup Script
echo "🚀 Starting Enhanced Compressor Bot..."

# Check if running in Google Colab
if [ -d "/content" ]; then
    echo "☁️ Google Colab environment detected"
    
    # Run Colab setup if needed
    if [ ! -f "/tmp/colab_setup_done" ]; then
        echo "🔧 Running Colab setup..."
        python3 colab_setup.py
        touch /tmp/colab_setup_done
    fi
    
    # Check for GPU
    if command -v nvidia-smi &> /dev/null; then
        echo "🚀 NVIDIA GPU detected:"
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    else
        echo "💻 No GPU detected, using CPU encoding"
    fi
else
    echo "🖥️ Standard environment detected"
fi

# Check FFmpeg installation
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg not found! Installing..."
    if command -v apt &> /dev/null; then
        apt update && apt install -y ffmpeg
    elif command -v yum &> /dev/null; then
        yum install -y ffmpeg
    else
        echo "❌ Cannot install FFmpeg automatically"
        exit 1
    fi
fi

# Check Python dependencies
echo "📦 Checking Python dependencies..."
python3 -c "import telethon, aiohttp, psutil, pymediainfo" 2>/dev/null || {
    echo "📦 Installing Python dependencies..."
    pip3 install -r requirements.txt
}

# Create necessary directories
mkdir -p downloads encode thumb

# Start the bot
echo "✅ Starting bot..."
python3 -m bot
