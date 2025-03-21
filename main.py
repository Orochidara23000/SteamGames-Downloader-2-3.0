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

# Define critical functions early to avoid undefined references
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

def handle_queue(game_input_text, username_val, password_val, guard_code_val, 
                anonymous_val, validate_val, game_info_json):
    """Add a download to the queue instead of starting it immediately"""
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
        
        # Add to queue
        with queue_lock:
            position = len(download_queue) + 1
            download_queue.append({
                "username": username_val,
                "password": password_val,
                "guard_code": guard_code_val,
                "anonymous": anonymous_val,
                "appid": appid,
                "validate": validate_val,
                "added_time": datetime.now()
            })
            logging.info(f"Added download for AppID {appid} to queue at position {position}")
        
        return f"Added download for AppID {appid} to queue at position {position}"
            
    except Exception as e:
        logging.error(f"Queue error: {str(e)}")
        return f"Error adding to queue: {str(e)}"

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
    # Print the share URL more prominently
    print("\n" + "=" * 70)
    print(f"SHARE URL: {share_url}")
    print("Copy this URL to access the application from any device")
    print("=" * 70 + "\n")

# Forward declarations to ensure functions are defined before use
def forward_to_download(username, password, guard_code, anonymous, game_input, validate_download):
    """Forward function to handle circular imports"""
    # Implementation already moved to top of file
    return queue_download(username, password, guard_code, anonymous, game_input, validate_download)

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
                with gr.Group():
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
                with gr.Group():
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
                with gr.Group():
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

def handle_login_toggle(anonymous):
    """Handle visibility of login fields based on anonymous selection"""
    return gr.update(visible=not anonymous)

# Main application entry point
if __name__ == "__main__":
    print("="*50)
    print("Starting Steam Games Downloader - FULL VERSION")
    print("="*50)
    
    # Initialize background threads and services
    download_queue_thread = threading.Thread(target=process_download_queue, daemon=True)
    download_queue_thread.start()
    
    # Create the full user interface
    with gr.Blocks(title="Steam Games Downloader") as app:
        gr.Markdown("# Steam Games Downloader")
        
        with gr.Tabs():
            download_tab = create_download_games_tab()
            library_tab = create_library_tab()
            setup_tab = create_setup_tab()
            settings_tab = create_settings_tab()
        
        # Set up periodic refresh for downloads
        refresh_interval = setup_refresh_interval()
            
        print("Full interface created, launching application...")
    
    # Launch the application
    app.launch(
        server_port=int(os.environ.get("PORT", 7862)),
        server_name="0.0.0.0",
        share=True,  # Always enable sharing
        debug=os.environ.get("DEBUG", "False").lower() == "true",
        share_callback=update_share_url  # Capture and display the share URL
    )
    
    # Print confirmation after launch
    print("="*50)
    print("Application running. Access URLs listed above.")
    print("Sharing is ENABLED - look for the 'Running on public URL:' link above")
    print("="*50)