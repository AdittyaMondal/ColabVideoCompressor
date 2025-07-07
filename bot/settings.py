import json
import os
import asyncio
from typing import Dict, Any, Optional
from .config import LOGS, GPU_TYPE

class SettingsManager:
    """Dynamic settings manager for the bot with JSON persistence"""
    
    def __init__(self, settings_file: str = "bot_settings.json"):
        self.settings_file = settings_file
        self.settings = {}
        self.user_settings = {}  # Per-user settings
        self.load_settings()
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Get default settings based on current config and hardware"""
        return {
            # Compression Presets
            "compression_presets": {
                "ultra_fast": {"v_codec": "libx264", "v_preset": "ultrafast", "v_qp": 35, "v_scale": 720},
                "fast": {"v_codec": "libx264", "v_preset": "fast", "v_qp": 28, "v_scale": 1080},
                "balanced": {"v_codec": "libx264", "v_preset": "medium", "v_qp": 26, "v_scale": 1080},
                "quality": {"v_codec": "libx264", "v_preset": "slow", "v_qp": 22, "v_scale": 1080},
                "high_quality": {"v_codec": "libx264", "v_preset": "veryslow", "v_qp": 18, "v_scale": 1080},
                "nvidia_fast": {"v_codec": "h264_nvenc", "v_preset": "p1", "v_qp": 28, "v_scale": 1080},
                "nvidia_balanced": {"v_codec": "h264_nvenc", "v_preset": "p3", "v_qp": 26, "v_scale": 1080},
                "nvidia_quality": {"v_codec": "h264_nvenc", "v_preset": "p6", "v_qp": 22, "v_scale": 1080},
            },
            
            # Current Active Settings
            "active_preset": "balanced" if GPU_TYPE == "cpu" else "nvidia_balanced",
            
            # Custom Compression Settings
            "custom_compression": {
                "v_codec": "h264_nvenc" if GPU_TYPE == "nvidia" else "libx264",
                "v_preset": "p3" if GPU_TYPE == "nvidia" else "medium",
                "v_profile": "high",
                "v_level": "4.0",
                "v_qp": 26,
                "v_scale": 1080,
                "v_fps": 30,
                "a_bitrate": "192k",
                "enable_hardware_acceleration": True if GPU_TYPE != "cpu" else False,
            },
            
            # Output Settings
            "output_settings": {
                "filename_template": "{original_name} [{resolution} {codec}]",
                "auto_delete_original": False,
                "default_upload_mode": "Document",
                "max_file_size": 4000,
                "max_queue_size": 15,
            },
            
            # Preview & Screenshots
            "preview_settings": {
                "enable_screenshots": True,  # Enable by default for better user experience
                "screenshot_count": 5,
                "enable_video_preview": True,  # Enable by default for better user experience
                "preview_duration": 10,
                "preview_quality": 28,
            },
            
            # Advanced Configuration
            "advanced_settings": {
                "watermark_enabled": False,
                "watermark_text": "Compressed by Bot",
                "watermark_position": "bottom-right",
                "upload_connections": 5,
                "progress_update_interval": 5,
                "enable_eval": False,
                "enable_bash": False,
            },
            
            # Thumbnail Settings
            "thumbnail_settings": {
                "custom_url": "",
                "auto_generate": True,
                "timestamp": "00:00:10",  # Default timestamp
            }
        }
    
    def load_settings(self):
        """Load settings from JSON file or create default"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    default_settings = self.get_default_settings()
                    self.settings = self._merge_settings(default_settings, loaded_settings)
                    LOGS.info("✅ Settings loaded from file")
            else:
                self.settings = self.get_default_settings()
                self.save_settings()
                LOGS.info("✅ Default settings created")

            # Also load user settings
            self.load_user_settings()
        except Exception as e:
            LOGS.error(f"Error loading settings: {e}")
            self.settings = self.get_default_settings()
            self.user_settings = {}
    
    def _merge_settings(self, default: Dict, loaded: Dict) -> Dict:
        """Recursively merge loaded settings with defaults"""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_settings(result[key], value)
            else:
                result[key] = value
        return result
    
    def save_settings(self):
        """Save current settings to JSON file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            LOGS.info("✅ Settings saved to file")
        except Exception as e:
            LOGS.error(f"Error saving settings: {e}")

    def save_user_settings(self):
        """Save user settings to JSON file"""
        try:
            user_settings_file = "user_settings.json"
            with open(user_settings_file, 'w') as f:
                # Convert user_id keys to strings for JSON compatibility
                user_settings_str = {str(k): v for k, v in self.user_settings.items()}
                json.dump(user_settings_str, f, indent=2)
            LOGS.info("✅ User settings saved to file")
        except Exception as e:
            LOGS.error(f"Error saving user settings: {e}")

    def load_user_settings(self):
        """Load user settings from JSON file"""
        try:
            user_settings_file = "user_settings.json"
            if os.path.exists(user_settings_file):
                with open(user_settings_file, 'r') as f:
                    user_settings_str = json.load(f)
                    # Convert string keys back to integers
                    self.user_settings = {int(k): v for k, v in user_settings_str.items()}
                LOGS.info("✅ User settings loaded from file")
            else:
                self.user_settings = {}
                LOGS.info("✅ No user settings file found, starting fresh")
        except Exception as e:
            LOGS.error(f"Error loading user settings: {e}")
            self.user_settings = {}
    
    def get_setting(self, category: str, key: str = None, user_id: int = None):
        """Get a setting value"""
        try:
            # Check user-specific settings first
            if user_id and user_id in self.user_settings:
                user_setting = self.user_settings[user_id].get(category, {})
                if key:
                    if key in user_setting:
                        return user_setting[key]
                else:
                    if category in self.user_settings[user_id]:
                        return self.user_settings[user_id][category]
            
            # Fall back to global settings
            if key:
                return self.settings.get(category, {}).get(key)
            else:
                return self.settings.get(category, {})
        except Exception as e:
            LOGS.error(f"Error getting setting {category}.{key}: {e}")
            return None
    
    def set_setting(self, category: str, key: str, value: Any, user_id: int = None):
        """Set a setting value"""
        try:
            if user_id:
                # Set user-specific setting
                if user_id not in self.user_settings:
                    self.user_settings[user_id] = {}
                if category not in self.user_settings[user_id]:
                    self.user_settings[user_id][category] = {}
                self.user_settings[user_id][category][key] = value
                LOGS.info(f"Set user setting {category}.{key} = {value} for user {user_id}")
                # Save user settings to JSON
                self.save_user_settings()
            else:
                # Set global setting
                if category not in self.settings:
                    self.settings[category] = {}
                self.settings[category][key] = value
                LOGS.info(f"Set global setting {category}.{key} = {value}")
                self.save_settings()
            return True
        except Exception as e:
            LOGS.error(f"Error setting {category}.{key}: {e}")
            return False
    
    def get_active_compression_settings(self, user_id: int = None) -> Dict[str, Any]:
        """Get the currently active compression settings for a user"""
        active_preset = self.get_setting("active_preset", user_id=user_id) or "balanced"
        
        # Check if it's a preset or custom
        if active_preset == "custom":
            return self.get_setting("custom_compression", user_id=user_id)
        else:
            presets = self.get_setting("compression_presets")
            if active_preset in presets:
                return presets[active_preset]
            else:
                # Fallback to balanced preset
                return presets.get("balanced", self.get_setting("custom_compression"))
    
    def set_active_preset(self, preset_name: str, user_id: int = None):
        """Set the active compression preset for a user"""
        if user_id:
            # Set user-specific setting
            if user_id not in self.user_settings:
                self.user_settings[user_id] = {}
            self.user_settings[user_id]["active_preset"] = preset_name
        else:
            # Set global setting
            self.settings["active_preset"] = preset_name
            self.save_settings()
        return True
    
    def get_available_presets(self) -> Dict[str, str]:
        """Get available compression presets with descriptions"""
        presets = self.get_setting("compression_presets")
        descriptions = {
            "ultra_fast": "🚀 Ultra Fast - Fastest compression, larger file size",
            "fast": "⚡ Fast - Quick compression, good quality",
            "balanced": "⚖️ Balanced - Good balance of speed and quality",
            "quality": "🎯 Quality - Better quality, slower compression",
            "high_quality": "💎 High Quality - Best quality, slowest compression",
            "nvidia_fast": "🚀 NVIDIA Fast - Hardware accelerated, fast",
            "nvidia_balanced": "⚖️ NVIDIA Balanced - Hardware accelerated, balanced",
            "nvidia_quality": "💎 NVIDIA Quality - Hardware accelerated, high quality",
            "custom": "🔧 Custom - User-defined settings"
        }
        
        available = {}
        for preset in presets.keys():
            if preset.startswith("nvidia") and GPU_TYPE != "nvidia":
                continue
            available[preset] = descriptions.get(preset, f"📋 {preset.title()}")
        
        available["custom"] = descriptions["custom"]
        return available

    def set_active_preset(self, preset_name: str, user_id: int = None):
        """Set the active compression preset"""
        try:
            if preset_name in self.settings.get("compression_presets", {}):
                if user_id:
                    # Set user-specific preset
                    if user_id not in self.user_settings:
                        self.user_settings[user_id] = {}
                    self.user_settings[user_id]["active_preset"] = preset_name
                    self.save_user_settings()
                else:
                    # Set global preset
                    self.settings["active_preset"] = preset_name
                    self.save_settings()
                LOGS.info(f"Set active preset to {preset_name} for user {user_id if user_id else 'global'}")
                return True
            return False
        except Exception as e:
            LOGS.error(f"Error setting active preset: {e}")
            return False

    def get_active_compression_settings(self, user_id: int = None):
        """Get the active compression settings based on current preset"""
        try:
            active_preset = self.get_setting("active_preset", user_id=user_id) or "balanced"

            # Get preset settings
            preset_settings = self.settings.get("compression_presets", {}).get(active_preset, {})

            # Get custom overrides
            custom_settings = self.get_setting("custom_compression", user_id=user_id) or {}

            # Merge preset with custom overrides
            final_settings = preset_settings.copy()
            final_settings.update(custom_settings)

            return final_settings
        except Exception as e:
            LOGS.error(f"Error getting active compression settings: {e}")
            return self.settings.get("custom_compression", {})

# Global settings manager instance
settings_manager = SettingsManager()
