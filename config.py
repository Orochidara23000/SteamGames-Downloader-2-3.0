#!/usr/bin/env python3
"""
Configuration module for Steam Games Downloader
"""

import os
import json
import logging
from pathlib import Path

# Set up logger
logger = logging.getLogger(__name__)

class Config:
    """Configuration class for Steam Games Downloader"""
    
    # Default configuration
    DEFAULT_CONFIG = {
        "download_path": "/data/downloads" if os.path.exists("/data/downloads") else os.path.join(os.path.expanduser("~"), "downloads"),
        "steamcmd_path": "/root/steamcmd" if os.path.exists("/root/steamcmd") else os.path.join(os.path.expanduser("~"), "steamcmd"),
        "auto_login": False,
        "anonymous_login": True,
        "username": "",
        "password": "",
        "remember_password": False,
        "default_platform": "windows",
        "language": "english",
        "max_concurrent_downloads": 1,
        "validate_files": True
    }
    
    def __init__(self):
        """Initialize the configuration"""
        logger.info("Initializing configuration")
        
        # Create config directory if it doesn't exist
        self.config_dir = os.path.join(os.getcwd(), "data", "config")
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Config file path
        self.config_file = os.path.join(self.config_dir, "config.json")
        
        # Load or create configuration
        self.config = self._load_config()
        logger.info("Configuration loaded")
    
    def _load_config(self):
        """Load configuration from file or create default"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                logger.info(f"Loaded configuration from {self.config_file}")
                
                # Update with any missing defaults
                updated = False
                for key, value in self.DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                        updated = True
                
                if updated:
                    self._save_config(config)
                    logger.info("Updated configuration with missing defaults")
                
                return config
            else:
                logger.info("No configuration file found, using defaults")
                self._save_config(self.DEFAULT_CONFIG)
                return self.DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            logger.info("Using default configuration")
            return self.DEFAULT_CONFIG.copy()
    
    def _save_config(self, config):
        """Save configuration to file"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def get(self, key, default=None):
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set a configuration value"""
        self.config[key] = value
        self._save_config(self.config)
    
    def reset(self):
        """Reset configuration to defaults"""
        self.config = self.DEFAULT_CONFIG.copy()
        self._save_config(self.config)
        logger.info("Configuration reset to defaults")

# Singleton instance
_config = None

def get_config():
    """Get the singleton configuration instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config

# For direct testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Get configuration
    config = get_config()
    
    # Print current configuration
    print("Current configuration:")
    for key, value in config.config.items():
        print(f"  {key}: {value}")
    
    # Test setting a value
    config.set("download_threads", 2)
    print(f"Updated download_threads: {config.get('download_threads')}") 