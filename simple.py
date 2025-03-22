#!/usr/bin/env python3
"""
Simple launcher for Steam Games Downloader
This script handles import paths and gracefully handles errors
"""

import os
import sys
import logging
import platform
import traceback
from pathlib import Path
import importlib
import shutil

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simple")

def ensure_path():
    """Ensure proper import paths are set"""
    # Add current directory to path
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    
    # Add subdirectories to path
    for subdir in ["ui", "modules", "utils"]:
        subdir_path = os.path.join(cwd, subdir)
        if os.path.isdir(subdir_path) and subdir_path not in sys.path:
            sys.path.append(subdir_path)
    
    # Log Python path
    logger.info(f"Python path: {':'.join(sys.path)}")

def ensure_init_files():
    """Ensure all directories have __init__.py files"""
    for subdir in ["ui", "modules", "utils"]:
        init_file = os.path.join(os.getcwd(), subdir, "__init__.py")
        if not os.path.exists(init_file):
            try:
                Path(init_file).touch()
                logger.info(f"Created {init_file}")
            except Exception as e:
                logger.error(f"Error creating {init_file}: {str(e)}")

def check_system_info():
    """Print system information for debugging"""
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Current directory: {os.getcwd()}")
    
    # Check if running in Docker
    in_docker = os.path.exists("/.dockerenv")
    logger.info(f"Running in Docker: {in_docker}")
    
    # Check directory structure
    for subdir in ["ui", "modules", "utils"]:
        subdir_path = os.path.join(os.getcwd(), subdir)
        logger.info(f"Directory {subdir_path} exists: {os.path.isdir(subdir_path)}")

def check_required_files():
    """Check if required UI files exist"""
    ui_dir = os.path.join(os.getcwd(), "ui")
    if not os.path.isdir(ui_dir):
        logger.error(f"UI directory not found: {ui_dir}")
        return False
    
    # Check for main UI files
    required_files = [
        "main_ui.py",
        "download_tab.py",
        "library_tab.py",
        "settings_tab.py"
    ]
    
    for file in required_files:
        file_path = os.path.join(ui_dir, file)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            logger.info(f"File {file} exists with size {file_size} bytes")
        else:
            logger.error(f"Required file not found: {file_path}")
            return False
    
    return True

def safe_import(module_name, fallback_path=None):
    """Safely import a module with fallback"""
    logger.info(f"Attempting to import {module_name}")
    
    try:
        # Try direct import
        module = importlib.import_module(module_name)
        logger.info(f"Successfully imported {module_name}")
        return module
    except ImportError as e:
        logger.warning(f"Failed to import {module_name}: {str(e)}")
        
        # Try from ui package
        try:
            module = importlib.import_module(f"ui.{module_name}")
            logger.info(f"Successfully imported ui.{module_name}")
            return module
        except ImportError as e:
            logger.warning(f"Failed to import ui.{module_name}: {str(e)}")
            
            # If fallback path provided, try copying the file
            if fallback_path:
                try:
                    # Check if file exists
                    if os.path.exists(fallback_path):
                        # Copy to current directory
                        dest_path = os.path.basename(fallback_path)
                        shutil.copy2(fallback_path, dest_path)
                        logger.info(f"Copied {fallback_path} to {dest_path}")
                        
                        # Try importing again
                        module_name_only = os.path.splitext(os.path.basename(fallback_path))[0]
                        module = importlib.import_module(module_name_only)
                        logger.info(f"Successfully imported {module_name_only} after copying")
                        return module
                except Exception as e:
                    logger.error(f"Failed to import after copying: {str(e)}")
            
            raise ImportError(f"Could not import {module_name}")

def main():
    """Main entry point"""
    try:
        # Setup and checks
        check_system_info()
        ensure_path()
        ensure_init_files()
        
        if not check_required_files():
            logger.error("Some required files are missing")
            sys.exit(1)
        
        # Try to import required modules
        try:
            download_tab = safe_import("download_tab", 
                                     fallback_path=os.path.join(os.getcwd(), "ui", "download_tab.py"))
            logger.info("Successfully imported download_tab")
        except ImportError as e:
            logger.error(f"Failed to import download_tab: {str(e)}")
            sys.exit(1)
        
        try:
            import utils.config as config
            logger.info("Successfully imported utils.config")
        except ImportError as e:
            logger.error(f"Failed to import config: {str(e)}")
            
            # Try fallback
            try:
                config = safe_import("config", 
                                     fallback_path=os.path.join(os.getcwd(), "utils", "config.py"))
                logger.info("Successfully imported config via fallback")
            except ImportError as e:
                logger.error(f"Failed to import config via fallback: {str(e)}")
                sys.exit(1)
        
        # Import main UI
        try:
            main_ui = safe_import("main_ui", 
                                 fallback_path=os.path.join(os.getcwd(), "ui", "main_ui.py"))
            logger.info("Successfully imported main_ui")
        except ImportError as e:
            logger.error(f"Failed to import main_ui: {str(e)}")
            sys.exit(1)
        
        # Last resort: copy all UI files to current directory
        if not hasattr(main_ui, "create_ui"):
            logger.warning("main_ui module doesn't have create_ui function, trying last resort")
            
            # Copy all UI files to current directory
            ui_dir = os.path.join(os.getcwd(), "ui")
            for file in os.listdir(ui_dir):
                if file.endswith(".py"):
                    src_path = os.path.join(ui_dir, file)
                    dest_path = file
                    try:
                        shutil.copy2(src_path, dest_path)
                        logger.info(f"Copied {src_path} to {dest_path}")
                    except Exception as e:
                        logger.error(f"Failed to copy {src_path}: {str(e)}")
            
            # Try importing again
            try:
                main_ui = importlib.import_module("main_ui")
                logger.info("Successfully imported main_ui after copying")
            except ImportError as e:
                logger.error(f"Still failed to import main_ui: {str(e)}")
                sys.exit(1)
        
        # Launch the application
        logger.info("Launching the application")
        
        # Get the UI interface
        app = main_ui.create_ui()
        
        # Launch the app
        app.launch(server_name="0.0.0.0", server_port=7860)
        
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 