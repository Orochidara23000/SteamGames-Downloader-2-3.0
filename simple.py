#!/usr/bin/env python3
"""
Extremely simple launcher for Steam Games Downloader
"""

import os
import sys
import logging
import traceback
from pathlib import Path

# Absolute path to this script
script_path = os.path.dirname(os.path.abspath(__file__))

# Configure logging first to capture everything
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for maximum information
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(script_path, "app.log"))
    ]
)
logger = logging.getLogger("simple")
logger.info("=" * 80)
logger.info("Starting Steam Games Downloader (simple launcher)")
logger.info("=" * 80)

# Log system information
logger.info(f"Python version: {sys.version}")
logger.info(f"Platform: {sys.platform}")
logger.info(f"Current directory: {script_path}")
logger.info(f"Is Docker container: {os.path.exists('/.dockerenv')}")

try:
    # Ensure all necessary directories exist
    for directory in ["ui", "modules", "utils", "logs", "data", "downloads"]:
        dir_path = os.path.join(script_path, directory)
        Path(dir_path).mkdir(exist_ok=True)
        logger.info(f"Ensuring directory exists: {dir_path}")

    # Ensure data subdirectories exist
    for subdir in ["config", "cache", "library"]:
        data_dir = os.path.join(script_path, f"data/{subdir}")
        Path(data_dir).mkdir(exist_ok=True)
        logger.info(f"Ensuring data directory exists: {data_dir}")

    # Create empty __init__.py files if they don't exist
    for directory in ["", "ui", "modules", "utils"]:
        dir_path = script_path if directory == "" else os.path.join(script_path, directory)
        init_file = os.path.join(dir_path, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write(f'"""{directory} package"""')
            logger.info(f"Created {init_file}")
        else:
            logger.info(f"Init file already exists: {init_file}")

    # Ensure Python can find our modules
    for path in [script_path, 
               os.path.join(script_path, "ui"),
               os.path.join(script_path, "modules"),
               os.path.join(script_path, "utils")]:
        if path not in sys.path:
            sys.path.insert(0, path)
            logger.info(f"Added to Python path: {path}")
        else:
            logger.info(f"Already in Python path: {path}")

    # Print Python path for debugging
    logger.info("Full Python path:")
    for i, path in enumerate(sys.path):
        logger.info(f"  {i}: {path}")

    # Check if ui directory has the required files
    ui_dir = os.path.join(script_path, "ui")
    if os.path.exists(ui_dir):
        logger.info(f"Files in ui directory:")
        for file in os.listdir(ui_dir):
            file_path = os.path.join(ui_dir, file)
            if os.path.isfile(file_path):
                logger.info(f"  - {file} ({os.path.getsize(file_path)} bytes)")

    # Attempt to import each required module separately
    try:
        logger.info("Testing import of download_tab")
        import download_tab
        logger.info("Success: download_tab imported directly")
    except ImportError as e:
        logger.info(f"Failed to import download_tab directly: {e}")
        try:
            logger.info("Testing import from ui.download_tab")
            from ui import download_tab
            logger.info("Success: download_tab imported from ui")
        except ImportError as e:
            logger.error(f"Failed to import download_tab from ui: {e}")

    try:
        logger.info("Testing import of config")
        import config
        logger.info("Success: config imported directly")
    except ImportError as e:
        logger.info(f"Failed to import config directly: {e}")
        try:
            logger.info("Testing import from utils.config")
            from utils import config
            logger.info("Success: config imported from utils")
        except ImportError as e:
            logger.error(f"Failed to import config from utils: {e}")

    # Attempt to import and run the UI
    logger.info("Attempting to import main_ui")
    try:
        logger.info("Trying direct import: from main_ui import create_ui")
        from main_ui import create_ui
        logger.info("Success: main_ui imported directly")
    except ImportError as e:
        logger.info(f"Direct import failed: {e}")
        try:
            logger.info("Trying full path: from ui.main_ui import create_ui")
            from ui.main_ui import create_ui
            logger.info("Success: main_ui imported from ui")
        except ImportError as e:
            logger.error(f"Full path import also failed: {e}")
            
            # Last resort: try to fix imports by copying files
            logger.info("Attempting to copy UI files to current directory as a last resort")
            for ui_file in ['main_ui.py', 'download_tab.py', 'library_tab.py', 'settings_tab.py']:
                source = os.path.join(script_path, 'ui', ui_file)
                if os.path.exists(source):
                    import shutil
                    dest = os.path.join(script_path, ui_file)
                    shutil.copy2(source, dest)
                    logger.info(f"Copied {source} to {dest}")
            
            # Try import again after copying
            logger.info("Trying direct import again after copying files")
            from main_ui import create_ui
            logger.info("Success: main_ui imported after copying")

    # If we get here, we've successfully imported create_ui
    logger.info("Creating UI")
    app = create_ui()
    
    logger.info("Launching application")
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        prevent_thread_lock=False
    )
    logger.info("Application launched successfully")
    
except Exception as e:
    logger.error(f"Error starting application: {str(e)}")
    logger.error("Traceback:")
    logger.error(traceback.format_exc())
    sys.exit(1) 