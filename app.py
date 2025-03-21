import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.info("Starting Steam Games Downloader via app.py entry point")

# Set environment variables
os.environ["ENABLE_SHARE"] = "True"
os.environ["PORT"] = os.environ.get("PORT", "8080")

# Import and run the main application
if __name__ == "__main__":
    print("="*50)
    print("Starting Steam Games Downloader via app.py")
    print("="*50)
    
    # Import the main module
    import main 