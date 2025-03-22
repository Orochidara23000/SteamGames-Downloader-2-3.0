#!/usr/bin/env python3
"""
Extremely simple launcher for Steam Games Downloader
"""

import os
import sys
import logging
from pathlib import Path

# Absolute path to this script
script_path = os.path.dirname(os.path.abspath(__file__))

# Ensure all necessary directories exist
for directory in ["ui", "modules", "utils", "logs", "data", "downloads"]:
    Path(os.path.join(script_path, directory)).mkdir(exist_ok=True)

# Ensure data subdirectories exist
for subdir in ["config", "cache", "library"]:
    Path(os.path.join(script_path, f"data/{subdir}")).mkdir(exist_ok=True)

# Ensure Python can find our modules
for path in [script_path, 
           os.path.join(script_path, "ui"),
           os.path.join(script_path, "modules"),
           os.path.join(script_path, "utils")]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(script_path, "app.log"))
    ]
)
logger = logging.getLogger("simple")
logger.info("Starting Steam Games Downloader (simple launcher)")

# Create empty __init__.py files if they don't exist
for directory in ["", "ui", "modules", "utils"]:
    init_file = os.path.join(script_path, directory, "__init__.py")
    if directory and not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write(f'"""{directory} package"""')
        logger.info(f"Created {init_file}")

# Print Python path for debugging
logger.info("Python path:")
for path in sys.path:
    logger.info(f"  - {path}")

# Attempt to import and run the UI
try:
    logger.info("Attempting direct import of main_ui")
    try:
        from main_ui import create_ui
    except ImportError:
        logger.info("Trying from ui.main_ui")
        from ui.main_ui import create_ui
    
    logger.info("Creating UI")
    app = create_ui()
    
    logger.info("Launching application")
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        prevent_thread_lock=False
    )
    logger.info("Application launched")
    
except Exception as e:
    logger.error(f"Error starting application: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1) 