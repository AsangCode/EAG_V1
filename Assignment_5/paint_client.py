import asyncio
from mcp.client.stdio import stdio_client
import sys
import logging
import os
from dotenv import load_dotenv
import google.generativeai as genai
from mcp import ClientSession, StdioServerParameters, types
import json

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
    """Process a natural language command using LLM with structured reasoning"""
    system_prompt = f"""You are an Expert Paint Control Assistant with advanced analytical capabilities.

CRITICAL: You MUST format your response EXACTLY as shown below, starting with the opening curly brace of the JSON:

{{
    "problem_type": "paint_operation",
    "confidence_level": 95,
    "reasoning_steps": [
        {{
            "step_number": 1,
            "reasoning": "Opening Paint application to start drawing",
            "tool_needed": "open_paint",
            "parameters": "none required"
        }}
    ],
    "self_verification": {{
        "logic_check": "Simple operation with no parameters needed",
        "edge_cases": ["Paint might already be open"],
        "confidence_explanation": "High confidence as this is a basic operation"
    }},
    "fallback_suggestions": ["Could try launching Paint manually if tool fails"]
}}

TOOL_CALL: open_paint

IMPORTANT:
- Start your response with {{ immediately
- No text before the JSON
- No explanations or comments
- Just JSON, then blank line, then TOOL_CALL

Available tools:
{tools_description}

Tool call formats:
TOOL_CALL: open_paint
TOOL_CALL: draw_rectangle|200|200|600|500
TOOL_CALL: add_text_in_paint|Hello World|300|300

Coordinate rules:
- Rectangle: (x1,y1) = top-left, (x2,y2) = bottom-right
- Text: (x,y) = start position
- Use coordinates within 0-1920 x 0-1080
- Default rectangle: 200,200,600,500
- Default text position: 300,300"""

    prompt = f"{system_prompt}\n\nCommand: {command}"
    response = await generate_with_timeout(prompt)
    response_text = response.text.strip()
    
    try:
        # Split response into parts and debug log
        logger.debug("Full response received:")
        logger.debug(response_text)
        
        # Find the tool call line from the bottom up
        lines = response_text.split('\n')
        tool_call = None
        json_lines = []
        
        # Process lines in reverse to find the last TOOL_CALL
        for line in reversed(lines):
            line = line.strip()
            if not tool_call and line.startswith("TOOL_CALL:"):
                tool_call = line
            elif tool_call:  # Once we found tool_call, add remaining lines to JSON
                if line:  # Only add non-empty lines
                    json_lines.insert(0, line)  # Insert at beginning since we're going backwards
        
        if not tool_call:
            logger.error("No tool call found in response. Full response:")
            logger.error(response_text)
            raise ValueError("No tool call found in response")
            
        logger.debug(f"Found tool call: {tool_call}")
        
        # Try to parse the JSON part
        try:
            # Clean up JSON text - ensure it starts with { and ends with }
            json_text = '\n'.join(json_lines).strip()
            if not json_text.startswith('{'):
                # Find the first { and use everything after it
                start_idx = json_text.find('{')
                if start_idx != -1:
                    json_text = json_text[start_idx:]
            if not json_text.endswith('}'):
                # Find the last } and use everything before it
                end_idx = json_text.rfind('}')
                if end_idx != -1:
                    json_text = json_text[:end_idx+1]
                    
            logger.debug("Attempting to parse JSON:")
            logger.debug(json_text)
            
            reasoning_data = json.loads(json_text)
            
            # Log the reasoning process
            logger.info(f"\nReasoning Process:")
            logger.info(f"Problem Type: {reasoning_data.get('problem_type', 'unknown')}")
            logger.info(f"Confidence: {reasoning_data.get('confidence_level', 0)}%")
            steps = reasoning_data.get('reasoning_steps', [])
            for step in steps:
                logger.info(f"Step {step.get('step_number', '?')}: {step.get('reasoning', 'unknown')}")
            verification = reasoning_data.get('self_verification', {})
            logger.info(f"Verification: {verification.get('logic_check', 'none')}")
            
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse reasoning JSON: {e}")
            logger.warning("JSON text attempted to parse:")
            logger.warning(json_text)
            logger.warning(f"Error location: line {e.lineno}, column {e.colno}")
            logger.warning(f"Error message: {e.msg}")
            logger.warning("Continuing with tool call only")
            
        # Process the tool call
        _, function_info = tool_call.split(":", 1)
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
        
    except Exception as e:
        logger.error(f"Error processing command: {e}")
        logger.error(f"Full response was:\n{response_text}")
        raise

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
                    "Draw a black rectangle starting at coordinates (200, 200) and ending at (600, 500)",
                    "Add the text 'Hello from Paint!' at coordinates (300, 300)"
                ]
                
                # Track if Paint is open
                paint_open = False
                
                for command in commands:
                    logger.info(f"\nProcessing command: {command}")
                    
                    # Skip opening Paint if it's already open
                    if "Open Microsoft Paint" in command and paint_open:
                        logger.info("Paint is already open, skipping...")
                        continue
                        
                    result = await process_command(session, command, tools_description)
                    
                    # Update Paint state
                    if "Open Microsoft Paint" in command:
                        paint_open = True
                    
                    # Add delay between commands to ensure proper tool switching
                    await asyncio.sleep(3)  # Increased delay for better reliability

    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 