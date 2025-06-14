<template>
  <div class="thread-manager">
    <div class="thread-list">
      <h2 class="text-xl font-bold mb-4">Threads</h2>
      <button 
        @click="createNewThread" 
        class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded mb-4"
      >
        Create New Thread
      </button>
      
      <div v-if="loading" class="text-gray-500">Loading threads...</div>
      
      <div v-else-if="threads.length === 0" class="text-gray-500">
        No threads yet. Create one to get started.
      </div>
      
      <div v-else class="space-y-2">
        <div 
          v-for="thread in threads" 
          :key="thread.thread_id"
          @click="selectThread(thread)"
          class="p-3 border rounded cursor-pointer hover:bg-gray-100"
          :class="{'bg-blue-100': selectedThread && selectedThread.thread_id === thread.thread_id}"
        >
          <div class="font-medium">{{ thread.name }}</div>
          <div class="text-xs text-gray-500">{{ formatDate(thread.created_at) }}</div>
        </div>
      </div>
    </div>
    
    <div class="thread-content">
      <div v-if="!selectedThread" class="text-center text-gray-500 mt-10">
        Select a thread or create a new one to start chatting
      </div>
      
      <div v-else>
        <h2 class="text-xl font-bold mb-4">{{ selectedThread.name }}</h2>
        
        <div class="messages-container mb-4">
          <div v-if="loadingMessages" class="text-gray-500">Loading messages...</div>
          
          <div v-else-if="messages.length === 0" class="text-gray-500">
            No messages in this thread yet. Send a message to get started.
          </div>
          
          <div v-else class="space-y-4">
            <div 
              v-for="message in messages" 
              :key="message.message_id"
              class="p-3 rounded"
              :class="{
                'bg-blue-100': message.status === 'completed',
                'bg-yellow-100': message.status === 'pending' || message.status === 'processing',
                'bg-red-100': message.status === 'failed' || message.status === 'timeout'
              }"
            >
              <div class="font-medium">{{ message.content || 'Loading...' }}</div>
              <div class="text-xs text-gray-500 mt-1">
                Status: {{ message.status }} | 
                {{ formatDate(message.created_at) }}
              </div>
            </div>
          </div>
        </div>
        
        <div class="message-input">
          <textarea 
            v-model="newMessage" 
            class="w-full p-2 border rounded"
            placeholder="Type your message here..."
            rows="3"
          ></textarea>
          <button 
            @click="sendMessage" 
            class="mt-2 bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded"
            :disabled="!newMessage.trim() || sendingMessage"
          >
            {{ sendingMessage ? 'Sending...' : 'Send Message' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useSettings } from '~/composables/useSettings'

const BACKEND_URL = 'http://localhost:8002'

// Get settings for API credentials
const { settings } = useSettings()

// Thread management
const threads = ref<any[]>([])
const selectedThread = ref<any>(null)
const loading = ref(false)

// Message management
const messages = ref<any[]>([])
const newMessage = ref('')
const loadingMessages = ref(false)
const sendingMessage = ref(false)

// Polling interval for message updates
let messagePollingInterval: any = null

// Format date for display
const formatDate = (dateString: string) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString()
}

// Fetch all threads
const fetchThreads = async () => {
  loading.value = true
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/threads`, {
      headers: {
        'X-Organization-ID': settings.value.codegenOrgId,
        'X-Token': settings.value.codegenToken,
        'X-Base-URL': settings.value.apiBaseUrl || ''
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      threads.value = data.threads
    } else {
      console.error('Failed to fetch threads:', await response.text())
    }
  } catch (error) {
    console.error('Error fetching threads:', error)
  } finally {
    loading.value = false
  }
}

// Create a new thread
const createNewThread = async () => {
  loading.value = true
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/threads`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Organization-ID': settings.value.codegenOrgId,
        'X-Token': settings.value.codegenToken,
        'X-Base-URL': settings.value.apiBaseUrl || ''
      },
      body: JSON.stringify({
        name: `Thread ${new Date().toLocaleString()}`
      })
    })
    
    if (response.ok) {
      const newThread = await response.json()
      await fetchThreads()
      selectThread(newThread)
    } else {
      console.error('Failed to create thread:', await response.text())
    }
  } catch (error) {
    console.error('Error creating thread:', error)
  } finally {
    loading.value = false
  }
}

// Select a thread and load its messages
const selectThread = async (thread: any) => {
  selectedThread.value = thread
  await fetchMessages(thread.thread_id)
  
  // Start polling for message updates
  if (messagePollingInterval) {
    clearInterval(messagePollingInterval)
  }
  
  messagePollingInterval = setInterval(() => {
    if (selectedThread.value) {
      fetchMessages(selectedThread.value.thread_id, false)
    }
  }, 3000) // Poll every 3 seconds
}

// Fetch messages for a thread
const fetchMessages = async (threadId: string, showLoading = true) => {
  if (showLoading) {
    loadingMessages.value = true
  }
  
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/threads/${threadId}/messages`, {
      headers: {
        'X-Organization-ID': settings.value.codegenOrgId,
        'X-Token': settings.value.codegenToken,
        'X-Base-URL': settings.value.apiBaseUrl || ''
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      messages.value = data.messages
    } else {
      console.error('Failed to fetch messages:', await response.text())
    }
  } catch (error) {
    console.error('Error fetching messages:', error)
  } finally {
    if (showLoading) {
      loadingMessages.value = false
    }
  }
}

// Send a new message
const sendMessage = async () => {
  if (!selectedThread.value || !newMessage.value.trim()) return
  
  sendingMessage.value = true
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/threads/${selectedThread.value.thread_id}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Organization-ID': settings.value.codegenOrgId,
        'X-Token': settings.value.codegenToken,
        'X-Base-URL': settings.value.apiBaseUrl || ''
      },
      body: JSON.stringify({
        content: newMessage.value,
        thread_id: selectedThread.value.thread_id
      })
    })
    
    if (response.ok) {
      newMessage.value = ''
      await fetchMessages(selectedThread.value.thread_id)
    } else {
      console.error('Failed to send message:', await response.text())
    }
  } catch (error) {
    console.error('Error sending message:', error)
  } finally {
    sendingMessage.value = false
  }
}

// Load threads on component mount
onMounted(async () => {
  await fetchThreads()
})

// Clean up polling interval when component is unmounted
onUnmounted(() => {
  if (messagePollingInterval) {
    clearInterval(messagePollingInterval)
  }
})
</script>

<style scoped>
.thread-manager {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 20px;
  height: 100%;
}

.thread-list {
  border-right: 1px solid #e2e8f0;
  padding: 20px;
  overflow-y: auto;
}

.thread-content {
  padding: 20px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.messages-container {
  flex-grow: 1;
  overflow-y: auto;
  max-height: 60vh;
}

.message-input {
  margin-top: auto;
}
</style>

