import os
import json
import asyncio
import logging
import socket
from datetime import datetime
from typing import List, Dict
from pathlib import Path

import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
import aiohttp
import httpx
from dotenv import load_dotenv
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

def check_credentials():
    """Check if all required credentials are present."""
    missing = []
    
    # Check Telegram token
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        missing.append('TELEGRAM_BOT_TOKEN')
    
    # Check Google Sheets credentials
    creds_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH')
    if not creds_file or not Path(creds_file).is_file():
        missing.append('Google Sheets credentials file (GOOGLE_SHEETS_CREDENTIALS_PATH)')
    
    return missing

def find_available_port(start_port: int = 8000, max_port: int = 9000) -> int:
    """Find an available port in the given range."""
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(('0.0.0.0', port))
                return port
            except OSError:
                continue
    raise RuntimeError("No available ports found")

# Load environment variables
load_dotenv()

# Check credentials before starting
missing_creds = check_credentials()
if missing_creds:
    raise ValueError(f"Missing required credentials: {', '.join(missing_creds)}")

# Configure logging with DEBUG level
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI()

# Initialize Telegram bot with custom connection pool settings and timeout
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
logger.debug(f"Bot token found: {'Yes' if TELEGRAM_TOKEN else 'No'}")

# Proxy settings (if needed)
PROXY_URL = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')
if PROXY_URL:
    logger.debug(f"Using proxy: {PROXY_URL}")

# Store connected clients for SSE
CONNECTIONS: List[asyncio.Queue] = []

# Global variable to store the Telegram application
telegram_app = None

async def create_telegram_application():
    """Create and configure the Telegram application with proper settings."""
    # Configure proxy if available
    proxy_url = PROXY_URL
    if proxy_url:
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

    # Create application with custom settings
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .request(request)
        .build()
    )
    
    return application

async def f1_standings_to_sheet() -> str:
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
        return f"Error: {str(e)}"

async def broadcast_event(event_data: Dict):
    """Broadcast event to all connected clients."""
    logger.debug(f"Broadcasting event: {event_data}")
    for queue in CONNECTIONS:
        await queue.put(event_data)

@app.get('/events')
async def events(request: Request):
    """SSE endpoint for real-time updates."""
    logger.debug("New SSE connection established")
    queue = asyncio.Queue()
    CONNECTIONS.append(queue)
    
    async def event_generator():
        try:
            while True:
                event_data = await queue.get()
                logger.debug(f"Sending event: {event_data}")
                yield {
                    "event": "update",
                    "data": json.dumps(event_data)
                }
        except asyncio.CancelledError:
            logger.debug("SSE connection closed")
            CONNECTIONS.remove(queue)
    
    return EventSourceResponse(event_generator())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    logger.debug(f"Received /start command from user {update.effective_user.id}")
    await update.message.reply_text(
        "Hello! I'm your F1 Stats Bot. Send me a message to get F1 standings in a spreadsheet!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages."""
    logger.debug(f"Received message: {update.message.text} from user {update.effective_user.id}")
    
    if "standings" in update.message.text.lower():
        logger.debug("Processing standings request")
        await update.message.reply_text("Fetching F1 standings and creating spreadsheet...")
        
        # Broadcast event to SSE clients
        await broadcast_event({
            "type": "request",
            "message": "Fetching F1 standings",
            "timestamp": datetime.now().isoformat()
        })
        
        # Get standings and create sheet
        sheet_url = await f1_standings_to_sheet()
        logger.debug(f"Got sheet URL: {sheet_url}")
        
        if sheet_url.startswith("Error"):
            logger.error(f"Error in standings request: {sheet_url}")
            await update.message.reply_text(f"Sorry, there was an error: {sheet_url}")
        else:
            await update.message.reply_text(f"Here's your F1 standings spreadsheet: {sheet_url}")
        
        # Broadcast completion event
        await broadcast_event({
            "type": "completion",
            "message": "F1 standings spreadsheet created",
            "timestamp": datetime.now().isoformat()
        })
    else:
        await update.message.reply_text(
            "Send me a message containing 'standings' to get the current F1 standings!"
        )

@app.on_event("startup")
async def startup_event():
    """Start the Telegram bot when the FastAPI server starts."""
    global telegram_app
    logger.debug("FastAPI server starting")
    
    try:
        # Create and initialize the Telegram application
        telegram_app = await create_telegram_application()
        
        # Add handlers
        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Initialize the application
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling()
        
        logger.info("Telegram bot started successfully")
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
        if isinstance(e, httpx.ConnectError):
            logger.error("Connection error. This might be due to network restrictions or proxy requirements.")
            logger.error("Try setting HTTPS_PROXY or HTTP_PROXY environment variables if you're behind a proxy.")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the Telegram bot when the FastAPI server stops."""
    global telegram_app
    if telegram_app:
        logger.debug("Stopping Telegram bot")
        await telegram_app.stop()
        await telegram_app.updater.stop()
        logger.info("Telegram bot stopped successfully")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server")
    try:
        port = find_available_port(start_port=8090, max_port=9000)
        logger.info(f"Found available port: {port}")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="debug")
    except RuntimeError as e:
        logger.error(f"Failed to find available port: {e}")
        raise 