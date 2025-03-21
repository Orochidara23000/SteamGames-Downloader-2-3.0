# Steam Games Downloader

A web-based application to download Steam games using SteamCMD.

## Features

- Download games using SteamCMD
- Support for both anonymous (free games) and account-based downloads
- Queue system for multiple downloads
- Monitoring of download progress
- Easy-to-use web interface

## Deployment Options

### Local Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   python main.py
   ```

### Docker Deployment

1. Build and run using Docker Compose:
   ```
   docker-compose up -d
   ```

2. Access the application at `http://localhost:7862`

### Environment Variables

- `PORT`: Port to run the application (default: 7862)
- `LOG_LEVEL`: Logging level (default: INFO)
- `STEAM_DOWNLOAD_PATH`: Path to store downloaded games (default: /data/downloads)
- `ENABLE_SHARE`: Enable Gradio sharing feature (default: False)
- `DEBUG`: Enable debug mode (default: False)

### Cloud Deployment

#### Heroku

1. Create a new Heroku app
2. Connect your GitHub repository
3. Deploy the main branch

#### Hugging Face Spaces

1. Create a new Space on Hugging Face
2. Choose Gradio as the SDK
3. Connect your GitHub repository
4. Set the appropriate environment variables

## Requirements

- Python 3.10+
- SteamCMD (will be installed automatically in Docker)
- At least 1GB of RAM
- Sufficient disk space for game downloads