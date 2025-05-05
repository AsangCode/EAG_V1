document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    const searchResults = document.getElementById('searchResults');
    
    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    async function performSearch() {
        const query = searchInput.value.trim();
        if (!query) return;
        
        searchButton.disabled = true;
        searchResults.innerHTML = '<div class="result-item">Searching...</div>';
        
        try {
            const response = await fetch('http://localhost:5000/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: query })
            });
            
            const results = await response.json();
            displayResults(results);
            
        } catch (error) {
            searchResults.innerHTML = `
                <div class="result-item" style="color: red;">
                    Error: Make sure the Python backend is running on port 5000
                </div>
            `;
        } finally {
            searchButton.disabled = false;
        }
    }
    
    function displayResults(results) {
        if (!results.length) {
            searchResults.innerHTML = '<div class="result-item">No results found</div>';
            return;
        }
        
        searchResults.innerHTML = results.map(result => `
            <div class="result-item" data-url="${result.url}" data-confidence="${result.confidence}">
                <a href="#" class="url">${result.url}</a>
                <div class="confidence">Confidence: ${(result.confidence * 100).toFixed(1)}%</div>
            </div>
        `).join('');
        
        // Add click handlers for results
        document.querySelectorAll('.result-item').forEach(item => {
            item.addEventListener('click', async function() {
                const url = this.dataset.url;
                const confidence = this.dataset.confidence;
                
                // Open the URL in a new tab
                const tab = await chrome.tabs.create({ url: url });
                
                // Wait for the tab to load and then highlight content
                chrome.tabs.onUpdated.addListener(function listener(tabId, info) {
                    if (tabId === tab.id && info.status === 'complete') {
                        chrome.tabs.onUpdated.removeListener(listener);
                        
                        // Send message to content script to highlight content
                        chrome.tabs.sendMessage(tab.id, {
                            action: 'highlight',
                            query: searchInput.value,
                            confidence: confidence
                        });
                    }
                });
            });
        });
    }
}); 