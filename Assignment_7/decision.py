import validators
import re

class SearchDecision:
    def __init__(self):
        # List of sensitive domains and patterns
        self.sensitive_domains = {
            'gmail.com',
            'mail.google.com',
            'outlook.com',
            'yahoo.mail.com',
            'web.whatsapp.com',
            'facebook.com',
            'messenger.com',
            'twitter.com',
            'linkedin.com',
            'banking',
            'chase.com',
            'wellsfargo.com',
            'paypal.com',
        }
        
        # Patterns for sensitive URLs
        self.sensitive_patterns = [
            r'mail\.',
            r'email\.',
            r'account\.',
            r'login\.',
            r'signin\.',
            r'banking\.',
            r'secure\.',
            r'private\.',
        ]
        
    def is_sensitive_url(self, url):
        """Determine if a URL should be considered sensitive."""
        if not validators.url(url):
            return True  # Invalid URLs are treated as sensitive
            
        # Extract domain
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower()
            
            # Check against sensitive domains
            if any(sensitive in domain for sensitive in self.sensitive_domains):
                return True
                
            # Check against sensitive patterns
            if any(re.search(pattern, domain, re.IGNORECASE) for pattern in self.sensitive_patterns):
                return True
                
            return False
            
        except Exception:
            return True  # If we can't parse the URL, treat it as sensitive
            
    def should_process_page(self, url, content_length):
        """Decide if a page should be processed based on various factors."""
        if self.is_sensitive_url(url):
            return False
            
        # Skip if content is too small or too large
        if content_length < 100 or content_length > 1000000:
            return False
            
        return True
        
    def evaluate_search_relevance(self, query, results):
        """Evaluate and filter search results for relevance."""
        relevant_results = []
        
        for result in results:
            # Increase minimum confidence threshold
            if result['confidence'] < 0.4:  # Increased from 0.2
                continue
                
            # Check if the result's semantic similarity makes sense
            if self._is_semantically_relevant(query, result):
                relevant_results.append(result)
            
        return relevant_results
        
    def _is_semantically_relevant(self, query, result):
        """Check if a result is semantically relevant to the query."""
        # If confidence is very high, consider it relevant
        if result['confidence'] > 0.8:
            return True
            
        # For medium confidence results, apply additional checks
        query_terms = set(query.lower().split())
        url_terms = set(result['url'].lower().split('/'))
        
        # Check for term overlap between query and URL
        term_overlap = query_terms.intersection(url_terms)
        if len(term_overlap) > 0:
            return True
            
        return False 