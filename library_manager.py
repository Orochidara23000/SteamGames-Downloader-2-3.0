import os
import json
import logging
import pandas as pd
from pathlib import Path
import time

# Initialize logger
logger = logging.getLogger(__name__)

class LibraryManager:
    """Manager for the game library"""
    
    def __init__(self):
        """Initialize the library manager"""
        self.library_dir = Path("data/library")
        self.library_file = self.library_dir / "library.json"
        
        # Ensure library directory exists
        self.library_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or create library
        self.library = self._load_library()
        
        logger.info("Library manager initialized")
    
    def _load_library(self):
        """Load library from file or create a new one"""
        try:
            if self.library_file.exists():
                with open(self.library_file, 'r') as f:
                    library = json.load(f)
                logger.info("Library loaded from file")
                return library
            else:
                logger.info("Library file not found, creating new library")
                return {"games": []}
        except Exception as e:
            logger.error(f"Error loading library: {str(e)}")
            return {"games": []}
    
    def save_library(self):
        """Save library to file"""
        try:
            with open(self.library_file, 'w') as f:
                json.dump(self.library, f, indent=4)
            logger.info("Library saved to file")
            return True
        except Exception as e:
            logger.error(f"Error saving library: {str(e)}")
            return False
    
    def add_game(self, app_id, name, location, size=0):
        """Add a game to the library"""
        # Check if game already exists
        for game in self.library["games"]:
            if game["app_id"] == str(app_id):
                logger.info(f"Game {name} (AppID: {app_id}) already in library, updating")
                game["name"] = name
                game["location"] = location
                game["size"] = size
                game["last_played"] = ""
                return self.save_library()
        
        # Add new game
        self.library["games"].append({
            "app_id": str(app_id),
            "name": name,
            "location": location,
            "size": size,
            "last_played": "",
            "time_added": time.time()
        })
        
        logger.info(f"Added {name} (AppID: {app_id}) to library")
        return self.save_library()
    
    def remove_game(self, app_id):
        """Remove a game from the library"""
        # Find game index
        for i, game in enumerate(self.library["games"]):
            if game["app_id"] == str(app_id):
                # Remove game
                removed_game = self.library["games"].pop(i)
                logger.info(f"Removed {removed_game['name']} (AppID: {app_id}) from library")
                return self.save_library()
        
        logger.warning(f"Game with AppID {app_id} not found in library")
        return False
    
    def get_game(self, app_id):
        """Get a game from the library by AppID"""
        for game in self.library["games"]:
            if game["app_id"] == str(app_id):
                return game
        return None
    
    def get_all_games(self):
        """Get all games in the library"""
        return self.library["games"]
    
    def get_library_dataframe(self):
        """Get the library as a pandas DataFrame"""
        if not self.library["games"]:
            # Return empty dataframe with expected columns
            return pd.DataFrame(columns=["app_id", "name", "location", "size", "last_played"])
        
        # Create DataFrame
        df = pd.DataFrame(self.library["games"])
        
        # Format columns
        if "size" in df.columns:
            df["size"] = df["size"].apply(self._format_size)
        
        if "last_played" in df.columns:
            df["last_played"] = df["last_played"].apply(
                lambda x: x if x else "Never"
            )
        
        return df
    
    def _format_size(self, size_bytes):
        """Format size in bytes to human-readable format"""
        if not size_bytes:
            return "Unknown"
        
        try:
            size_bytes = int(size_bytes)
            
            # Define size units
            units = ["B", "KB", "MB", "GB", "TB"]
            
            # Calculate appropriate unit
            unit_index = 0
            while size_bytes >= 1024 and unit_index < len(units) - 1:
                size_bytes /= 1024
                unit_index += 1
            
            # Format and return
            return f"{size_bytes:.2f} {units[unit_index]}"
        except:
            return "Unknown"
    
    def verify_game_files(self, app_id):
        """Verify game files for a specific game"""
        # Get game
        game = self.get_game(app_id)
        if not game:
            logger.warning(f"Cannot verify files for game with AppID {app_id}, not found in library")
            return False
        
        # Check if game location exists
        location = game["location"]
        if not os.path.exists(location):
            logger.warning(f"Game location does not exist: {location}")
            return False
        
        # TODO: Implement actual verification logic
        # In a real implementation, we would check if all game files are present and valid
        # For now, we just check if the directory exists
        
        logger.info(f"Verified files for {game['name']} (AppID: {app_id})")
        return True
    
    def update_last_played(self, app_id):
        """Update the last played timestamp for a game"""
        # Get game
        for game in self.library["games"]:
            if game["app_id"] == str(app_id):
                # Update last played timestamp
                game["last_played"] = time.strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"Updated last played time for {game['name']} (AppID: {app_id})")
                return self.save_library()
        
        logger.warning(f"Game with AppID {app_id} not found in library")
        return False

# Singleton instance
_instance = None

def get_library_manager():
    """Get the singleton library manager instance"""
    global _instance
    if _instance is None:
        _instance = LibraryManager()
    return _instance

# For direct testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Get library manager
    lm = get_library_manager()
    
    # Add some test games
    lm.add_game(730, "Counter-Strike: Global Offensive", "/data/downloads/steamapps/common/app_730", 15000000000)
    lm.add_game(570, "Dota 2", "/data/downloads/steamapps/common/app_570", 20000000000)
    
    # Print all games
    print("All games:")
    for game in lm.get_all_games():
        print(f"  {game['name']} (AppID: {game['app_id']})")
    
    # Get library as DataFrame
    df = lm.get_library_dataframe()
    print("\nLibrary as DataFrame:")
    print(df) 