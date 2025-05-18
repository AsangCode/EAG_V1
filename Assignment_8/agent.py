# agent.py

import asyncio
import yaml
import os
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import aiohttp
from core.loop import AgentLoop
from core.session import MultiMCP
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING,  # Changed to WARNING to reduce output
    handlers=[
        logging.FileHandler('agent.log'),  # Log to file
        logging.StreamHandler()  # Log to console
    ]
)
logger = logging.getLogger(__name__)

# Set specific loggers to higher levels to reduce noise
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('gspread').setLevel(logging.WARNING)

def log(stage: str, msg: str, console_only: bool = False):
    """Simple timestamped console logger."""
    now = datetime.now().strftime("%H:%M:%S")
    if console_only:
        print(f"[{now}] [{stage}] {msg}")
    else:
        logger.info(f"[{stage}] {msg}")

class AgentManager:
    def __init__(self):
        self.multi_mcp = None
        self.telegram_app = None
        
    async def initialize(self):
        """Initialize MCP servers."""
        # Load MCP server configs from profiles.yaml
        with open("config/profiles.yaml", "r") as f:
            profile = yaml.safe_load(f)
            mcp_servers = profile.get("mcp_servers", [])

        self.multi_mcp = MultiMCP(server_configs=mcp_servers)
        await self.multi_mcp.initialize()

    async def fetch_f1_standings(self) -> str:
        """Fetch F1 standings and create a Google Sheet."""
        try:
            logger.debug("Starting F1 standings fetch")
            # Fetch F1 standings from Ergast API
            async with aiohttp.ClientSession() as session:
                logger.debug("Fetching from Ergast API")
                async with session.get('http://ergast.com/api/f1/current/driverStandings.json') as response:
                    if response.status != 200:
                        raise ValueError(f"Failed to fetch F1 data: HTTP {response.status}")
                    data = await response.json()
                    logger.debug("Received data from Ergast API")
                    
            standings = data['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']
            
            # Convert to DataFrame
            standings_data = []
            for pos in standings:
                standings_data.append({
                    'Position': pos['position'],
                    'Driver': f"{pos['Driver']['givenName']} {pos['Driver']['familyName']}",
                    'Points': pos['points'],
                    'Wins': pos['wins'],
                    'Constructor': pos['Constructors'][0]['name']
                })
            
            df = pd.DataFrame(standings_data)
            logger.debug("Created DataFrame with standings")
            
            # Initialize Google Sheets API
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            
            credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH')
            if not credentials_file or not Path(credentials_file).is_file():
                raise FileNotFoundError(f"Google Sheets credentials file not found: {credentials_file}")
                
            logger.debug(f"Using credentials file: {credentials_file}")
            
            try:
                credentials = ServiceAccountCredentials.from_json_keyfile_name(
                    credentials_file, scope)
                gc = gspread.authorize(credentials)
                logger.debug("Authorized with Google Sheets")
            except Exception as e:
                raise ValueError(f"Failed to authenticate with Google Sheets: {str(e)}")
            
            # Create new sheet
            sheet_title = f"F1 Standings {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            try:
                spreadsheet = gc.create(sheet_title)
                logger.debug(f"Created new sheet: {sheet_title}")
            except Exception as e:
                raise ValueError(f"Failed to create spreadsheet: {str(e)}")
            
            # Share the spreadsheet with anyone with the link
            try:
                spreadsheet.share('', perm_type='anyone', role='reader')
                logger.debug("Shared spreadsheet with public access")
            except Exception as e:
                raise ValueError(f"Failed to share spreadsheet: {str(e)}")
            
            # Get the first worksheet
            worksheet = spreadsheet.get_worksheet(0)
            
            # Update the worksheet with the DataFrame
            try:
                worksheet.update([df.columns.values.tolist()] + df.values.tolist())
                logger.debug("Updated worksheet with data")
            except Exception as e:
                raise ValueError(f"Failed to update spreadsheet data: {str(e)}")
            
            return spreadsheet.url
            
        except Exception as e:
            logger.error(f"Error creating spreadsheet: {e}", exc_info=True)
            raise
        
    async def process_query(self, query: str, telegram_update: Optional[Update] = None) -> str:
        """Process a query through the agent loop."""
        if not self.multi_mcp:
            await self.initialize()

        # Check if this is an F1 standings request
        if "f1" in query.lower() and "stand" in query.lower():
            try:
                if telegram_update:
                    await telegram_update.message.reply_text("Fetching F1 standings and creating spreadsheet...")
                
                sheet_url = await self.fetch_f1_standings()
                response = f"Here's your F1 standings spreadsheet: {sheet_url}"
                
                if telegram_update:
                    await telegram_update.message.reply_text(response)
                
                return response
            except Exception as e:
                error_msg = f"Failed to fetch F1 standings: {str(e)}"
                if telegram_update:
                    await telegram_update.message.reply_text(error_msg)
                raise ValueError(error_msg)
            
        # For all other queries, use the regular agent loop
        agent = AgentLoop(
            user_input=query,
            dispatcher=self.multi_mcp
        )

        try:
            final_response = await agent.run()
            clean_response = final_response.replace("FINAL_ANSWER:", "").strip()
            
            if telegram_update:
                await telegram_update.message.reply_text(clean_response)
            
            return clean_response
        except Exception as e:
            error_msg = f"Agent failed: {e}"
            log("fatal", error_msg)
            if telegram_update:
                await telegram_update.message.reply_text(f"Sorry, an error occurred: {str(e)}")
            raise

    async def handle_telegram_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "Hello! I'm your AI Agent. Send me any query and I'll help you process it!"
        )

    async def handle_telegram_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming Telegram messages."""
        query = update.message.text
        logger.info(f"Received Telegram query: {query}")
        
        # Send typing action
        await update.message.chat.send_action(action="typing")
        
        try:
            await self.process_query(query, update)
        except Exception as e:
            logger.error(f"Error processing Telegram query: {e}", exc_info=True)
            await update.message.reply_text(
                "Sorry, I encountered an error while processing your request. Please try again."
            )

    async def setup_telegram(self):
        """Set up and start the Telegram bot."""
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            logger.warning("No Telegram token found, skipping Telegram bot setup")
            return

        try:
            # Get proxy settings from environment variables
            proxy_url = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')
            
            # Create request object with proxy if available
            if proxy_url:
                print(f"\nUsing proxy: {proxy_url}")
                request = HTTPXRequest(
                    connection_pool_size=8,
                    read_timeout=30.0,
                    write_timeout=30.0,
                    connect_timeout=30.0,
                    proxy=proxy_url
                )
            else:
                request = HTTPXRequest(
                    connection_pool_size=8,
                    read_timeout=30.0,
                    write_timeout=30.0,
                    connect_timeout=30.0
                )

            # Create application with custom request object
            self.telegram_app = (
                Application.builder()
                .token(token)
                .request(request)
                .build()
            )

            # Add handlers
            self.telegram_app.add_handler(CommandHandler("start", self.handle_telegram_start))
            self.telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_telegram_message))

            # Start the bot
            await self.telegram_app.initialize()
            await self.telegram_app.start()
            await self.telegram_app.updater.start_polling()
            
            logger.info("Telegram bot started successfully")
            
        except Exception as e:
            error_msg = str(e)
            if "ConnectError" in error_msg:
                print("\n❌ Error: Cannot connect to Telegram API.")
                print("This could be due to:")
                print("1. No internet connection")
                print("2. Proxy/firewall blocking the connection")
                print("\nTo fix this:")
                print("1. Check your internet connection")
                print("2. If you're behind a proxy, set the HTTP_PROXY or HTTPS_PROXY environment variable:")
                print("   Example: set HTTPS_PROXY=http://your-proxy:port")
                print("\nPress Enter to continue in console mode...")
                input()
                return False
            else:
                logger.error(f"Failed to start Telegram bot: {e}", exc_info=True)
                raise
            
        return True

async def console_mode(agent_manager: AgentManager):
    """Run the agent in console mode."""
    log("system", "🧠 Cortex-R Agent Ready", console_only=True)
    while True:
        try:
            user_input = input("🧑 What do you want to solve today? → ")
            if user_input.lower() in ['exit', 'quit']:
                break
                
            response = await agent_manager.process_query(user_input)
            print("\n💡 Final Answer:\n", response)
        except Exception as e:
            print(f"Error: {e}")

async def main():
    """Main function that handles both console and Telegram modes."""
    agent_manager = AgentManager()
    
    # Initialize the agent manager
    await agent_manager.initialize()
    
    # Ask user for preferred mode
    print("\n=== S8 Share Agent ===")
    print("1. Console Mode")
    print("2. Telegram Mode")
    
    while True:
        mode = input("\nSelect mode (1 or 2): ").strip()
        if mode in ['1', '2']:
            break
        print("Invalid selection. Please enter 1 or 2.")
    
    if mode == '2':
        # Check if Telegram token is available
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            print("\n❌ Error: TELEGRAM_BOT_TOKEN not found in environment variables.")
            print("Please set up your Telegram bot token first:")
            print("1. Create a bot with @BotFather on Telegram")
            print("2. Copy the token")
            print("3. Set the environment variable:")
            print("   set TELEGRAM_BOT_TOKEN=your-token-here")
            print("\nPress Enter to continue in console mode...")
            input()
            await console_mode(agent_manager)
            return
            
        try:
            print("\nStarting Telegram bot...")
            success = await agent_manager.setup_telegram()
            
            if success:
                print("\n✅ Telegram bot is now running!")
                print("🔍 Please open your Telegram app and search for your bot")
                print("💡 Type /start in the chat to begin")
                print("\nPress Ctrl+C to stop the bot")
                
                # Keep the bot running until interrupted
                while True:
                    await asyncio.sleep(1)
            else:
                # If Telegram setup failed, fall back to console mode
                await console_mode(agent_manager)
                
        except KeyboardInterrupt:
            print("\n👋 Shutting down Telegram bot...")
            if agent_manager.telegram_app:
                await agent_manager.telegram_app.stop()
            print("Goodbye!")
            
    else:
        # Run console mode
        await console_mode(agent_manager)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("system", "👋 Goodbye!", console_only=True)
    except Exception as e:
        log("fatal", f"Application failed: {e}")
        raise


# Find the ASCII values of characters in INDIA and then return sum of exponentials of those values.
# How much Anmol singh paid for his DLF apartment via Capbridge? 
# What do you know about Don Tapscott and Anthony Williams?
# What is the relationship between Gensol and Go-Auto?
# which course are we teaching on Canvas LMS?
# Summarize this page: https://theschoolof.ai/
# What is the log value of the amount that Anmol singh paid for his DLF apartment via Capbridge? 