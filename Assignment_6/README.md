# Personalized AI Assistant using MCP Architecture

This project implements a personalized AI assistant using the Model Context Protocol (MCP) architecture. The system collects user preferences and provides personalized recommendations and actions based on the user's interests, location, and past interactions.

## Architecture

The system follows the MCP architecture with four main components:

1. **Perception (LLM)**: Analyzes user input and preferences using Google's Gemini Flash 2.0 model
2. **Memory**: Stores and retrieves relevant past experiences and interactions
3. **Decision-Making**: Processes perception and memory outputs to make recommendations
4. **Action**: Executes the decided actions and provides feedback

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the project root with your Google API key:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

## Usage

Run the main script:
```bash
python main.py
```

The system will:
1. Collect your preferences (name, location, interests, etc.)
2. Start an interactive loop where you can:
   - Input your current needs or questions
   - Receive personalized recommendations
   - Get actionable steps
   - Build a memory of interactions

Type 'quit' to exit the program.

## Components

- `models.py`: Pydantic models for data validation
- `perception.py`: Gemini-based analysis of user input
- `memory.py`: Experience storage and retrieval
- `decision.py`: Recommendation engine
- `action.py`: Action execution
- `main.py`: Main program flow

## Features

- Personalized recommendations based on user preferences
- Memory of past interactions
- Context-aware decision making
- Actionable outputs with next steps
- Error handling and graceful degradation 