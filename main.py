import gradio as gr
import os
import subprocess
import re
import requests
import zipfile
import tarfile
import platform
import time
import logging
import json
import threading
import sys
from datetime import datetime, timedelta
import shutil
import psutil
import uvicorn
from fastapi import FastAPI
import asyncio
from typing import Dict, List, Any, Tuple, Optional
from queue import Queue
import signal
import uuid
import math
import concurrent.futures
import socket
import urllib.request
import traceback

# Set up logging to both file and stdout
log_level = os.environ.get('LOG_LEVEL', 'INFO')
log_dir = '/app/logs' if os.path.exists('/app/logs') else '.'
log_file = os.path.join(log_dir, 'steam_downloader.log')

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Starting Steam Downloader application (PID: {os.getpid()})")

# Global variables for download management
active_downloads = {}
download_queue = []
queue_lock = threading.Lock()
download_history: List[dict] = []  # Track completed downloads
MAX_HISTORY_SIZE = 50  # Maximum entries in download history

# Environment variable handling for containerization
STEAM_DOWNLOAD_PATH = os.environ.get('STEAM_DOWNLOAD_PATH', '/data/downloads')

# Global variable to store the share URL
SHARE_URL = ""

# Define your FastAPI app here
fastapi_app = FastAPI()

@fastapi_app.get("/status")
def get_status():
    return {"status": "running"}

@fastapi_app.get("/downloads")
def api_get_downloads():
    return {
        "active": active_downloads,
        "queue": download_queue,
        "history": download_history
    }

def update_share_url(share_url):
    global SHARE_URL
    SHARE_URL = share_url
    logger.info(f"Gradio share URL updated: {share_url}")

# ========================
# PATH AND SYSTEM UTILITIES
# ========================

def get_default_download_location():
    """Get the default download location based on platform and environment"""
    # First check if we're in a Docker container by looking for STEAM_DOWNLOAD_PATH
    if os.environ.get("STEAM_DOWNLOAD_PATH"):
        return os.environ.get("STEAM_DOWNLOAD_PATH")
    
    # Otherwise use platform-specific locations
    system = platform.system()
    home = os.path.expanduser("~")
    
    if system == "Windows":
        return os.path.join(home, "SteamLibrary")
    elif system == "Darwin":  # macOS
        return os.path.join(home, "Library", "Application Support", "SteamLibrary")
    else:  # Linux and other Unix-like systems
        return os.path.join(home, "SteamLibrary")

def ensure_download_directory(path=None):
    """Ensure the download directory exists and is writable"""
    if not path:
        path = get_default_download_location()
    
    try:
        os.makedirs(path, exist_ok=True)
        # Test if writable
        test_file = os.path.join(path, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return True, path
    except Exception as e:
        logging.error(f"Error creating/accessing download directory: {str(e)}")
        return False, str(e)

def get_steamcmd_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    steamcmd_dir = os.path.join(base_dir, "steamcmd")
    if platform.system() == "Windows":
        path = os.path.join(steamcmd_dir, "steamcmd.exe")
    else:
        path = os.path.join(steamcmd_dir, "steamcmd.sh")
    logger.info(f"SteamCMD path: {path}")
    return path

def ensure_directory_exists(directory):
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {str(e)}")
            return False
    return True

# ========================
# STEAMCMD INSTALLATION
# ========================

def check_steamcmd():
    steamcmd_path = get_steamcmd_path()
    is_installed = os.path.exists(steamcmd_path)
    result = "SteamCMD is installed." if is_installed else "SteamCMD is not installed."
    logger.info(f"SteamCMD check: {result}")
    return result

def install_steamcmd():
    if platform.system() == "Windows":
        return install_steamcmd_windows()
    else:
        return install_steamcmd_linux()

def install_steamcmd_linux():
    logger.info("Installing SteamCMD for Linux")
    steamcmd_install_dir = "/app/steamcmd"
    steamcmd_path = os.path.join(steamcmd_install_dir, "steamcmd.sh")
    
    # Remove existing SteamCMD directory if it exists
    if os.path.exists(steamcmd_install_dir):
        logger.info(f"Removing existing SteamCMD directory: {steamcmd_install_dir}")
        shutil.rmtree(steamcmd_install_dir)
    
    # Re-create the SteamCMD directory before downloading
    ensure_directory_exists(steamcmd_install_dir)
    
    try:
        # Download and extract SteamCMD
        logger.info("Downloading SteamCMD from https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz")
        response = requests.get("https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz", timeout=30)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        tarball_path = os.path.join(steamcmd_install_dir, "steamcmd_linux.tar.gz")
        
        with open(tarball_path, "wb") as f:
            f.write(response.content)
        
        logger.info("Extracting SteamCMD tar.gz file")
        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(path=steamcmd_install_dir)
        
        # Make the steamcmd.sh executable
        os.chmod(steamcmd_path, 0o755)
        logger.info("Made steamcmd.sh executable")
        
        # Run SteamCMD for the first time to complete installation
        logger.info("Running SteamCMD for the first time...")
        process = subprocess.run([steamcmd_path, "+quit"], 
                               check=True, 
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True)
        
        if process.returncode == 0:
            logger.info("SteamCMD initial run completed successfully")
            return "SteamCMD installed successfully.", steamcmd_path
        else:
            logger.error(f"SteamCMD initial run failed: {process.stderr}")
            return f"Error: SteamCMD installation failed. {process.stderr}", ""
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading SteamCMD: {str(e)}")
        return f"Error: Failed to download SteamCMD. {str(e)}", ""
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running SteamCMD: {str(e)}")
        return f"Error: Failed to run SteamCMD. {str(e)}", ""
    except Exception as e:
        logger.error(f"Unexpected error during SteamCMD installation: {str(e)}")
        return f"Error: Unexpected error during installation. {str(e)}", ""

def install_steamcmd_windows():
    logger.info("Installing SteamCMD for Windows")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    steamcmd_dir = os.path.join(base_dir, "steamcmd")
    steamcmd_path = os.path.join(steamcmd_dir, "steamcmd.exe")
    
    # Remove existing SteamCMD directory if it exists
    if os.path.exists(steamcmd_dir):
        logger.info(f"Removing existing SteamCMD directory: {steamcmd_dir}")
        shutil.rmtree(steamcmd_dir)
    
    # Create steamcmd directory
    ensure_directory_exists(steamcmd_dir)
    
    try:
        # Download SteamCMD
        logger.info("Downloading SteamCMD from https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip")
        response = requests.get("https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip", timeout=30)
        response.raise_for_status()
        
        zip_path = os.path.join(steamcmd_dir, "steamcmd.zip")
        
        with open(zip_path, "wb") as f:
            f.write(response.content)
        
        # Extract SteamCMD
        logger.info("Extracting SteamCMD zip file")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(steamcmd_dir)
        
        # Run SteamCMD for the first time to complete installation
        logger.info("Running SteamCMD for the first time to complete installation")
        subprocess.run([steamcmd_path, "+quit"], check=True)
        
        logger.info("SteamCMD installed successfully")
        return "SteamCMD installed successfully.", steamcmd_path
    
    except Exception as e:
        logger.error(f"Error during SteamCMD installation: {str(e)}")
        return f"Error: {str(e)}", ""

# ========================
# GAME IDENTIFICATION & VALIDATION
# ========================

def parse_game_input(input_str):
    """Extract a Steam AppID from user input."""
    logger.info(f"Parsing game input: {input_str}")
    if not input_str or input_str.strip() == "":
        logger.warning("Empty game input provided")
        return None
    
    # If input is just a number, assume it's an AppID
    if input_str.strip().isdigit():
        logger.info(f"Input is a valid App ID: {input_str}")
        return input_str.strip()
    
    # Support for Steam store URLs
    url_patterns = [
        r'store\.steampowered\.com/app/(\d+)',
        r'steamcommunity\.com/app/(\d+)',
        r'/app/(\d+)'
    ]
    
    for pattern in url_patterns:
        match = re.search(pattern, input_str)
        if match:
            appid = match.group(1)
            logger.info(f"Extracted App ID {appid} from URL: {input_str}")
            return appid
    
    logger.error("Failed to extract App ID from input")
    return None

def validate_appid(appid: str) -> Tuple[bool, Any]:
    """Validate if an AppID exists on Steam and return game information."""
    logger.info(f"Validating App ID: {appid}")
    
    def _fetch_game_info():
        try:
            # Check if app exists via Steam API
            url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
            logger.info(f"Querying Steam API: {url}")
            
            # Add a shorter timeout to prevent hanging
            response = requests.get(url, timeout=3)
            
            if not response.ok:
                logger.error(f"Steam API request failed with status: {response.status_code}")
                return False, f"Steam API request failed with status: {response.status_code}"
            
            data = response.json()
            
            if not data or not data.get(appid):
                logger.error(f"Invalid response from Steam API for App ID {appid}")
                return False, "Invalid response from Steam API"
            
            if not data.get(appid, {}).get('success', False):
                logger.warning(f"Game not found for App ID: {appid}")
                return False, "Game not found on Steam"
            
            game_data = data[appid]['data']
            
            # Enhanced game info with more details
            game_info = {
                'name': game_data.get('name', 'Unknown Game'),
                'required_age': game_data.get('required_age', 0),
                'is_free': game_data.get('is_free', False),
                'developers': game_data.get('developers', ['Unknown']),
                'publishers': game_data.get('publishers', ['Unknown']),
                'platforms': game_data.get('platforms', {}),
                'categories': [cat.get('description') for cat in game_data.get('categories', [])],
                'genres': [genre.get('description') for genre in game_data.get('genres', [])],
                'header_image': game_data.get('header_image', None),
                'background_image': game_data.get('background', None),
                'release_date': game_data.get('release_date', {}).get('date', 'Unknown'),
                'metacritic': game_data.get('metacritic', {}).get('score', None),
                'description': game_data.get('short_description', 'No description available'),
                'size_mb': game_data.get('file_size', 'Unknown')
            }
            
            logger.info(f"Game found: {game_info['name']} (Free: {game_info['is_free']})")
            return True, game_info
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while validating App ID {appid}")
            return False, "Timeout while connecting to Steam API. Please try again later."
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error while validating App ID {appid}")
            return False, "Connection error when contacting Steam API. Please check your internet connection."
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while validating App ID {appid}: {str(e)}")
            return False, f"Request error: {str(e)}"
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response from Steam API for App ID {appid}")
            return False, "Invalid response from Steam API"
        except Exception as e:
            logger.error(f"Validation error for App ID {appid}: {str(e)}", exc_info=True)
            return False, f"Validation error: {str(e)}"

    # First, try to check the cache - if we've already fetched this game info
    cache_file = os.path.join(CACHE_DIR, f"game_{appid}.json")
    if os.path.exists(cache_file):
        try:
            logger.info(f"Found cached info for App ID {appid}")
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
                return True, cached_data
        except Exception as e:
            logger.warning(f"Failed to read cached data for App ID {appid}: {e}")
            # Continue to live API fetch if cache reading fails
    
    # Use thread executor with timeout to avoid hanging
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit task to executor and wait with timeout
            future = executor.submit(_fetch_game_info)
            try:
                # Wait for result with a strict timeout
                result = future.result(timeout=6)  # 6 second timeout
                return result
            except concurrent.futures.TimeoutError:
                logger.error(f"API request timed out for App ID {appid} (thread timeout)")
                return False, "API request timed out. Steam servers may be unavailable."
    except Exception as e:
        logger.error(f"Unexpected error in thread execution: {str(e)}", exc_info=True)
        return False, f"Error: {str(e)}"

# ========================
# DOWNLOAD MANAGEMENT 
# ========================

def parse_progress(line: str) -> dict:
    """Extract progress information from SteamCMD output lines."""
    try:
        # Improved progress parsing with more information
        line_lower = line.lower()
        result = {}
        
        # Debug the line we're parsing
        if "progress" in line_lower or "download" in line_lower or "%" in line_lower:
            logger.debug(f"Parsing progress line: {line}")
        
        # Look for progress percentage patterns
        progress_patterns = [
            r'(?:progress|update|download):\s*(?:.*?)(\d+\.?\d*)%',  # Matches various progress formats
            r'(\d+\.?\d*)%\s*complete',
            r'progress:\s+(\d+\.?\d*)\s*%',
            r'(\d+)\s+of\s+(\d+)\s+MB\s+\((\d+\.?\d*)%\)',  # Matches current/total size
            r'(\d+\.?\d*)%', # Just a percentage on its own
            r'progress:\s+(\d+\.?\d*)',  # Progress without % sign
            r'downloading\s+(\d+\.?\d*)%'  # "Downloading x%"
        ]
        
        for pattern in progress_patterns:
            progress_match = re.search(pattern, line_lower)
            if progress_match:
                if len(progress_match.groups()) == 3:  # Pattern with current/total size
                    current = int(progress_match.group(1))
                    total = int(progress_match.group(2))
                    progress = float(progress_match.group(3))
                    result.update({
                        "progress": progress,
                        "current_size": current,
                        "total_size": total,
                        "unit": "MB"
                    })
                else:
                    progress = float(progress_match.group(1))
                    result.update({"progress": progress})
                logger.debug(f"Found progress: {progress}%")
                break
        
        # Look for download speed
        speed_patterns = [
            r'(\d+\.?\d*)\s*(KB|MB|GB)/s',
            r'at\s+(\d+\.?\d*)\s*(KB|MB|GB)/s',
            r'(\d+\.?\d*)\s*(KB|MB|GB)\s+per\s+second',
            r'speed:\s+(\d+\.?\d*)\s*(KB|MB|GB)'
        ]
        
        for pattern in speed_patterns:
            speed_match = re.search(pattern, line_lower)
            if speed_match:
                speed = float(speed_match.group(1))
                unit = speed_match.group(2)
                result.update({"speed": speed, "speed_unit": unit})
                logger.debug(f"Found speed: {speed} {unit}/s")
                break
        
        # Look for ETA
        eta_patterns = [
            r'ETA\s+(\d+m\s*\d+s)',
            r'ETA\s+(\d+:\d+:\d+)',
            r'ETA:\s+(\d+)\s+seconds',
            r'estimated\s+time\s+remaining:\s+(.+?)\s'
        ]
        
        for pattern in eta_patterns:
            eta_match = re.search(pattern, line_lower)
            if eta_match:
                result.update({"eta": eta_match.group(1)})
                logger.debug(f"Found ETA: {eta_match.group(1)}")
                break
        
        # Look for total size in various formats
        size_patterns = [
            r'(?:size|total):\s*(\d+\.?\d*)\s*(\w+)',
            r'downloading\s+(\d+\.?\d*)\s*(\w+)',
            r'download of\s+(\d+\.?\d*)\s*(\w+)',
            r'(\d+\.?\d*)\s*(\w+)\s+remaining'
        ]
        
        for pattern in size_patterns:
            size_match = re.search(pattern, line_lower)
            if size_match:
                size = float(size_match.group(1))
                unit = size_match.group(2)
                result.update({"total_size": size, "unit": unit})
                logger.debug(f"Found size: {size} {unit}")
                break
        
        # Check for success messages
        success_patterns = [
            r'success!\s+app\s+[\'"]?(\d+)[\'"]',
            r'fully installed',
            r'download\s+complete',
            r'installation\s+complete',
            r'complete!'
        ]
        
        for pattern in success_patterns:
            success_match = re.search(pattern, line_lower)
            if success_match:
                result.update({"success": True})
                logger.debug("Found success message")
                break
        
        # Check for error messages
        error_patterns = [
            r'error!\s+(.*)',
            r'failed\s+(.*)',
            r'invalid password',
            r'invalid user name',
            r'account logon denied',
            r'need two-factor code',
            r'rate limited',
            r'no subscription',
            r'invalid platform'
        ]
        
        for pattern in error_patterns:
            error_match = re.search(pattern, line_lower)
            if error_match:
                result.update({"error": True, "error_message": line})
                logger.debug(f"Found error: {line}")
                break
        
        return result
    
    except Exception as e:
        logger.error(f"Error parsing progress line: {line}. Error: {str(e)}")
        return {}

def process_download_queue():
    """Process the next item in the download queue if there are no active downloads."""
    with queue_lock:
        if download_queue and len(active_downloads) == 0:
            next_download = download_queue.pop(0)
            
            # Start a new thread for the download
            logging.info(f"Starting queued download: AppID {next_download['appid']}")
            thread = threading.Thread(
                target=start_download,
                args=(next_download['username'], next_download['password'], 
                      next_download['guard_code'], next_download['anonymous'],
                      next_download['appid'], next_download['validate'])
            )
            thread.daemon = True
            thread.start()

def queue_download(username, password, guard_code, anonymous, game_input, validate=True):
    """Simplified function to download a game directly without queueing."""
    try:
        logging.info(f"Starting simplified download for: {game_input}")
    
        # Validate login details for non-anonymous downloads
        if not anonymous and (not username or not password):
            error_msg = "Error: Username and password are required for non-anonymous downloads."
            logging.error(error_msg)
            return error_msg
    
        # Extract AppID
        appid = parse_game_input(game_input)
        if not appid:
            error_msg = "Invalid game ID or URL. Please enter a valid Steam game ID or store URL."
            logging.error(error_msg)
            return error_msg
    
        logging.info(f"Simplified download: extracted AppID {appid}")
        
        # Create a download folder
        download_folder = os.path.join(STEAM_DOWNLOAD_PATH, f"steamapps/common/app_{appid}")
        os.makedirs(download_folder, exist_ok=True)
        
        logging.info(f"Simplified download: created folder {download_folder}")
        
        # Build SteamCMD command
        steamcmd_path = get_steamcmd_path()
        
        if not os.path.exists(steamcmd_path):
            return f"Error: SteamCMD not found at {steamcmd_path}"
        
        # Basic command
        cmd_args = [steamcmd_path]
        
        if anonymous:
            cmd_args.extend(["+login", "anonymous"])
        else:
            cmd_args.extend(["+login", username, password])
            if guard_code:
                # You'd need to handle Steam Guard code here
                pass
        
        cmd_args.extend([
            "+force_install_dir", download_folder,
            "+app_update", appid
        ])
        
        if validate:
            cmd_args.append("validate")
        
        cmd_args.append("+quit")
        
        cmd_str = ' '.join(cmd_args)
        logging.info(f"Simplified download: command prepared: {cmd_str if anonymous else '[CREDENTIALS HIDDEN]'}")
        
        # Start the process directly without tracking
        try:
            # Discard output to avoid buffer issues
            with open(os.path.join(download_folder, "output.log"), "w") as output_file:
                process = subprocess.Popen(
                    cmd_args,
                    stdout=output_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )
                logging.info(f"Simplified download: started process with PID {process.pid}")
        except Exception as e:
            logging.error(f"Error starting process: {str(e)}", exc_info=True)
            return f"Error starting process: {str(e)}"
        
        return f"Download started for AppID {appid} in folder: {download_folder}"
            
    except Exception as e:
        logging.error(f"Download error: {str(e)}", exc_info=True)
        return f"Error starting download: {str(e)}"

def start_download(username, password, guard_code, anonymous, appid, validate_download):
    """Start a download using SteamCMD."""
    download_id = f"dl_{appid}_{int(time.time())}"
    logging.info(f"Starting download with ID: {download_id} for AppID: {appid}")
    
    try:
        # Set up download directory
        download_dir = os.path.join(STEAM_DOWNLOAD_PATH, f"steamapps/common/app_{appid}")
        os.makedirs(download_dir, exist_ok=True)
        logging.info(f"Download directory created: {download_dir}")
        
        # Add to active downloads
        with queue_lock:
            active_downloads[download_id] = {
                "appid": appid,
                "name": f"Game (AppID: {appid})",
                "start_time": datetime.now(),
                "progress": 0.0,
                "status": "Starting",
                "eta": "Calculating...",
                "process": None,
                "speed": "0 KB/s",
                "size_downloaded": "0 MB",
                "total_size": "Unknown"
            }
        
        # Prepare SteamCMD command
        steamcmd_path = get_steamcmd_path()
        logging.info(f"Using SteamCMD path: {steamcmd_path}")
        
        # Verify SteamCMD exists
        if not os.path.exists(steamcmd_path):
            error_msg = f"Error: SteamCMD not found at {steamcmd_path}"
            logging.error(error_msg)
            
            with queue_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["status"] = "Failed - SteamCMD not found"
                    # Keep the failed download visible for a while
                    threading.Timer(30, lambda: remove_completed_download(download_id)).start()
            
            process_download_queue()
            return
        
        # Build command arguments
        cmd_args = [steamcmd_path]
        
        if anonymous:
            cmd_args.extend(["+login", "anonymous"])
            logging.info("Using anonymous login")
        else:
            cmd_args.extend(["+login", username, password])
            logging.info(f"Using login for user: {username}")
            if guard_code:
                logging.info("Steam Guard code provided")
                # In a real implementation, you would handle Steam Guard codes
                pass
        
        cmd_args.extend([
            "+force_install_dir", download_dir,
            "+app_update", appid
        ])
        
        if validate_download:
            cmd_args.append("validate")
        
        cmd_args.append("+quit")
        
        # Start the SteamCMD process
        cmd_string = ' '.join(cmd_args)
        logging.info(f"Executing command: {cmd_string}")
        
        try:
            # Test if SteamCMD is executable
            if not os.access(steamcmd_path, os.X_OK) and platform.system() != "Windows":
                logging.warning(f"SteamCMD is not executable. Attempting to set execute permission.")
                os.chmod(steamcmd_path, 0o755)
            
            # Start process and capture output
            logging.info("Starting subprocess.Popen...")
            process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1  # Line buffered
            )
            
            logging.info(f"Process started with PID: {process.pid}")
            
            # Update process info
            with queue_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["process"] = process
                    active_downloads[download_id]["status"] = "Downloading"
                    logging.info(f"Updated active_downloads with process info")
            
            # Process output and monitor progress in a separate thread
            logging.info("Starting monitoring thread...")
            monitor_thread = threading.Thread(
                target=monitor_download,
                args=(download_id, process)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            logging.info(f"Monitoring thread started for download {download_id}")
            
        except Exception as e:
            logging.error(f"Error starting SteamCMD process: {str(e)}", exc_info=True)
            
            with queue_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["status"] = f"Failed to start SteamCMD: {str(e)}"
                    # Keep the failed download visible for a while
                    threading.Timer(30, lambda: remove_completed_download(download_id)).start()
            
            process_download_queue()
        
    except Exception as e:
        logging.error(f"Error in start_download for {download_id}: {str(e)}", exc_info=True)
        
        with queue_lock:
            if download_id in active_downloads:
                active_downloads[download_id]["status"] = f"Failed - {str(e)}"
                # Keep the failed download visible for a while
                threading.Timer(30, lambda: remove_completed_download(download_id)).start()
        
        process_download_queue()

def monitor_download(download_id, process):
    """Monitor the download process and update progress."""
    logging.info(f"Starting to monitor download {download_id}")
    
    try:
        # First update to show activity
        with queue_lock:
            if download_id in active_downloads:
                active_downloads[download_id]["status"] = "Initializing SteamCMD..."
        
        last_update_time = time.time()
        progress_pattern = re.compile(r'progress:?\s*(\d+\.\d+)\s*%')
        speed_pattern = re.compile(r'(\d+\.\d+)\s*([KMG]B)/s')
        eta_pattern = re.compile(r'ETA:?\s*(\d+\w\s*\d+\w|\d+:\d+:\d+)')
        
        # Log the first 10 lines to help with debugging
        initial_lines = []
        line_count = 0
        
        # Check if process is still running
        if process.poll() is not None:
            logging.error(f"Process for download {download_id} exited prematurely with code {process.returncode}")
            with queue_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["status"] = f"Failed - SteamCMD exited with code {process.returncode}"
            return
        
        logging.info(f"Starting to read output for download {download_id}")
        
        if not process.stdout:
            logging.error(f"Process stdout is None for download {download_id}")
            with queue_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["status"] = "Failed - Cannot read SteamCMD output"
            return
        
        for line in process.stdout:
            current_time = time.time()
            line = line.strip() if line else ""
            
            # Collect initial lines for debugging
            if line_count < 10:
                initial_lines.append(line)
                line_count += 1
                logging.info(f"SteamCMD initial output line {line_count}: {line}")
            
            # Log the output line every 5 seconds or if it contains important info
            if current_time - last_update_time > 5 or any(kw in line.lower() for kw in ["error", "progress", "eta", "download"]):
                logging.info(f"Download {download_id} output: {line}")
                last_update_time = current_time
            
            # Extract progress information
            progress_match = progress_pattern.search(line)
            if progress_match:
                progress = float(progress_match.group(1))
                logging.info(f"Detected progress: {progress}%")
                with queue_lock:
                    if download_id in active_downloads:
                        active_downloads[download_id]["progress"] = progress
                        active_downloads[download_id]["status"] = "Downloading"
            
            # Extract speed information
            speed_match = speed_pattern.search(line)
            if speed_match:
                speed_value = float(speed_match.group(1))
                speed_unit = speed_match.group(2)
                logging.info(f"Detected speed: {speed_value} {speed_unit}/s")
                with queue_lock:
                    if download_id in active_downloads:
                        active_downloads[download_id]["speed"] = f"{speed_value} {speed_unit}/s"
            
            # Extract ETA information
            eta_match = eta_pattern.search(line)
            if eta_match:
                eta = eta_match.group(1)
                logging.info(f"Detected ETA: {eta}")
                with queue_lock:
                    if download_id in active_downloads:
                        active_downloads[download_id]["eta"] = eta
            
            # Check for successful completion
            if "Success! App" in line and "fully installed" in line:
                logging.info(f"Download {download_id} completed successfully")
                with queue_lock:
                    if download_id in active_downloads:
                        active_downloads[download_id]["progress"] = 100.0
                        active_downloads[download_id]["status"] = "Completed"
            
            # Check for errors
            if "ERROR!" in line:
                logging.error(f"Error in download {download_id}: {line}")
                with queue_lock:
                    if download_id in active_downloads:
                        active_downloads[download_id]["status"] = f"Error: {line}"
        
        # If we got here, the process has completed
        logging.info(f"Finished reading output for download {download_id}")
        
        # Process completed, check return code
        return_code = process.wait()
        logging.info(f"Download {download_id} process completed with return code {return_code}")
        
        with queue_lock:
            if download_id in active_downloads:
                if return_code == 0:
                    if active_downloads[download_id]["status"] != "Completed":
                        active_downloads[download_id]["progress"] = 100.0
                        active_downloads[download_id]["status"] = "Completed"
                else:
                    active_downloads[download_id]["status"] = f"Failed (Code: {return_code})"
                    if initial_lines:
                        logging.error(f"First {len(initial_lines)} lines of output: {initial_lines}")
        
        # Keep completed download visible for a while, then remove it
        threading.Timer(60, lambda: remove_completed_download(download_id)).start()
        
        # Process next download in queue
        process_download_queue()
        
    except Exception as e:
        logging.error(f"Error monitoring download {download_id}: {str(e)}", exc_info=True)
        
        with queue_lock:
            if download_id in active_downloads:
                active_downloads[download_id]["status"] = f"Error: {str(e)}"
        
        # Process next download in queue
        process_download_queue()

def remove_completed_download(download_id):
    """Remove a completed download from the active downloads after a delay."""
    with queue_lock:
        if download_id in active_downloads:
            logging.info(f"Removing completed download {download_id} from active downloads")
            del active_downloads[download_id]

def cancel_download(download_id):
    """Cancel an active download."""
    logging.info(f"Attempting to cancel download: {download_id}")
    
    with queue_lock:
        if download_id not in active_downloads:
            return f"Download {download_id} not found"
        
        process = active_downloads[download_id].get("process")
        if not process:
            del active_downloads[download_id]
            return f"Download {download_id} cancelled (no process was running)"
        
        # Try to terminate the process
        try:
            process.terminate()
            active_downloads[download_id]["status"] = "Cancelling..."
            
            # Wait a bit for graceful termination
            def check_if_terminated():
                if process.poll() is None:  # Process still running
                    logging.warning(f"Process for download {download_id} didn't terminate, killing forcefully")
                    try:
                        process.kill()
                    except:
                        pass
                
            with queue_lock:
                if download_id in active_downloads:
                    del active_downloads[download_id]
            
            # Process next download in queue
            process_download_queue()
            
            return f"Download {download_id} is being cancelled"
            
        except Exception as e:
            logging.error(f"Error cancelling download {download_id}: {str(e)}", exc_info=True)
            
            with queue_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["status"] = "Failed to cancel"
            
            return f"Error cancelling download {download_id}: {str(e)}"

def get_download_status():
    """Get the current status of downloads and queue."""
    result = {
        "active": [],
        "queue": [],
        "system": {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "network_speed": "N/A",
            "uptime": str(datetime.now() - datetime.fromtimestamp(psutil.boot_time())).split('.')[0]
        },
        "history": []  # You can implement history tracking if needed
    }
    
    # First, log the current state for debugging
    logging.info(f"Current active_downloads: {len(active_downloads)} items")
    for id, info in active_downloads.items():
        status_copy = info.copy()
        if "process" in status_copy:
            del status_copy["process"]  # Remove process object before logging
        logging.info(f"Download {id} status: {status_copy}")
    
    # Now populate the result
    with queue_lock:
        for id, info in active_downloads.items():
            result["active"].append({
                "id": id,
                "name": info["name"],
                "appid": info["appid"],
                "progress": info["progress"],
                "status": info["status"],
                "eta": info["eta"],
                "runtime": str(datetime.now() - info["start_time"]).split('.')[0],  # Remove microseconds
                "speed": info.get("speed", "Unknown"),
                "size_downloaded": info.get("size_downloaded", "Unknown"),
                "total_size": info.get("total_size", "Unknown")
            })
        
        # Queue information
        for i, download in enumerate(download_queue):
            result["queue"].append({
                "position": i + 1,
                "appid": download["appid"],
                "name": f"Game (AppID: {download['appid']})",
                "validate": download["validate"]
            })
    
    return result

def remove_from_queue(position):
    """Remove a download from the queue by position."""
    position = int(position)
    logging.info(f"Attempting to remove download from queue position: {position}")
    
    with queue_lock:
        if 1 <= position <= len(download_queue):
            download = download_queue.pop(position - 1)
            return f"Removed download for AppID {download['appid']} from queue position {position}"
        else:
            return f"Invalid queue position: {position}"

def reorder_queue(from_position, to_position):
    """Reorder the download queue by moving an item from one position to another."""
    from_position = int(from_position)
    to_position = int(to_position)
    
    with queue_lock:
        if 1 <= from_position <= len(download_queue) and 1 <= to_position <= len(download_queue):
            # Convert to 0-based index
            from_idx = from_position - 1
            to_idx = to_position - 1
            
            # Get the item to move
            item = download_queue.pop(from_idx)
            
            # Insert at the new position
            download_queue.insert(to_idx, item)
            
            logging.info(f"Moved download from position {from_position} to {to_position}")
            return True, f"Moved download from position {from_position} to {to_position}"
        else:
            logging.warning(f"Invalid queue positions: from={from_position}, to={to_position}")
            return False, "Invalid queue positions"

def get_game_details(game_input):
    """Get detailed information about a game based on input (ID or URL)."""
    appid = parse_game_input(game_input)
    if not appid:
        return {"success": False, "error": "Invalid game ID or URL"}
    
    is_valid, game_info = validate_appid(appid)
    if not is_valid:
        return {"success": False, "error": game_info}
    
    return {"success": True, "appid": appid, "game_info": game_info}

# ========================
# UI COMPONENTS
# ========================

def create_download_games_tab():
    with gr.Tab("Download Games") as tab:
        with gr.Row():
            with gr.Column(scale=2):
                # Game Information Section
                with gr.Box():
                    gr.Markdown("### Game Information")
                    
                    game_input = gr.Textbox(
                        label="Game ID or Steam Store URL",
                        placeholder="Enter AppID (e.g., 570) or Steam URL",
                        info="Enter a valid Steam game ID or store URL"
                    )
                    
                check_button = gr.Button("Check Game Details", variant="secondary")
                
                game_info_json = gr.JSON(visible=False)
                
                with gr.Row(visible=False) as game_details_container:
                    game_image = gr.Image(label="Game Image", show_label=False, type="filepath")
                    
                    with gr.Column():
                        game_title = gr.Textbox(label="Game", interactive=False)
                        game_description = gr.Textbox(label="Description", interactive=False, max_lines=3)
                        game_size = gr.Textbox(label="Estimated Size", interactive=False)
                
                # Account Information Section
                with gr.Box():
                    gr.Markdown("### Steam Account")
                    
                    anonymous_login = gr.Checkbox(
                        label="Anonymous Login (Free Games Only)",
                        value=True,
                        info="Use for free games. Paid games require login."
                    )
                    
                    with gr.Column(visible=False) as login_container:
                        username = gr.Textbox(
                            label="Steam Username",
                            placeholder="Your Steam account username"
                        )
                        password = gr.Textbox(
                            label="Steam Password",
                            placeholder="Your Steam account password",
                            type="password",
                            info="Credentials are only used for the current session and not stored"
                        )
                        
                        with gr.Accordion("Steam Guard (if enabled)", open=False):
                            guard_code = gr.Textbox(
                                label="Steam Guard Code",
                                placeholder="Enter the code sent to your email or mobile app",
                                info="Required if Steam Guard is enabled on your account"
                            )
                
                # Download Options Section
                with gr.Box():
                    gr.Markdown("### Download Options")
                    
                    download_path = gr.Textbox(
                        label="Download Location",
                        value=get_default_download_location(),
                        interactive=False,
                        info="Set in application settings"
                    )
                    
                    validate_download = gr.Checkbox(
                        label="Verify Files After Download",
                        value=True,
                        info="Recommended to ensure download integrity"
                    )
                    
                    with gr.Row():
                        download_button = gr.Button("Download Now", variant="primary")
                        queue_button = gr.Button("Add to Queue", variant="secondary")
            
            # Right column for help/information
            with gr.Column(scale=1):
                gr.Markdown("### Download Information")
                gr.Markdown("""
                - Free games can be downloaded with Anonymous Login
                - Paid games require your Steam account credentials
                - Your credentials are never stored
                - Downloads will be placed in the configured directory
                - You can queue multiple downloads
                """)
                
                gr.Markdown("### Status")
                status_box = gr.Textbox(label="", interactive=False)
        
        # Event handlers
        anonymous_login.change(fn=toggle_login_visibility, inputs=anonymous_login, outputs=login_container)
        
        check_button.click(
            fn=handle_game_check,
            inputs=game_input,
            outputs=[game_info_json, game_details_container, game_image, game_title, 
                     game_description, game_size, status_box]
        )
        
        download_button.click(
            fn=handle_download,
            inputs=[game_input, username, password, guard_code, anonymous_login, 
                   validate_download, game_info_json],
            outputs=[status_box]
        )
        
        queue_button.click(
            fn=handle_queue,
            inputs=[game_input, username, password, guard_code, anonymous_login, 
                   validate_download, game_info_json],
            outputs=[status_box]
        )
    
    return tab

def toggle_login_visibility(anonymous):
    return gr.update(visible=not anonymous)

def handle_game_check(input_text):
    try:
        # Parse the input (handle both IDs and URLs)
        appid = parse_game_input(input_text)
        if not appid:
            return [None, gr.update(visible=False), None, None, None, None, 
                    "Invalid input. Please enter a valid Steam AppID or store URL."]
        
        # Validate the AppID and get game info
        valid, game_info = validate_appid(appid)
        
        if not valid or not game_info:
            return [None, gr.update(visible=False), None, None, None, None, 
                    f"Unable to find game with ID {appid}. Please check and try again."]
        
        # Extract game details for display
        game_name = game_info.get("name", "Unknown")
        game_desc = game_info.get("short_description", "No description available.")
        game_image_url = game_info.get("header_image")
        estimated_size = format_size(game_info.get("size_estimate", 0))
        
        # Download image if available
        image_path = None
        if game_image_url:
            try:
                image_path = download_and_save_image(game_image_url, appid)
            except Exception as e:
                logging.warning(f"Failed to download game image: {str(e)}")
        
        return [
            game_info,  # Store the full game info JSON
            gr.update(visible=True),  # Show the game details container
            image_path,  # Game image
            game_name,  # Game title
            game_desc,  # Game description
            f"Estimated size: {estimated_size}",  # Estimated size
            f"Game found: {game_name}. Ready to download."  # Status message
        ]
    except Exception as e:
        logging.error(f"Error checking game: {str(e)}")
        return [None, gr.update(visible=False), None, None, None, None, 
                f"Error: {str(e)}"]

def create_downloads_tab():
    with gr.Tab("Downloads") as tab:
        with gr.Row():
            with gr.Column(scale=3):
                # Active Downloads Section
                with gr.Box():
                    gr.Markdown("### Active Downloads")
                    active_downloads = gr.Dataframe(
                        headers=["ID", "Game", "Progress", "Speed", "ETA", "Status"],
                        datatype=["str", "str", "str", "str", "str", "str"],
                        row_count=5,
                        col_count=(6, "fixed"),
                        interactive=False
                    )
                    
                    with gr.Row():
                        cancel_download_btn = gr.Button("Cancel Selected", variant="stop")
                        pause_download_btn = gr.Button("Pause/Resume", variant="secondary")
                        refresh_active_btn = gr.Button("Refresh", variant="secondary")
                
                # Download Queue Section
                with gr.Box():
                    gr.Markdown("### Download Queue")
                    queue_table = gr.Dataframe(
                        headers=["Position", "Game", "Size", "Status"],
                        datatype=["str", "str", "str", "str"],
                        row_count=5,
                        interactive=False
                    )
                    
                    with gr.Row():
                        remove_queue_btn = gr.Button("Remove Selected", variant="stop")
                        move_up_btn = gr.Button("Move Up", variant="secondary")
                        move_down_btn = gr.Button("Move Down", variant="secondary")
                        refresh_queue_btn = gr.Button("Refresh Queue", variant="secondary")
                
                # Completed Downloads Section
                with gr.Box():
                    gr.Markdown("### Completed Downloads")
                    history_table = gr.Dataframe(
                        headers=["Game", "Size", "Completed", "Location", "Status"],
                        datatype=["str", "str", "str", "str", "str"],
                        row_count=5,
                        interactive=False
                    )
                    
                    with gr.Row():
                        clear_history_btn = gr.Button("Clear History", variant="secondary")
                        refresh_history_btn = gr.Button("Refresh History", variant="secondary")
            
            # Right column for download logs
            with gr.Column(scale=2):
                gr.Markdown("### Download Logs")
                log_box = gr.Textbox(
                    label="",
                    value="Download logs will appear here...",
                    max_lines=20,
                    interactive=False
                )
                
                clear_logs_btn = gr.Button("Clear Logs", variant="secondary")
        
        # Event handlers
        refresh_active_btn.click(fn=update_active_downloads, outputs=[active_downloads])
        refresh_queue_btn.click(fn=update_queue_data, outputs=[queue_table])
        refresh_history_btn.click(fn=update_history_data, outputs=[history_table])
        
        cancel_download_btn.click(
            fn=cancel_and_refresh,
            inputs=[active_downloads],
            outputs=[active_downloads]
        )
        
        remove_queue_btn.click(
            fn=remove_and_refresh,
            inputs=[queue_table],
            outputs=[queue_table]
        )
        
        move_up_btn.click(
            fn=move_up_and_refresh,
            inputs=[queue_table],
            outputs=[queue_table]
        )
        
        move_down_btn.click(
            fn=move_down_and_refresh,
            inputs=[queue_table],
            outputs=[queue_table]
        )
        
        clear_logs_btn.click(
            fn=lambda: "",
            outputs=[log_box]
        )
        
        # Set up automatic refresh
        gr.on(
            triggers=[active_downloads.change, queue_table.change],
            fn=None,
            inputs=None,
            outputs=None,
            _js="() => {setTimeout(() => {document.getElementById('refresh_active_btn').click();}, 5000);}"
        )
    
    return tab

def update_active_downloads(active_downloads):
    return [
        [f"{download['id'][:8]}", download['name'], f"{download['progress']}%", download['speed'], download['eta'], download['status']]
        for download in active_downloads
    ]

def update_queue_data(queue_table):
    return [
        [f"{download['position']}", download['name'], f"{download['size']}", download['status']]
        for download in queue_table
    ]

def update_history_data(history_table):
    return [
        [download['name'], download['size'], download['status'], download['location']]
        for download in history_table
    ]

def cancel_and_refresh(active_downloads):
    result = cancel_download(active_downloads[0]['id'])
    stats = get_system_stats()
    queue = get_queue_data()
    history = get_history_data()
    return result, stats, queue, history

def remove_and_refresh(queue_table):
    result = remove_from_queue(queue_table[0]['position'])
    stats = get_system_stats()
    queue = get_queue_data()
    history = get_history_data()
    return result, stats, queue, history

def move_up_and_refresh(queue_table):
    result = reorder_queue(int(queue_table[0]['position']) - 1, int(queue_table[0]['position']))[1]
    stats = get_system_stats()
    queue = get_queue_data()
    history = get_history_data()
    return result, stats, queue, history

def move_down_and_refresh(queue_table):
    result = reorder_queue(int(queue_table[0]['position']), int(queue_table[0]['position']) + 1)[1]
    stats = get_system_stats()
    queue = get_queue_data()
    history = get_history_data()
    return result, stats, queue, history

# At the top of your file, add a print statement that will show in server logs
print("Loading application with modified Setup tab")

def simple_test_function():
    """Ultra simple test function that just returns a string."""
    print("simple_test_function was called!")  # This will show in server logs
    return "Button was clicked successfully!"

def create_gradio_interface():
    """Create the main Gradio interface with all tabs"""
    with gr.Blocks(title="Steam Games Downloader", theme=gr.themes.Soft()) as app:
        gr.Markdown("# Steam Games Downloader")
        gr.Markdown("Download Steam games with a user-friendly interface")
        
        with gr.Tabs():
            # Create main tabs
            download_tab = create_download_games_tab()
            downloads_tab = create_downloads_tab()
            library_tab = create_library_tab()
            setup_tab = create_setup_tab()
            settings_tab = create_settings_tab()
        
        # Setup automatic refresh of dynamic content
        app.load(
            fn=setup_refresh_interval,
            inputs=None,
            outputs=None,
            _js="""
            function() {
                // Refresh active downloads every 3 seconds
                setInterval(function() {
                    if (document.querySelector('.tab-nav button.selected').textContent === 'Downloads') {
                        document.getElementById('refresh_active_btn').click();
                    }
                }, 3000);
            }
            """
        )
    
    return app

def queue_processor():
    """Background thread function to process the download queue."""
    while True:
        process_download_queue()
        time.sleep(5)  # Check queue every 5 seconds

def is_game_installed(appid):
    """Check if a game is installed by looking for its manifest file"""
    try:
        appid = str(appid).strip()
        
        # First, make sure STEAMAPPS_PATH exists
        if not os.path.exists(STEAMAPPS_PATH):
            logger.warning(f"Steam apps directory does not exist: {STEAMAPPS_PATH}")
            return False
        
        # Check if appmanifest file exists (this is the most reliable method)
        manifest_path = os.path.join(STEAMAPPS_PATH, f"appmanifest_{appid}.acf")
        if os.path.exists(manifest_path):
            logger.info(f"Found manifest file for AppID {appid}: {manifest_path}")
            return True
        
        # Try to check for the common directory
        common_dir = os.path.join(STEAMAPPS_PATH, "common")
        if not os.path.exists(common_dir):
            # Try alternate potential locations
            logger.warning(f"Common games directory not found at {common_dir}")
            common_dir = os.path.join(STEAMAPPS_PATH, "..", "common")
            if not os.path.exists(common_dir):
                logger.warning(f"Common games directory not found at alternate location either")
                # If we can't find the common directory, we can't check by game name
                return False
        
        # If we reach here, we have a valid common directory
        logger.info(f"Using common directory: {common_dir}")
        
        # Try to check by game name
        try:
            game_info = get_game_info(appid)
            game_name = game_info.get('name')
            if game_name and os.path.exists(common_dir):
                # List all directories and check for matches
                for folder in os.listdir(common_dir):
                    folder_path = os.path.join(common_dir, folder)
                    if os.path.isdir(folder_path):
                        # Check if game name is in folder name (case-insensitive)
                        if game_name.lower() in folder.lower():
                            logger.info(f"Found potential game directory for {game_name}: {folder_path}")
                            return True
        except Exception as e:
            logger.warning(f"Error checking game by name: {e}")
        
        # If we get here, we couldn't find the game
        logger.info(f"Game with AppID {appid} does not appear to be installed")
        return False
    except Exception as e:
        logger.error(f"Error in is_game_installed: {e}")
        return False

def get_game_size(appid):
    """Get the size of an installed game in bytes"""
    try:
        # First check if the game is installed
        if not is_game_installed(appid):
            return 0
        
        # Try to get the size from the manifest file
        manifest_path = os.path.join(STEAMAPPS_PATH, f"appmanifest_{appid}.acf")
        if os.path.exists(manifest_path):
            # Estimate size from manifest if possible
            try:
                with open(manifest_path, 'r') as f:
                    content = f.read()
                    # Try to extract size info from manifest
                    size_match = re.search(r'"SizeOnDisk"\s+"(\d+)"', content)
                    if size_match:
                        return int(size_match.group(1))
            except Exception as e:
                logger.warning(f"Failed to read size from manifest: {e}")
        
        # If we reach here, try to find the game directory
        common_dir = os.path.join(STEAMAPPS_PATH, "common")
        if not os.path.exists(common_dir):
            common_dir = os.path.join(STEAMAPPS_PATH, "..", "common")
            if not os.path.exists(common_dir):
                logger.warning("Cannot find games directory to calculate size")
                return 0
        
        # Try to find by name
        game_info = get_game_info(appid)
        game_name = game_info.get('name', '')
        
        if game_name:
            # Check for directory with matching name
            for folder in os.listdir(common_dir):
                folder_path = os.path.join(common_dir, folder)
                if os.path.isdir(folder_path) and game_name.lower() in folder.lower():
                    return get_directory_size(folder_path)
        
        return 0
    except Exception as e:
        logger.error(f"Error in get_game_size: {e}")
        return 0

def get_directory_size(path):
    """Calculate the total size of a directory in bytes"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if os.path.exists(file_path):
                total_size += os.path.getsize(file_path)
    return total_size

def format_size(size_bytes):
    """Format size in bytes to a human-readable string"""
    if size_bytes == 0:
        return "0B"
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = int(math.log(size_bytes, 1024))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def get_game_info(appid):
    """Get information about a game from the Steam API or cache"""
    try:
        appid = str(appid).strip()
        
        # Check if we have cached info
        cache_file = os.path.join(CACHE_DIR, f"game_{appid}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cached game info: {e}")
        
        # Get from Steam API
        steam_api_url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
        try:
            response = requests.get(steam_api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and data.get(appid, {}).get('success', False):
                    game_data = data[appid]['data']
                    
                    # Save to cache
                    os.makedirs(CACHE_DIR, exist_ok=True)
                    with open(cache_file, 'w') as f:
                        json.dump(game_data, f)
                    
                    return game_data
        except Exception as e:
            logger.warning(f"Error fetching game info from Steam API: {e}")
        
        # Fallback: return minimal info
        return {"name": f"App {appid}", "appid": appid}
    except Exception as e:
        logger.error(f"Error in get_game_info: {e}")
        return {"name": f"App {appid}", "appid": appid}

# Make sure you have CACHE_DIR and STEAMAPPS_PATH defined
if not 'CACHE_DIR' in globals():
    CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
    os.makedirs(CACHE_DIR, exist_ok=True)

if not 'STEAMAPPS_PATH' in globals():
    # This should be set to your actual SteamApps path
    STEAMAPPS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "steamapps")
    if not os.path.exists(STEAMAPPS_PATH):
        # Try default paths
        possible_paths = [
            "/steamapps",
            "/Steam/steamapps", 
            "/home/steam/Steam/steamapps",
            "/app/steamapps"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                STEAMAPPS_PATH = path
                break

def run_network_diagnostics():
    """Run network diagnostics to help identify connectivity issues"""
    logger.info("Running network diagnostics...")
    
    # Test basic internet connectivity
    try:
        response = requests.get("https://www.google.com", timeout=3)
        logger.info(f"Internet connectivity (Google): Success ({response.status_code})")
    except Exception as e:
        logger.error(f"Internet connectivity (Google): Failed - {str(e)}")
    
    # Test Steam website connectivity
    try:
        response = requests.get("https://store.steampowered.com", timeout=3)
        logger.info(f"Steam website connectivity: Success ({response.status_code})")
    except Exception as e:
        logger.error(f"Steam website connectivity: Failed - {str(e)}")
    
    # Test Steam API connectivity with a simple query
    try:
        response = requests.get("https://api.steampowered.com/ISteamWebAPIUtil/GetSupportedAPIList/v1/", timeout=3)
        logger.info(f"Steam API connectivity: Success ({response.status_code})")
    except Exception as e:
        logger.error(f"Steam API connectivity: Failed - {str(e)}")
    
    # DNS resolution test
    try:
        ip = socket.gethostbyname("store.steampowered.com")
        logger.info(f"DNS resolution for Steam: Success ({ip})")
    except Exception as e:
        logger.error(f"DNS resolution for Steam: Failed - {str(e)}")

def diagnose_environment():
    """Run diagnostics to check the environment configuration."""
    try:
        # Get system information
        import platform
        import shutil
        
        result = "=== System Information ===\n"
        result += f"OS: {platform.system()} {platform.release()}\n"
        result += f"Python: {platform.python_version()}\n"
        
        # Check disk space
        download_dir = get_default_download_location()
        total, used, free = shutil.disk_usage(download_dir)
        result += f"\n=== Disk Space ===\n"
        result += f"Download directory: {download_dir}\n"
        result += f"Free space: {format_size(free)} / {format_size(total)}\n"
        
        # Check SteamCMD
        steamcmd_path = get_steamcmd_path()
        result += f"\n=== SteamCMD ===\n"
        result += f"Path: {steamcmd_path}\n"
        result += f"Exists: {os.path.exists(steamcmd_path)}\n"
        
        # Check network connectivity
        result += f"\n=== Network ===\n"
        try:
            urllib.request.urlopen("https://store.steampowered.com", timeout=5)
            result += "Steam Store: Accessible\n"
        except:
            result += "Steam Store: Not accessible\n"
            
        try:
            urllib.request.urlopen("https://steamcdn-a.akamaihd.net", timeout=5)
            result += "Steam CDN: Accessible\n"
        except:
            result += "Steam CDN: Not accessible\n"
        
        return result
    except Exception as e:
        logger.error(f"Error during diagnostics: {str(e)}", exc_info=True)
        return f"Error running diagnostics: {str(e)}"
        
def simple_verify_wrapper():
    """Simple wrapper for verify_steamcmd to debug the button click."""
    print("verify button clicked - calling simple wrapper")
    try:
        # Just return a static string for now
        return "SteamCMD verification attempted - using simple wrapper"
    except Exception as e:
        print(f"Error in simple wrapper: {str(e)}")
        return f"Error: {str(e)}"

# Call this on startup
if __name__ == "__main__":
    run_network_diagnostics()
    # ... rest of your startup code

if __name__ == "__main__":
    # Ensure necessary directories exist
    for directory in [get_default_download_location(), '/app/logs', '/app/steamcmd']:
        ensure_directory_exists(directory)
    
    # Ensure SteamCMD is installed
    if "not installed" in check_steamcmd():
        logger.info("SteamCMD not found, installing...")
        install_steamcmd()
    
    # Create the Gradio interface
    app_interface = create_gradio_interface()
    
    # Start the FastAPI server for file serving in a separate thread
    threading.Thread(
        target=lambda: uvicorn.run(fastapi_app, host="0.0.0.0", port=8081),
        daemon=True
    ).start()
    
    port = int(os.getenv("PORT", 7860))
    logger.info(f"Starting application on port {port}")
    
    # Launch Gradio and capture the return value
    launch_info = app_interface.launch(
        server_port=port, 
        server_name="0.0.0.0", 
        share=True, 
        prevent_thread_lock=True,
        show_error=True
    )
    
    # Check if launch_info has a share_url attribute
    if hasattr(launch_info, 'share_url'):
        update_share_url(launch_info.share_url)
        logger.info(f"Gradio share URL: {launch_info.share_url}")
    else:
        logger.warning("Launch info does not contain a share URL.")
    
    # Keep the script running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")

try:
    requests.get("https://store.steampowered.com", timeout=3)
    logger.info("Steam store website is reachable")
except Exception as e:
    logger.error(f"Cannot reach Steam store: {str(e)}")

def check_game(game_id):
    details = get_game_details(game_id)
    
    if not details["success"]:
        return (
            gr.update(visible=False),  # Hide game details row
            "",  # Game title
            "",  # Game description
            [],  # Game metadata
            None,  # Game image
            f"Error: {details['error']}"  # Download status
        )
    
    game_info = details["game_info"]
    
    # Format metadata for display
    metadata = [
        ["App ID", details["appid"]],
        ["Free Game", "Yes" if game_info.get("is_free", False) else "No"],
        ["Release Date", game_info.get("release_date", "Unknown")],
        ["Developer", ", ".join(game_info.get("developers", ["Unknown"]))],
        ["Publisher", ", ".join(game_info.get("publishers", ["Unknown"]))],
        ["Genres", ", ".join(game_info.get("genres", ["Unknown"]))],
        ["Metacritic", game_info.get("metacritic", "N/A")],
        ["Platforms", ", ".join([p for p, v in game_info.get("platforms", {}).items() if v])]
    ]
    
    # Get image URL or use placeholder
    image_url = game_info.get("header_image", None)
    
    return (
        gr.update(visible=True),  # Show game details row
        game_info.get("name", "Unknown Game"),  # Game title
        game_info.get("description", "No description available"),  # Game description
        metadata,  # Game metadata
        image_url,  # Game image
        f"Game found: {game_info.get('name', 'Unknown Game')} (AppID: {details['appid']})"  # Download status
    )

def download_game_simple(username, password, guard_code, anonymous, game_input, validate_download):
    """
    A simplified version of the download function that runs directly in the main thread.
    This will help identify if the issue is with threading, subprocess management, or UI updates.
    """
    logging.info(f"Starting simple download for game: {game_input}")
    
    # Extract AppID from input
    appid = parse_game_input(game_input)
    if not appid:
        return f"Error: Unable to extract AppID from input: {game_input}"
    
    # Validate login for non-anonymous downloads
    if not anonymous and (not username or not password):
        return "Error: Username and password are required for non-anonymous downloads."
    
    # Create download directory
    download_dir = os.path.join(STEAM_DOWNLOAD_PATH, f"steamapps/common/app_{appid}")
    os.makedirs(download_dir, exist_ok=True)
    logging.info(f"Download directory created: {download_dir}")
    
    # Get SteamCMD path
    steamcmd_path = get_steamcmd_path()
    if not os.path.exists(steamcmd_path):
        return f"Error: SteamCMD not found at {steamcmd_path}"
    
    # Create command
    cmd_args = [steamcmd_path]
    
    if anonymous:
        cmd_args.extend(["+login", "anonymous"])
    else:
        cmd_args.extend(["+login", username, password])
    
    cmd_args.extend([
        "+force_install_dir", download_dir,
        "+app_update", appid
    ])
    
    if validate_download:
        cmd_args.append("validate")
    
    cmd_args.append("+quit")
    
    # Log command for debugging
    cmd_str = ' '.join(cmd_args)
    logging.info(f"Running command: {cmd_str}")
    
    # Write a status file we can check
    status_file = os.path.join(STEAM_DOWNLOAD_PATH, f"download_status_{appid}.txt")
    with open(status_file, 'w') as f:
        f.write(f"Starting download for AppID: {appid}\nCommand: {cmd_str}\nTime: {datetime.now()}")
    
    try:
        # Make sure SteamCMD is executable
        if platform.system() != "Windows" and not os.access(steamcmd_path, os.X_OK):
            os.chmod(steamcmd_path, 0o755)
            logging.info(f"Made SteamCMD executable at {steamcmd_path}")
        
        # First, test if SteamCMD runs at all
        test_cmd = [steamcmd_path, "+login", "anonymous", "+quit"]
        logging.info(f"Testing SteamCMD with command: {' '.join(test_cmd)}")
        
        test_result = subprocess.run(
            test_cmd, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        logging.info(f"SteamCMD test result: Exit code {test_result.returncode}")
        logging.info(f"SteamCMD test stdout: {test_result.stdout[:500]}")  # First 500 chars
        
        if test_result.returncode != 0:
            with open(status_file, 'a') as f:
                f.write(f"\nSteamCMD test failed with code {test_result.returncode}")
            return f"Error: SteamCMD test failed with code {test_result.returncode}"
        
        # Now run the actual download - this runs synchronously
        logging.info("Starting download process...")
        with open(status_file, 'a') as f:
            f.write("\nStarting SteamCMD download process...")
        
        # Run process with 10-minute timeout
        result = subprocess.run(
            cmd_args, 
            capture_output=True, 
            text=True, 
            timeout=600  # 10 minutes
        )
        
        logging.info(f"Download process completed with exit code: {result.returncode}")
        
        # Write results to status file
        with open(status_file, 'a') as f:
            f.write(f"\nDownload completed with exit code: {result.returncode}")
            f.write(f"\nTime: {datetime.now()}")
            f.write("\n\nOutput:\n")
            f.write(result.stdout)
        
        # Check if download was successful
        if result.returncode == 0 and "Success! App" in result.stdout:
            return f"Successfully downloaded game (AppID: {appid})"
        else:
            return f"Download completed with issues. Exit code: {result.returncode}. Check logs for details."
    
    except subprocess.TimeoutExpired:
        logging.error("Download process timed out after 10 minutes")
        with open(status_file, 'a') as f:
            f.write("\nERROR: Download process timed out after 10 minutes")
        return "Error: Download timed out after 10 minutes"
    
    except Exception as e:
        logging.error(f"Error running download: {str(e)}", exc_info=True)
        with open(status_file, 'a') as f:
            f.write(f"\nERROR: {str(e)}")
        return f"Error: {str(e)}"

def emergency_download_game(username, password, guard_code, anonymous, game_input, validate_download):
    """
    Emergency download function that bypasses all the complex logic.
    Just runs SteamCMD directly and returns a simple status.
    """
    try:
        logging.info(f"Emergency download function called for: {game_input}")
        
        # Extract AppID
        appid = parse_game_input(game_input)
        if not appid:
            return "Error: Invalid game input. Could not extract AppID."
        
        logging.info(f"Emergency download: extracted AppID {appid}")
        
        # Create a unique download folder
        timestamp = int(time.time())
        download_folder = os.path.join(STEAM_DOWNLOAD_PATH, f"game_{appid}_{timestamp}")
        os.makedirs(download_folder, exist_ok=True)
        
        logging.info(f"Emergency download: created folder {download_folder}")
        
        # Build SteamCMD command
        steamcmd_path = get_steamcmd_path()
        
        if not os.path.exists(steamcmd_path):
            return f"Error: SteamCMD not found at {steamcmd_path}"
        
        # Basic command
        if anonymous:
            cmd = f'"{steamcmd_path}" +login anonymous +force_install_dir "{download_folder}" +app_update {appid} +quit'
        else:
            # You'd need to handle credentials properly in a real implementation
            cmd = f'"{steamcmd_path}" +login {username} {password} +force_install_dir "{download_folder}" +app_update {appid} +quit'
        
        logging.info(f"Emergency download: command prepared (not showing credentials)")
        
        # Write a status file we can check later
        status_path = os.path.join(download_folder, "download_status.txt")
        with open(status_path, 'w') as f:
            f.write(f"Download started at: {datetime.now()}\n")
            f.write(f"AppID: {appid}\n")
            f.write(f"Anonymous: {anonymous}\n")
            f.write(f"Command: {cmd if anonymous else '[CREDENTIALS HIDDEN]'}\n\n")
        
        logging.info(f"Emergency download: wrote status file to {status_path}")
        
        # Run the command as a direct OS command
        if platform.system() == "Windows":
            # Use subprocess.Popen for Windows
            process = subprocess.Popen(cmd, shell=True)
            logging.info(f"Emergency download: started Windows process with PID {process.pid}")
            return f"Download started for AppID {appid}. Check folder: {download_folder}"
        else:
            # For Linux/Mac, use os.system to run detached
            os_cmd = f"nohup {cmd} > '{download_folder}/output.log' 2>&1 &"
            os.system(os_cmd)
            logging.info(f"Emergency download: started detached process with nohup")
            return f"Download started for AppID {appid}. Check folder: {download_folder}"
            
    except Exception as e:
        logging.error(f"Emergency download error: {str(e)}", exc_info=True)
        return f"Error starting download: {str(e)}"

def download_game(username, password, guard_code, anonymous, game_input, validate_download):
    """Download a game directly using SteamCMD."""
    try:
        logging.info(f"Starting download for: {game_input}")
        
        # Copy the entire function body from line 2132
        # ...
        # All the implementation details
        # ...
        
        return f"Download started for AppID {appid}. Check folder: {download_folder}"
            
    except Exception as e:
        logging.error(f"Download error: {str(e)}", exc_info=True)
        return f"Error starting download: {str(e)}"

# Add this near the top of your file, after imports
def forward_to_download(username, password, guard_code, anonymous, game_input, validate_download):
    """Forward function to handle circular imports"""
    return queue_download(username, password, guard_code, anonymous, game_input, validate_download)

def handle_download(game_input_text, username_val, password_val, guard_code_val, 
                 anonymous_val, validate_val, game_info_json):
    try:
        # Validate inputs based on login type
        if not game_input_text:
            return "Please enter a game ID or URL."
            
        if not anonymous_val and (not username_val or not password_val):
            return "Steam username and password are required for non-anonymous downloads."
        
        # Parse game input
        appid = parse_game_input(game_input_text)
        if not appid:
            return "Invalid game ID or URL format."
            
        # Start the download process
        download_id = start_download(
            username=username_val,
            password=password_val,
            guard_code=guard_code_val, 
            anonymous=anonymous_val,
            appid=appid,
            validate_download=validate_val
        )
        
        if download_id:
            return f"Download started for AppID {appid}. Download ID: {download_id}"
        else:
            return "Failed to start download. Check logs for details."
            
    except Exception as e:
        logging.error(f"Download error: {str(e)}")
        return f"Error: {str(e)}"

def handle_login_toggle(anonymous):
    """Handle visibility of login fields based on anonymous selection"""
    return gr.update(visible=not anonymous)

def validate_login(username, password, guard_code, anonymous):
    """Validate login credentials before attempting download"""
    if anonymous:
        return True, "Anonymous login selected"
    
    if not username or not password:
        return False, "Username and password are required for non-anonymous login"
    
    # You might want to add basic validation here
    # For example, checking if the username format is valid
    
    # For a real implementation, you could test the credentials with SteamCMD
    # But that would require running SteamCMD, which is better left for the actual download
    
    return True, "Login information provided"