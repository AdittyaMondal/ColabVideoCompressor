# 🎥 Enhanced Video Compressor Bot

A powerful Telegram bot for video compression with GPU acceleration, dynamic settings management, and real-time configuration. Optimized for Google Colab with comprehensive features for professional video processing.

## 🚀 Quick Start

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AdittyaMondal/ColabVideoCompressor/blob/main/colab_notebook.ipynb)

Click the "Open in Colab" button above to instantly deploy your bot with enhanced features!

## ✨ Key Features

### �️ **Dynamic Settings Management**
- **Real-time Configuration** - Change all settings through the bot without restarting
- **Per-user Settings** - Each user maintains their own compression preferences
- **Persistent Storage** - Settings automatically saved and restored
- **Interactive Menus** - Easy-to-use inline keyboard interfaces

### 🎬 **Advanced Compression**
- **GPU Acceleration** - NVIDIA NVENC hardware encoding for ultra-fast compression
- **Smart Presets** - Auto-detected hardware-optimized presets
- **Custom Compression** - Full control over codecs, quality, resolution, and FPS
- **Multiple Formats** - Support for H.264, H.265, and various quality levels

### 📸 **Media Enhancement**
- **Video Previews** - Generate short preview clips with configurable duration
- **Screenshot Generation** - Multiple screenshots at optimal timestamps
- **Real-time Thumbnails** - Upload custom thumbnails or auto-generate from video
- **Watermark Support** - Customizable text watermarks with position control

### ⚡ **Performance & Reliability**
- **Queue System** - Handle multiple videos efficiently with progress tracking
- **Real-time Monitoring** - Live compression progress and system status
- **Error Recovery** - Robust error handling and automatic retries
- **Resource Management** - Optimized for Colab's time and resource limits

## 🔧 Setup & Configuration

### **Required Credentials (Colab Only)**
Set these in the Colab notebook - all other settings are managed through the bot:

```env
APP_ID=your_app_id          # Get from my.telegram.org
API_HASH=your_api_hash      # Get from my.telegram.org
BOT_TOKEN=your_bot_token    # Get from @BotFather
OWNER=your_telegram_id      # Your Telegram user ID
```

### **Dynamic Settings (Configure via Bot)**
All these settings can be changed in real-time using `/settings` in your bot:

**🎬 Compression Presets:**
- Ultra Fast, Fast, Balanced, Quality, High Quality
- NVIDIA hardware-accelerated variants (auto-detected)
- Custom settings with full parameter control

**📤 Output Settings:**
- Filename templates with variables
- Upload modes (Document/File)
- Auto-delete original files
- File size and queue limits

**📸 Preview & Screenshots:**
- Enable/disable video previews and screenshots
- Configurable count, duration, and quality
- Custom thumbnail URLs

**⚙️ Advanced Configuration:**
- Watermark text, position, and styling
- Hardware acceleration settings
- Progress update intervals
- Upload connection limits

## 📋 Bot Commands

### **Core Commands**
- `/start` - Welcome message and bot introduction
- `/help` - Comprehensive command guide and features overview
- `/settings` - **🎛️ Access dynamic settings menu (NEW!)**
- `/status` - Bot status, queue info, and system stats
- `/ping` - Check bot response time and connectivity

### **Video Processing**
- `/link <url>` - Download and compress video from URL
- **Send video file** - Direct video compression with current settings
- **Queue system** - Multiple files processed automatically

### **Quick Settings**
- `/watermark` - Toggle watermark on/off quickly
- `/toggle_upload_mode` - Switch between Document/File upload modes

### **System & Monitoring**
- `/usage` - Detailed system resource usage
- **Real-time progress** - Automatic progress updates during compression

## 🎯 Compression Presets & Quality Options

### **🚀 Speed-Optimized Presets**
- **Ultra Fast** - Fastest compression, larger file size (480p, CRF 35)
- **Fast** - Quick compression with good quality (720p, CRF 28)

### **⚖️ Balanced Presets (Recommended)**
- **Balanced** - Optimal quality/speed ratio (1080p, CRF 26)
- **Quality** - Better quality, moderate speed (1080p, CRF 22)

### **💎 Quality-Focused Presets**
- **High Quality** - Premium quality, slower compression (1080p, CRF 18)
- **Cinema Quality** - Professional grade with HEVC (1440p, CRF 20)
- **Film Grade** - Maximum quality for archival (4K, CRF 16)

### **🎮 Specialized Presets**
- **Desktop Recording** - Optimized for screen content (1080p 60fps)
- **Mobile Optimized** - Perfect for mobile devices (720p, baseline profile)
- **Gaming Content** - High quality for gaming videos (1080p 60fps)
- **Animation** - Optimized for animated content (HEVC, 24fps)

### **🔧 Hardware-Accelerated (NVIDIA)**
- **NVIDIA Fast/Balanced/Quality** - GPU-accelerated variants
- **Auto-detection** - Automatically selects best preset for available hardware

### **⚙️ Custom Configuration**
- **Full Control** - Customize codec, resolution, FPS, quality, and audio settings
- **Real-time Preview** - See settings impact before compression
- **Save Presets** - Create and save your own custom presets

## 🖥️ Google Colab Usage

### **🚀 Quick Setup (2 Minutes)**
1. **Click** the "Open in Colab" button above
2. **Configure** your 4 required credentials (APP_ID, API_HASH, BOT_TOKEN, OWNER)
3. **Run** the setup cell and watch real-time logs
4. **Start** using your bot immediately!

### **📊 Enhanced Colab Features**
- **Real-time Logs** - Color-coded, timestamped log monitoring
- **Live Status** - Bot status and activity tracking
- **Simplified Setup** - Only 4 credentials needed, everything else via bot
- **Auto-restart** - Robust error handling and recovery

## ⚡ Performance Tips & Best Practices

### **🎯 Preset Selection**
- **Ultra Fast** - For quick tests and previews
- **Balanced** - Best for most videos (recommended default)
- **Quality/High Quality** - For important content
- **NVIDIA presets** - Automatically used when GPU available

### **🚀 Optimization Tips**
- **Enable GPU runtime** in Colab for 5-10x faster compression
- **Use hardware presets** when available (auto-detected)
- **Configure via bot** - Change settings without restarting Colab
- **Monitor queue** - Use `/status` to track multiple files

### **📏 File & Time Management**
- **File size limits** - Configurable per user via `/settings`
- **Queue management** - Handle multiple videos efficiently
- **Progress tracking** - Real-time compression status
- **Auto-cleanup** - Optional original file deletion

## 🎛️ Settings Menu Overview

Access the complete settings interface with `/settings` in your bot:

### **🎬 Compression Presets**
- Choose from 10+ optimized presets
- Hardware-accelerated options (NVIDIA)
- Custom preset creation and management

### **🔧 Custom Compression**
- **Video Codec**: H.264, H.265, NVENC variants
- **Quality Control**: CRF values from 15-40
- **Resolution**: 240p to 4K with custom options
- **Frame Rate**: 24fps to 120fps
- **Audio Bitrate**: 64k to 384k

### **📤 Output Settings**
- **Filename Templates**: Customizable with variables
- **Upload Modes**: Document or File
- **Auto-delete**: Optional original file cleanup
- **File Limits**: Configurable size and queue limits

### **� Preview & Screenshots**
- **Video Previews**: Enable/disable with custom duration
- **Screenshots**: Configurable count and quality
- **Thumbnails**: Custom URLs or auto-generation

### **⚙️ Advanced Configuration**
- **Watermarks**: Custom text, position, and styling
- **Hardware Settings**: GPU acceleration control
- **Performance**: Upload connections and update intervals

## 🔄 Real-time Features

- **Live Settings Changes** - No restart required
- **Per-user Preferences** - Each user has independent settings
- **Instant Thumbnails** - Upload and preview in real-time
- **Progress Monitoring** - Live compression status
- **Queue Management** - Multiple file handling

## �📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Credits & Acknowledgments

- **Enhanced Architecture** - Complete rewrite with dynamic settings
- **GPU Optimization** - NVIDIA NVENC hardware acceleration
- **User Experience** - Intuitive bot interface design
- **Colab Integration** - Optimized for Google Colab environment

## 🆕 What's New in This Version

- ✅ **Dynamic Settings System** - Configure everything through the bot
- ✅ **Per-user Settings** - Individual preferences for each user
- ✅ **Real-time Thumbnails** - Upload and manage thumbnails instantly
- ✅ **Enhanced Logging** - Color-coded real-time logs in Colab
- ✅ **Smart Presets** - Hardware-aware compression presets
- ✅ **Advanced Watermarks** - Customizable text and positioning
- ✅ **Queue System** - Efficient multi-file processing
- ✅ **Progress Tracking** - Live compression status updates
