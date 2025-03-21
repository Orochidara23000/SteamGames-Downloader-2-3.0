#!/usr/bin/env python3

import os
import sys
import logging
import subprocess
import time
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Handle SIGTERM gracefully
def handle_sigterm(signum, frame):
    logger.info("Received SIGTERM signal, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

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
    
    # Start the main application in a subprocess
    process = subprocess.Popen(["python", "main.py"])
    
    # Wait for a short time to make sure Gradio has time to start
    time.sleep(5)
    
    # Keep container running until stopped
    logger.info("Main application started. Container will stay running until stopped.")
    try:
        # Check if process is still running and keep the container alive
        while process.poll() is None:
            time.sleep(1)
            
        # If we get here, the process has exited
        exit_code = process.returncode
        logger.info(f"Main application exited with code {exit_code}")
        if exit_code != 0:
            logger.error("Main application crashed. Check logs for details.")
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    finally:
        # Try to clean up the process if it's still running
        if process.poll() is None:
            logger.info("Terminating main application...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Application did not terminate gracefully, forcing...")
                process.kill()

if __name__ == "__main__":
    main() 