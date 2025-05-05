import os
import google.generativeai as genai
from bs4 import BeautifulSoup
import numpy as np
from dotenv import load_dotenv
import re

class WebPagePerception:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize Gemini with API key from .env
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in .env file")
            
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')  # Using pro model for better embeddings
        
    def process_content(self, html_content):
        """Extract and clean text content from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script, style, and nav elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
            
        # Get text and clean it
        text = soup.get_text()
        
        # Clean the text while preserving sentence structure and special characters
        lines = (line.strip() for line in text.splitlines())
        text = ' '.join(line for line in lines if line)
        
        # Remove URLs but keep important punctuation and structure
        text = re.sub(r'http[s]?://\S+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Get the most relevant content (first 2000 chars to fit Gemini's context window)
        return text[:2000]
        
    def generate_embedding(self, text):
        """Generate embedding using Gemini."""
        try:
            # Create a focused semantic representation prompt
            prompt = f"""
            Analyze this text and create a semantic representation focusing on:
            1. Core topic and main ideas
            2. Key entities (people, places, organizations)
            3. Important facts and relationships
            4. Domain-specific terminology
            
            Text: {text}
            
            Provide a concise semantic summary that captures the essence of the content.
            """
            
            # Get embedding from Gemini
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.1,  # Slight randomness for better semantic coverage
                    'candidate_count': 1,
                    'max_output_tokens': 256,  # Shorter, more focused output
                }
            )
            
            if not response.text:
                return np.zeros(64, dtype='float32')
            
            # Convert response text to numerical embedding using a simple but effective method
            words = response.text.lower().split()
            # Use word positions as weights
            weighted_sum = np.zeros(64, dtype='float32')
            for i, word in enumerate(words[:64]):  # Use up to 64 words
                # Create a position-weighted hash for each word
                word_hash = np.array([hash(word + str(j)) % 100 for j in range(64)], dtype='float32')
                position_weight = 1.0 / (i + 1)  # Words earlier in the response have more weight
                weighted_sum += word_hash * position_weight
            
            # Normalize to unit length
            norm = np.linalg.norm(weighted_sum)
            if norm > 0:
                weighted_sum = weighted_sum / norm
            
            return weighted_sum
            
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return np.zeros(64, dtype='float32') 