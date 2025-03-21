#!/usr/bin/env python3

import os
import sys
import logging
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Steam Games Downloader Docker entrypoint...")
    
    # Print environment variables for debugging
    logger.info(f"PORT={os.environ.get('PORT', '7862')}")
    logger.info(f"SHARE={os.environ.get('ENABLE_SHARE', 'True')}")
    logger.info(f"DEBUG={os.environ.get('DEBUG', 'False')}")
    
    # Set environment variables for the app
    os.environ["PORT"] = os.environ.get("PORT", "7862")
    os.environ["ENABLE_SHARE"] = "True"
    
    print("="*50)
    print("Starting Steam Games Downloader in Docker container")
    print("="*50)
    
    # Run the main application
    try:
        subprocess.run(["python", "main.py"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Application exited with error code {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    main() 