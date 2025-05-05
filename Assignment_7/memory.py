import faiss
import numpy as np
import os
import json

class FaissMemory:
    def __init__(self):
        self.dimension = 64  # Reduced dimension for better performance
        self.index = faiss.IndexFlatL2(self.dimension)
        self.urls = []
        self.index_file = "faiss_index.bin"
        self.urls_file = "urls.json"
        self.load_index()
        
    def load_index(self):
        """Load existing index and URLs if they exist."""
        try:
            if os.path.exists(self.index_file):
                self.index = faiss.read_index(self.index_file)
            if os.path.exists(self.urls_file):
                with open(self.urls_file, 'r') as f:
                    self.urls = json.load(f)
        except Exception as e:
            print(f"Error loading index: {e}")
            
    def save_index(self):
        """Save index and URLs to disk."""
        try:
            faiss.write_index(self.index, self.index_file)
            with open(self.urls_file, 'w') as f:
                json.dump(self.urls, f)
        except Exception as e:
            print(f"Error saving index: {e}")
            
    def add_to_index(self, url, embedding):
        """Add a new embedding and URL to the index."""
        # Ensure embedding has correct dimension
        if len(embedding) != self.dimension:
            # Resize embedding to match index dimension
            if len(embedding) > self.dimension:
                embedding = embedding[:self.dimension]
            else:
                embedding = np.pad(embedding, (0, self.dimension - len(embedding)))
                
        # Reshape and ensure correct type
        embedding = embedding.reshape(1, -1).astype(np.float32)
        
        # Add to FAISS index
        self.index.add(embedding)
        
        # Store URL
        self.urls.append(url)
        
        # Save to disk
        self.save_index()
        
    def search(self, query_embedding, query_text, k=5):
        """Search for similar embeddings."""
        if self.index.ntotal == 0:
            return []
            
        # Ensure query embedding has correct dimension
        if len(query_embedding) != self.dimension:
            if len(query_embedding) > self.dimension:
                query_embedding = query_embedding[:self.dimension]
            else:
                query_embedding = np.pad(query_embedding, (0, self.dimension - len(query_embedding)))
                
        # Reshape and ensure correct type
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)
            
        # Perform search
        distances, indices = self.index.search(
            query_embedding, 
            min(k, self.index.ntotal)
        )
        
        # Format results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.urls):  # Safety check
                results.append({
                    'url': self.urls[idx],
                    'distance': float(distances[0][i]),
                    'query': query_text  # Add the query text for term matching
                })
                
        return results 