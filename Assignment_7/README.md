# Web Page Semantic Search Chrome Extension

This Chrome extension builds semantic embeddings for web pages you visit and enables semantic search across your browsing history. It uses Google's Gemini Flash 2.0 for embeddings and FAISS for efficient similarity search.

## Features
- Automatically creates embeddings for visited web pages (excluding sensitive sites)
- Builds and maintains a FAISS index for fast semantic search
- Highlights relevant content when searching
- Uses MCP (Monitor-Control-Plan) protocol for robust system architecture

## Components
- Chrome Extension: Frontend interface and page monitoring
- Python Backend:
  - AGENT: Main coordinator
  - PERCEPTION: Web page content processing
  - MEMORY: FAISS index management
  - ACTION: Search execution and highlighting
  - DECISION: Search relevance and execution planning

## Setup
1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the root directory with your Google Gemini API key:
```bash
# Create .env file
echo "GOOGLE_API_KEY=your_gemini_api_key_here" > .env
```
Replace `your_gemini_api_key_here` with your actual API key from https://makersuite.google.com/app/apikey

3. Load the Chrome extension:
   - Open Chrome
   - Go to chrome://extensions/
   - Enable Developer Mode
   - Click "Load unpacked"
   - Select the `extension` folder

4. Start the Python backend:
```bash
python agent.py
```

## Architecture
The system follows the MCP (Monitor-Control-Plan) protocol:
- Monitor: Observes web page visits and user searches
- Control: Manages the flow of data and operations
- Plan: Determines search relevance and execution strategy

## Security Note
- The `.env` file containing your API key is automatically ignored by git
- Never commit your actual API key to version control
- Keep your API key secure and don't share it with others 