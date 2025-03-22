#!/usr/bin/env python3
"""
Steam Games Downloader - Simple Entry Point

This script provides a simple entry point for the Steam Games Downloader
application, with improved import handling.
"""

import os
import sys
import logging
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
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger("app")

# Initialize directories
def initialize_directories():
    """Initialize necessary directories"""
    directories = ["logs", "data", "downloads"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    # Create data subdirectories
    data_subdirs = ["config", "cache", "library"]
    for subdir in data_subdirs:
        Path(f"data/{subdir}").mkdir(exist_ok=True)
    
    logger.info("Directories initialized")

# Main function
def main():
    """Main application entry point"""
    logger.info("Starting Steam Games Downloader")
    
    # Initialize directories
    initialize_directories()
    
    try:
        # Try importing the main UI directly
        try:
            from main_ui import create_ui
            logger.info("Imported UI using direct import")
        except ImportError:
            # Fall back to using full import path
            logger.info("Direct import failed, trying with full path")
            from ui.main_ui import create_ui
        
        # Create and launch the UI
        app = create_ui()
        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            prevent_thread_lock=False
        )
        
    except ImportError as e:
        logger.error(f"Import error: {str(e)}")
        logger.error("Make sure the project structure is correct with 'ui', 'modules', and 'utils' directories")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 