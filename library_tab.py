"""
Library Tab for Steam Games Downloader
"""

import logging
import gradio as gr
import pandas as pd

# Import local modules
from config import get_config
from library_manager import get_library_manager

# Configure logger
logger = logging.getLogger(__name__)

class LibraryTab:
    """Library Tab for Steam Games Downloader"""
    
    def __init__(self):
        """Initialize the library tab"""
        logger.info("Initializing Library Tab")
        self.config = get_config()
        self.library_manager = get_library_manager()
    
    def create_tab(self):
        """Create the library tab UI"""
        with gr.Column():
            gr.Markdown("## Game Library")
            gr.Markdown("This is a minimal implementation of the library tab.")
            
            library_status = gr.Markdown(
                "The library functionality will be available in the full version."
            )
            
            refresh_btn = gr.Button("Refresh Library")
            
            def refresh_library():
                try:
                    # This is a placeholder - in the full version, it would scan the library
                    return "Library scan is not implemented in the minimal UI."
                except Exception as e:
                    logger.error(f"Error refreshing library: {str(e)}")
                    return f"Error: {str(e)}"
            
            refresh_btn.click(refresh_library, inputs=[], outputs=[library_status])
            
            # Library table
            library_table = gr.Dataframe(
                headers=["Name", "AppID", "Location", "Size", "Last Played"],
                row_count=10,
                interactive=False,
                wrap=True
            )
            
            # Selected game details
            with gr.Row():
                with gr.Column(scale=2):
                    selected_game_info = gr.Markdown("Select a game to view details")
                
                with gr.Column(scale=1):
                    verify_button = gr.Button("Verify Game Files")
                    uninstall_button = gr.Button("Uninstall Game", variant="stop")
                    
                    operation_status = gr.Markdown("Select a game and an operation")
            
            # Connect components
            refresh_btn.click(
                fn=self.refresh_library,
                outputs=[library_table]
            )
            
            library_table.select(
                fn=self.show_game_details,
                outputs=[selected_game_info]
            )
            
            verify_button.click(
                fn=self.verify_game_files,
                inputs=[library_table],
                outputs=[operation_status]
            )
            
            uninstall_button.click(
                fn=self.uninstall_game,
                inputs=[library_table],
                outputs=[operation_status, library_table]
            )
            
            # Initial load
            library_df = self.library_manager.get_installed_games_dataframe()
            library_table.update(value=library_df)
        
        return
    
    def refresh_library(self):
        """Refresh the game library"""
        try:
            self.library_manager.refresh_library()
            library_df = self.library_manager.get_installed_games_dataframe()
            return library_df
        except Exception as e:
            logger.error(f"Error refreshing library: {str(e)}")
            # Return empty DataFrame with correct structure
            return pd.DataFrame(columns=["Name", "AppID", "Location", "Size", "Last Played"])
    
    def show_game_details(self, table_row):
        """Show details for selected game"""
        try:
            if table_row is None or table_row.empty or len(table_row.index) == 0:
                return "No game selected"
            
            # Get selected game data
            row_data = table_row.iloc[0]
            game_name = row_data["Name"]
            appid = row_data["AppID"]
            location = row_data["Location"]
            size = row_data["Size"]
            last_played = row_data["Last Played"]
            
            # Format details
            details_html = f"""
            ## {game_name}
            
            **AppID:** {appid}
            
            **Install Location:** {location}
            
            **Size:** {size}
            
            **Last Played:** {last_played}
            """
            
            return details_html
            
        except Exception as e:
            logger.error(f"Error showing game details: {str(e)}")
            return f"Error showing game details: {str(e)}"
    
    def verify_game_files(self, table_row):
        """Verify game files for selected game"""
        try:
            if table_row is None or table_row.empty or len(table_row.index) == 0:
                return "No game selected"
            
            # Get selected game data
            row_data = table_row.iloc[0]
            game_name = row_data["Name"]
            appid = row_data["AppID"]
            
            # Verify game files
            success, message = self.library_manager.verify_game(appid)
            
            if success:
                return f"✅ {message} for {game_name} (AppID: {appid})"
            else:
                return f"❌ {message} for {game_name} (AppID: {appid})"
            
        except Exception as e:
            logger.error(f"Error verifying game files: {str(e)}")
            return f"Error verifying game files: {str(e)}"
    
    def uninstall_game(self, table_row):
        """Uninstall selected game"""
        try:
            if table_row is None or table_row.empty or len(table_row.index) == 0:
                return "No game selected", None
            
            # Get selected game data
            row_data = table_row.iloc[0]
            game_name = row_data["Name"]
            appid = row_data["AppID"]
            
            # Uninstall game
            success, message = self.library_manager.uninstall_game(appid)
            
            # Refresh library after uninstallation
            library_df = self.refresh_library()
            
            if success:
                return f"✅ {message} for {game_name} (AppID: {appid})", library_df
            else:
                return f"❌ {message} for {game_name} (AppID: {appid})", library_df
            
        except Exception as e:
            logger.error(f"Error uninstalling game: {str(e)}")
            return f"Error uninstalling game: {str(e)}", None

# Singleton instance
_instance = None

def get_library_tab():
    """Get the singleton library tab instance"""
    global _instance
    if _instance is None:
        _instance = LibraryTab()
    return _instance

# For testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create tab
    library_tab = get_library_tab()
    
    # Create interface
    with gr.Blocks() as interface:
        library_tab.create_tab()
    
    # Launch interface
    interface.launch(server_name="0.0.0.0", server_port=7860) 