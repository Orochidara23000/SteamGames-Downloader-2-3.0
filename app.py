#!/usr/bin/env python3
"""
Steam Games Downloader - Simple Entry Point

This script provides a simple entry point for the Steam Games Downloader
application, with improved import handling.
"""

import os
import sys
import logging
import traceback
from pathlib import Path

# Ensure paths are set correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
for subdir in ["ui", "modules", "utils"]:
    subdir_path = os.path.join(current_dir, subdir)
    if os.path.exists(subdir_path) and subdir_path not in sys.path:
        sys.path.insert(0, subdir_path)

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more information
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger("app")

# Print system information for debugging
logger.info(f"Python version: {sys.version}")
logger.info(f"Current directory: {current_dir}")
logger.info(f"Python path: {sys.path}")
logger.info(f"Environment: {os.environ.get('PYTHONPATH', 'Not set')}")

# Initialize directories
def initialize_directories():
    """Initialize necessary directories"""
    directories = ["logs", "data", "downloads"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")
    
    # Create data subdirectories
    data_subdirs = ["config", "cache", "library"]
    for subdir in data_subdirs:
        os.makedirs(f"data/{subdir}", exist_ok=True)
        logger.info(f"Ensured subdirectory exists: data/{subdir}")
    
    logger.info("Directories initialized")

# Create any missing __init__.py files
def create_init_files():
    """Create __init__.py files in all package directories if missing"""
    for dir_name in ["ui", "modules", "utils"]:
        init_file = os.path.join(current_dir, dir_name, "__init__.py")
        if not os.path.exists(init_file):
            Path(init_file).touch()
            logger.info(f"Created {init_file}")

# Check for UI files
def check_ui_files():
    """Check if UI files exist"""
    ui_files = ["main_ui.py", "download_tab.py", "library_tab.py", "settings_tab.py"]
    ui_dir = os.path.join(current_dir, "ui")
    
    for file in ui_files:
        file_path = os.path.join(ui_dir, file)
        if os.path.exists(file_path):
            logger.info(f"UI file exists: {file}")
        else:
            logger.error(f"UI file missing: {file}")

# Main function
def main():
    """Main application entry point"""
    logger.info("Starting Steam Games Downloader")
    
    # Create init files
    create_init_files()
    
    # Initialize directories
    initialize_directories()
    
    # Check UI files
    check_ui_files()
    
    try:
        # First try importing main_ui from ui package
        logger.info("Attempting to import ui.main_ui")
        from ui.main_ui import create_ui
        logger.info("Successfully imported ui.main_ui")
    except ImportError as e:
        logger.error(f"Failed to import ui.main_ui: {str(e)}")
        
        try:
            # Fall back to direct import
            logger.info("Trying direct import of main_ui")
            sys.path.insert(0, os.path.join(current_dir, "ui"))
            import main_ui
            create_ui = main_ui.create_ui
            logger.info("Successfully imported main_ui using direct import")
        except ImportError as e:
            logger.error(f"All import attempts failed: {str(e)}")
            logger.error(f"Python path: {sys.path}")
            logger.error(f"Files in ui directory: {os.listdir(os.path.join(current_dir, 'ui'))}")
            sys.exit(1)
    
    try:
        # Create and launch the UI
        logger.info("Creating UI interface")
        app = create_ui()
        
        logger.info("Launching application")
        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            prevent_thread_lock=False
        )
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}")
        logger.critical(traceback.format_exc())
        sys.exit(1) 