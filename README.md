# Steam Games Downloader

A user-friendly interface for downloading Steam games using SteamCMD.

## Features

- Download Steam games using a simple interface
- Check game information from Steam URLs or IDs
- Manage your local game library
- Configure SteamCMD settings
- Works in containerized environments

## Project Structure

The project has been refactored into a modular structure for better maintainability:

```
SteamGames-Downloader/
├── main.py             # Main application entry point
├── modules/            # Core functionality modules
│   ├── download_manager.py     # Manages download queue and processes
│   ├── library_manager.py      # Manages the game library
│   ├── steam_api.py            # Steam API integration
│   └── steamcmd_manager.py     # SteamCMD interaction
├── ui/                 # User interface components
│   ├── download_tab.py         # UI for downloading games
│   ├── library_tab.py          # UI for managing game library
│   ├── main_ui.py              # Main UI that combines all tabs
│   └── settings_tab.py         # UI for configuring settings
└── utils/              # Utility functions and helpers
    └── config.py               # Configuration management
```

## Installation

1. Clone the repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python main.py
   ```

## Docker Deployment

The application can be deployed in a Docker container:

```bash
docker build -t steam-games-downloader .
docker run -p 7860:7860 -v /path/to/downloads:/downloads steam-games-downloader
```

## License

MIT License

## Note

This application is in demo mode if SteamCMD is not installed. In demo mode, downloads are simulated for demonstration purposes. To enable actual downloads, make sure SteamCMD is installed and properly configured in the Settings tab.