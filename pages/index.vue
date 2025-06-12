<template>
  <div class="flex h-screen bg-slate-950">
    <!-- Sidebar -->
    <div class="w-80 bg-slate-900 border-r border-slate-700 flex flex-col">
      <!-- Header -->
      <div class="p-4 border-b border-slate-700">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h1 class="text-xl font-bold text-white">Codegen AI</h1>
            <p class="text-xs text-gray-400">Agent Dashboard</p>
          </div>
          <button
            @click="showSettings = true"
            class="p-2 text-gray-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            title="Settings"
          >
            <CogIcon class="w-5 h-5" />
          </button>
        </div>
        
        <!-- New Thread Button -->
        <button
          @click="createNewThread"
          class="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg transition-colors flex items-center justify-center gap-2 font-medium"
        >
          <PlusIcon class="w-4 h-4" />
          New Thread
        </button>
      </div>

      <!-- Thread List -->
      <div class="flex-1 overflow-y-auto scrollbar-thin">
        <div class="p-2">
          <div
            v-for="thread in threads"
            :key="thread.id"
            @click="selectThread(thread.id)"
            class="p-3 rounded-lg cursor-pointer transition-all mb-2 group relative"
            :class="[
              currentThreadId === thread.id
                ? 'bg-blue-600 text-white shadow-lg'
                : 'text-gray-300 hover:bg-slate-800'
            ]"
          >
            <div class="flex items-center justify-between">
              <div class="flex-1 min-w-0">
                <h3 class="font-medium truncate">{{ thread.name }}</h3>
                <p class="text-sm opacity-70 truncate">
                  {{ thread.messages.length }} messages
                  <span v-if="thread.lastActivity" class="ml-2">
                    • {{ formatRelativeTime(thread.lastActivity) }}
                  </span>
                </p>
              </div>
              <button
                v-if="threads.length > 1"
                @click.stop="deleteThread(thread.id)"
                class="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-600 rounded transition-all"
                title="Delete thread"
              >
                <TrashIcon class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Connection Status -->
      <div class="p-4 border-t border-slate-700">
        <div class="flex items-center gap-3 text-sm">
          <div
            class="w-3 h-3 rounded-full"
            :class="connectionStatus.connected ? 'bg-emerald-500' : 'bg-red-500'"
          ></div>
          <span :class="connectionStatus.connected ? 'text-emerald-400' : 'text-red-400'">
            {{ connectionStatus.message }}
          </span>
        </div>
      </div>
    </div>

    <!-- Main Chat Area -->
    <div class="flex-1 flex flex-col">
      <!-- Chat Header -->
      <div class="p-4 border-b border-slate-700 bg-slate-900">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-semibold text-white">
              {{ currentThread?.name || 'Select a thread' }}
            </h2>
            <p class="text-sm text-gray-400">
              {{ currentThread ? `${currentThread.messages.length} messages` : 'No thread selected' }}
            </p>
          </div>
          <div class="flex items-center gap-4">
            <!-- Active tasks indicator -->
            <div v-if="activeTasks > 0" class="flex items-center gap-2 text-sm text-blue-400">
              <div class="animate-spin rounded-full h-4 w-4 border-2 border-blue-400 border-t-transparent"></div>
              <span class="font-medium">{{ activeTasks }} active task{{ activeTasks > 1 ? 's' : '' }}</span>
            </div>
            
            <!-- Connection indicator -->
            <div class="flex items-center gap-2">
              <div
                class="w-2 h-2 rounded-full"
                :class="connectionStatus.connected ? 'bg-emerald-500' : 'bg-red-500'"
              ></div>
              <span class="text-xs text-gray-400">
                {{ connectionStatus.connected ? 'Connected' : 'Disconnected' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Messages -->
      <div
        ref="messagesContainer"
        class="flex-1 overflow-y-auto scrollbar-thin p-6"
      >
        <div v-if="!currentThread" class="flex items-center justify-center h-full">
          <div class="text-center text-gray-400 max-w-md">
            <div class="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4">
              <ChatBubbleLeftRightIcon class="w-8 h-8 text-gray-500" />
            </div>
            <h3 class="text-xl font-medium mb-3 text-white">Welcome to Codegen AI</h3>
            <p class="mb-6 text-gray-400">Create a new thread to start chatting with AI agents and see real-time progress updates.</p>
            <button
              @click="createNewThread"
              class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors font-medium"
            >
              Create New Thread
            </button>
          </div>
        </div>

        <div v-else-if="currentThread.messages.length === 0" class="flex items-center justify-center h-full">
          <div class="text-center text-gray-400 max-w-md">
            <h3 class="text-lg font-medium mb-2 text-white">{{ currentThread.name }}</h3>
            <p class="text-gray-400">Start a conversation by typing a message below. You'll see real-time progress as the AI agent processes your request.</p>
          </div>
        </div>

        <div v-else class="space-y-1">
          <ChatMessage
            v-for="message in currentThread.messages"
            :key="message.id"
            :message="message"
            @copy="showNotification"
          />
        </div>

        <!-- Loading indicator -->
        <div
          v-if="isLoading"
          class="flex gap-3 justify-start mb-4"
        >
          <div class="bg-slate-800 text-gray-100 rounded-xl p-5 border border-slate-700 shadow-lg">
            <div class="flex items-center gap-3">
              <div class="animate-spin rounded-full h-5 w-5 border-2 border-blue-500 border-t-transparent"></div>
              <span class="text-sm font-medium">AI is processing your request...</span>
            </div>
            <div class="mt-2 text-xs text-gray-400">
              This may take a few moments depending on the complexity
            </div>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="p-4 border-t border-slate-700 bg-slate-900">
        <form @submit.prevent="sendMessage" class="flex gap-3">
          <div class="flex-1 relative">
            <textarea
              v-model="newMessage"
              @keydown.enter.exact.prevent="sendMessage"
              @keydown.enter.shift.exact="newMessage += '\n'"
              placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
              class="w-full bg-slate-800 text-white border border-slate-600 rounded-lg px-4 py-3 pr-16 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none transition-colors"
              rows="3"
              :disabled="!currentThread || isLoading"
            ></textarea>
            <div class="absolute bottom-3 right-3 text-xs text-gray-500">
              {{ newMessage.length }}/4000
            </div>
          </div>
          <button
            type="submit"
            :disabled="!newMessage.trim() || !currentThread || isLoading || newMessage.length > 4000"
            class="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg transition-colors flex items-center gap-2 self-end font-medium"
          >
            <PaperAirplaneIcon class="w-4 h-4" />
            Send
          </button>
        </form>
      </div>
    </div>

    <!-- Settings Modal -->
    <SettingsModal
      v-if="showSettings"
      :settings="settings"
      @close="showSettings = false"
      @save="saveSettings"
    />

    <!-- Notification Toast -->
    <div
      v-if="notification.show"
      class="fixed top-4 right-4 bg-slate-800 border text-white px-4 py-3 rounded-lg shadow-xl z-50 transition-all max-w-sm"
      :class="notification.type === 'error' ? 'border-red-500 bg-red-950' : 'border-emerald-500 bg-emerald-950'"
    >
      <div class="flex items-center gap-2">
        <CheckIcon v-if="notification.type !== 'error'" class="w-4 h-4 text-emerald-400" />
        <XMarkIcon v-else class="w-4 h-4 text-red-400" />
        <span class="text-sm">{{ notification.message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch, onUnmounted } from 'vue'
import { v4 as uuidv4 } from 'uuid'
import {
  PlusIcon,
  CogIcon,
  TrashIcon,
  PaperAirplaneIcon,
  ChatBubbleLeftRightIcon,
  CheckIcon,
  XMarkIcon
} from '@heroicons/vue/24/outline'

// Reactive state
const threads = ref([])
const currentThreadId = ref(null)
const newMessage = ref('')
const isLoading = ref(false)
const showSettings = ref(false)
const messagesContainer = ref(null)
const activeTasks = ref(0)
const notification = ref({ show: false, message: '', type: 'info' })

// Connection status
const connectionStatus = ref({
  connected: false,
  message: 'Disconnected',
  lastCheck: null
})

// Settings
const settings = ref({
  codegenToken: '',
  codegenOrgId: '',
  backendUrl: 'http://localhost:8887'
})

// Computed
const currentThread = computed(() => 
  threads.value.find(t => t.id === currentThreadId.value)
)

// Methods
const createNewThread = () => {
  const threadName = prompt('Enter thread name:') || `Thread ${threads.value.length + 1}`
  const newThread = {
    id: uuidv4(),
    name: threadName,
    messages: [],
    createdAt: new Date(),
    lastActivity: new Date()
  }
  threads.value.unshift(newThread)
  selectThread(newThread.id)
  saveToLocalStorage()
}

const selectThread = (threadId) => {
  currentThreadId.value = threadId
  nextTick(() => {
    scrollToBottom()
  })
}

const deleteThread = (threadId) => {
  if (confirm('Are you sure you want to delete this thread?')) {
    threads.value = threads.value.filter(t => t.id !== threadId)
    if (currentThreadId.value === threadId) {
      currentThreadId.value = threads.value[0]?.id || null
    }
    saveToLocalStorage()
  }
}

const sendMessage = async (message: string) => {
  if (!message.trim()) return

  // Add user message
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: message,
    sent: true
  })

  // Add AI message placeholder
  const aiMessage = {
    id: Date.now() + 1,
    role: 'assistant',
    content: '',
    sent: false,
    steps: [
      { id: 1, title: 'Initializing Agent', description: 'Setting up the AI agent', status: 'pending' },
      { id: 2, title: 'Processing Request', description: 'Analyzing your prompt', status: 'pending' },
      { id: 3, title: 'Generating Response', description: 'Creating the response', status: 'pending' },
      { id: 4, title: 'Finalizing', description: 'Completing the task', status: 'pending' }
    ],
    taskId: null,
    webUrl: null
  }
  messages.value.push(aiMessage)

  try {
    activeTasks.value++

    // Initial request to start the task
    const response = await fetch(`${settings.value.backendUrl}/api/v1/run-task`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Organization-ID': settings.value.orgId,
        'X-API-Token': settings.value.token,
        'X-API-Base-URL': settings.value.apiBaseUrl || ''
      },
      body: JSON.stringify({
        prompt: message,
        stream: true,
        thread_id: threadId.value
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
    const eventSource = new EventSource(`${settings.value.backendUrl}/api/v1/task/${data.task_id}/stream`)
    
    eventSource.onmessage = (event) => {
      try {
        if (event.data === '[DONE]') {
          console.log('Stream completed')
          eventSource.close()
          activeTasks.value = Math.max(0, activeTasks.value - 1)
          return
        }

        const parsed = JSON.parse(event.data)
        console.log('Stream update:', parsed)

        // Update step information
        if (parsed.current_step) {
          const stepIndex = aiMessage.steps.findIndex(s => 
            s.description.toLowerCase().includes(parsed.current_step.toLowerCase())
          )
          if (stepIndex !== -1) {
            aiMessage.steps[stepIndex].status = 'completed'
            // Mark previous steps as completed
            for (let i = 0; i < stepIndex; i++) {
              aiMessage.steps[i].status = 'completed'
            }
            // Set next step as active if available
            if (stepIndex < aiMessage.steps.length - 1) {
              aiMessage.steps[stepIndex + 1].status = 'active'
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
          aiMessage.content = parsed.result || 'Task completed successfully.'
          aiMessage.sent = true
          // Mark all steps as completed
          aiMessage.steps.forEach(step => step.status = 'completed')
        }
        // Handle errors
        else if (parsed.status === 'failed' || parsed.status === 'error') {
          aiMessage.content = parsed.error || 'Task failed'
          aiMessage.sent = true
          aiMessage.error = true
          // Mark remaining steps as failed
          aiMessage.steps.forEach(step => {
            if (step.status === 'pending' || step.status === 'active') {
              step.status = 'failed'
            }
          })
        }
      } catch (e) {
        console.error('Error processing stream message:', e)
      }
    }

    eventSource.onerror = (error) => {
      console.error('EventSource error:', error)
      eventSource.close()
      activeTasks.value = Math.max(0, activeTasks.value - 1)
      
      // Only update message if it hasn't been completed
      if (!aiMessage.sent) {
        aiMessage.content = 'Error: Failed to get response from agent'
        aiMessage.sent = true
        aiMessage.error = true
        // Mark remaining steps as failed
        aiMessage.steps.forEach(step => {
          if (step.status === 'pending' || step.status === 'active') {
            step.status = 'failed'
          }
        })
      }
    }

  } catch (error) {
    console.error('Error:', error)
    activeTasks.value = Math.max(0, activeTasks.value - 1)
    
    // Update AI message with error
    aiMessage.content = `Error: ${error.message}`
    aiMessage.sent = true
    aiMessage.error = true
    // Mark all steps as failed
    aiMessage.steps.forEach(step => step.status = 'failed')
  }
}

const formatRelativeTime = (timestamp) => {
  const now = new Date()
  const time = new Date(timestamp)
  const diffMs = now - time
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return time.toLocaleDateString()
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const saveSettings = (newSettings) => {
  settings.value = { ...newSettings }
  localStorage.setItem('codegen-settings', JSON.stringify(settings.value))
  showSettings.value = false
  checkConnection()
  showNotification('Settings saved successfully!')
}

const checkConnection = async () => {
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 5000)
    
    const response = await fetch(`${settings.value.backendUrl}/api/v1/health`, {
      signal: controller.signal
    })
    
    clearTimeout(timeoutId)
    
    if (response.ok) {
      const data = await response.json()
      connectionStatus.value = {
        connected: true,
        message: data.codegen_available ? 'Connected' : 'Connected (Codegen SDK unavailable)',
        lastCheck: new Date()
      }
    } else {
      throw new Error(`HTTP ${response.status}`)
    }
  } catch (error) {
    connectionStatus.value = {
      connected: false,
      message: error.name === 'AbortError' ? 'Connection timeout' : 'Connection failed',
      lastCheck: new Date()
    }
  }
}

const showNotification = (message, type = 'info') => {
  notification.value = { show: true, message, type }
  setTimeout(() => {
    notification.value.show = false
  }, 3000)
}

const saveToLocalStorage = () => {
  localStorage.setItem('codegen-threads', JSON.stringify(threads.value))
  localStorage.setItem('codegen-current-thread', currentThreadId.value)
}

const loadFromLocalStorage = () => {
  const savedThreads = localStorage.getItem('codegen-threads')
  const savedCurrentThread = localStorage.getItem('codegen-current-thread')
  const savedSettings = localStorage.getItem('codegen-settings')

  if (savedThreads) {
    threads.value = JSON.parse(savedThreads)
  }

  if (savedCurrentThread && threads.value.find(t => t.id === savedCurrentThread)) {
    currentThreadId.value = savedCurrentThread
  } else if (threads.value.length > 0) {
    currentThreadId.value = threads.value[0].id
  }

  if (savedSettings) {
    settings.value = { ...settings.value, ...JSON.parse(savedSettings) }
  }
}

// Connection check interval
let connectionInterval = null

// Lifecycle
onMounted(() => {
  loadFromLocalStorage()
  checkConnection()
  
  // Check connection periodically
  connectionInterval = setInterval(checkConnection, 30000)
  
  // Create default thread if none exist
  if (threads.value.length === 0) {
    const defaultThread = {
      id: uuidv4(),
      name: 'General Chat',
      messages: [],
      createdAt: new Date(),
      lastActivity: new Date()
    }
    threads.value.push(defaultThread)
    currentThreadId.value = defaultThread.id
    saveToLocalStorage()
  }
})

onUnmounted(() => {
  if (connectionInterval) {
    clearInterval(connectionInterval)
  }
})

// Watch for thread changes to scroll to bottom
watch(currentThread, () => {
  nextTick(() => {
    scrollToBottom()
  })
}, { deep: true })
</script>
