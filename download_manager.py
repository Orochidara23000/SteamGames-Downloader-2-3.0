#!/usr/bin/env python3
"""
Download Manager Module for Steam Games Downloader
Handles game downloads and manages download queue
"""

import os
import sys
import time
import json
import logging
import subprocess
import threading
import uuid
from pathlib import Path
from datetime import datetime

# Configure logger
logger = logging.getLogger(__name__)

class DownloadManager:
    """Manages game downloads using SteamCMD"""
    
    def __init__(self, config=None):
        """Initialize the download manager"""
        try:
            # Import config lazily to avoid circular imports
            if config is None:
                from utils.config import get_config
                self.config = get_config()
            else:
                self.config = config
            
            # Get paths from config
            self.downloads_path = self.config.get("download_path", "/data/downloads")
            self.steamcmd_path = self.config.get("steamcmd_path", "/root/steamcmd")
            
            # Ensure directories exist
            os.makedirs(self.downloads_path, exist_ok=True)
            os.makedirs(self.steamcmd_path, exist_ok=True)
            
            # Downloads state
            self.downloads = {}
            self.active_downloads = {}
            self.max_concurrent = self.config.get("max_concurrent_downloads", 1)
            self.download_lock = threading.Lock()
            
            # Load existing downloads if available
            self._load_downloads()
            
            logger.info(f"Download Manager initialized with path: {self.downloads_path}")
            logger.info(f"SteamCMD path: {self.steamcmd_path}")
            logger.info(f"Max concurrent downloads: {self.max_concurrent}")
            
            # Start background thread for download processing
            self.should_stop = False
            self.download_thread = threading.Thread(target=self._process_downloads, daemon=True)
            self.download_thread.start()
            
        except Exception as e:
            logger.error(f"Error initializing Download Manager: {str(e)}")
            raise
    
    def _load_downloads(self):
        """Load existing downloads from file"""
        try:
            download_file = os.path.join(self.downloads_path, "downloads.json")
            if os.path.exists(download_file):
                with open(download_file, "r") as f:
                    downloads = json.load(f)
                
                # Reset status for any in-progress downloads
                for dl_id, dl_info in downloads.items():
                    if dl_info["status"] == "downloading":
                        dl_info["status"] = "pending"
                
                self.downloads = downloads
                logger.info(f"Loaded {len(downloads)} downloads from file")
            else:
                logger.info("No existing downloads file found")
        
        except Exception as e:
            logger.error(f"Error loading downloads: {str(e)}")
            self.downloads = {}
    
    def _save_downloads(self):
        """Save downloads to file"""
        try:
            download_file = os.path.join(self.downloads_path, "downloads.json")
            with open(download_file, "w") as f:
                json.dump(self.downloads, f, indent=4)
            logger.debug("Saved downloads to file")
        
        except Exception as e:
            logger.error(f"Error saving downloads: {str(e)}")
    
    def add_download(self, app_id, app_name, platform=None):
        """Add a game to the download queue"""
        try:
            logger.info(f"Adding download for {app_name} (AppID: {app_id})")
            
            # Generate a unique ID for this download
            dl_id = f"dl_{app_id}_{int(time.time())}"
            
            # Create download info
            download_info = {
                "id": dl_id,
                "app_id": app_id,
                "app_name": app_name,
                "platform": platform or "windows",
                "status": "pending",
                "progress": 0,
                "added_time": datetime.now().isoformat(),
                "start_time": None,
                "end_time": None,
                "error": None,
                "install_dir": os.path.join(self.downloads_path, str(app_id))
            }
            
            # Add to downloads dictionary
            with self.download_lock:
                self.downloads[dl_id] = download_info
                self._save_downloads()
            
            logger.info(f"Download added with ID: {dl_id}")
            return dl_id
        
        except Exception as e:
            logger.error(f"Error adding download: {str(e)}")
            return None
    
    def cancel_download(self, dl_id):
        """Cancel a download"""
        try:
            logger.info(f"Cancelling download {dl_id}")
            
            with self.download_lock:
                if dl_id in self.downloads:
                    # If active, need to terminate process
                    if dl_id in self.active_downloads:
                        process = self.active_downloads[dl_id]
                        try:
                            process.terminate()
                            logger.info(f"Terminated download process for {dl_id}")
                        except:
                            logger.warning(f"Failed to terminate download process for {dl_id}")
                        
                        del self.active_downloads[dl_id]
                    
                    # Update status
                    self.downloads[dl_id]["status"] = "cancelled"
                    self.downloads[dl_id]["end_time"] = datetime.now().isoformat()
                    self._save_downloads()
                    logger.info(f"Download {dl_id} marked as cancelled")
                    return True
                else:
                    logger.warning(f"Download {dl_id} not found for cancellation")
                    return False
        
        except Exception as e:
            logger.error(f"Error cancelling download {dl_id}: {str(e)}")
            return False
    
    def retry_download(self, dl_id):
        """Retry a failed or cancelled download"""
        try:
            logger.info(f"Retrying download {dl_id}")
            
            with self.download_lock:
                if dl_id in self.downloads:
                    download = self.downloads[dl_id]
                    
                    # Only retry failed or cancelled downloads
                    if download["status"] in ["failed", "cancelled"]:
                        download["status"] = "pending"
                        download["progress"] = 0
                        download["error"] = None
                        download["start_time"] = None
                        download["end_time"] = None
                        self._save_downloads()
                        logger.info(f"Download {dl_id} marked for retry")
                        return True
                    else:
                        logger.warning(f"Cannot retry download {dl_id} with status {download['status']}")
                        return False
                else:
                    logger.warning(f"Download {dl_id} not found for retry")
                    return False
        
        except Exception as e:
            logger.error(f"Error retrying download {dl_id}: {str(e)}")
            return False
    
    def get_downloads(self):
        """Get all downloads"""
        with self.download_lock:
            return self.downloads.copy()
    
    def get_download(self, dl_id):
        """Get a specific download"""
        with self.download_lock:
            return self.downloads.get(dl_id)
    
    def clear_completed(self):
        """Clear completed downloads from the list"""
        try:
            with self.download_lock:
                # Find completed downloads
                completed = [dl_id for dl_id, dl in self.downloads.items() 
                           if dl["status"] == "completed"]
                
                # Remove them
                for dl_id in completed:
                    del self.downloads[dl_id]
                
                self._save_downloads()
                
                logger.info(f"Cleared {len(completed)} completed downloads")
                return len(completed)
        
        except Exception as e:
            logger.error(f"Error clearing completed downloads: {str(e)}")
            return 0
    
    def clear_failed(self):
        """Clear failed downloads from the list"""
        try:
            with self.download_lock:
                # Find failed downloads
                failed = [dl_id for dl_id, dl in self.downloads.items() 
                        if dl["status"] == "failed"]
                
                # Remove them
                for dl_id in failed:
                    del self.downloads[dl_id]
                
                self._save_downloads()
                
                logger.info(f"Cleared {len(failed)} failed downloads")
                return len(failed)
        
        except Exception as e:
            logger.error(f"Error clearing failed downloads: {str(e)}")
            return 0
    
    def _process_downloads(self):
        """Process pending downloads in a background thread"""
        try:
            logger.info("Download processing thread started")
            
            while not self.should_stop:
                # Check for pending downloads
                with self.download_lock:
                    # Get pending downloads
                    pending = [dl_id for dl_id, dl in self.downloads.items() 
                             if dl["status"] == "pending"]
                    
                    # Check if we can start any new downloads
                    available_slots = self.max_concurrent - len(self.active_downloads)
                    
                    if available_slots > 0 and pending:
                        # Start next pending download
                        dl_id = pending[0]
                        download = self.downloads[dl_id]
                        download["status"] = "downloading"
                        download["start_time"] = datetime.now().isoformat()
                        self._save_downloads()
                        
                        # Start download in a new thread
                        thread = threading.Thread(
                            target=self._download_game,
                            args=(dl_id,),
                            daemon=True
                        )
                        thread.start()
                
                # Sleep for a bit before checking again
                time.sleep(1)
                
            logger.info("Download processing thread stopped")
        
        except Exception as e:
            logger.error(f"Error in download processing thread: {str(e)}")
    
    def _download_game(self, dl_id):
        """Download a game using SteamCMD"""
        try:
            logger.info(f"Starting download for {dl_id}")
            
            with self.download_lock:
                if dl_id not in self.downloads:
                    logger.warning(f"Download {dl_id} not found for processing")
                    return
                
                download = self.downloads[dl_id]
                app_id = download["app_id"]
                install_dir = download["install_dir"]
            
            # Ensure install directory exists
            os.makedirs(install_dir, exist_ok=True)
            
            # Get login information
            anonymous = self.config.get("anonymous_login", True)
            username = None if anonymous else self.config.get("username")
            password = None if anonymous else self.config.get("password")
            
            # Check if SteamCMD exists and is executable
            steamcmd_script = os.path.join(self.steamcmd_path, "steamcmd.sh")
            linux32_binary = os.path.join(self.steamcmd_path, "linux32", "steamcmd")
            
            if not os.path.exists(steamcmd_script) or not os.path.exists(linux32_binary):
                logger.warning(f"SteamCMD not properly installed, attempting to fix")
                self._fix_steamcmd()
            
            # Build command
            cmd = [steamcmd_script]
            
            # Login
            if anonymous or not username or not password:
                cmd.append("+login anonymous")
            else:
                cmd.append(f"+login {username} {password}")
            
            # Set install directory
            cmd.append(f"+force_install_dir {install_dir}")
            
            # Set platform if specified
            platform = download["platform"]
            if platform and platform != "windows":
                cmd.append(f"+@sSteamCmdForcePlatformType {platform}")
            
            # Download app
            validate = self.config.get("validate_files", True)
            validate_flag = " validate" if validate else ""
            cmd.append(f"+app_update {app_id}{validate_flag}")
            
            # Quit
            cmd.append("+quit")
            
            # Run command
            command_str = " ".join(cmd)
            logger.info(f"Running SteamCMD command: {command_str}")
            
            # Start process
            process = subprocess.Popen(
                command_str,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Register active download
            with self.download_lock:
                self.active_downloads[dl_id] = process
            
            # Monitor process output for progress updates
            for line in process.stdout:
                # Log the output
                logger.debug(f"SteamCMD output: {line.strip()}")
                
                # Try to parse progress
                if "%" in line:
                    try:
                        # Extract progress percentage
                        progress_str = line.strip().split("%")[0].strip("[] ")
                        progress = int(progress_str)
                        
                        # Update progress
                        with self.download_lock:
                            if dl_id in self.downloads:
                                self.downloads[dl_id]["progress"] = progress
                                # Don't save on every progress update to avoid file contention
                                if progress % 10 == 0:  # Save every 10% progress
                                    self._save_downloads()
                    except:
                        pass
            
            # Wait for process to complete
            process.wait()
            
            # Process completed, update status
            with self.download_lock:
                if dl_id in self.active_downloads:
                    del self.active_downloads[dl_id]
                
                if dl_id in self.downloads:
                    download = self.downloads[dl_id]
                    download["end_time"] = datetime.now().isoformat()
                    
                    if process.returncode == 0:
                        download["status"] = "completed"
                        download["progress"] = 100
                        logger.info(f"Download {dl_id} completed successfully")
                    else:
                        download["status"] = "failed"
                        stderr = process.stderr.read() if process.stderr else ""
                        download["error"] = f"Process exited with code {process.returncode}: {stderr}"
                        logger.error(f"Download {dl_id} failed: {download['error']}")
                    
                    self._save_downloads()
        
        except Exception as e:
            logger.error(f"Error downloading game {dl_id}: {str(e)}")
            
            # Update status
            with self.download_lock:
                if dl_id in self.active_downloads:
                    del self.active_downloads[dl_id]
                
                if dl_id in self.downloads:
                    download = self.downloads[dl_id]
                    download["status"] = "failed"
                    download["error"] = str(e)
                    download["end_time"] = datetime.now().isoformat()
                    self._save_downloads()
    
    def _fix_steamcmd(self):
        """Attempt to fix SteamCMD installation"""
        try:
            logger.info("Attempting to fix SteamCMD installation")
            
            # Check if fix script exists
            fix_script = "/app/fix_steamcmd.sh"
            if os.path.exists(fix_script):
                logger.info(f"Running fix script: {fix_script}")
                subprocess.run(
                    ["bash", fix_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                return True
            
            # If script doesn't exist, try manual fix
            steamcmd_dir = self.steamcmd_path
            linux32_dir = os.path.join(steamcmd_dir, "linux32")
            
            # Create directories
            os.makedirs(linux32_dir, exist_ok=True)
            
            # Download SteamCMD
            tar_path = os.path.join(steamcmd_dir, "steamcmd_linux.tar.gz")
            logger.info(f"Downloading SteamCMD to {tar_path}")
            
            # Use subprocess to download with curl or wget
            try:
                subprocess.run(
                    ["curl", "-sqL", "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz", "-o", tar_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
            except:
                try:
                    subprocess.run(
                        ["wget", "-q", "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz", "-O", tar_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
                except:
                    logger.error("Failed to download SteamCMD, both curl and wget failed")
                    return False
            
            # Extract archive
            logger.info(f"Extracting SteamCMD to {steamcmd_dir}")
            try:
                subprocess.run(
                    ["tar", "-xzf", tar_path, "-C", steamcmd_dir],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
            except:
                logger.error("Failed to extract SteamCMD archive")
                return False
            
            # Make script executable
            steamcmd_script = os.path.join(steamcmd_dir, "steamcmd.sh")
            os.chmod(steamcmd_script, 0o755)
            
            # Copy steamcmd binary to linux32 directory
            steam_bin = os.path.join(steamcmd_dir, "steamcmd")
            linux32_bin = os.path.join(linux32_dir, "steamcmd")
            
            if os.path.exists(steam_bin):
                import shutil
                shutil.copy2(steam_bin, linux32_bin)
                os.chmod(linux32_bin, 0o755)
                logger.info(f"Copied SteamCMD binary to {linux32_bin}")
            
            logger.info("SteamCMD installation fixed")
            return True
            
        except Exception as e:
            logger.error(f"Error fixing SteamCMD: {str(e)}")
            return False
    
    def shutdown(self):
        """Shut down the download manager"""
        try:
            logger.info("Shutting down Download Manager")
            
            # Signal thread to stop
            self.should_stop = True
            
            # Cancel all active downloads
            with self.download_lock:
                for dl_id, process in list(self.active_downloads.items()):
                    try:
                        process.terminate()
                        logger.info(f"Terminated download process for {dl_id}")
                    except:
                        logger.warning(f"Failed to terminate download process for {dl_id}")
                
                # Update status for active downloads
                for dl_id in self.active_downloads:
                    if dl_id in self.downloads:
                        self.downloads[dl_id]["status"] = "cancelled"
                        self.downloads[dl_id]["end_time"] = datetime.now().isoformat()
                
                self.active_downloads.clear()
                self._save_downloads()
            
            # Wait for thread to finish
            if self.download_thread.is_alive():
                self.download_thread.join(timeout=2)
            
            logger.info("Download Manager shut down successfully")
        
        except Exception as e:
            logger.error(f"Error shutting down Download Manager: {str(e)}")

# Singleton instance
_instance = None

def get_download_manager():
    """Get the singleton download manager instance"""
    global _instance
    if _instance is None:
        _instance = DownloadManager()
    return _instance 