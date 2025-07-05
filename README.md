# 🎥 Colab Video Compressor

A powerful Telegram bot for video compression with GPU acceleration, optimized for Google Colab.

## 🚀 Quick Start

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AdittyaMondal/ColabVideoCompressor/blob/main/colab_notebook.ipynb)

Click the "Open in Colab" button above to instantly deploy your bot!

## ✨ Features

- 🎮 **GPU Acceleration** - Utilizes Colab's GPU for faster compression
- 🔄 **Queue System** - Handle multiple videos efficiently
- 📊 **Real-time Progress** - Track compression status live
- 🎛️ **Multiple Presets** - From ultra-fast to high quality
- 🛠️ **Custom Settings** - Fine-tune your compression parameters
- 🔒 **Secure** - Enhanced security features

## 🔧 Configuration

Required environment variables:
```env
APP_ID=your_app_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
OWNER=your_telegram_id
```

Optional settings:
```env
THUMBNAIL=thumbnail_url
MAX_FILE_SIZE=2000
MAX_QUEUE_SIZE=10
```

## 📋 Commands

- `/start` - Start the bot
- `/help` - Show help message
- `/ping` - Check bot response
- `/status` - Show bot status
- `/link` - Process video from URL
- `/usage` - Show system stats

## 🎯 Compression Presets

1. **Ultra Fast**
   - Best for quick 10-minute compressions
   - Lower quality, fastest speed

2. **Balanced** (Recommended)
   - Good balance of quality and speed
   - 720p output with optimized settings

3. **High Quality**
   - Better quality, slower compression
   - 1080p output with enhanced settings

4. **Max Quality**
   - Best quality, slowest compression
   - 1080p output with maximum settings

5. **Custom**
   - Customize resolution, CRF, presets
   - Fine-tune all encoding parameters

## 🖥️ Google Colab Usage

1. Click the "Open in Colab" button above
2. Fill in your Telegram credentials
3. Select your preferred compression preset
4. Run the notebook
5. Start sending videos to your bot!

## ⚡ Performance Tips

- Use "Ultra Fast" preset for quick compressions
- "Balanced" preset works best for most videos
- Enable GPU runtime in Colab for best performance
- Keep files under 10 minutes for Colab's time limits
- Use "High Quality" preset only for important videos

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Credits

- Original concept inspired by video compression tools
- Enhanced and optimized for Google Colab
