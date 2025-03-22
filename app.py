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

# Ensure current directory is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

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

# Check for UI files
def check_files():
    """Check if required files exist"""
    required_files = ["main_ui.py", "download_tab.py", "library_tab.py", "settings_tab.py", 
                     "download_manager.py", "steamcmd_manager.py", "library_manager.py", 
                     "steam_api.py", "config.py"]
    missing_files = []
    
    for file in required_files:
        file_path = os.path.join(current_dir, file)
        if os.path.exists(file_path):
            logger.info(f"File exists: {file}")
        else:
            logger.error(f"File missing: {file}")
            missing_files.append(file)
    
    return missing_files

# Create minimal main_ui.py if missing
def create_minimal_main_ui():
    """Create minimal main_ui.py if it is missing"""
    main_ui_path = os.path.join(current_dir, "main_ui.py")
    if not os.path.exists(main_ui_path):
        with open(main_ui_path, "w") as f:
            f.write("""
import logging
import gradio as gr

logger = logging.getLogger(__name__)

def create_ui():
    logger.info("Creating minimal UI")
    interface = gr.Blocks(title="Steam Games Downloader")
    with interface:
        gr.Markdown("# Steam Games Downloader")
        gr.Markdown("## Minimal Interface")
        gr.Markdown("SteamCMD is installed and working. This is a minimal UI for testing.")
    return interface
""")
        logger.info(f"Created minimal main_ui.py")

# Main function
def main():
    """Main application entry point"""
    logger.info("Starting Steam Games Downloader")
    
    # Initialize directories
    initialize_directories()
    
    # Check required files
    missing_files = check_files()
    
    # Create minimal main_ui if needed
    if "main_ui.py" in missing_files:
        logger.warning(f"Creating minimal main_ui.py")
        create_minimal_main_ui()
    
    try:
        # Import main_ui
        logger.info("Attempting to import main_ui")
        import main_ui
        logger.info("Successfully imported main_ui")
        create_ui = main_ui.create_ui
    except ImportError as e:
        logger.error(f"Failed to import main_ui: {str(e)}")
        
        # Last resort - create a minimal UI function directly
        logger.warning("Creating a minimal UI function directly")
        def create_ui():
            import gradio as gr
            interface = gr.Blocks(title="Steam Games Downloader - Emergency UI")
            with interface:
                gr.Markdown("# Steam Games Downloader")
                gr.Markdown("## Emergency UI")
                gr.Markdown("Failed to load UI modules. This is an emergency interface.")
            return interface
        
        # Make sure gradio is imported
        try:
            import gradio as gr
        except ImportError:
            logger.error("Gradio not installed, cannot create UI")
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