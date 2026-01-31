import asyncio
import re
from telethon import Button, events
from .settings import settings_manager
from .settings_menu import settings_menu
from .config import LOGS, OWNER

class SettingsHandlers:
    """Handlers for settings interactions"""
    
    def __init__(self):
        self.settings_manager = settings_manager
        self.settings_menu = settings_menu
        self.waiting_for_input = {}  # Track users waiting for text input
    
    async def handle_settings_callback(self, event):
        """Handle settings callback queries"""
        user_id = event.sender_id
        data = event.data.decode()

        LOGS.info(f"Settings callback: {data} from user {user_id}")

        if str(user_id) not in OWNER.split():
            return await event.answer("❌ Access denied", alert=True)
        
        try:
            if data == "settings_main":
                await self.settings_menu.show_main_menu(event, user_id)
            elif data == "settings_presets":
                await self.settings_menu.show_compression_presets(event, user_id)
            elif data == "settings_custom":
                await self.settings_menu.show_custom_compression(event, user_id)
            elif data == "settings_output":
                await self.settings_menu.show_output_settings(event, user_id)
            elif data == "settings_preview":
                await self.settings_menu.show_preview_settings(event, user_id)
            elif data == "settings_advanced":
                await self.settings_menu.show_advanced_settings(event, user_id)
            elif data == "settings_thumbnail":
                await self.settings_menu.show_thumbnail_settings(event, user_id)
            elif data == "settings_current":
                await self.settings_menu.show_current_settings(event, user_id)
            elif data == "settings_close":
                await event.delete()
            elif data == "settings_reset":
                await self.handle_reset_settings(event, user_id)
            elif data.startswith("preset_"):
                await self.handle_preset_selection(event, user_id, data)
            elif data.startswith("custom_"):
                await self.handle_custom_setting(event, user_id, data)
            elif data.startswith("output_"):
                await self.handle_output_setting(event, user_id, data)
            elif data.startswith("preview_"):
                await self.handle_preview_setting(event, user_id, data)
            elif data.startswith("advanced_"):
                await self.handle_advanced_setting(event, user_id, data)
            elif data.startswith("thumb_"):
                await self.handle_thumbnail_setting(event, user_id, data)
            elif data.startswith("set_codec_"):
                await self.handle_codec_setting(event, user_id, data)
            elif data.startswith("set_resolution_"):
                await self.handle_resolution_setting(event, user_id, data)
            elif data.startswith("set_audio_"):
                await self.handle_audio_setting(event, user_id, data)
            elif data.startswith("set_watermark_pos_"):
                await self.handle_watermark_position(event, user_id, data)
            elif data.startswith("set_preset_"):
                await self.handle_encoder_preset_setting(event, user_id, data)
            elif data == "settings_export":
                await self.handle_export_settings(event, user_id)
            elif data == "settings_import":
                await self.handle_import_settings(event, user_id)
            elif data == "custom_save_preset":
                await self.handle_save_custom_preset(event, user_id)
            elif data == "confirm_reset":
                await self.handle_confirm_reset(event, user_id)
            else:
                await event.answer("Unknown setting", alert=True)
                
        except Exception as e:
            LOGS.error(f"Settings callback error: {e}", exc_info=True)
            await event.answer("❌ Error processing setting", alert=True)
    
    async def handle_preset_selection(self, event, user_id: int, data: str):
        """Handle compression preset selection"""
        preset_name = data.replace("preset_", "")
        
        if self.settings_manager.set_active_preset(preset_name, user_id):
            await event.answer(f"✅ Preset changed to {preset_name.replace('_', ' ').title()}")
            await self.settings_menu.show_compression_presets(event, user_id)
        else:
            await event.answer("❌ Failed to change preset", alert=True)
    
    async def handle_custom_setting(self, event, user_id: int, data: str):
        """Handle custom compression settings"""
        setting = data.replace("custom_", "")
        
        if setting == "codec":
            await self.show_codec_selection(event, user_id)
        elif setting == "preset":
            await self.show_preset_selection(event, user_id)
        elif setting == "quality":
            await self.request_text_input(event, user_id, "custom_quality", 
                "🎯 **Set Quality (CRF)**\n\nEnter CRF value (0-51):\n• Lower = Better quality, larger file\n• Higher = Lower quality, smaller file\n• Recommended: 18-28")
        elif setting == "resolution":
            await self.show_resolution_selection(event, user_id)
        elif setting == "fps":
            await self.request_text_input(event, user_id, "custom_fps",
                "🎞️ **Set Frame Rate**\n\nEnter FPS value (1-120):\n• Common values: 24, 30, 60\n• 0 = Keep original")
        elif setting == "audio":
            await self.show_audio_bitrate_selection(event, user_id)
        elif setting == "hwaccel":
            await self.toggle_hardware_acceleration(event, user_id)
    
    async def show_codec_selection(self, event, user_id: int):
        """Show video codec selection"""
        menu_text = "🎥 **Select Video Codec**\n\nChoose encoding codec:"
        
        buttons = [
            [Button.inline("H.264 (libx264) - Universal", data="set_codec_libx264")],
            [Button.inline("H.265 (libx265) - Better compression", data="set_codec_libx265")],
        ]
        
        # Add hardware codecs if available
        from .config import GPU_TYPE
        if GPU_TYPE == "nvidia":
            buttons.extend([
                [Button.inline("H.264 NVENC - Hardware accelerated", data="set_codec_h264_nvenc")],
                [Button.inline("H.265 NVENC - Hardware accelerated", data="set_codec_hevc_nvenc")]
            ])
        
        buttons.append([Button.inline("🔙 Back", data="settings_custom")])
        
        await event.edit(menu_text, buttons=buttons)
    
    async def show_preset_selection(self, event, user_id: int):
        """Show encoder preset selection (speed vs quality tradeoff)"""
        menu_text = "⚡ **Select Encoder Preset**\n\nFaster = Larger file, Lower quality\nSlower = Smaller file, Higher quality"
        
        from .config import GPU_TYPE
        
        if GPU_TYPE == "nvidia":
            # NVENC presets
            buttons = [
                [Button.inline("🚀 P1 - Fastest", data="set_preset_p1")],
                [Button.inline("⚡ P2 - Very Fast", data="set_preset_p2")],
                [Button.inline("🏃 P3 - Fast", data="set_preset_p3")],
                [Button.inline("⚖️ P4 - Medium", data="set_preset_p4")],
                [Button.inline("🎯 P5 - Slow", data="set_preset_p5")],
                [Button.inline("💎 P6 - Slower", data="set_preset_p6")],
                [Button.inline("🏆 P7 - Slowest/Best", data="set_preset_p7")],
            ]
        else:
            # CPU presets (x264/x265)
            buttons = [
                [Button.inline("🚀 Ultrafast", data="set_preset_ultrafast")],
                [Button.inline("⚡ Superfast", data="set_preset_superfast")],
                [Button.inline("🏃 Veryfast", data="set_preset_veryfast")],
                [Button.inline("⏩ Faster", data="set_preset_faster")],
                [Button.inline("▶️ Fast", data="set_preset_fast")],
                [Button.inline("⚖️ Medium", data="set_preset_medium")],
                [Button.inline("🎯 Slow", data="set_preset_slow")],
                [Button.inline("💎 Slower", data="set_preset_slower")],
                [Button.inline("🏆 Veryslow", data="set_preset_veryslow")],
            ]
        
        buttons.append([Button.inline("🔙 Back", data="settings_custom")])
        
        await event.edit(menu_text, buttons=buttons)
    
    async def show_resolution_selection(self, event, user_id: int):
        """Show resolution selection"""
        menu_text = "📐 **Select Resolution**\n\nChoose target resolution:"
        
        buttons = [
            [Button.inline("🔄 Keep Original", data="set_resolution_0")],
            [Button.inline("📱 720p (HD)", data="set_resolution_720")],
            [Button.inline("🖥️ 1080p (Full HD)", data="set_resolution_1080")],
            [Button.inline("📺 1440p (2K)", data="set_resolution_1440")],
            [Button.inline("🎬 2160p (4K)", data="set_resolution_2160")],
            [Button.inline("🔙 Back", data="settings_custom")]
        ]
        
        await event.edit(menu_text, buttons=buttons)
    
    async def show_audio_bitrate_selection(self, event, user_id: int):
        """Show audio bitrate selection"""
        menu_text = "🔊 **Select Audio Bitrate**\n\nChoose audio quality:"
        
        buttons = [
            [Button.inline("💾 96k - Low quality, small size", data="set_audio_96k")],
            [Button.inline("⚖️ 128k - Good quality", data="set_audio_128k")],
            [Button.inline("🎯 192k - High quality", data="set_audio_192k")],
            [Button.inline("💎 256k - Very high quality", data="set_audio_256k")],
            [Button.inline("🎵 320k - Maximum quality", data="set_audio_320k")],
            [Button.inline("🔙 Back", data="settings_custom")]
        ]
        
        await event.edit(menu_text, buttons=buttons)
    
    async def toggle_hardware_acceleration(self, event, user_id: int):
        """Toggle hardware acceleration"""
        current = self.settings_manager.get_setting("custom_compression", "enable_hardware_acceleration", user_id)
        new_value = not current
        
        if self.settings_manager.set_setting("custom_compression", "enable_hardware_acceleration", new_value, user_id):
            status = "✅ Enabled" if new_value else "❌ Disabled"
            await event.answer(f"Hardware Acceleration {status}")
            await self.settings_menu.show_custom_compression(event, user_id)
        else:
            await event.answer("❌ Failed to toggle setting", alert=True)
    
    async def handle_output_setting(self, event, user_id: int, data: str):
        """Handle output settings"""
        setting = data.replace("output_", "")
        
        if setting == "upload_mode":
            await self.toggle_upload_mode(event, user_id)
        elif setting == "format":
            await self.toggle_output_format(event, user_id)
        elif setting == "auto_delete":
            await self.toggle_auto_delete(event, user_id)
        elif setting == "filename":
            await self.request_text_input(event, user_id, "output_filename",
                "📝 **Set Filename Template**\n\nAvailable variables:\n• {original_name}\n• {resolution}\n• {codec}\n• {date}\n• {time}\n\nExample: `{original_name} [{resolution} {codec}]`")
        elif setting == "max_size":
            await self.request_text_input(event, user_id, "output_max_size",
                "📏 **Set Maximum File Size**\n\nEnter size in MB (1-8000):")
        elif setting == "queue_size":
            await self.request_text_input(event, user_id, "output_queue_size",
                "📋 **Set Maximum Queue Size**\n\nEnter number of files (1-50):")
    
    async def toggle_upload_mode(self, event, user_id: int):
        """Toggle upload mode between Document and File"""
        current = self.settings_manager.get_setting("output_settings", "default_upload_mode", user_id)
        new_mode = "File" if current == "Document" else "Document"

        if self.settings_manager.set_setting("output_settings", "default_upload_mode", new_mode, user_id):
            await event.answer(f"✅ Upload mode: {new_mode}")
            await self.settings_menu.show_output_settings(event, user_id)
        else:
            await event.answer("❌ Failed to change upload mode", alert=True)

    async def toggle_output_format(self, event, user_id: int):
        """Toggle output format between MKV and MP4"""
        current = self.settings_manager.get_setting("output_settings", "output_format", user_id)
        new_format = "mp4" if current == "mkv" else "mkv"

        if self.settings_manager.set_setting("output_settings", "output_format", new_format, user_id):
            await event.answer(f"✅ Output format: {new_format.upper()}")
            await self.settings_menu.show_output_settings(event, user_id)
        else:
            await event.answer("❌ Failed to change output format", alert=True)

    async def toggle_auto_delete(self, event, user_id: int):
        """Toggle auto delete original files"""
        current = self.settings_manager.get_setting("output_settings", "auto_delete_original", user_id)
        new_value = not current

        if self.settings_manager.set_setting("output_settings", "auto_delete_original", new_value, user_id):
            status = "✅ Enabled" if new_value else "❌ Disabled"
            await event.answer(f"Auto Delete Original {status}")
            await self.settings_menu.show_output_settings(event, user_id)
        else:
            await event.answer("❌ Failed to toggle setting", alert=True)
    
    async def toggle_auto_delete(self, event, user_id: int):
        """Toggle auto delete original files"""
        current = self.settings_manager.get_setting("output_settings", "auto_delete_original", user_id)
        new_value = not current
        
        if self.settings_manager.set_setting("output_settings", "auto_delete_original", new_value, user_id):
            status = "✅ Enabled" if new_value else "❌ Disabled"
            await event.answer(f"Auto Delete Original {status}")
            await self.settings_menu.show_output_settings(event, user_id)
        else:
            await event.answer("❌ Failed to toggle setting", alert=True)
    
    async def request_text_input(self, event, user_id: int, setting_key: str, prompt: str):
        """Request text input from user"""
        self.waiting_for_input[user_id] = setting_key
        
        buttons = [[Button.inline("❌ Cancel", data="settings_main")]]
        await event.edit(prompt, buttons=buttons)
    
    async def handle_text_input(self, event, user_id: int):
        """Handle text input from user"""
        if user_id not in self.waiting_for_input:
            return False
        
        setting_key = self.waiting_for_input[user_id]
        text = event.text.strip()
        
        try:
            success = await self.process_text_input(setting_key, text, user_id)
            if success:
                await event.reply("✅ Setting updated successfully!")
                # Show appropriate menu
                if setting_key.startswith("custom_"):
                    await self.settings_menu.show_custom_compression(event, user_id)
                elif setting_key.startswith("output_"):
                    await self.settings_menu.show_output_settings(event, user_id)
                # Add more menu redirects as needed
            else:
                await event.reply("❌ Invalid value. Please try again.")
                return False
        except Exception as e:
            LOGS.error(f"Text input processing error: {e}")
            await event.reply("❌ Error processing input.")
        finally:
            del self.waiting_for_input[user_id]
        
        return True
    
    async def process_text_input(self, setting_key: str, text: str, user_id: int) -> bool:
        """Process text input for specific settings"""
        try:
            if setting_key == "custom_quality":
                value = int(text)
                if 0 <= value <= 51:
                    return self.settings_manager.set_setting("custom_compression", "v_qp", value, user_id)
            elif setting_key == "custom_fps":
                value = int(text)
                if 0 <= value <= 120:
                    return self.settings_manager.set_setting("custom_compression", "v_fps", value, user_id)
            elif setting_key == "output_filename":
                if text and len(text) <= 100:
                    return self.settings_manager.set_setting("output_settings", "filename_template", text, user_id)
            elif setting_key == "output_max_size":
                value = int(text)
                if 1 <= value <= 8000:
                    return self.settings_manager.set_setting("output_settings", "max_file_size", value, user_id)
            elif setting_key == "output_queue_size":
                value = int(text)
                if 1 <= value <= 50:
                    return self.settings_manager.set_setting("output_settings", "max_queue_size", value, user_id)
            elif setting_key == "preview_count":
                value = int(text)
                if 1 <= value <= 20:
                    return self.settings_manager.set_setting("preview_settings", "screenshot_count", value, user_id)
            elif setting_key == "preview_duration":
                value = int(text)
                if 5 <= value <= 60:
                    return self.settings_manager.set_setting("preview_settings", "preview_duration", value, user_id)
            elif setting_key == "preview_quality":
                value = int(text)
                if 18 <= value <= 35:
                    return self.settings_manager.set_setting("preview_settings", "preview_quality", value, user_id)
            elif setting_key == "thumb_custom_url":
                if text and text.startswith(('http://', 'https://')):
                    return self.settings_manager.set_setting("thumbnail_settings", "custom_url", text, user_id)
            elif setting_key == "thumb_timestamp":
                # Basic timestamp validation (HH:MM:SS format)
                import re
                if re.match(r'^\d{1,2}:\d{2}:\d{2}$', text):
                    return self.settings_manager.set_setting("thumbnail_settings", "timestamp", text, user_id)
            elif setting_key == "advanced_watermark_text":
                if text and len(text) <= 50:
                    return self.settings_manager.set_setting("advanced_settings", "watermark_text", text, user_id)
            elif setting_key == "advanced_upload_conn":
                value = int(text)
                if 1 <= value <= 10:
                    return self.settings_manager.set_setting("advanced_settings", "upload_connections", value, user_id)
            elif setting_key == "advanced_progress":
                value = int(text)
                if 1 <= value <= 30:
                    return self.settings_manager.set_setting("advanced_settings", "progress_update_interval", value, user_id)
            elif setting_key == "import_settings":
                import json
                try:
                    imported = json.loads(text)
                    if isinstance(imported, dict):
                        self.settings_manager.user_settings[user_id] = imported
                        self.settings_manager.save_user_settings()
                        return True
                except json.JSONDecodeError:
                    pass
            # Add more text input processors as needed
            
        except ValueError:
            pass
        
        return False
    
    async def handle_reset_settings(self, event, user_id: int):
        """Handle settings reset confirmation"""
        menu_text = (
            "🔄 **Reset Settings**\n\n"
            "⚠️ This will reset ALL settings to default values.\n"
            "This action cannot be undone.\n\n"
            "Are you sure?"
        )

        buttons = [
            [Button.inline("✅ Yes, Reset All", data="confirm_reset")],
            [Button.inline("❌ Cancel", data="settings_main")]
        ]

        await event.edit(menu_text, buttons=buttons)

    async def handle_codec_setting(self, event, user_id: int, data: str):
        """Handle codec selection"""
        codec = data.replace("set_codec_", "")
        if self.settings_manager.set_setting("custom_compression", "v_codec", codec, user_id):
            await event.answer(f"✅ Codec set to {codec}")
            await self.settings_menu.show_custom_compression(event, user_id)
        else:
            await event.answer("❌ Failed to set codec", alert=True)

    async def handle_resolution_setting(self, event, user_id: int, data: str):
        """Handle resolution selection"""
        resolution = int(data.replace("set_resolution_", ""))
        if self.settings_manager.set_setting("custom_compression", "v_scale", resolution, user_id):
            res_text = f"{resolution}p" if resolution > 0 else "Original"
            await event.answer(f"✅ Resolution set to {res_text}")
            await self.settings_menu.show_custom_compression(event, user_id)
        else:
            await event.answer("❌ Failed to set resolution", alert=True)

    async def handle_audio_setting(self, event, user_id: int, data: str):
        """Handle audio bitrate selection"""
        bitrate = data.replace("set_audio_", "")
        if self.settings_manager.set_setting("custom_compression", "a_bitrate", bitrate, user_id):
            await event.answer(f"✅ Audio bitrate set to {bitrate}")
            await self.settings_menu.show_custom_compression(event, user_id)
        else:
            await event.answer("❌ Failed to set audio bitrate", alert=True)

    async def handle_preview_setting(self, event, user_id: int, data: str):
        """Handle preview settings"""
        setting = data.replace("preview_", "")

        if setting == "screenshots":
            await self.toggle_screenshots(event, user_id)
        elif setting == "count":
            await self.request_text_input(event, user_id, "preview_count",
                "📸 **Set Screenshot Count**\n\nEnter number of screenshots (1-20):")
        elif setting == "video":
            await self.toggle_video_preview(event, user_id)
        elif setting == "duration":
            await self.request_text_input(event, user_id, "preview_duration",
                "⏱️ **Set Preview Duration**\n\nEnter duration in seconds (5-60):")
        elif setting == "quality":
            await self.request_text_input(event, user_id, "preview_quality",
                "🎯 **Set Preview Quality (CRF)**\n\nEnter CRF value (18-35):")

    async def toggle_screenshots(self, event, user_id: int):
        """Toggle screenshot generation"""
        current = self.settings_manager.get_setting("preview_settings", "enable_screenshots", user_id)
        new_value = not current

        if self.settings_manager.set_setting("preview_settings", "enable_screenshots", new_value, user_id):
            status = "✅ Enabled" if new_value else "❌ Disabled"
            await event.answer(f"Screenshots {status}")
            await self.settings_menu.show_preview_settings(event, user_id)
        else:
            await event.answer("❌ Failed to toggle setting", alert=True)

    async def toggle_video_preview(self, event, user_id: int):
        """Toggle video preview generation"""
        current = self.settings_manager.get_setting("preview_settings", "enable_video_preview", user_id)
        new_value = not current

        if self.settings_manager.set_setting("preview_settings", "enable_video_preview", new_value, user_id):
            status = "✅ Enabled" if new_value else "❌ Disabled"
            await event.answer(f"Video Preview {status}")
            await self.settings_menu.show_preview_settings(event, user_id)
        else:
            await event.answer("❌ Failed to toggle setting", alert=True)

    async def handle_thumbnail_setting(self, event, user_id: int, data: str):
        """Handle thumbnail settings"""
        setting = data.replace("thumb_", "")

        if setting == "auto_generate":
            await self.toggle_auto_thumbnail(event, user_id)
        elif setting == "custom_url":
            await self.request_text_input(event, user_id, "thumb_custom_url",
                "🔗 **Set Custom Thumbnail URL**\n\nEnter image URL:")
        elif setting == "timestamp":
            await self.request_text_input(event, user_id, "thumb_timestamp",
                "⏱️ **Set Thumbnail Timestamp**\n\nEnter timestamp (e.g., 00:01:30):")
        elif setting == "preview":
            await self.show_thumbnail_preview(event, user_id)
        elif setting == "clear_url":
            await self.clear_custom_thumbnail(event, user_id)

    async def toggle_auto_thumbnail(self, event, user_id: int):
        """Toggle automatic thumbnail generation"""
        current = self.settings_manager.get_setting("thumbnail_settings", "auto_generate", user_id)
        new_value = not current

        if self.settings_manager.set_setting("thumbnail_settings", "auto_generate", new_value, user_id):
            status = "✅ Enabled" if new_value else "❌ Disabled"
            await event.answer(f"Auto Thumbnail {status}")
            await self.settings_menu.show_thumbnail_settings(event, user_id)
        else:
            await event.answer("❌ Failed to toggle setting", alert=True)

    async def show_thumbnail_preview(self, event, user_id: int):
        """Show current thumbnail preview"""
        await event.answer("🖼️ Thumbnail preview feature coming soon!")

    async def clear_custom_thumbnail(self, event, user_id: int):
        """Clear custom thumbnail URL"""
        if self.settings_manager.set_setting("thumbnail_settings", "custom_url", "", user_id):
            await event.answer("✅ Custom thumbnail URL cleared")
            await self.settings_menu.show_thumbnail_settings(event, user_id)
        else:
            await event.answer("❌ Failed to clear URL", alert=True)

    async def handle_advanced_setting(self, event, user_id: int, data: str):
        """Handle advanced settings"""
        setting = data.replace("advanced_", "")

        if setting == "watermark":
            await self.toggle_watermark(event, user_id)
        elif setting == "watermark_text":
            await self.request_text_input(event, user_id, "advanced_watermark_text",
                "✏️ **Set Watermark Text**\n\nEnter watermark text:")
        elif setting == "watermark_pos":
            await self.show_watermark_position_selection(event, user_id)
        elif setting == "upload_conn":
            await self.request_text_input(event, user_id, "advanced_upload_conn",
                "🔗 **Set Upload Connections**\n\nEnter number of connections (1-10):")
        elif setting == "progress":
            await self.request_text_input(event, user_id, "advanced_progress",
                "⏱️ **Set Progress Update Interval**\n\nEnter interval in seconds (1-30):")

    async def toggle_watermark(self, event, user_id: int):
        """Toggle watermark"""
        current = self.settings_manager.get_setting("advanced_settings", "watermark_enabled", user_id)
        new_value = not current

        if self.settings_manager.set_setting("advanced_settings", "watermark_enabled", new_value, user_id):
            status = "✅ Enabled" if new_value else "❌ Disabled"
            await event.answer(f"Watermark {status}")
            await self.settings_menu.show_advanced_settings(event, user_id)
        else:
            await event.answer("❌ Failed to toggle setting", alert=True)

    async def show_watermark_position_selection(self, event, user_id: int):
        """Show watermark position selection"""
        menu_text = "📍 **Select Watermark Position**\n\nChoose position:"

        buttons = [
            [Button.inline("↖️ Top Left", data="set_watermark_pos_top-left")],
            [Button.inline("↗️ Top Right", data="set_watermark_pos_top-right")],
            [Button.inline("↙️ Bottom Left", data="set_watermark_pos_bottom-left")],
            [Button.inline("↘️ Bottom Right", data="set_watermark_pos_bottom-right")],
            [Button.inline("🔙 Back", data="settings_advanced")]
        ]

        await event.edit(menu_text, buttons=buttons)

    async def handle_watermark_position(self, event, user_id: int, data: str):
        """Handle watermark position selection"""
        position = data.replace("set_watermark_pos_", "")
        if self.settings_manager.set_setting("advanced_settings", "watermark_position", position, user_id):
            await event.answer(f"✅ Watermark position set to {position}")
            await self.settings_menu.show_advanced_settings(event, user_id)
        else:
            await event.answer("❌ Failed to set position", alert=True)

    async def handle_confirm_reset(self, event, user_id: int):
        """Handle confirmed settings reset"""
        try:
            # Reset user settings to defaults
            if user_id in self.settings_manager.user_settings:
                del self.settings_manager.user_settings[user_id]

            await event.answer("✅ Settings reset to defaults")
            await self.settings_menu.show_main_menu(event, user_id)
        except Exception as e:
            LOGS.error(f"Error resetting settings: {e}")
            await event.answer("❌ Failed to reset settings", alert=True)

    async def handle_encoder_preset_setting(self, event, user_id: int, data: str):
        """Handle encoder preset setting (speed vs quality)"""
        preset = data.replace("set_preset_", "")
        if self.settings_manager.set_setting("custom_compression", "v_preset", preset, user_id):
            await event.answer(f"✅ Encoder preset set to {preset}")
            await self.settings_menu.show_custom_compression(event, user_id)
        else:
            await event.answer("❌ Failed to set preset", alert=True)

    async def handle_export_settings(self, event, user_id: int):
        """Export user settings as JSON"""
        import json
        try:
            user_settings = self.settings_manager.user_settings.get(user_id, {})
            if not user_settings:
                return await event.answer("❌ No custom settings to export", alert=True)
            
            settings_json = json.dumps(user_settings, indent=2)
            
            # Send as a message (Telegram has a limit, so we truncate if needed)
            if len(settings_json) > 4000:
                settings_json = settings_json[:4000] + "\n... (truncated)"
            
            await event.edit(
                f"📋 **Your Settings Export**\n\n```json\n{settings_json}\n```\n\n"
                "Copy and save this JSON to import later.",
                buttons=[[Button.inline("🔙 Back", data="settings_current")]]
            )
        except Exception as e:
            LOGS.error(f"Error exporting settings: {e}")
            await event.answer("❌ Failed to export settings", alert=True)

    async def handle_import_settings(self, event, user_id: int):
        """Request settings import from user"""
        self.waiting_for_input[user_id] = "import_settings"
        
        await event.edit(
            "📥 **Import Settings**\n\n"
            "Paste your previously exported JSON settings below.\n\n"
            "⚠️ This will overwrite your current settings!",
            buttons=[[Button.inline("❌ Cancel", data="settings_current")]]
        )

    async def handle_save_custom_preset(self, event, user_id: int):
        """Save current custom settings as a reminder"""
        custom_settings = self.settings_manager.get_setting("custom_compression", user_id=user_id)
        
        settings_summary = (
            f"💾 **Custom Settings Saved!**\n\n"
            f"Your current custom compression settings:\n"
            f"• Codec: `{custom_settings.get('v_codec', 'N/A')}`\n"
            f"• Preset: `{custom_settings.get('v_preset', 'N/A')}`\n"
            f"• Quality: `{custom_settings.get('v_qp', 'N/A')} CRF`\n"
            f"• Resolution: `{custom_settings.get('v_scale', 'N/A')}p`\n"
            f"• FPS: `{custom_settings.get('v_fps', 'N/A')}`\n"
            f"• Audio: `{custom_settings.get('a_bitrate', 'N/A')}`\n\n"
            f"Select 'Custom' preset to use these settings."
        )
        
        await event.edit(
            settings_summary,
            buttons=[[Button.inline("🔙 Back", data="settings_custom")]]
        )
        await event.answer("✅ Custom settings are saved!")

# Global settings handlers instance
settings_handlers = SettingsHandlers()
