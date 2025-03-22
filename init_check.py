#!/usr/bin/env python3
"""
Initialization Check Script

This script performs system checks at startup to ensure the environment
is properly configured for running the Steam Games Downloader.
"""

import os
import sys
import logging
import platform
import shutil
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("InitCheck")

def check_system():
    """Check system compatibility and environment"""
    logger.info("Checking system compatibility...")
    
    # Check Python version
    python_version = platform.python_version()
    logger.info(f"Python version: {python_version}")
    
    # Check OS
    os_system = platform.system()
    os_release = platform.release()
    logger.info(f"Operating System: {os_system} {os_release}")
    
    # Check if we're in a container
    is_container = os.path.exists("/.dockerenv") or os.path.exists("/var/run/docker.sock")
    logger.info(f"Running in container: {is_container}")
    
    # Check for required libraries
    try:
        import gradio
        logger.info(f"Gradio version: {gradio.__version__}")
    except ImportError:
        logger.error("Gradio is not installed. Please install it with: pip install gradio")
        return False
    
    try:
        import pandas
        logger.info(f"Pandas version: {pandas.__version__}")
    except ImportError:
        logger.error("Pandas is not installed. Please install it with: pip install pandas")
        return False
    
    try:
        import requests
        logger.info(f"Requests version: {requests.__version__}")
    except ImportError:
        logger.error("Requests is not installed. Please install it with: pip install requests")
        return False
    
    return True

def check_directories():
    """Check and create necessary directories"""
    logger.info("Checking directories...")
    
    # Essential directories
    directories = [
        "logs",
        "data",
        "data/config",
        "data/cache",
        "data/library",
        "downloads",
        "downloads/steamapps",
        "downloads/steamapps/common"
    ]
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            logger.info(f"Creating directory: {path}")
            path.mkdir(parents=True, exist_ok=True)
        
        # Check permissions
        if not os.access(path, os.W_OK):
            logger.warning(f"No write permission for directory: {path}")
            if os.name != 'nt':  # Not on Windows
                logger.info(f"Attempting to fix permissions for {path}")
                try:
                    os.chmod(path, 0o755)
                    if os.access(path, os.W_OK):
                        logger.info(f"Fixed permissions for {path}")
                    else:
                        logger.warning(f"Could not fix permissions for {path}")
                except Exception as e:
                    logger.error(f"Error fixing permissions: {str(e)}")
    
    return True

def check_steamcmd():
    """Check SteamCMD installation"""
    logger.info("Checking SteamCMD...")
    
    # Import our SteamCMD manager
    try:
        from modules.steamcmd_manager import get_instance
        steamcmd = get_instance()
        
        if steamcmd.is_installed():
            logger.info(f"SteamCMD found at: {steamcmd.steamcmd_path}")
            logger.info("Testing SteamCMD...")
            
            if steamcmd.verify_installation():
                logger.info("SteamCMD is working correctly")
                return True
            else:
                logger.warning("SteamCMD test failed, but will try to recover during runtime")
        else:
            logger.warning("SteamCMD not found, but will be installed during runtime if needed")
            
        # Note: We don't fail if SteamCMD is not installed
        # The application will handle this during runtime
        return True
        
    except Exception as e:
        logger.error(f"Error checking SteamCMD: {str(e)}")
        logger.warning("Will attempt to recover during runtime")
        return True

def check_network():
    """Check network connectivity for Steam services"""
    logger.info("Checking network connectivity...")
    
    try:
        import requests
        
        # Check Steam Store connectivity
        logger.info("Testing connection to Steam Store...")
        response = requests.get("https://store.steampowered.com/", timeout=5)
        if response.status_code == 200:
            logger.info("Steam Store is accessible")
        else:
            logger.warning(f"Steam Store returned status code: {response.status_code}")
        
        # Check Steam API connectivity
        logger.info("Testing connection to Steam API...")
        response = requests.get("https://api.steampowered.com/ISteamWebAPIUtil/GetSupportedAPIList/v1/", timeout=5)
        if response.status_code == 200:
            logger.info("Steam API is accessible")
        else:
            logger.warning(f"Steam API returned status code: {response.status_code}")
            
        return True
    except Exception as e:
        logger.warning(f"Network connectivity test failed: {str(e)}")
        logger.warning("The application may have limited functionality without network access")
        return True  # Continue anyway, as we might be offline intentionally

def run_checks():
    """Run all checks and return overall status"""
    logger.info("Starting initialization checks...")
    
    checks = [
        check_system(),
        check_directories(),
        check_steamcmd(),
        check_network()
    ]
    
    if all(checks):
        logger.info("All checks passed successfully!")
        return True
    else:
        logger.warning("Some checks failed. The application may have limited functionality.")
        return False

if __name__ == "__main__":
    # Add parent directory to path to ensure modules are found
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    success = run_checks()
    sys.exit(0 if success else 1)