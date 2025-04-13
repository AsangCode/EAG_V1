# Structured Prompt Paint Application

This project demonstrates the use of structured prompting techniques to control a Paint application using natural language commands. The implementation follows the prompt evaluation criteria to ensure robust, step-by-step reasoning.

## Project Structure

- `paint_client.py`: Main client application that processes natural language commands
- `paint_agent.py`: Agent that controls Microsoft Paint
- `prompt_of_prompts.md`: Evaluation criteria for structured prompting
- `requirements.txt`: Project dependencies

## Structured Prompting Implementation

The project implements all criteria from the prompt evaluation framework:

1. ✅ **Explicit Reasoning Instructions**
   - Uses step-by-step reasoning for each paint operation
   - Requires explicit explanation of actions
   - Enforces structured thinking before execution

2. ✅ **Structured Output Format**
   - Uses JSON format for reasoning steps
   - Enforces specific tool call format
   - Maintains consistent output structure

3. ✅ **Separation of Reasoning and Tools**
   - Clearly separates reasoning from tool execution
   - Validates parameters before tool use
   - Maintains clean separation of concerns

4. ✅ **Conversation Loop Support**
   - Tracks Paint application state
   - Handles multi-step operations
   - Provides feedback for each action

5. ✅ **Instructional Framing**
   - Provides clear examples
   - Defines exact response format
   - Shows coordinate system rules

6. ✅ **Internal Self-Checks**
   - Validates coordinates
   - Checks parameter types
   - Verifies tool availability

7. ✅ **Reasoning Type Awareness**
   - Identifies operation types
   - Tags reasoning steps
   - Categorizes actions

8. ✅ **Error Handling**
   - Handles JSON parsing errors
   - Provides fallback options
   - Includes coordinate validation

9. ✅ **Overall Clarity**
   - Clear prompt structure
   - Consistent formatting
   - Robust execution

## Example Commands

The application supports natural language commands like:
```
"Open Microsoft Paint application"
"Draw a black rectangle starting at coordinates (200, 200) and ending at (600, 500)"
"Add the text 'Hello from Paint!' at coordinates (300, 300)"
```

## Dependencies

- Python 3.10+
- Required packages in requirements.txt
- Microsoft Paint application
- Google Gemini API key

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   - Create a .env file
   - Add your Gemini API key: `GEMINI_API_KEY=your_key_here`

3. Run the application:
   ```bash
   python paint_client.py
   ```

## Implementation Details

The project uses a structured prompt that enforces:
1. JSON-formatted reasoning steps
2. Explicit tool calls
3. Coordinate validation
4. Error handling
5. State management

Example prompt response format:
```json
{
    "problem_type": "paint_operation",
    "confidence_level": 95,
    "reasoning_steps": [
        {
            "step_number": 1,
            "reasoning": "Opening Paint application",
            "tool_needed": "open_paint",
            "parameters": "none required"
        }
    ],
    "self_verification": {
        "logic_check": "Operation validated",
        "edge_cases": ["Paint might already be open"],
        "confidence_explanation": "High confidence in operation"
    },
    "fallback_suggestions": ["Alternative approaches if needed"]
}
TOOL_CALL: open_paint
```

## Future Improvements

1. Add more paint operations
2. Implement undo/redo functionality
3. Add color selection support
4. Enhance error recovery
5. Add more complex shape drawing 