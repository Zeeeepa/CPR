<template>
  <div
    class="flex gap-3 mb-6"
    :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
  >
    <div
      class="max-w-4xl rounded-xl p-5 relative group shadow-lg"
      :class="[
        message.role === 'user'
          ? 'bg-blue-600 text-white'
          : 'bg-slate-800 text-gray-100 border border-slate-700'
      ]"
    >
      <!-- Message Header -->
      <div class="flex items-center gap-3 mb-3">
        <div
          class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold"
          :class="[
            message.role === 'user'
              ? 'bg-blue-700 text-white'
              : 'bg-slate-700 text-gray-300'
          ]"
        >
          {{ message.role === 'user' ? 'U' : 'AI' }}
        </div>
        <div class="flex-1">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium">
              {{ message.role === 'user' ? 'You' : 'Codegen AI' }}
            </span>
            <span class="text-xs opacity-60">
              {{ formatTime(message.timestamp) }}
            </span>
          </div>
          
          <!-- Status Badge -->
          <div v-if="message.status && message.status !== 'completed'" class="mt-1">
            <span
              class="status-badge"
              :class="message.status"
            >
              <div class="pulse-dot" :class="message.status"></div>
              {{ getStatusText(message.status) }}
            </span>
          </div>
        </div>
        
        <!-- Copy button -->
        <button
          v-if="message.content"
          @click="copyMessage"
          class="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-black hover:bg-opacity-20 transition-all"
          title="Copy message"
        >
          <ClipboardIcon class="w-4 h-4" />
        </button>
      </div>
      
      <!-- Progress Steps (for AI messages) -->
      <div v-if="message.role === 'assistant' && message.steps && !message.content" class="mb-4">
        <div class="space-y-2">
          <div
            v-for="step in message.steps"
            :key="step.id"
            class="progress-step"
            :class="step.status"
          >
            <div class="flex-shrink-0">
              <div v-if="step.status === 'pending'" class="w-5 h-5 border-2 border-current rounded-full opacity-50"></div>
              <div v-else-if="step.status === 'active'" class="w-5 h-5">
                <div class="animate-spin rounded-full h-5 w-5 border-2 border-current border-t-transparent"></div>
              </div>
              <div v-else-if="step.status === 'completed'" class="w-5 h-5 bg-current rounded-full flex items-center justify-center">
                <CheckIcon class="w-3 h-3 text-slate-900" />
              </div>
              <div v-else-if="step.status === 'failed'" class="w-5 h-5 bg-current rounded-full flex items-center justify-center">
                <XMarkIcon class="w-3 h-3 text-slate-900" />
              </div>
            </div>
            <div class="flex-1">
              <div class="text-sm font-medium">{{ step.title }}</div>
              <div v-if="step.description" class="text-xs opacity-75 mt-1">{{ step.description }}</div>
              <div v-if="step.duration" class="text-xs opacity-60 mt-1">{{ step.duration }}ms</div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Message Content -->
      <div
        v-if="message.role === 'user'"
        class="whitespace-pre-wrap break-words text-base"
      >
        {{ message.content }}
      </div>
      
      <div
        v-else-if="message.content"
        class="markdown-content prose prose-invert max-w-none"
        v-html="renderMarkdown(message.content)"
      ></div>

      <div
        v-else-if="message.role === 'assistant' && !message.content && !message.steps"
        class="flex items-center gap-2 text-sm opacity-75"
      >
        <div class="animate-spin rounded-full h-4 w-4 border-2 border-current border-t-transparent"></div>
        <span>Waiting for response...</span>
      </div>

      <!-- Task Information -->
      <div
        v-if="message.taskId || message.webUrl"
        class="mt-4 pt-3 border-t border-opacity-20 space-y-2"
        :class="message.role === 'user' ? 'border-blue-400' : 'border-slate-600'"
      >
        <div class="text-xs opacity-70">
          <div v-if="message.taskId" class="flex items-center gap-2">
            <span class="font-mono bg-slate-700 px-2 py-1 rounded">{{ message.taskId }}</span>
            <span>Task ID</span>
          </div>
          <div v-if="message.webUrl" class="mt-2">
            <a 
              :href="message.webUrl" 
              target="_blank" 
              class="inline-flex items-center gap-2 text-blue-300 hover:text-blue-200 underline transition-colors"
            >
              <span>View in Codegen</span>
              <ArrowTopRightOnSquareIcon class="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>

      <!-- Loading indicator for pending messages -->
      <div
        v-if="message.status === 'pending' || message.status === 'running'"
        class="mt-3 flex items-center gap-3 text-sm opacity-75"
      >
        <div class="animate-spin rounded-full h-4 w-4 border-2 border-current border-t-transparent"></div>
        <span>{{ getStatusText(message.status) }}</span>
        <div v-if="message.estimatedTime" class="text-xs opacity-60">
          ~{{ message.estimatedTime }}s remaining
        </div>
      </div>

      <!-- Debug information (only in development) -->
      <div v-if="showDebugInfo && message.role === 'assistant'" class="mt-4 pt-3 border-t border-gray-700 text-xs font-mono">
        <div class="text-gray-400 mb-1">Debug Info:</div>
        <div class="bg-gray-900 p-2 rounded overflow-auto max-h-40">
          <div><span class="text-blue-400">taskId:</span> {{ message.taskId || 'null' }}</div>
          <div><span class="text-blue-400">webUrl:</span> {{ message.webUrl || 'null' }}</div>
          <div><span class="text-blue-400">status:</span> {{ message.status || 'null' }}</div>
          <div><span class="text-blue-400">sent:</span> {{ message.sent }}</div>
          <div><span class="text-blue-400">error:</span> {{ message.error || false }}</div>
          <div><span class="text-blue-400">timestamp:</span> {{ message.timestamp }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { marked } from 'marked'
import { 
  ClipboardIcon, 
  CheckIcon, 
  XMarkIcon,
  ArrowTopRightOnSquareIcon 
} from '@heroicons/vue/24/outline'

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['copy'])

// Enable debug info in development mode
const showDebugInfo = ref(process.env.NODE_ENV === 'development' || window.location.hostname === 'localhost')

// Configure marked for better code highlighting
marked.setOptions({
  highlight: function(code, lang) {
    return code;
  },
  breaks: true,
  gfm: true
})

const renderMarkdown = (content) => {
  if (!content) return ''
  
  try {
    // Check if content is an error message and handle it specially
    if (typeof content === 'string' && content.startsWith('Error:')) {
      // For error messages, we'll still render them as markdown but with special styling
      const sanitizedContent = content
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
      
      return `<div class="error-message">${marked(sanitizedContent)}</div>`
    }
    
    // Ensure content is a string
    const stringContent = typeof content === 'string' ? content : String(content)
    
    // Sanitize content to prevent XSS
    const sanitizedContent = stringContent
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
    
    // Process markdown
    return marked(sanitizedContent)
  } catch (error) {
    console.error('Error rendering markdown:', error)
    // Return a fallback message if rendering fails
    return `<div class="error-message">Error rendering content: ${error.message}</div>`
  }
}

const formatTime = (timestamp) => {
  try {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  } catch (error) {
    console.error('Error formatting time:', error)
    return 'Invalid time'
  }
}

const getStatusText = (status) => {
  if (!status) return 'Unknown'
  
  switch (status) {
    case 'pending':
      return 'Queued'
    case 'queued':
      return 'In Queue'
    case 'running':
    case 'active':
    case 'initiated':
      return 'Processing'
    case 'completed':
      return 'Completed'
    case 'failed':
    case 'error':
      return 'Failed'
    case 'timeout':
      return 'Timed Out'
    default:
      return status
  }
}

const copyMessage = async () => {
  try {
    await navigator.clipboard.writeText(props.message.content)
    emit('copy', 'Message copied to clipboard!')
  } catch (err) {
    console.error('Failed to copy message:', err)
    emit('copy', 'Failed to copy message')
  }
}
</script>

<style scoped>
.progress-step {
  @apply flex items-center gap-3 p-2 rounded-lg transition-all duration-300;
}

.progress-step.pending {
  @apply text-gray-400 bg-gray-800/30;
}

.progress-step.active {
  @apply text-blue-400 bg-blue-900/20 border border-blue-800/30;
}

.progress-step.completed {
  @apply text-green-400 bg-green-900/20;
}

.progress-step.failed {
  @apply text-red-400 bg-red-900/20;
}

/* Add styles for error messages */
:deep(.error-message) {
  @apply text-gray-100;
}

/* Add styles for status badges */
.status-badge {
  @apply inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full;
}

.status-badge.pending, .status-badge.queued {
  @apply bg-gray-700 text-gray-300;
}

.status-badge.running, .status-badge.active, .status-badge.initiated {
  @apply bg-blue-900/50 text-blue-300;
}

.status-badge.completed {
  @apply bg-green-900/50 text-green-300;
}

.status-badge.failed, .status-badge.error, .status-badge.timeout {
  @apply bg-red-900/50 text-red-300;
}

/* Pulse animation for active status */
.pulse-dot {
  @apply w-2 h-2 rounded-full mr-1;
}

.pulse-dot.running, .pulse-dot.active, .pulse-dot.initiated {
  @apply bg-blue-400 animate-pulse;
}

.pulse-dot.pending, .pulse-dot.queued {
  @apply bg-gray-400;
}

.pulse-dot.completed {
  @apply bg-green-400;
}

.pulse-dot.failed, .pulse-dot.error, .pulse-dot.timeout {
  @apply bg-red-400;
}
</style>

