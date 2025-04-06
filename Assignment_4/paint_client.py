import asyncio
from mcp.client.stdio import stdio_client
import sys
import logging
import os
from dotenv import load_dotenv
import google.generativeai as genai
from mcp import ClientSession, StdioServerParameters, types

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables and configure Gemini
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

async def generate_with_timeout(prompt, timeout=10):
    """Generate content with a timeout"""
    logger.info("Starting LLM generation...")
    try:
        loop = asyncio.get_event_loop()
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        response = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: model.generate_content(prompt)),
            timeout=timeout
        )
        logger.info("LLM generation completed")
        return response
    except Exception as e:
        logger.error(f"Error in LLM generation: {e}")
        raise

async def process_command(session, command: str, tools_description: str):
    """Process a natural language command using LLM"""
    system_prompt = f"""You are a Paint assistant that controls Microsoft Paint through commands.
Available tools:
{tools_description}

You must respond with EXACTLY ONE line in this format:
TOOL_CALL: tool_name|param1|param2|...

For example:
TOOL_CALL: open_paint
TOOL_CALL: draw_rectangle|300|200|700|500
TOOL_CALL: add_text_in_paint|Hello World|400|300

DO NOT include any explanations or additional text."""

    prompt = f"{system_prompt}\n\nCommand: {command}"
    response = await generate_with_timeout(prompt)
    response_text = response.text.strip()
    
    if response_text.startswith("TOOL_CALL:"):
        _, function_info = response_text.split(":", 1)
        parts = [p.strip() for p in function_info.split("|")]
        func_name, params = parts[0], parts[1:]
        
        # Convert parameters to appropriate types
        arguments = {}
        if func_name == "draw_rectangle":
            arguments = {
                "x1": int(params[0]),
                "y1": int(params[1]),
                "x2": int(params[2]),
                "y2": int(params[3])
            }
        elif func_name == "add_text_in_paint":
            if len(params) == 3:
                arguments = {
                    "text": params[0],
                    "x": int(params[1]),
                    "y": int(params[2])
                }
            else:
                arguments = {"text": params[0]}
        
        result = await session.call_tool(func_name, arguments=arguments)
        logger.info(result.content[0].text)
        return result

async def main():
    logger.info("Starting Paint client...")
    try:
        # Create MCP server connection
        python_path = r"C:\Users\asang\AppData\Local\Programs\Python\Python310\python.exe"
        server_params = StdioServerParameters(
            command=python_path,
            args=["paint_agent.py", "stdio"]
        )

        async with stdio_client(server_params) as (read, write):
            logger.info("Connection established, creating session...")
            async with ClientSession(read, write) as session:
                logger.info("Session created, initializing...")
                await session.initialize()
                
                # Get available tools description
                tools_result = await session.list_tools()
                tools_description = "\n".join([
                    f"{tool.name}: {tool.description}" 
                    for tool in tools_result.tools
                ])
                
                # Let the LLM handle all paint operations through natural language commands
                commands = [
                    "Open Microsoft Paint application",
                    "Draw a black rectangle in the middle of the screen, make it about 400 pixels wide and 300 pixels tall",
                    "Add the text 'Hello from Paint!' inside the rectangle we just drew"
                ]
                
                for command in commands:
                    logger.info(f"\nProcessing command: {command}")
                    await process_command(session, command, tools_description)
                    await asyncio.sleep(2)  # Wait between commands to ensure completion

    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 