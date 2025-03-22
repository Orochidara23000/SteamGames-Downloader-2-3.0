import os
import sys
import logging
import argparse
from pathlib import Path

# Add project root to path to ensure modules are found
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.insert(0, current_dir)

# Set up logging
def setup_logging(log_level=logging.INFO):
    """Set up logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("app.log")
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized")
    return logger

# Parse command line arguments
def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Steam Games Downloader")
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug logging"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=7860, 
        help="Port to run the server on"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0", 
        help="Host to run the server on"
    )
    parser.add_argument(
        "--share", 
        action="store_true", 
        help="Create a public share link"
    )
    return parser.parse_args()

# Initialize directories
def initialize_directories():
    """Initialize necessary directories"""
    # Create directories if they don't exist
    directories = ["logs", "data", "downloads"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    # Create data subdirectories
    data_subdirs = ["config", "cache", "library"]
    for subdir in data_subdirs:
        Path(f"data/{subdir}").mkdir(exist_ok=True)

# Main function
def main():
    """Main application entry point"""
    # Parse arguments
    args = parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logging(log_level)
    logger.info("Starting Steam Games Downloader")
    
    # Initialize directories
    initialize_directories()
    logger.info("Directories initialized")
    
    try:
        # Import UI components after path is set
        from ui.main_ui import create_ui
        app = create_ui()
        
        # Launch the application
        logger.info(f"Launching UI on {args.host}:{args.port}")
        app.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
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