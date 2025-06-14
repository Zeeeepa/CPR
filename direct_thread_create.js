// direct_thread_create.js
// This script can be run in the browser console to directly create a thread in localStorage

// Function to create a new thread with a message
function createThread(userMessage, assistantResponse = "This is a response created directly in localStorage.") {
  // Generate UUIDs for thread and messages
  function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
  
  const threadId = generateUUID();
  const userMessageId = generateUUID();
  const assistantMessageId = generateUUID();
  const timestamp = Date.now();
  const isoDate = new Date().toISOString();
  
  // Create thread object
  const newThread = {
    id: threadId,
    name: `Thread created at ${new Date().toLocaleString()}`,
    messages: [
      {
        id: userMessageId,
        role: "user",
        content: userMessage,
        sent: true,
        timestamp: timestamp
      },
      {
        id: assistantMessageId,
        role: "assistant",
        content: assistantResponse,
        sent: true,
        timestamp: timestamp + 1000
      }
    ],
    lastActivity: isoDate
  };
  
  // Get existing threads
  let threads = JSON.parse(localStorage.getItem('cpr_threads') || '[]');
  
  // Add new thread
  threads.push(newThread);
  
  // Save back to localStorage
  localStorage.setItem('cpr_threads', JSON.stringify(threads));
  
  console.log(`Thread created with ID: ${threadId}`);
  console.log("Refresh the page to see the new thread");
  
  return threadId;
}

// Example usage:
// createThread("Hello from direct JavaScript!", "This is a response created directly in localStorage.");

