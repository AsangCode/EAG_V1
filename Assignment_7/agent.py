import os
from flask import Flask, request, jsonify
from perception import WebPagePerception
from memory import FaissMemory
from action import SearchAction
from decision import SearchDecision
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables at startup
load_dotenv()

# Verify API key is present
if not os.getenv('GOOGLE_API_KEY'):
    raise ValueError("GOOGLE_API_KEY not found in .env file. Please add it to continue.")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/')
def health_check():
    """Root endpoint for health checks."""
    return jsonify({"status": "ok"})

class Agent:
    def __init__(self):
        self.perception = WebPagePerception()
        self.memory = FaissMemory()
        self.action = SearchAction()
        self.decision = SearchDecision()
        
    def process_page(self, url, content):
        """Process a new web page."""
        # Skip sensitive URLs
        if self.decision.is_sensitive_url(url):
            return {"status": "skipped", "reason": "sensitive url"}
            
        # Extract and process content
        processed_content = self.perception.process_content(content)
        
        # Generate embedding and store in FAISS
        embedding = self.perception.generate_embedding(processed_content)
        self.memory.add_to_index(url, embedding)
        
        return {"status": "success"}
        
    def search(self, query):
        """Perform semantic search."""
        # Generate query embedding
        query_embedding = self.perception.generate_embedding(query)
        
        # Search in FAISS index with both embedding and original query
        results = self.memory.search(query_embedding, query)
        
        # Process and format results
        processed_results = self.action.process_search_results(results)
        
        return processed_results

agent = Agent()

@app.route('/process', methods=['POST'])
def process_page():
    data = request.json
    url = data.get('url')
    content = data.get('content')
    
    if not url or not content:
        return jsonify({"error": "Missing url or content"}), 400
        
    result = agent.process_page(url, content)
    return jsonify(result)

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    query = data.get('query')
    
    if not query:
        return jsonify({"error": "Missing query"}), 400
        
    results = agent.search(query)
    return jsonify(results)

if __name__ == '__main__':
    app.run(port=5000) 