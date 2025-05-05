class SearchAction:
    def __init__(self):
        self.min_confidence_threshold = 0.4  # Minimum confidence to consider a result
        self.semantic_weight = 0.7  # Weight for semantic similarity
        self.term_weight = 0.3  # Weight for term matching
        
    def process_search_results(self, results):
        """Process and format search results."""
        processed_results = []
        
        if not results:
            return processed_results
            
        # Calculate absolute confidence scores
        for result in results:
            # Convert L2 distance to similarity score (closer to 1 means more similar)
            semantic_similarity = 1.0 / (1.0 + result['distance'])
            
            # Calculate term match score
            query_terms = set(result['query'].lower().split())
            url_terms = set(result['url'].lower().replace('-', ' ').replace('_', ' ').split('/'))
            url_terms.update(result['url'].lower().replace('-', ' ').replace('_', ' ').split())
            
            # Calculate exact and partial matches
            exact_matches = sum(1 for term in query_terms if any(term == url_term for url_term in url_terms))
            partial_matches = sum(1 for term in query_terms if any(term in url_term for url_term in url_terms))
            
            # Weight exact matches more heavily
            term_match_score = (exact_matches + 0.5 * partial_matches) / len(query_terms) if query_terms else 0
            
            # Calculate final confidence score
            confidence = (semantic_similarity * self.semantic_weight) + (term_match_score * self.term_weight)
            
            # Ensure confidence is in [0, 1] range
            confidence = max(0.0, min(1.0, confidence))
            
            # Only include results above minimum threshold
            if confidence >= self.min_confidence_threshold:
                processed_results.append({
                    'url': result['url'],
                    'confidence': round(confidence, 3),
                    'semantic_score': round(semantic_similarity, 3),
                    'term_score': round(term_match_score, 3),
                    'highlight_instructions': {
                        'method': 'semantic_highlight',
                        'confidence_threshold': confidence
                    }
                })
            
        # Sort by confidence
        processed_results.sort(key=lambda x: x['confidence'], reverse=True)
        
        return processed_results
        
    def generate_highlight_script(self, query, confidence_threshold=0.5):
        """Generate JavaScript code for highlighting matching content."""
        return {
            'script': """
                function highlightText(query, threshold) {
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    
                    let node;
                    while (node = walker.nextNode()) {
                        const text = node.textContent.toLowerCase();
                        if (text.includes(query.toLowerCase())) {
                            const span = document.createElement('span');
                            span.style.backgroundColor = `rgba(255, 255, 0, ${threshold})`;
                            span.textContent = node.textContent;
                            node.parentNode.replaceChild(span, node);
                        }
                    }
                }
            """,
            'params': {
                'query': query,
                'threshold': confidence_threshold
            }
        } 