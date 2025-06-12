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
            <SpinnerIcon class="w-4 h-4 animate-spin" />
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
            <span class="text-sm">{{ connected ? 'Connected' : 'Disconnected' }}</span>
            <div
              class="w-2 h-2 rounded-full"
              :class="connected ? 'bg-green-500' : 'bg-red-500'"
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
  SpinnerIcon
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
const connected = ref(true)
const activeTasks = ref(0)
const messagesContainer = ref<HTMLElement | null>(null)

// Settings
const settings = ref({
  backendUrl: process.env.BACKEND_URL || 'http://localhost:8002',
  orgId: '',
  token: '',
  apiBaseUrl: ''
})

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
})

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
      { id: 1, title: 'Initializing Agent', description: 'Setting up the AI agent', status: 'active' },
      { id: 2, title: 'Processing Request', description: 'Analyzing your prompt', status: 'pending' },
      { id: 3, title: 'Generating Response', description: 'Creating the response', status: 'pending' },
      { id: 4, title: 'Finalizing', description: 'Completing the task', status: 'pending' }
    ],
    taskId: null,
    webUrl: null
  }
  currentThread.value.messages.push(aiMessage)
  saveToLocalStorage()
  scrollToBottom()

  try {
    activeTasks.value++
    const requestId = Date.now().toString(36) + Math.random().toString(36).substr(2, 5)
    console.log(`[${requestId}] === STARTING NEW TASK ===`)
    console.log(`[${requestId}] Prompt:`, prompt)
    console.log(`[${requestId}] Settings:`, {
      backendUrl: settings.value.backendUrl,
      orgId: settings.value.orgId ? settings.value.orgId.substring(0, 8) + '...' : 'None',
      token: settings.value.token ? '***' + settings.value.token.slice(-4) : 'None',
      apiBaseUrl: settings.value.apiBaseUrl
    })

    // Initial request to start the task
    console.log(`[${requestId}] Making request to:`, `${settings.value.backendUrl}/api/v1/run-task`)
    const requestBody = {
      prompt,
      stream: true,
      thread_id: currentThread.value.id
    }
    console.log(`[${requestId}] Request body:`, requestBody)
    
    const response = await fetch(`${settings.value.backendUrl}/api/v1/run-task`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Organization-ID': settings.value.orgId,
        'X-API-Token': settings.value.token,
        'X-API-Base-URL': settings.value.apiBaseUrl || ''
      },
      body: JSON.stringify(requestBody)
    })

    console.log(`[${requestId}] Response status:`, response.status)
    console.log(`[${requestId}] Response headers:`, Object.fromEntries(response.headers.entries()))

    if (!response.ok) {
      const errorText = await response.text()
      console.error(`[${requestId}] HTTP error response:`, errorText)
      throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`)
    }

    const data = await response.json()
    console.log(`[${requestId}] Task started successfully:`, data)

    // Update AI message with task ID
    if (data.task_id) {
      aiMessage.taskId = data.task_id
    }

    // Connect to SSE stream for updates
    const streamUrl = `${settings.value.backendUrl}/api/v1/task/${data.task_id}/stream`
    console.log(`[${requestId}] Connecting to stream:`, streamUrl)
    const eventSource = new EventSource(streamUrl)
    
    eventSource.onmessage = (event) => {
      try {
        console.log(`[${requestId}] Stream event received:`, event.data)
        
        if (event.data === '[DONE]') {
          console.log(`[${requestId}] Stream completed`)
          clearTimeout(timeoutId)
          eventSource.close()
          activeTasks.value = Math.max(0, activeTasks.value - 1)
          return
        }

        const parsed = JSON.parse(event.data)
        console.log(`[${requestId}] Stream update parsed:`, parsed)

        // Update step information based on current_step or status
        if (aiMessage.steps) {
          if (parsed.current_step) {
            // Map current_step to our step progression
            let currentStepIndex = -1
            const stepLower = parsed.current_step.toLowerCase()
            
            if (stepLower.includes('initializing') || stepLower.includes('setup')) {
              currentStepIndex = 0
            } else if (stepLower.includes('processing') || stepLower.includes('analyzing')) {
              currentStepIndex = 1
            } else if (stepLower.includes('generating') || stepLower.includes('creating')) {
              currentStepIndex = 2
            } else if (stepLower.includes('finalizing') || stepLower.includes('completing')) {
              currentStepIndex = 3
            }
            
            if (currentStepIndex >= 0) {
              // Mark previous steps as completed
              for (let i = 0; i <= currentStepIndex; i++) {
                if (aiMessage.steps[i]) {
                  aiMessage.steps[i].status = 'completed'
                }
              }
              // Set next step as active if available
              if (currentStepIndex < aiMessage.steps.length - 1 && aiMessage.steps[currentStepIndex + 1]) {
                aiMessage.steps[currentStepIndex + 1].status = 'active'
              }
            }
          } else if (parsed.status === 'running' || parsed.status === 'active') {
            // If no specific step but task is running, progress through steps
            const completedSteps = aiMessage.steps.filter(s => s.status === 'completed').length
            if (completedSteps < aiMessage.steps.length - 1) {
              const nextStepIndex = completedSteps
              if (aiMessage.steps[nextStepIndex] && aiMessage.steps[nextStepIndex].status !== 'active') {
                aiMessage.steps[nextStepIndex].status = 'active'
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
          aiMessage.content = parsed.result || 'Task completed successfully.'
          aiMessage.sent = true
          // Mark all steps as completed
          if (aiMessage.steps) {
            aiMessage.steps.forEach(step => step.status = 'completed')
          }
          currentThread.value!.lastActivity = new Date()
          saveToLocalStorage()
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

    // Add timeout to prevent infinite spinning
    const timeoutId = setTimeout(() => {
      console.warn('Task timeout after 5 minutes')
      eventSource.close()
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
      console.error(`[${requestId}] EventSource error:`, error)
      console.error(`[${requestId}] EventSource readyState:`, eventSource.readyState)
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
    console.error(`[${requestId}] Critical error in sendMessage:`, error)
    console.error(`[${requestId}] Error details:`, {
      name: error.name,
      message: error.message,
      stack: error.stack
    })
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
