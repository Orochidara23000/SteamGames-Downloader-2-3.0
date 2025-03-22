#!/usr/bin/env python3
"""
Main launcher for Steam Games Downloader
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("run")

def main():
    """Main entry point"""
    logger.info("Starting Steam Games Downloader...")
    
    # Add directories to Python path
    cwd = os.getcwd()
    for path in [cwd, 
                os.path.join(cwd, "ui"),
                os.path.join(cwd, "modules"),
                os.path.join(cwd, "utils")]:
        if path not in sys.path:
            sys.path.insert(0, path)
            logger.info(f"Added to Python path: {path}")
    
    # Ensure __init__.py files exist
    for subdir in ["ui", "modules", "utils"]:
        init_file = os.path.join(cwd, subdir, "__init__.py")
        if not os.path.exists(init_file):
            Path(init_file).touch()
            logger.info(f"Created {init_file}")
    
    # Import main UI
    try:
        from ui.main_ui import create_ui
        logger.info("Successfully imported main_ui")
    except ImportError as e:
        logger.error(f"Failed to import main_ui from ui: {str(e)}")
        
        try:
            import main_ui
            create_ui = main_ui.create_ui
            logger.info("Successfully imported main_ui directly")
        except ImportError as e:
            logger.error(f"Failed to import main_ui directly: {str(e)}")
            sys.exit(1)
    
    # Create and launch UI
    logger.info("Creating UI interface...")
    interface = create_ui()
    
    # Launch UI
    logger.info("Launching application...")
    interface.launch(server_name="0.0.0.0", server_port=7860)

if __name__ == "__main__":
    main() 