#!/usr/bin/env python3
"""
SteamCMD Manager module for Steam Games Downloader
Handles downloading, installing, and running SteamCMD
"""

import os
import sys
import platform
import logging
import subprocess
import urllib.request
import tarfile
import zipfile
import shutil
import time
from pathlib import Path

# Configure logger
logger = logging.getLogger(__name__)

class SteamCMD:
    """Class to manage SteamCMD functionality"""
    
    def __init__(self, path=None):
        """Initialize SteamCMD with the given path"""
        try:
            # Determine the system type
            self.system = platform.system().lower()
            logger.info(f"Operating system: {self.system}")
            
            # Check if running in a container
            self.is_container = self._check_if_container()
            logger.info(f"Running in container: {self.is_container}")
            
            # Set default path if not provided
            if path is None:
                if self.is_container or os.path.exists("/root/steamcmd"):
                    path = "/root/steamcmd"
                elif self.system == "windows":
                    path = os.path.join(os.path.expanduser("~"), "steamcmd")
                else:
                    path = os.path.join(os.path.expanduser("~"), "steamcmd")
            
            self.path = path
            logger.info(f"SteamCMD path: {self.path}")
            
            # Ensure path exists
            os.makedirs(self.path, exist_ok=True)
            
            # Set executable path based on system
            if self.system == "windows":
                self.exe = os.path.join(self.path, "steamcmd.exe")
            else:
                self.exe = os.path.join(self.path, "steamcmd.sh")
            
            logger.info(f"SteamCMD executable: {self.exe}")
            
            # Check if SteamCMD is already installed
            self.installed = self._check_if_installed()
            logger.info(f"SteamCMD installed: {self.installed}")
            
        except Exception as e:
            logger.error(f"Error initializing SteamCMD: {str(e)}")
            raise
    
    def _check_if_container(self):
        """Check if running in a container environment"""
        # Common ways to detect container environments
        if os.path.exists("/.dockerenv"):
            return True
        
        # Check cgroup
        try:
            with open("/proc/1/cgroup", "r") as f:
                return "docker" in f.read() or "kubepods" in f.read()
        except:
            pass
        
        return False
    
    def _check_if_installed(self):
        """Check if SteamCMD is already installed"""
        # For Windows
        if self.system == "windows":
            return os.path.exists(self.exe)
        
        # For Linux and macOS
        return os.path.exists(self.exe) and os.path.exists(os.path.join(self.path, "linux32", "steamcmd"))
    
    def install_steamcmd(self):
        """Download and install SteamCMD"""
        try:
            logger.info("Installing SteamCMD...")
            
            # Create directory if it doesn't exist
            os.makedirs(self.path, exist_ok=True)
            
            # Windows installation
            if self.system == "windows":
                return self._install_windows()
            
            # Linux/macOS installation
            return self._install_linux()
            
        except Exception as e:
            logger.error(f"Error installing SteamCMD: {str(e)}")
            return False
    
    def _install_windows(self):
        """Install SteamCMD on Windows"""
        try:
            logger.info("Installing SteamCMD for Windows...")
            
            # Download SteamCMD zip
            url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
            zip_path = os.path.join(self.path, "steamcmd.zip")
            
            logger.info(f"Downloading SteamCMD from {url}...")
            urllib.request.urlretrieve(url, zip_path)
            
            # Extract zip
            logger.info(f"Extracting to {self.path}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.path)
            
            # Clean up
            os.remove(zip_path)
            
            # Update executable permission flag
            logger.info("Installation completed successfully")
            self.installed = True
            return True
            
        except Exception as e:
            logger.error(f"Error installing SteamCMD for Windows: {str(e)}")
            return False
    
    def _install_linux(self):
        """Install SteamCMD on Linux"""
        try:
            logger.info("Installing SteamCMD for Linux...")
            
            # Download SteamCMD tarball
            url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
            tar_path = os.path.join(self.path, "steamcmd_linux.tar.gz")
            
            logger.info(f"Downloading SteamCMD from {url}...")
            urllib.request.urlretrieve(url, tar_path)
            
            # Extract tarball
            logger.info(f"Extracting to {self.path}...")
            with tarfile.open(tar_path, 'r:gz') as tar:
                tar.extractall(self.path)
            
            # Make the script executable
            os.chmod(self.exe, 0o755)
            
            # Clean up
            os.remove(tar_path)
            
            # Ensure linux32 directory exists
            linux32_dir = os.path.join(self.path, "linux32")
            if not os.path.exists(linux32_dir):
                os.makedirs(linux32_dir, exist_ok=True)
            
            # Copy steamcmd binary to linux32 directory if it doesn't exist
            steam_bin = os.path.join(self.path, "steamcmd")
            linux32_bin = os.path.join(linux32_dir, "steamcmd")
            if os.path.exists(steam_bin) and not os.path.exists(linux32_bin):
                shutil.copy2(steam_bin, linux32_bin)
                os.chmod(linux32_bin, 0o755)
            
            logger.info("Installation completed successfully")
            self.installed = True
            return True
            
        except Exception as e:
            logger.error(f"Error installing SteamCMD for Linux: {str(e)}")
            return False
    
    def verify_installation(self):
        """Verify SteamCMD installation by running a simple command"""
        try:
            logger.info("Verifying SteamCMD installation...")
            
            if not self.installed:
                logger.warning("SteamCMD is not installed, cannot verify")
                return False
            
            # Run SteamCMD with quit command
            if self.system == "windows":
                cmd = [self.exe, "+quit"]
            else:
                cmd = [self.exe, "+quit"]
            
            logger.info(f"Running command: {' '.join(cmd)}")
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if process.returncode == 0:
                logger.info("SteamCMD verification successful")
                return True
            else:
                logger.warning(f"SteamCMD verification failed with return code {process.returncode}")
                logger.warning(f"STDERR: {process.stderr}")
                return False
            
        except Exception as e:
            logger.error(f"Error verifying SteamCMD: {str(e)}")
            return False
    
    def download_game(self, app_id, install_dir, username=None, password=None, validate=True, platform=None):
        """Download a game using SteamCMD"""
        try:
            logger.info(f"Downloading game {app_id} to {install_dir}...")
            
            if not self.installed:
                logger.warning("SteamCMD is not installed, cannot download game")
                return False
            
            # Create install directory if it doesn't exist
            os.makedirs(install_dir, exist_ok=True)
            
            # Build command
            cmd = [self.exe]
            
            # Login
            if username and password:
                cmd.extend([f"+login {username} {password}"])
            else:
                cmd.append("+login anonymous")
            
            # Set install directory and platform if specified
            cmd.append(f"+force_install_dir {install_dir}")
            
            if platform:
                cmd.append(f"+@sSteamCmdForcePlatformType {platform}")
            
            # Download app
            validate_flag = " validate" if validate else ""
            cmd.append(f"+app_update {app_id}{validate_flag}")
            
            # Quit
            cmd.append("+quit")
            
            # Run command
            logger.info(f"Running command: {' '.join(cmd)}")
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if process.returncode == 0:
                logger.info(f"Game {app_id} downloaded successfully")
                return True
            else:
                logger.warning(f"Game download failed with return code {process.returncode}")
                logger.warning(f"STDERR: {process.stderr}")
                return False
            
        except Exception as e:
            logger.error(f"Error downloading game: {str(e)}")
            return False

# Singleton instance
_instance = None

def get_steamcmd():
    """Get the singleton SteamCMD instance"""
    global _instance
    if _instance is None:
        _instance = SteamCMD()
    return _instance

# For direct testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test SteamCMD
    steamcmd = get_steamcmd()
    
    if not steamcmd.installed:
        steamcmd.install_steamcmd()
        
    steamcmd.verify_installation()