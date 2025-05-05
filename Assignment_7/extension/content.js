// Process the page when it loads
async function processPage() {
    // Skip processing if the URL is sensitive
    if (isLikelySensitive(window.location.href)) {
        return;
    }
    
    try {
        const content = document.documentElement.outerHTML;
        
        // Send the page content to the backend
        await fetch('http://localhost:5000/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: window.location.href,
                content: content
            })
        });
    } catch (error) {
        console.error('Error processing page:', error);
    }
}

// Function to check if a URL is likely sensitive
function isLikelySensitive(url) {
    const sensitivePatterns = [
        /mail\./i,
        /email\./i,
        /account\./i,
        /login\./i,
        /signin\./i,
        /banking\./i,
        /secure\./i,
        /private\./i,
        /gmail\.com/i,
        /outlook\.com/i,
        /yahoo\.mail\.com/i,
        /web\.whatsapp\.com/i,
        /facebook\.com/i,
        /messenger\.com/i,
        /twitter\.com/i,
        /linkedin\.com/i,
    ];
    
    return sensitivePatterns.some(pattern => pattern.test(url));
}

// Function to highlight text on the page
function highlightText(query, confidence) {
    const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );
    
    let node;
    const highlights = [];
    
    while (node = walker.nextNode()) {
        const text = node.textContent.toLowerCase();
        if (text.includes(query.toLowerCase())) {
            const span = document.createElement('span');
            span.style.backgroundColor = `rgba(255, 255, 0, ${confidence})`;
            span.textContent = node.textContent;
            node.parentNode.replaceChild(span, node);
            highlights.push(span);
            
            // Scroll to the first highlight
            if (highlights.length === 1) {
                span.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }
        }
    }
    
    return highlights;
}

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'highlight') {
        const highlights = highlightText(request.query, request.confidence);
        sendResponse({ count: highlights.length });
    }
});

// Process the page when it loads
if (document.readyState === 'complete') {
    processPage();
} else {
    window.addEventListener('load', processPage);
} 