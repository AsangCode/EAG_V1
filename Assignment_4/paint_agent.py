from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.prompts import base
from mcp.types import TextContent
from mcp import types
from pywinauto.application import Application
import win32gui
import win32con
import time
from win32api import GetSystemMetrics
import sys
import logging
from pywinauto.keyboard import send_keys
import google.generativeai as genai
import os
from dotenv import load_dotenv
import asyncio
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables and configure Gemini
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# Global variable to store Paint application instance
paint_app = None

# instantiate an MCP server client
mcp = FastMCP("Paint Agent")

async def get_llm_response(prompt, timeout=10):
    """Get response from LLM with timeout"""
    try:
        loop = asyncio.get_event_loop()
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        response = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: model.generate_content(prompt)),
            timeout=timeout
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error in LLM generation: {e}")
        raise

async def get_paint_actions(operation: str, **kwargs) -> dict:
    """Get Paint actions from LLM"""
    system_prompt = """You are a Paint automation expert. Your task is to convert operations into precise mouse and keyboard actions.

IMPORTANT: You must respond ONLY with a valid JSON object containing an "actions" array. No other text.

Available action types:
1. Click tool/button: {"type": "click", "x": <x>, "y": <y>, "delay": <seconds>}
2. Type text: {"type": "type", "keys": "<text>", "delay": <seconds>}
3. Mouse actions: {"type": "<press|move|release>", "x": <x>, "y": <y>, "delay": <seconds>}

Tool coordinates:
- Text tool (A): (341, 95)
- Rectangle tool: (535, 95)
- Outline button: (1207, 195)
- Black color: (755, 82)

Example valid response for "draw_rectangle":
{
    "actions": [
        {"type": "click", "x": 535, "y": 95, "delay": 1.0},
        {"type": "click", "x": 755, "y": 82, "delay": 1.0},
        {"type": "click", "x": 1207, "y": 195, "delay": 1.0},
        {"type": "press", "x": 200, "y": 200, "delay": 0.5},
        {"type": "move", "x": 600, "y": 500, "delay": 0.5},
        {"type": "release", "x": 600, "y": 500, "delay": 0.5}
    ]
}"""

    operation_prompt = f"Operation: {operation}\nParameters: {json.dumps(kwargs)}\n\nRespond with ONLY the JSON actions array:"
    
    try:
        response = await get_llm_response(f"{system_prompt}\n\n{operation_prompt}")
        
        # Try to clean up the response if it's not pure JSON
        response = response.strip()
        if not response.startswith('{'):
            # Find the first { and last }
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != 0:
                response = response[start:end]
            else:
                raise json.JSONDecodeError("No JSON object found", response, 0)
        
        actions_data = json.loads(response)
        
        # Validate the response structure
        if not isinstance(actions_data, dict) or 'actions' not in actions_data:
            raise ValueError("Response must contain 'actions' array")
        
        # Provide default actions if none returned
        if operation == "draw_rectangle":
            if not actions_data['actions']:
                actions_data['actions'] = [
                    {"type": "click", "x": 535, "y": 95, "delay": 1.0},  # Rectangle tool
                    {"type": "click", "x": 755, "y": 82, "delay": 1.0},  # Black color
                    {"type": "click", "x": 1207, "y": 195, "delay": 1.0},  # Outline button
                    {"type": "click", "x": kwargs['x1'], "y": kwargs['y1'], "delay": 0.5},  # First click to focus
                    {"type": "press", "x": kwargs['x1'], "y": kwargs['y1'], "delay": 1.0},  # Start rectangle
                    {"type": "move", "x": kwargs['x2'], "y": kwargs['y2'], "delay": 1.0},  # Drag to end
                    {"type": "release", "x": kwargs['x2'], "y": kwargs['y2'], "delay": 1.0}  # Complete rectangle
                ]
        elif operation == "add_text":
            if not actions_data['actions']:
                actions_data['actions'] = [
                    {"type": "click", "x": 341, "y": 95, "delay": 1.0},  # Text tool
                    {"type": "click", "x": kwargs['x'], "y": kwargs['y'], "delay": 1.0},  # Click position
                    {"type": "type", "keys": kwargs['text'], "delay": 1.0},  # Type text
                    {"type": "click", "x": 50, "y": 50, "delay": 0.5}  # Click away to finish
                ]
        
        return actions_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from LLM: {e}")
        # Return default actions based on operation
        if operation == "draw_rectangle":
            return {
                "actions": [
                    {"type": "click", "x": 535, "y": 95, "delay": 1.0},  # Rectangle tool
                    {"type": "click", "x": 755, "y": 82, "delay": 1.0},  # Black color
                    {"type": "click", "x": 1207, "y": 195, "delay": 1.0},  # Outline button
                    {"type": "click", "x": kwargs['x1'], "y": kwargs['y1'], "delay": 0.5},  # First click to focus
                    {"type": "press", "x": kwargs['x1'], "y": kwargs['y1'], "delay": 1.0},  # Start rectangle
                    {"type": "move", "x": kwargs['x2'], "y": kwargs['y2'], "delay": 1.0},  # Drag to end
                    {"type": "release", "x": kwargs['x2'], "y": kwargs['y2'], "delay": 1.0}  # Complete rectangle
                ]
            }
        elif operation == "add_text":
            return {
                "actions": [
                    {"type": "click", "x": 341, "y": 95, "delay": 1.0},  # Text tool
                    {"type": "click", "x": kwargs['x'], "y": kwargs['y'], "delay": 1.0},  # Click position
                    {"type": "type", "keys": kwargs['text'], "delay": 1.0},  # Type text
                    {"type": "click", "x": 50, "y": 50, "delay": 0.5}  # Click away to finish
                ]
            }
        else:
            raise

async def execute_paint_actions(actions: list) -> None:
    """Execute the sequence of Paint actions"""
    global paint_app
    if not paint_app:
        raise Exception("Paint is not open")

    paint_window = paint_app.window(class_name='MSPaintApp')
    canvas = paint_window.child_window(class_name='MSPaintView')

    for action in actions:
        try:
            if action["type"] == "click":
                paint_window.click_input(coords=(action["x"], action["y"]))
            elif action["type"] == "type":
                paint_window.type_keys(action["keys"], with_spaces=True)
            elif action["type"] == "press":
                canvas.press_mouse_input(coords=(action["x"], action["y"]))
            elif action["type"] == "move":
                canvas.move_mouse_input(coords=(action["x"], action["y"]))
            elif action["type"] == "release":
                canvas.release_mouse_input(coords=(action["x"], action["y"]))
            
            time.sleep(action.get("delay", 0.5))
        except Exception as e:
            logger.error(f"Error executing action {action}: {e}")
            raise

@mcp.tool()
async def open_paint() -> dict:
    """Open Microsoft Paint maximized"""
    logger.debug("Opening Paint...")
    global paint_app
    try:
        paint_app = Application().start('mspaint.exe')
        time.sleep(1)
        
        paint_window = paint_app.window(class_name='MSPaintApp')
        win32gui.ShowWindow(paint_window.handle, win32con.SW_MAXIMIZE)
        time.sleep(1)
        
        return {
            "content": [
                TextContent(
                    type="text",
                    text="Paint opened successfully and maximized"
                )
            ]
        }
    except Exception as e:
        logger.error(f"Error opening Paint: {str(e)}")
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Error opening Paint: {str(e)}"
                )
            ]
        }

@mcp.tool()
async def draw_rectangle(x1: int, y1: int, x2: int, y2: int) -> dict:
    """Draw a rectangle in Paint from (x1,y1) to (x2,y2)"""
    logger.debug(f"Drawing rectangle from ({x1},{y1}) to ({x2},{y2})")
    global paint_app
    try:
        if not paint_app:
            return {
                "content": [
                    TextContent(
                        type="text",
                        text="Paint is not open. Please call open_paint first."
                    )
                ]
            }
        
        # Get the Paint window
        paint_window = paint_app.window(class_name='MSPaintApp')
        
        # Ensure Paint window is active
        if not paint_window.has_focus():
            paint_window.set_focus()
            time.sleep(1)
        
        # Click the rectangle shape in the Shapes section
        paint_window.click_input(coords=(535, 95))  # Rectangle tool
        time.sleep(1)
        
        # Select black color
        paint_window.click_input(coords=(755, 82))  # Black color
        time.sleep(1)
        
        # Get the canvas area
        canvas = paint_window.child_window(class_name='MSPaintView')
        
        # Click to ensure canvas focus
        canvas.click_input(coords=(x1, y1))
        time.sleep(0.5)
        
        # Draw rectangle
        canvas.press_mouse_input(coords=(x1, y1))
        time.sleep(0.5)
        canvas.move_mouse_input(coords=(x2, y2))
        time.sleep(0.5)
        canvas.release_mouse_input(coords=(x2, y2))
        time.sleep(0.5)
        
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Rectangle drawn from ({x1},{y1}) to ({x2},{y2})"
                )
            ]
        }
    except Exception as e:
        logger.error(f"Error drawing rectangle: {str(e)}")
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Error drawing rectangle: {str(e)}"
                )
            ]
        }

@mcp.tool()
async def add_text_in_paint(text: str, x: int = 400, y: int = 300) -> dict:
    """Add text in Paint at specified coordinates"""
    try:
        # Get LLM-determined actions for adding text
        actions_data = await get_paint_actions(
            "add_text",
            text=text,
            x=x,
            y=y
        )
        
        # Execute the actions
        await execute_paint_actions(actions_data["actions"])
        
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Text '{text}' added at ({x},{y})"
                )
            ]
        }
    except Exception as e:
        logger.error(f"Error adding text: {str(e)}")
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Error adding text: {str(e)}"
                )
            ]
        }

# Set up the agent prompt
base.system_prompt = """You are a helpful Paint assistant that can control Microsoft Paint through natural language commands.
You have access to the following tools:

1. open_paint() - Opens Microsoft Paint and maximizes it
2. draw_rectangle(x1, y1, x2, y2) - Draws a rectangle from point (x1,y1) to (x2,y2)
3. add_text_in_paint(text, x=400, y=300) - Adds text at the specified coordinates

When asked to perform actions in Paint:
1. First open Paint if it's not already open
2. Then perform the requested drawing or text operations
3. Use appropriate coordinates based on the canvas size (typically 800x600)
4. Respond with clear confirmations of what was done

Remember:
- Coordinates are relative to the Paint window
- The canvas starts at (0,0) in the top-left corner
- Positive x goes right, positive y goes down
- Wait for each operation to complete before starting the next one

Example commands you can handle:
- "Open Paint and draw a rectangle"
- "Add some text to the paint window"
- "Create a rectangle with text inside it"
"""

if __name__ == "__main__":
    logger.info("Starting Paint Agent...")
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "stdio":
            logger.info("Running with stdio transport")
            mcp.run(transport="stdio")
        else:
            logger.info("Running in dev mode")
            mcp.run()
    except Exception as e:
        logger.error(f"Error running MCP server: {str(e)}")
        raise 