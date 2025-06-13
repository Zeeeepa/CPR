<template>
  <div class="flex h-screen bg-gray-900 text-white">
    <!-- Sidebar -->
    <div class="w-64 bg-gray-800 flex flex-col">
      <!-- New Thread Button -->
      <button
        class="m-4 p-3 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center justify-center gap-2 transition-colors"
        @click="createNewThread"
      >
        <PlusIcon class="w-5 h-5" />
        <span>New Thread</span>
      </button>

      <!-- Thread List -->
      <div class="flex-1 overflow-y-auto">
        <div v-for="thread in threads" :key="thread.id" class="px-2">
          <button
            class="w-full p-3 rounded-lg text-left hover:bg-gray-700 transition-colors mb-1"
            :class="{ 'bg-gray-700': currentThread?.id === thread.id }"
            @click="selectThread(thread)"
          >
            <div class="flex items-center justify-between">
              <div class="flex-1 min-w-0">
                <h3 class="font-medium truncate">{{ thread.name }}</h3>
                <p class="text-sm opacity-70 truncate">
                  {{ thread.messages.length }} messages
                </p>
              </div>
              <button
                v-if="currentThread?.id === thread.id"
                class="ml-2 p-1 text-gray-400 hover:text-white transition-colors"
                @click.stop="deleteThread(thread.id)"
              >
                <TrashIcon class="w-4 h-4" />
              </button>
            </div>
          </button>
        </div>
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

// State
const threads = ref<Thread[]>([])
const currentThread = ref<Thread | null>(null)
const newMessage = ref('')
const showSettings = ref(false)
const connected = ref(false)
const connectionTesting = ref(false)
const activeTasks = ref(0)
const messagesContainer = ref<HTMLElement | null>(null)

// Settings
const settings = ref({
  codegenToken: '',
  codegenOrgId: '',
  apiBaseUrl: ''
})

// Hardcoded backend URL (no longer configurable)
const BACKEND_URL = 'http://localhost:8002'

// Load settings from localStorage
onMounted(() => {
  const savedSettings = localStorage.getItem('settings')
  if (savedSettings) {
    settings.value = JSON.parse(savedSettings)
  }

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

const toggleSettings = () => {
  showSettings.value = !showSettings.value
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
  currentThread.value.messages.push(aiMessage)
  saveToLocalStorage()
  scrollToBottom()

  try {
    activeTasks.value++

    // Initial request to start the task
    const response = await fetch(`${BACKEND_URL}/api/v1/run-task`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Organization-ID': settings.value.codegenOrgId,
        'X-API-Token': settings.value.codegenToken,
        'X-API-Base-URL': settings.value.apiBaseUrl || ''
      },
      body: JSON.stringify({
        prompt,
        stream: true,
        thread_id: currentThread.value.id
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()
    console.log('Task started:', data)

    // Update AI message with task ID
    if (data.task_id) {
      aiMessage.taskId = data.task_id
    }

    // Connect to SSE stream for updates
    const eventSource = new EventSource(`${BACKEND_URL}/api/v1/task/${data.task_id}/stream`)
    
    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error)
      // Don't close immediately, let it retry
    }
    
    eventSource.onmessage = (event) => {
      try {
        if (event.data === '[DONE]') {
          console.log('Stream completed')
          clearTimeout(timeoutId)
          clearInterval(pollInterval)
          eventSource.close()
          activeTasks.value = Math.max(0, activeTasks.value - 1)
          return
        }

        const parsed = JSON.parse(event.data)
        console.log('Stream update:', parsed)

        // Update step information based on current_step or status
        if (aiMessage.steps) {
          if (parsed.current_step) {
            // Check if this step already exists
            const stepExists = aiMessage.steps.some(step => 
              step.title.toLowerCase().includes(parsed.current_step.toLowerCase()) ||
              step.description.toLowerCase().includes(parsed.current_step.toLowerCase())
            )
            
            if (!stepExists) {
              // Mark previous steps as completed
              aiMessage.steps.forEach(step => {
                if (step.status === 'active') {
                  step.status = 'completed'
                }
              })
              
              // Add new step
              aiMessage.steps.push({
                id: aiMessage.steps.length + 1,
                title: parsed.current_step,
                description: `Processing: ${parsed.current_step}`,
                status: 'active'
              })
              
              console.log('Added new step:', parsed.current_step)
            } else {
              // Update existing step description
              const existingStep = aiMessage.steps.find(step => 
                step.title.toLowerCase().includes(parsed.current_step.toLowerCase()) ||
                step.description.toLowerCase().includes(parsed.current_step.toLowerCase())
              )
              if (existingStep && existingStep.status !== 'completed') {
                existingStep.status = 'active'
                existingStep.description = `Processing: ${parsed.current_step}`
              }
            }
          } else if (parsed.status && ['running', 'in_progress', 'active', 'processing'].includes(parsed.status)) {
            // Update description of active step with status
            const activeStep = aiMessage.steps.find(step => step.status === 'active')
            if (activeStep) {
              activeStep.description = `Status: ${parsed.status}`
            } else {
              // No active step, mark first pending as active
              const pendingStep = aiMessage.steps.find(step => step.status === 'pending')
              if (pendingStep) {
                pendingStep.status = 'active'
                pendingStep.description = `Status: ${parsed.status}`
              }
            }
          }
        }

        // Update task ID and web URL
        if (parsed.task_id && !aiMessage.taskId) {
          aiMessage.taskId = parsed.task_id
        }
        if (parsed.web_url) {
          aiMessage.webUrl = parsed.web_url
        }

        // Handle completion
        if (parsed.status === 'completed') {
          console.log('Task completion detected:', parsed)
          
          // Ensure we have actual response text
          let finalResponse = parsed.result || 'Task completed successfully.'
          
          // If the result looks like a generic message, try to get more details
          if (finalResponse === 'Task completed successfully.' && parsed.web_url) {
            finalResponse = `Task completed successfully. View full details at: ${parsed.web_url}`
          }
          
          console.log('Setting final response:', finalResponse)
          aiMessage.content = finalResponse
          aiMessage.sent = true
          
          // Mark all steps as completed and add final step
          if (aiMessage.steps) {
            aiMessage.steps.forEach(step => step.status = 'completed')
            
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
          
          console.log('Task completed with response:', finalResponse)
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
        }

        scrollToBottom()
      } catch (e) {
        console.error('Error processing stream message:', e)
      }
    }

    // Add polling fallback in case SSE fails
    const pollTaskStatus = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/v1/task/${data.task_id}/status`)
        if (response.ok) {
          const status = await response.json()
          console.log('Polling status:', status)
          
          if (status.status === 'completed' && !aiMessage.sent) {
            console.log('Completion detected via polling')
            const finalResponse = status.result || 'Task completed successfully.'
            aiMessage.content = finalResponse
            aiMessage.sent = true
            
            // Mark all steps as completed
            if (aiMessage.steps) {
              aiMessage.steps.forEach(step => step.status = 'completed')
            }
            
            currentThread.value!.lastActivity = new Date()
            saveToLocalStorage()
            scrollToBottom()
            
            eventSource.close()
            activeTasks.value = Math.max(0, activeTasks.value - 1)
            clearTimeout(timeoutId)
            clearInterval(pollInterval)
          }
        }
      } catch (error) {
        console.error('Polling error:', error)
      }
    }
    
    // Poll every 10 seconds as fallback
    const pollInterval = setInterval(pollTaskStatus, 10000)
    
    // Add timeout to prevent infinite spinning
    const timeoutId = setTimeout(() => {
      console.warn('Task timeout after 5 minutes')
      eventSource.close()
      clearInterval(pollInterval)
      activeTasks.value = Math.max(0, activeTasks.value - 1)
      
      if (!aiMessage.sent) {
        aiMessage.content = 'Task timed out after 5 minutes. Please try again.'
        aiMessage.sent = true
        aiMessage.error = true
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
      }
    }, 300000) // 5 minutes

    eventSource.onerror = (error) => {
      console.error('EventSource error:', error)
      clearTimeout(timeoutId)
      eventSource.close()
      activeTasks.value = Math.max(0, activeTasks.value - 1)
      
      // Only update message if it hasn't been completed
      if (!aiMessage.sent) {
        aiMessage.content = 'Error: Failed to get response from agent'
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
  }
}

// Watch for thread changes to scroll to bottom
watch(currentThread, () => {
  nextTick(() => {
    scrollToBottom()
  })
}, { deep: true })
</script>
