import os
import re
import json
import logging
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import requests
import time
from pathlib import Path

# Initialize logger
logger = logging.getLogger(__name__)

# Constants
STEAM_API_BASE = "https://api.steampowered.com"
STORE_API_BASE = "https://store.steampowered.com/api"
DEFAULT_CACHE_TIME = 86400  # 24 hours

class SteamAPI:
    """Class for interacting with the Steam Web API"""
    
    def __init__(self, api_key=None):
        """Initialize SteamAPI with optional API key"""
        self.api_key = api_key
        
        # Cache directory for API responses
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Steam API initialized")
    
    def get_app_details(self, app_id):
        """Get detailed information about a Steam app/game"""
        cache_file = self.cache_dir / f"app_{app_id}.json"
        
        # Check cache first
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                # Check if cache is still valid
                if time.time() - data.get("_cache_time", 0) < DEFAULT_CACHE_TIME:
                    logger.info(f"Using cached data for AppID {app_id}")
                    return data
                else:
                    logger.info(f"Cache expired for AppID {app_id}")
            except Exception as e:
                logger.error(f"Error reading cache for AppID {app_id}: {str(e)}")
        
        # Fetch from API
        try:
            logger.info(f"Fetching app details for AppID {app_id}")
            url = f"{STORE_API_BASE}/appdetails?appids={app_id}"
            response = requests.get(url)
            response.raise_for_status()
            
            result = response.json()
            if not result or not result.get(str(app_id), {}).get("success", False):
                logger.warning(f"Failed to get app details for AppID {app_id}")
                return None
            
            # Extract and cache data
            data = result[str(app_id)]["data"]
            data["_cache_time"] = time.time()
            
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Successfully fetched and cached details for AppID {app_id}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching app details for AppID {app_id}: {str(e)}")
            return None
    
    def search_games(self, query, limit=100):
        """Search for games by name"""
        if not query:
            return []
        
        cache_key = query.lower().replace(" ", "_")[:50]
        cache_file = self.cache_dir / f"search_{cache_key}.json"
        
        # Check cache first
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                # Check if cache is still valid (1 day for searches)
                if time.time() - data.get("_cache_time", 0) < DEFAULT_CACHE_TIME:
                    logger.info(f"Using cached search results for '{query}'")
                    return data["results"]
                else:
                    logger.info(f"Cache expired for search '{query}'")
            except Exception as e:
                logger.error(f"Error reading search cache for '{query}': {str(e)}")
        
        # Fetch from API
        try:
            logger.info(f"Searching Steam for '{query}'")
            url = f"{STORE_API_BASE}/storesearch/?"
            params = {
                "term": query,
                "l": "english",
                "cc": "US",
                "category1": 998  # Games category
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            result = response.json()
            if not result or "items" not in result:
                logger.warning(f"No search results for '{query}'")
                return []
            
            # Extract and cache data
            items = result["items"][:limit]
            cache_data = {
                "_cache_time": time.time(),
                "results": items
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.info(f"Found {len(items)} results for '{query}'")
            return items
            
        except Exception as e:
            logger.error(f"Error searching for '{query}': {str(e)}")
            return []
    
    def get_player_owned_games(self, steam_id):
        """Get list of games owned by a Steam user"""
        if not self.api_key:
            logger.error("API key required for player_owned_games")
            return None
        
        try:
            logger.info(f"Fetching owned games for SteamID {steam_id}")
            url = f"{STEAM_API_BASE}/IPlayerService/GetOwnedGames/v1/"
            params = {
                "key": self.api_key,
                "steamid": steam_id,
                "include_appinfo": 1,
                "include_played_free_games": 1
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            result = response.json()
            if not result or "response" not in result:
                logger.warning(f"Failed to get owned games for SteamID {steam_id}")
                return None
            
            games = result["response"].get("games", [])
            logger.info(f"Found {len(games)} owned games for SteamID {steam_id}")
            return games
            
        except Exception as e:
            logger.error(f"Error fetching owned games for SteamID {steam_id}: {str(e)}")
            return None
    
    def get_player_summaries(self, steam_id):
        """Get player profile information"""
        if not self.api_key:
            logger.error("API key required for player_summaries")
            return None
        
        try:
            logger.info(f"Fetching player summary for SteamID {steam_id}")
            url = f"{STEAM_API_BASE}/ISteamUser/GetPlayerSummaries/v2/"
            params = {
                "key": self.api_key,
                "steamids": steam_id
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            result = response.json()
            if not result or "response" not in result:
                logger.warning(f"Failed to get player summary for SteamID {steam_id}")
                return None
            
            players = result["response"].get("players", [])
            if not players:
                logger.warning(f"No player found for SteamID {steam_id}")
                return None
            
            return players[0]
            
        except Exception as e:
            logger.error(f"Error fetching player summary for SteamID {steam_id}: {str(e)}")
            return None
    
    def get_app_list(self, force_refresh=False):
        """Get list of all Steam apps"""
        cache_file = self.cache_dir / "app_list.json"
        
        # Check cache first (valid for 7 days unless force_refresh is True)
        if not force_refresh and cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                # Check if cache is still valid
                if time.time() - data.get("_cache_time", 0) < (7 * DEFAULT_CACHE_TIME):
                    logger.info("Using cached app list")
                    return data["apps"]
                else:
                    logger.info("App list cache expired")
            except Exception as e:
                logger.error(f"Error reading app list cache: {str(e)}")
        
        # Fetch from API
        try:
            logger.info("Fetching complete app list from Steam API")
            url = f"{STEAM_API_BASE}/ISteamApps/GetAppList/v2/"
            
            response = requests.get(url)
            response.raise_for_status()
            
            result = response.json()
            if not result or "applist" not in result:
                logger.warning("Failed to get app list")
                return []
            
            apps = result["applist"]["apps"]
            
            # Cache the results
            cache_data = {
                "_cache_time": time.time(),
                "apps": apps
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.info(f"Successfully fetched list of {len(apps)} apps")
            return apps
            
        except Exception as e:
            logger.error(f"Error fetching app list: {str(e)}")
            return []
    
    def clear_cache(self, app_id=None):
        """Clear API cache"""
        if app_id:
            # Clear specific app cache
            cache_file = self.cache_dir / f"app_{app_id}.json"
            if cache_file.exists():
                try:
                    os.remove(cache_file)
                    logger.info(f"Cleared cache for AppID {app_id}")
                    return True
                except Exception as e:
                    logger.error(f"Error clearing cache for AppID {app_id}: {str(e)}")
                    return False
        else:
            # Clear all cache
            try:
                for file in self.cache_dir.glob("*.json"):
                    os.remove(file)
                logger.info("Cleared all API cache")
                return True
            except Exception as e:
                logger.error(f"Error clearing API cache: {str(e)}")
                return False

# Singleton instance
_instance = None

def get_steam_api(api_key=None):
    """Get the singleton SteamAPI instance"""
    global _instance
    if _instance is None:
        _instance = SteamAPI(api_key)
    elif api_key and _instance.api_key is None:
        _instance.api_key = api_key
    return _instance

# For direct testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Get SteamAPI instance
    api = get_steam_api()
    
    # Test app details
    print("Getting app details for CS:GO (730)...")
    app_details = api.get_app_details(730)
    if app_details:
        print(f"Name: {app_details.get('name')}")
        print(f"Type: {app_details.get('type')}")
        print(f"Description: {app_details.get('short_description')[:100]}...")
    
    # Test search
    print("\nSearching for 'half-life'...")
    search_results = api.search_games("half-life", limit=5)
    for i, game in enumerate(search_results, 1):
        print(f"{i}. {game.get('name')} (AppID: {game.get('id')})") 