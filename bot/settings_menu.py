import asyncio
from telethon import Button
from .settings import settings_manager
from .config import LOGS, OWNER, GPU_TYPE

class SettingsMenu:
    """Settings menu interface for the bot"""
    
    def __init__(self):
        self.settings_manager = settings_manager
    
    async def show_main_menu(self, event, user_id: int):
        """Show the main settings menu. Assumes caller has already verified owner permissions."""
        try:
            # --- FIX: REMOVED REDUNDANT OWNER CHECK ---
            # The command handler in __main__.py already performs this check.
            # Removing it here simplifies the code and fixes the silent failure.

            # Check if settings manager is properly initialized
            if not hasattr(self, 'settings_manager') or self.settings_manager is None:
                LOGS.error("Settings manager not initialized")
                return await event.reply("❌ Settings system not initialized. Please restart the bot.")

            active_preset = self.settings_manager.get_setting("active_preset", user_id=user_id) or "balanced"

            menu_text = (
                "⚙️ **Bot Settings Menu**\n\n"
                f"🎯 **Current Preset**: `{active_preset.replace('_', ' ').title()}`\n"
                f"🖥️ **Hardware**: `{GPU_TYPE.upper()}`\n\n"
                "Select a category to configure:"
            )

            buttons = [
                [Button.inline("🎬 Compression Presets", data="settings_presets")],
                [Button.inline("🔧 Custom Compression", data="settings_custom")],
                [Button.inline("📤 Output Settings", data="settings_output")],
                [Button.inline("📸 Preview & Screenshots", data="settings_preview")],
                [Button.inline("⚡ Advanced Config", data="settings_advanced")],
                [Button.inline("🖼️ Thumbnail Settings", data="settings_thumbnail")],
                [Button.inline("📊 Current Settings", data="settings_current")],
                [Button.inline("🔄 Reset to Defaults", data="settings_reset")],
                [Button.inline("❌ Close", data="settings_close")]
            ]

            # This logic correctly handles both new commands (reply) and callbacks (edit)
            if hasattr(event, 'edit'):
                await event.edit(menu_text, buttons=buttons)
            else:
                await event.reply(menu_text, buttons=buttons)

        except Exception as e:
            LOGS.error(f"Error showing main settings menu: {e}", exc_info=True)
            await event.reply("❌ Error loading settings menu. Please check bot logs.")
    
    async def show_compression_presets(self, event, user_id: int):
        """Show compression presets menu"""
        available_presets = self.settings_manager.get_available_presets()
        active_preset = self.settings_manager.get_setting("active_preset", user_id=user_id) or "balanced"
        
        menu_text = (
            "🎬 **Compression Presets**\n\n"
            f"**Current**: `{active_preset.replace('_', ' ').title()}`\n\n"
            "Choose a preset:"
        )
        
        buttons = []
        for preset_key, description in available_presets.items():
            status = " ✅" if preset_key == active_preset else ""
            buttons.append([Button.inline(f"{description}{status}", data=f"preset_{preset_key}")])
        
        buttons.append([Button.inline("🔙 Back to Settings", data="settings_main")])
        
        await event.edit(menu_text, buttons=buttons)
    
    async def show_custom_compression(self, event, user_id: int):
        """Show custom compression settings menu"""
        custom_settings = self.settings_manager.get_setting("custom_compression", user_id=user_id)
        
        menu_text = (
            "🔧 **Custom Compression Settings**\n\n"
            f"**Codec**: `{custom_settings.get('v_codec', 'libx264')}`\n"
            f"**Preset**: `{custom_settings.get('v_preset', 'medium')}`\n"
            f"**Quality (CRF)**: `{custom_settings.get('v_qp', 26)}`\n"
            f"**Resolution**: `{custom_settings.get('v_scale', 1080)}p`\n"
            f"**FPS**: `{custom_settings.get('v_fps', 30)}`\n"
            f"**Audio Bitrate**: `{custom_settings.get('a_bitrate', '192k')}`\n"
            f"**Hardware Accel**: `{'✅' if custom_settings.get('enable_hardware_acceleration') else '❌'}`\n\n"
            "Select setting to modify:"
        )
        
        buttons = [
            [Button.inline("🎥 Video Codec", data="custom_codec")],
            [Button.inline("⚡ Preset/Speed", data="custom_preset")],
            [Button.inline("🎯 Quality (CRF)", data="custom_quality")],
            [Button.inline("📐 Resolution", data="custom_resolution")],
            [Button.inline("🎞️ Frame Rate", data="custom_fps")],
            [Button.inline("🔊 Audio Bitrate", data="custom_audio")],
            [Button.inline("🚀 Hardware Accel", data="custom_hwaccel")],
            [Button.inline("💾 Save as Preset", data="custom_save_preset")],
            [Button.inline("🔙 Back to Settings", data="settings_main")]
        ]
        
        await event.edit(menu_text, buttons=buttons)
    
    async def show_output_settings(self, event, user_id: int):
        """Show output settings menu"""
        output_settings = self.settings_manager.get_setting("output_settings", user_id=user_id)
        
        menu_text = (
            "📤 **Output Settings**\n\n"
            f"**Filename Template**: `{output_settings.get('filename_template', '{original_name} [{resolution} {codec}]')}`\n"
            f"**Upload Mode**: `{output_settings.get('default_upload_mode', 'Document')}`\n"
            f"**Auto Delete Original**: `{'✅' if output_settings.get('auto_delete_original') else '❌'}`\n"
            f"**Max File Size**: `{output_settings.get('max_file_size', 4000)}MB`\n"
            f"**Max Queue Size**: `{output_settings.get('max_queue_size', 15)}`\n\n"
            "Select setting to modify:"
        )
        
        buttons = [
            [Button.inline("📝 Filename Template", data="output_filename")],
            [Button.inline("☁️ Upload Mode", data="output_upload_mode")],
            [Button.inline("🗑️ Auto Delete Original", data="output_auto_delete")],
            [Button.inline("📏 Max File Size", data="output_max_size")],
            [Button.inline("📋 Max Queue Size", data="output_queue_size")],
            [Button.inline("🔙 Back to Settings", data="settings_main")]
        ]
        
        await event.edit(menu_text, buttons=buttons)
    
    async def show_preview_settings(self, event, user_id: int):
        """Show preview and screenshot settings menu"""
        preview_settings = self.settings_manager.get_setting("preview_settings", user_id=user_id)
        
        menu_text = (
            "📸 **Preview & Screenshots Settings**\n\n"
            f"**Screenshots**: `{'✅' if preview_settings.get('enable_screenshots') else '❌'}`\n"
            f"**Screenshot Count**: `{preview_settings.get('screenshot_count', 5)}`\n"
            f"**Video Preview**: `{'✅' if preview_settings.get('enable_video_preview') else '❌'}`\n"
            f"**Preview Duration**: `{preview_settings.get('preview_duration', 10)}s`\n"
            f"**Preview Quality**: `{preview_settings.get('preview_quality', 28)} CRF`\n\n"
            "Select setting to modify:"
        )
        
        buttons = [
            [Button.inline("📸 Toggle Screenshots", data="preview_screenshots")],
            [Button.inline("🔢 Screenshot Count", data="preview_count")],
            [Button.inline("🎬 Toggle Video Preview", data="preview_video")],
            [Button.inline("⏱️ Preview Duration", data="preview_duration")],
            [Button.inline("🎯 Preview Quality", data="preview_quality")],
            [Button.inline("🔙 Back to Settings", data="settings_main")]
        ]
        
        await event.edit(menu_text, buttons=buttons)
    
    async def show_advanced_settings(self, event, user_id: int):
        """Show advanced settings menu"""
        advanced_settings = self.settings_manager.get_setting("advanced_settings", user_id=user_id)
        
        menu_text = (
            "⚡ **Advanced Configuration**\n\n"
            f"**Watermark**: `{'✅' if advanced_settings.get('watermark_enabled') else '❌'}`\n"
            f"**Watermark Text**: `{advanced_settings.get('watermark_text', 'Compressed by Bot')}`\n"
            f"**Watermark Position**: `{advanced_settings.get('watermark_position', 'bottom-right')}`\n"
            f"**Upload Connections**: `{advanced_settings.get('upload_connections', 5)}`\n"
            f"**Progress Update Interval**: `{advanced_settings.get('progress_update_interval', 5)}s`\n\n"
            "Select setting to modify:"
        )
        
        buttons = [
            [Button.inline("🏷️ Toggle Watermark", data="advanced_watermark")],
            [Button.inline("✏️ Watermark Text", data="advanced_watermark_text")],
            [Button.inline("📍 Watermark Position", data="advanced_watermark_pos")],
            [Button.inline("🔗 Upload Connections", data="advanced_upload_conn")],
            [Button.inline("⏱️ Progress Interval", data="advanced_progress")],
            [Button.inline("🔙 Back to Settings", data="settings_main")]
        ]
        
        await event.edit(menu_text, buttons=buttons)
    
    async def show_thumbnail_settings(self, event, user_id: int):
        """Show thumbnail settings menu"""
        thumbnail_settings = self.settings_manager.get_setting("thumbnail_settings", user_id=user_id)
        
        current_url = thumbnail_settings.get('custom_thumbnail_url', '')
        url_display = current_url[:50] + "..." if len(current_url) > 50 else current_url or "None"
        
        menu_text = (
            "🖼️ **Thumbnail Settings**\n\n"
            f"**Auto Generate**: `{'✅' if thumbnail_settings.get('auto_generate_thumbnail') else '❌'}`\n"
            f"**Custom URL**: `{url_display}`\n"
            f"**Timestamp**: `{thumbnail_settings.get('thumbnail_timestamp_percent', 10)}% into video`\n\n"
            "Select option:"
        )
        
        buttons = [
            [Button.inline("🔄 Toggle Auto Generate", data="thumb_auto_generate")],
            [Button.inline("🔗 Set Custom URL", data="thumb_custom_url")],
            [Button.inline("⏱️ Set Timestamp", data="thumb_timestamp")],
            [Button.inline("👁️ Preview Current", data="thumb_preview")],
            [Button.inline("🗑️ Clear Custom URL", data="thumb_clear_url")],
            [Button.inline("🔙 Back to Settings", data="settings_main")]
        ]
        
        await event.edit(menu_text, buttons=buttons)
    
    async def show_current_settings(self, event, user_id: int):
        """Show current active settings summary"""
        active_preset = self.settings_manager.get_setting("active_preset", user_id=user_id) or "balanced"
        compression_settings = self.settings_manager.get_active_compression_settings(user_id)
        output_settings = self.settings_manager.get_setting("output_settings", user_id=user_id)
        
        menu_text = (
            "📊 **Current Active Settings**\n\n"
            f"**🎯 Active Preset**: `{active_preset.replace('_', ' ').title()}`\n\n"
            f"**🎬 Compression**:\n"
            f"• Codec: `{compression_settings.get('v_codec', 'N/A')}`\n"
            f"• Preset: `{compression_settings.get('v_preset', 'N/A')}`\n"
            f"• Quality: `{compression_settings.get('v_qp', 'N/A')} CRF`\n"
            f"• Resolution: `{compression_settings.get('v_scale', 'N/A')}p`\n"
            f"• FPS: `{compression_settings.get('v_fps', 'N/A')}`\n\n"
            f"**📤 Output**:\n"
            f"• Upload Mode: `{output_settings.get('default_upload_mode', 'N/A')}`\n"
            f"• Auto Delete: `{'✅' if output_settings.get('auto_delete_original') else '❌'}`\n"
        )
        
        buttons = [
            [Button.inline("📋 Export Settings", data="settings_export")],
            [Button.inline("📥 Import Settings", data="settings_import")],
            [Button.inline("🔙 Back to Settings", data="settings_main")]
        ]
        
        await event.edit(menu_text, buttons=buttons)

# Global settings menu instance
settings_menu = SettingsMenu()