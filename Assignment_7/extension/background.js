// Listen for installation
chrome.runtime.onInstalled.addListener(() => {
    console.log('Extension installed');
});

// Function to check backend status
async function checkBackendStatus() {
    try {
        const response = await fetch('http://localhost:5000/');
        return response.ok;
    } catch (error) {
        return false;
    }
}

// Update extension icon based on backend status
async function updateExtensionStatus() {
    const isBackendRunning = await checkBackendStatus();
    
    // Set icon based on backend status
    chrome.action.setIcon({
        path: {
            16: isBackendRunning ? 'icons/icon16.png' : 'icons/icon16_disabled.png',
            48: isBackendRunning ? 'icons/icon48.png' : 'icons/icon48_disabled.png',
            128: isBackendRunning ? 'icons/icon128.png' : 'icons/icon128_disabled.png'
        }
    });
}

// Check backend status periodically
setInterval(updateExtensionStatus, 30000);  // Every 30 seconds

// Initial status check
updateExtensionStatus(); 