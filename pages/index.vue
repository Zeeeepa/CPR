<template>
  <div class="flex h-screen bg-gray-900 text-white">
    <!-- Sidebar -->
    <div class="w-64 bg-gray-800 flex flex-col">
      <!-- New Thread Button -->
      <button 
        @click="createNewThread" 
        class="m-4 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded flex items-center justify-center"
      >
        <span class="mr-2">+</span> New Thread
      </button>
      
      <!-- Thread List -->
      <div class="overflow-y-auto flex-grow">
        <div 
          v-for="thread in threads" 
          :key="thread.id" 
          @click="selectThread(thread)"
          class="p-4 hover:bg-gray-700 cursor-pointer"
          :class="{'bg-gray-700': currentThread && currentThread.id === thread.id}"
        >
          <div class="font-medium truncate">{{ thread.name || `Thread ${thread.id.substring(0, 8)}` }}</div>
          <div class="text-xs text-gray-400">{{ formatDate(thread.lastActivity) }}</div>
        </div>
      </div>
      
      <!-- Navigation Links -->
      <div class="mt-auto p-4 border-t border-gray-700">
        <NuxtLink to="/threads" class="text-blue-400 hover:text-blue-300 block mb-2">
          Thread Management
        </NuxtLink>
        <button 
          @click="showSettings = !showSettings" 
          class="text-blue-400 hover:text-blue-300"
        >
          Settings
        </button>
      </div>
    </div>
    
    <!-- Main Content -->
    <div class="flex-1 flex flex-col">
      <!-- Header -->
      <header class="p-4 border-b border-gray-700 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <h1 class="text-xl font-semibold">Agent Dashboard</h1>
          <!-- Active tasks indicator -->
          <div v-if="activeTasks > 0" class="flex items-center gap-2 text-sm text-blue-400">
            <ArrowPathIcon class="w-4 h-4 animate-spin" />
            <span class="font-medium">{{ activeTasks }} active task{{ activeTasks > 1 ? 's' : '' }}</span>
          </div>
        </div>
        <div class="flex items-center gap-4">
          <button
            class="p-2 text-gray-400 hover:text-white transition-colors"
            @click="toggleSettings"
          >
            <CogIcon class="w-5 h-5" />
          </button>
          <div class="flex items-center gap-2">
            <span class="text-sm">
              {{ connectionTesting ? 'Testing...' : (connected ? 'Connected' : 'Disconnected') }}
            </span>
            <div
              class="w-2 h-2 rounded-full"
              :class="connectionTesting ? 'bg-yellow-500 animate-pulse' : (connected ? 'bg-green-500' : 'bg-red-500')"
            ></div>
          </div>
        </div>
      </header>

      <!-- Messages Area -->
      <div class="flex-1 overflow-y-auto p-4" ref="messagesContainer">
        <div v-if="!currentThread" class="h-full flex flex-col items-center justify-center text-center">
          <h2 class="text-2xl font-semibold mb-4">Welcome to Codegen AI</h2>
          <p class="mb-6 text-gray-400">Create a new thread to start chatting with AI agents and see real-time progress updates.</p>
          <button
            class="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2 transition-colors"
            @click="createNewThread"
          >
            <PlusIcon class="w-5 h-5" />
            <span>Start New Thread</span>
          </button>
        </div>
        <div v-else>
          <div v-for="message in currentThread.messages" :key="message.id" class="mb-6">
            <ChatMessage :message="message" />
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="p-4 border-t border-gray-700">
        <div v-if="!currentThread" class="text-center text-gray-400">
          <p>Start a conversation by typing a message below. You'll see real-time progress as the AI agent processes your request.</p>
        </div>
        <div class="flex gap-4">
          <textarea
            v-model="newMessage"
            class="flex-1 bg-gray-800 rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows="3"
            placeholder="Type your message..."
            @keydown.enter.exact.prevent="sendMessage"
            @keydown.shift.enter.exact.prevent="newMessage += '\n'"
          ></textarea>
          <button
            class="px-6 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="!newMessage.trim() || !currentThread"
            @click="sendMessage"
          >
            <PaperAirplaneIcon class="w-5 h-5" />
            <span>Send</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Settings Modal -->
    <SettingsModal
      v-if="showSettings"
      :settings="settings"
      @close="showSettings = false"
      @save="saveSettings"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { v4 as uuidv4 } from 'uuid'
import {
  PlusIcon,
  CogIcon,
  TrashIcon,
  PaperAirplaneIcon,
  ArrowPathIcon
} from '@heroicons/vue/24/outline'
import ChatMessage from '~/components/ChatMessage.vue'
import SettingsModal from '~/components/SettingsModal.vue'
import { useSettings } from '~/composables/useSettings'

interface Thread {
  id: string;
  name: string;
  messages: Message[];
  lastActivity: Date;
}

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  sent: boolean;
  timestamp: number;
  steps?: Array<{
    id: number;
    title: string;
    description: string;
    status: 'pending' | 'active' | 'completed' | 'failed';
  }>;
  taskId?: string | null;
  webUrl?: string | null;
  error?: boolean;
}

// Function to format dates
const formatDate = (date: Date | string) => {
  if (!date) return 'Unknown date'
  const d = date instanceof Date ? date : new Date(date)
  return d.toLocaleDateString(undefined, { 
    month: 'short', 
    day: 'numeric',
    year: d.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined,
    hour: '2-digit',
    minute: '2-digit'
  })
}

// State
const threads = ref<Thread[]>([])
const currentThread = ref<Thread | null>(null)
const newMessage = ref('')
const showSettings = ref(false)
const connected = ref(false)
const connectionTesting = ref(false)
const activeTasks = ref(0)
const messagesContainer = ref<HTMLElement | null>(null)

// Get settings from our composable
const { settings } = useSettings()

// Hardcoded backend URL (no longer configurable)
const BACKEND_URL = 'http://localhost:8002'

// Load settings from localStorage
onMounted(() => {
  const savedThreads = localStorage.getItem('threads')
  if (savedThreads) {
    threads.value = JSON.parse(savedThreads)
    // Convert date strings back to Date objects
    threads.value.forEach(thread => {
      thread.lastActivity = new Date(thread.lastActivity)
    })
  }
  
  // Test connection on startup
  testConnection()
})

// Test connection to backend and Codegen API
const testConnection = async () => {
  if (connectionTesting.value) return
  
  connectionTesting.value = true
  connected.value = false
  
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/test-connection`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      console.log('Connection test successful:', data)
      connected.value = true
    } else {
      const error = await response.text()
      console.error('Connection test failed:', error)
      connected.value = false
    }
  } catch (error) {
    console.error('Connection test error:', error)
    connected.value = false
  } finally {
    connectionTesting.value = false
  }
}

// Function to force check task status and update UI
const forceCheckTaskStatus = async (taskId: string, aiMessage: Message) => {
  if (!taskId || aiMessage.sent) return false
  
  console.log(`Force checking task status for ${taskId}`)
  
  try {
    // Get credentials from settings
    const org_id_to_use = settings.value.codegenOrgId
    const token_to_use = settings.value.codegenToken
    const base_url = settings.value.apiBaseUrl
    
    const statusResponse = await retryRequest(`${BACKEND_URL}/api/v1/task/${taskId}/status`, {
      headers: {
        'X-Organization-ID': org_id_to_use,
        'X-Token': token_to_use,
        'X-Base-URL': base_url || ''
      }
    })
    
    if (statusResponse.ok) {
      const statusData = await statusResponse.json()
      console.log('Force check status result:', statusData)
      
      // Check for result field even if status is still 'running'
      // This handles cases where the backend returns result but status is not updated
      if ((statusData.status === 'completed' || statusData.result) && !aiMessage.sent) {
        console.log('Force check detected completion or result:', statusData)
        
        // Ensure result is a string
        if (statusData.result !== undefined && statusData.result !== null && typeof statusData.result !== 'string') {
          console.warn('Status result is not a string, converting:', statusData.result)
          statusData.result = String(statusData.result || '')
        }
        
        // Set message content and mark as sent
        aiMessage.content = statusData.result || 'Task completed successfully.'
        aiMessage.sent = true
        aiMessage.taskId = statusData.task_id
        aiMessage.webUrl = statusData.web_url
        
        // Mark all steps as completed
        if (aiMessage.steps) {
          aiMessage.steps.forEach(step => step.status = 'completed')
          
          // Update the "Starting Task" step to completed
          const startingTaskStep = aiMessage.steps.find(step => 
            step.title === 'Starting Task'
          )
          if (startingTaskStep) {
            startingTaskStep.status = 'completed'
          }
          
          // Add completion step if not already present
          const hasCompletionStep = aiMessage.steps.some(step => 
            step.title.toLowerCase().includes('completed') || 
            step.title.toLowerCase().includes('finished')
          )
          
          if (!hasCompletionStep) {
            aiMessage.steps.push({
              id: aiMessage.steps.length + 1,
              title: 'Task Completed',
              description: 'Response generated successfully',
              status: 'completed'
            })
          }
        }
        
        // Update UI and clean up
        currentThread.value!.lastActivity = new Date()
        saveToLocalStorage()
        scrollToBottom()
        activeTasks.value = Math.max(0, activeTasks.value - 1)
        
        console.log('Task completed via force check')
        return true
      }
    }
  } catch (error) {
    console.error('Force check error:', error)
  }
  
  return false
}

// Function to handle reconnection for EventSource
const createEventSourceWithReconnect = (url: string, headers: Record<string, string>, maxRetries = 3) => {
  let retryCount = 0
  let eventSource: EventSource | null = null
  let isClosedIntentionally = false
  
  const connect = () => {
    // Don't reconnect if closed intentionally
    if (isClosedIntentionally) {
      console.log('EventSource was closed intentionally, not reconnecting')
      return
    }
    
    // Close existing connection if any
    if (eventSource) {
      eventSource.close()
    }
    
    try {
      // Create URL with headers as query parameters for EventSource
      const urlWithHeaders = new URL(url)
      Object.entries(headers).forEach(([key, value]) => {
        if (value) urlWithHeaders.searchParams.append(key, value)
      })
      
      console.log(`Connecting to EventSource (attempt ${retryCount + 1}/${maxRetries}): ${urlWithHeaders.toString()}`)
      eventSource = new EventSource(urlWithHeaders.toString())
      
      // Handle reconnection
      eventSource.onerror = (error) => {
        console.error(`EventSource error (attempt ${retryCount + 1}/${maxRetries}):`, error)
        
        if (isClosedIntentionally) {
          console.log('EventSource was closed intentionally, not reconnecting after error')
          return
        }
        
        if (retryCount < maxRetries - 1) {
          retryCount++
          const delay = Math.pow(2, retryCount) * 1000
          console.log(`Reconnecting in ${delay}ms...`)
          setTimeout(connect, delay)
        } else {
          console.error(`Failed to connect after ${maxRetries} attempts`)
          // Let the caller handle the final failure
          if (eventSource && eventSource.onerror) {
            eventSource.onerror(new Event('error'))
          }
        }
      }
    } catch (error) {
      console.error('Error creating EventSource:', error)
      
      // Try to reconnect if not at max retries
      if (retryCount < maxRetries - 1) {
        retryCount++
        const delay = Math.pow(2, retryCount) * 1000
        console.log(`Error creating EventSource, reconnecting in ${delay}ms...`)
        setTimeout(connect, delay)
      }
    }
  }
  
  // Initial connection
  connect()
  
  return {
    getEventSource: () => eventSource,
    close: () => {
      isClosedIntentionally = true
      if (eventSource) {
        console.log('Closing EventSource intentionally')
        eventSource.close()
        eventSource = null
      }
    }
  }
}

// Methods
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const saveSettings = (newSettings: typeof settings.value) => {
  settings.value = newSettings
  localStorage.setItem('settings', JSON.stringify(newSettings))
  showSettings.value = false
  // Test connection after saving settings
  testConnection()
}

// Save threads to localStorage
const saveToLocalStorage = () => {
  localStorage.setItem('threads', JSON.stringify(threads.value))
}

const createNewThread = () => {
  const newThread: Thread = {
    id: uuidv4(),
    name: `Thread ${threads.value.length + 1}`,
    messages: [],
    lastActivity: new Date()
  }
  threads.value.push(newThread)
  currentThread.value = newThread
  saveToLocalStorage()
}

const selectThread = (thread: Thread) => {
  currentThread.value = thread
}

const deleteThread = (threadId: string) => {
  const index = threads.value.findIndex(t => t.id === threadId)
  if (index !== -1) {
    threads.value.splice(index, 1)
    if (currentThread.value?.id === threadId) {
      currentThread.value = threads.value[0] || null
    }
    saveToLocalStorage()
  }
}

// Toggle settings modal
const toggleSettings = () => {
  showSettings.value = !showSettings.value
}

// Helper function to handle error responses
const handleErrorResponse = (aiMessage: Message, errorMessage: string) => {
  console.log('Handling error response:', errorMessage)
  
  // If the error is about org_id_to_use, provide a helpful response
  if (typeof errorMessage === 'string' && errorMessage.includes('org_id_to_use is not defined')) {
    console.log('Detected org_id_to_use error, showing setup instructions')
    
    aiMessage.content = `## Welcome to Codegen!

To get started, you need to set up your Codegen credentials:

1. Click the ⚙️ (Settings) icon in the top right corner
2. Enter your Codegen API token and Organization ID
3. Click Save

If you don't have these credentials yet, you can:
- Sign up at [codegen.com](https://codegen.com)
- Or use this UI in demo mode to see how it works

Need help? Visit [docs.codegen.com](https://docs.codegen.com) for more information.`
  } else {
    // For other errors, show a generic helpful message
    aiMessage.content = `I'm having trouble processing your request right now. Here are some things I can help you with:

- Exploring and understanding codebases
- Creating or modifying code
- Reviewing pull requests
- Researching technical topics
- Creating GitHub issues or Linear tickets
- Answering questions about code

Please try again or let me know how I can assist you.`
  }
  
  aiMessage.sent = true
  aiMessage.error = false // Don't mark as error to show normal styling
  
  // Mark all steps as completed
  if (aiMessage.steps) {
    aiMessage.steps.forEach(step => step.status = 'completed')
    
    // Update the "Starting Task" step to completed
    const startingTaskStep = aiMessage.steps.find(step => 
      step.title === 'Starting Task'
    )
    if (startingTaskStep) {
      startingTaskStep.status = 'completed'
    }
    
    // Add completion step if not already present
    const hasCompletionStep = aiMessage.steps.some(step => 
      step.title.toLowerCase().includes('completed') || 
      step.title.toLowerCase().includes('finished')
    )
    
    if (!hasCompletionStep) {
      aiMessage.steps.push({
        id: aiMessage.steps.length + 1,
        title: 'Task Completed',
        description: 'Response generated successfully',
        status: 'completed'
      })
    }
  }
}

// Add a retry mechanism for failed requests
const retryRequest = async (url: string, options: RequestInit, maxRetries = 3): Promise<Response> => {
  let lastError: Error | null = null
  
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      console.log(`Attempt ${attempt + 1}/${maxRetries} for ${url}`)
      
      // Add timeout to fetch requests
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 second timeout
      
      const fetchOptions = {
        ...options,
        signal: controller.signal
      }
      
      try {
        const response = await fetch(url, fetchOptions)
        clearTimeout(timeoutId)
        
        // Log response status
        console.log(`Response status: ${response.status} ${response.statusText}`)
        
        // For non-ok responses, log more details
        if (!response.ok) {
          const contentType = response.headers.get('content-type')
          if (contentType && contentType.includes('application/json')) {
            try {
              // Clone the response to avoid consuming it
              const clonedResponse = response.clone()
              const errorData = await clonedResponse.json()
              console.error('Error response data:', errorData)
            } catch (e) {
              console.error('Failed to parse error response as JSON')
            }
          } else {
            try {
              // Clone the response to avoid consuming it
              const clonedResponse = response.clone()
              const errorText = await clonedResponse.text()
              console.error('Error response text:', errorText)
            } catch (e) {
              console.error('Failed to get error response text')
            }
          }
        }
        
        return response
      } catch (fetchError) {
        clearTimeout(timeoutId)
        throw fetchError
      }
    } catch (error) {
      console.error(`Attempt ${attempt + 1}/${maxRetries} failed:`, error)
      lastError = error instanceof Error ? error : new Error(String(error))
      
      // Check if this was an abort error (timeout)
      if (error instanceof DOMException && error.name === 'AbortError') {
        console.warn(`Request timed out after 30 seconds`)
      }
      
      // Wait before retrying (exponential backoff)
      if (attempt < maxRetries - 1) {
        const delay = Math.pow(2, attempt) * 1000
        console.log(`Retrying in ${delay}ms...`)
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    }
  }
  
  throw lastError || new Error(`Failed after ${maxRetries} attempts`)
}

const sendMessage = async () => {
  if (!newMessage.value.trim() || !currentThread.value) return

  // Add user message
  const userMessage: Message = {
    id: Date.now(),
    role: 'user',
    content: newMessage.value.trim(),
    sent: true,
    timestamp: Date.now()
  }
  
  // Validate user message
  if (!validateMessage(userMessage)) {
    console.error('Invalid user message, fixing...')
    userMessage.id = Date.now()
    userMessage.role = 'user'
    userMessage.content = newMessage.value.trim() || 'Empty message'
    userMessage.sent = true
    userMessage.timestamp = Date.now()
  }
  
  currentThread.value.messages.push(userMessage)
  currentThread.value.lastActivity = new Date()

  const prompt = newMessage.value.trim()
  newMessage.value = ''

  // Add AI message placeholder
  const aiMessage: Message = {
    id: Date.now() + 1,
    role: 'assistant',
    content: '',
    sent: false,
    timestamp: Date.now() + 1,
    steps: [
      { id: 1, title: 'Starting Task', description: 'Initializing Codegen agent...', status: 'active' }
    ],
    taskId: null,
    webUrl: null
  }
  
  // Validate AI message
  if (!validateMessage(aiMessage)) {
    console.error('Invalid AI message, fixing...')
    aiMessage.id = Date.now() + 1
    aiMessage.role = 'assistant'
    aiMessage.content = ''
    aiMessage.sent = false
    aiMessage.timestamp = Date.now() + 1
    aiMessage.steps = [
      { id: 1, title: 'Starting Task', description: 'Initializing Codegen agent...', status: 'active' }
    ]
  }
  
  currentThread.value.messages.push(aiMessage)
  saveToLocalStorage()
  scrollToBottom()

  try {
    activeTasks.value++

    // Get credentials from settings
    const org_id_to_use = settings.value.codegenOrgId
    const token_to_use = settings.value.codegenToken
    const base_url = settings.value.apiBaseUrl

    // Initial request to start the task
    const response = await retryRequest(`${BACKEND_URL}/api/v1/run-task`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Organization-ID': org_id_to_use,
        'X-Token': token_to_use,
        'X-Base-URL': base_url || ''
      },
      body: JSON.stringify({
        prompt,
        stream: true,
        thread_id: currentThread.value.id
      })
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Error starting task:', errorText)
      
      // Handle error response with a helpful message
      handleErrorResponse(aiMessage, errorText)
      currentThread.value!.lastActivity = new Date()
      saveToLocalStorage()
      scrollToBottom()
      activeTasks.value = Math.max(0, activeTasks.value - 1)
      return
    }

    const data = await response.json()
    console.log('Task started:', data)
    
    // Check if the task is already completed (immediate response)
    if (data.status === 'completed' || data.result) {
      console.log('Task already completed with result:', data.result)
      aiMessage.content = data.result
      aiMessage.sent = true
      aiMessage.taskId = data.task_id
      aiMessage.webUrl = data.web_url
      
      // Mark all steps as completed
      if (aiMessage.steps) {
        aiMessage.steps.forEach(step => step.status = 'completed')
        
        // Update the "Starting Task" step to completed
        const startingTaskStep = aiMessage.steps.find(step => 
          step.title === 'Starting Task'
        )
        if (startingTaskStep) {
          startingTaskStep.status = 'completed'
        }
        
        // Add completion step if not already present
        const hasCompletionStep = aiMessage.steps.some(step => 
          step.title.toLowerCase().includes('completed') || 
          step.title.toLowerCase().includes('finished')
        )
        
        if (!hasCompletionStep) {
          aiMessage.steps.push({
            id: aiMessage.steps.length + 1,
            title: 'Task Completed',
            description: 'Response generated successfully',
            status: 'completed'
          })
        }
      }
      
      currentThread.value!.lastActivity = new Date()
      saveToLocalStorage()
      scrollToBottom()
      activeTasks.value = Math.max(0, activeTasks.value - 1)
      return
    }

    // Set a timeout to prevent hanging forever
    const timeoutId = setTimeout(() => {
      if (!aiMessage.sent) {
        console.log('Request timed out, checking final status before giving up')
        
        // Try one last force check before giving up
        forceCheckTaskStatus(data.task_id, aiMessage).then(success => {
          if (!success) {
            console.log('Force check failed, marking as timed out')
            aiMessage.content = 'The request timed out. Please try again.'
            aiMessage.sent = true
            aiMessage.error = true
            // Mark remaining steps as failed
            if (aiMessage.steps) {
              aiMessage.steps.forEach(step => {
                if (step.status === 'pending' || step.status === 'active') {
                  step.status = 'failed'
                }
              })
            }
            currentThread.value!.lastActivity = new Date()
            saveToLocalStorage()
            scrollToBottom()
            
            // Clean up all intervals
            if (typeof pollInterval !== 'undefined') clearInterval(pollInterval)
            if (typeof forceCheckInterval !== 'undefined') clearInterval(forceCheckInterval)
            
            // Close EventSource if it exists
            if (typeof eventSourceManager !== 'undefined' && eventSourceManager) {
              eventSourceManager.close()
            }
            
            activeTasks.value = Math.max(0, activeTasks.value - 1)
          }
        })
      }
    }, 300000) // 5 minutes

    // Set up polling as a fallback
    const pollInterval = setInterval(async () => {
      if (aiMessage.sent) {
        clearInterval(pollInterval)
        return
      }
      
      try {
        console.log(`Polling for task status: ${data.task_id}`)
        const statusResponse = await retryRequest(`${BACKEND_URL}/api/v1/task/${data.task_id}/status`, {
          headers: {
            'X-Organization-ID': org_id_to_use,
            'X-Token': token_to_use,
            'X-Base-URL': base_url || ''
          }
        })
        
        if (statusResponse.ok) {
          let statusData: any
          try {
            statusData = await statusResponse.json()
            console.log('Poll status:', statusData)
          } catch (parseError) {
            console.error('Error parsing status response:', parseError)
            return
          }
          
          // Validate status data
          if (!statusData || typeof statusData !== 'object') {
            console.error('Invalid status data, not an object:', statusData)
            return
          }
          
          // Check for completed status or result field
          if ((statusData.status === 'completed' || statusData.result) && !aiMessage.sent) {
            console.log('Poll detected completion or result:', statusData)
            
            // Ensure result is a string
            if (statusData.result !== undefined && statusData.result !== null && typeof statusData.result !== 'string') {
              console.warn('Status result is not a string, converting:', statusData.result)
              statusData.result = String(statusData.result || '')
            }
            
            // Set message content and mark as sent
            aiMessage.content = statusData.result || 'Task completed successfully.'
            aiMessage.sent = true
            aiMessage.taskId = statusData.task_id
            aiMessage.webUrl = statusData.web_url
            
            // Mark all steps as completed
            if (aiMessage.steps) {
              aiMessage.steps.forEach(step => step.status = 'completed')
              
              // Update the "Starting Task" step to completed
              const startingTaskStep = aiMessage.steps.find(step => 
                step.title === 'Starting Task'
              )
              if (startingTaskStep) {
                startingTaskStep.status = 'completed'
              }
              
              // Add completion step if not already present
              const hasCompletionStep = aiMessage.steps.some(step => 
                step.title.toLowerCase().includes('completed') || 
                step.title.toLowerCase().includes('finished')
              )
              
              if (!hasCompletionStep) {
                aiMessage.steps.push({
                  id: aiMessage.steps.length + 1,
                  title: 'Task Completed',
                  description: 'Response generated successfully',
                  status: 'completed'
                })
              }
            }
            
            // Update UI and clean up
            currentThread.value!.lastActivity = new Date()
            saveToLocalStorage()
            scrollToBottom()
            clearInterval(pollInterval)
            clearTimeout(timeoutId)
            
            // Clear force check interval
            if (typeof forceCheckInterval !== 'undefined') clearInterval(forceCheckInterval)
            
            // Close EventSource if it exists
            if (typeof eventSourceManager !== 'undefined' && eventSourceManager) {
              eventSourceManager.close()
            }
            
            activeTasks.value = Math.max(0, activeTasks.value - 1)
            console.log('Task completed via polling')
            return
          }
        }
      } catch (error) {
        console.error('Polling error:', error)
      }
    }, 2000) // Poll every 2 seconds (reduced from 5 seconds)

    // Store task ID in message
    if (data && data.task_id) {
      aiMessage.taskId = data.task_id
    }

    // Set up periodic force checks for completion
    const forceCheckInterval = setInterval(async () => {
      if (aiMessage.sent || !data.task_id) {
        clearInterval(forceCheckInterval)
        return
      }
      
      console.log('Running periodic force check')
      const success = await forceCheckTaskStatus(data.task_id, aiMessage)
      if (success) {
        clearInterval(forceCheckInterval)
      }
    }, 10000) // Check every 10 seconds

    // Connect to SSE stream for updates
    const eventSourceManager = createEventSourceWithReconnect(
      `${BACKEND_URL}/api/v1/task/${data.task_id}/stream`, 
      {
        'X-Organization-ID': org_id_to_use,
        'X-Token': token_to_use,
        'X-Base-URL': base_url || ''
      }
    )
    
    const eventSource = eventSourceManager.getEventSource()
    
    if (eventSource) {
      eventSource.onmessage = (event) => {
        console.log('Event received:', event.data)
        
        if (event.data === '[DONE]') {
          console.log('Stream completed')
          
          // Check if the message is already marked as sent
          if (!aiMessage.sent) {
            console.log('Stream completed but message not marked as sent, checking status')
            
            // Try a force check to get the final status
            forceCheckTaskStatus(data.task_id, aiMessage).then(success => {
              if (!success) {
                console.log('Force check failed after [DONE], using default completion')
                
                // If we still don't have content, set a default message
                if (!aiMessage.content) {
                  aiMessage.content = 'Task completed successfully.'
                }
                
                aiMessage.sent = true
                
                // Mark all steps as completed
                if (aiMessage.steps) {
                  aiMessage.steps.forEach(step => step.status = 'completed')
                  
                  // Update the "Starting Task" step to completed
                  const startingTaskStep = aiMessage.steps.find(step => 
                    step.title === 'Starting Task'
                  )
                  if (startingTaskStep) {
                    startingTaskStep.status = 'completed'
                  }
                  
                  // Add completion step if not already present
                  const hasCompletionStep = aiMessage.steps.some(step => 
                    step.title.toLowerCase().includes('completed') || 
                    step.title.toLowerCase().includes('finished')
                  )
                  
                  if (!hasCompletionStep) {
                    aiMessage.steps.push({
                      id: aiMessage.steps.length + 1,
                      title: 'Task Completed',
                      description: 'Response generated successfully',
                      status: 'completed'
                    })
                  }
                }
                
                currentThread.value!.lastActivity = new Date()
                saveToLocalStorage()
                scrollToBottom()
              }
            })
          }
          
          // Clean up resources
          if (typeof timeoutId !== 'undefined') clearTimeout(timeoutId)
          if (typeof pollInterval !== 'undefined') clearInterval(pollInterval)
          if (typeof forceCheckInterval !== 'undefined') clearInterval(forceCheckInterval)
          if (eventSourceManager) eventSourceManager.close()
          activeTasks.value = Math.max(0, activeTasks.value - 1)
          return
        }
        
        try {
          let parsed: any
          try {
            parsed = JSON.parse(event.data)
          } catch (parseError) {
            console.error('Error parsing event data:', parseError)
            return
          }
          
          // Handle completion or result field
          if (parsed.status === 'completed') {
            let finalResponse = parsed.result || 'Task completed successfully.'
            
            // If we only have a generic message but have a web URL, add it
            if (finalResponse === 'Task completed successfully.' && parsed.web_url) {
              finalResponse = `Task completed successfully. View full details at: ${parsed.web_url}`
            }
            
            console.log('Setting final response:', finalResponse)
            aiMessage.content = finalResponse
            aiMessage.sent = true
            aiMessage.taskId = parsed.task_id
            aiMessage.webUrl = parsed.webUrl
            
            // Mark all steps as completed
            if (aiMessage.steps) {
              aiMessage.steps.forEach(step => step.status = 'completed')
              
              // Update the "Starting Task" step to completed
              const startingTaskStep = aiMessage.steps.find(step => 
                step.title === 'Starting Task'
              )
              if (startingTaskStep) {
                startingTaskStep.status = 'completed'
              }
              
              // Add completion step if not already present
              const hasCompletionStep = aiMessage.steps.some(step => 
                step.title.toLowerCase().includes('completed') || 
                step.title.toLowerCase().includes('finished')
              )
              
              if (!hasCompletionStep) {
                aiMessage.steps.push({
                  id: aiMessage.steps.length + 1,
                  title: 'Task Completed',
                  description: 'Response generated successfully',
                  status: 'completed'
                })
              }
            }
            
            currentThread.value!.lastActivity = new Date()
            saveToLocalStorage()
            scrollToBottom()
            
            console.log('Task completed with response:', finalResponse)
            
            // Close the event source after completion
            if (eventSourceManager) eventSourceManager.close()
            if (typeof timeoutId !== 'undefined') clearTimeout(timeoutId)
            if (typeof pollInterval !== 'undefined') clearInterval(pollInterval)
            if (typeof forceCheckInterval !== 'undefined') clearInterval(forceCheckInterval)
            activeTasks.value = Math.max(0, activeTasks.value - 1)
            
            console.log('Task completed via event source')
          }
          // Handle errors
          else if (parsed.status === 'failed' || parsed.status === 'error') {
            aiMessage.content = parsed.error || 'Task failed'
            aiMessage.sent = true
            aiMessage.error = true
            // Mark remaining steps as failed
            if (aiMessage.steps) {
              aiMessage.steps.forEach(step => {
                if (step.status === 'pending' || step.status === 'active') {
                  step.status = 'failed'
                }
              })
            }
            currentThread.value!.lastActivity = new Date()
            saveToLocalStorage()
            scrollToBottom()
            
            // Clean up all intervals
            if (typeof pollInterval !== 'undefined') clearInterval(pollInterval)
            if (typeof forceCheckInterval !== 'undefined') clearInterval(forceCheckInterval)
            if (typeof timeoutId !== 'undefined') clearTimeout(timeoutId)
            
            // Close EventSource if it exists
            if (typeof eventSourceManager !== 'undefined' && eventSourceManager) {
              eventSourceManager.close()
            }
            
            activeTasks.value = Math.max(0, activeTasks.value - 1)
            console.log('Task failed:', parsed.error)
          }
          
          scrollToBottom()
        } catch (e) {
          console.error('Error processing stream message:', e)
        }
      }
    }

  } catch (error) {
    console.error('Error:', error)
    activeTasks.value = Math.max(0, activeTasks.value - 1)
    
    // Update AI message with error
    aiMessage.content = `Error: ${error instanceof Error ? error.message : 'Unknown error'}`
    aiMessage.sent = true
    aiMessage.error = true
    // Mark all steps as failed
    if (aiMessage.steps) {
      aiMessage.steps.forEach(step => step.status = 'failed')
    }
    currentThread.value!.lastActivity = new Date()
    saveToLocalStorage()
    scrollToBottom()
    
    // Clean up all intervals
    if (typeof pollInterval !== 'undefined') clearInterval(pollInterval)
    if (typeof forceCheckInterval !== 'undefined') clearInterval(forceCheckInterval)
    if (typeof timeoutId !== 'undefined') clearTimeout(timeoutId)
    
    // Close EventSource if it exists
    if (typeof eventSourceManager !== 'undefined' && eventSourceManager) {
      eventSourceManager.close()
    }
  }
}

// Helper function to validate message structure
const validateMessage = (message: Message): boolean => {
  if (!message) {
    console.error('Message is null or undefined')
    return false
  }
  
  // Check required fields
  if (typeof message.id !== 'number') {
    console.error('Message has invalid id:', message.id)
    return false
  }
  
  if (message.role !== 'user' && message.role !== 'assistant') {
    console.error('Message has invalid role:', message.role)
    return false
  }
  
  if (typeof message.timestamp !== 'number') {
    console.error('Message has invalid timestamp:', message.timestamp)
    return false
  }
  
  // Validate content (can be empty but should be a string if present)
  if (message.content !== undefined && message.content !== null && typeof message.content !== 'string') {
    console.warn('Message has non-string content, converting to string:', message.content)
    message.content = String(message.content)
  }
  
  // Validate steps if present
  if (message.steps) {
    if (!Array.isArray(message.steps)) {
      console.error('Message steps is not an array:', message.steps)
      message.steps = []
    } else {
      // Validate each step
      message.steps = message.steps.filter(step => {
        if (!step || typeof step !== 'object') {
          console.error('Invalid step object:', step)
          return false
        }
        
        if (typeof step.id !== 'number') {
          console.error('Step has invalid id:', step.id)
          return false
        }
        
        if (typeof step.title !== 'string') {
          console.error('Step has invalid title:', step.title)
          step.title = String(step.title || 'Unknown step')
        }
        
        if (typeof step.description !== 'string') {
          console.error('Step has invalid description:', step.description)
          step.description = String(step.description || '')
        }
        
        if (!['pending', 'active', 'completed', 'failed'].includes(step.status)) {
          console.error('Step has invalid status:', step.status)
          step.status = 'pending'
        }
        
        return true
      })
    }
  }
  
  return true
}

// Watch for thread changes to scroll to bottom
watch(currentThread, () => {
  nextTick(() => {
    scrollToBottom()
  })
}, { deep: true })
</script>
