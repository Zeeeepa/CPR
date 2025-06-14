<template>
  <div class="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 backdrop-blur-sm">
    <div class="bg-slate-800 rounded-xl p-6 w-full max-w-md mx-4 border border-slate-700 shadow-2xl">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl font-semibold text-white">Settings</h2>
        <button
          @click="$emit('close')"
          class="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-slate-700 transition-colors"
        >
          <XMarkIcon class="w-6 h-6" />
        </button>
      </div>

      <form @submit.prevent="handleSave" class="space-y-5">
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-2">
            Codegen Token
          </label>
          <input
            v-model="localSettings.codegenToken"
            type="text"
            placeholder="sk-..."
            class="w-full bg-slate-700 text-white border border-slate-600 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
            required
          />
          <p class="text-xs text-gray-400 mt-2">
            Your Codegen API token for authentication
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-300 mb-2">
            Organization ID
          </label>
          <input
            v-model="localSettings.codegenOrgId"
            type="text"
            placeholder="323"
            class="w-full bg-slate-700 text-white border border-slate-600 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
            required
          />
          <p class="text-xs text-gray-400 mt-2">
            Your Codegen organization ID
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-300 mb-2">
            API Base URL (Optional)
          </label>
          <input
            v-model="localSettings.apiBaseUrl"
            type="text"
            placeholder="https://api.example.com"
            class="w-full bg-slate-700 text-white border border-slate-600 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
          />
          <p class="text-xs text-gray-400 mt-2">
            Custom API base URL (leave empty for default)
          </p>
        </div>

        <div class="flex gap-3 pt-4">
          <button
            type="button"
            @click="$emit('close')"
            class="flex-1 bg-slate-700 hover:bg-slate-600 text-white px-4 py-3 rounded-lg transition-colors font-medium"
          >
            Cancel
          </button>
          <button
            type="submit"
            class="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg transition-colors font-medium"
          >
            Save Settings
          </button>
        </div>
      </form>

      <div class="mt-6 pt-4 border-t border-slate-700">
        <h3 class="text-sm font-medium text-gray-300 mb-3">Environment Variables</h3>
        <div class="text-xs text-gray-400 space-y-2">
          <div class="flex items-center gap-2">
            <code class="bg-slate-700 px-2 py-1 rounded font-mono">CODEGEN_TOKEN</code>
            <span>Your API token</span>
          </div>
          <div class="flex items-center gap-2">
            <code class="bg-slate-700 px-2 py-1 rounded font-mono">CODEGEN_ORG_ID</code>
            <span>Your organization ID</span>
          </div>
          <div class="flex items-center gap-2">
            <code class="bg-slate-700 px-2 py-1 rounded font-mono">API_BASE_URL</code>
            <span>Custom API base URL</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { XMarkIcon } from '@heroicons/vue/24/outline'
import { useSettings } from '~/composables/useSettings'

const { settings, updateSetting } = useSettings()

// Create a local copy of settings for the form
const localSettings = ref({
  codegenToken: settings.value.codegenToken,
  codegenOrgId: settings.value.codegenOrgId,
  apiBaseUrl: settings.value.apiBaseUrl
})

// Update local settings when the global settings change
watch(() => settings.value, (newSettings) => {
  localSettings.value = {
    codegenToken: newSettings.codegenToken,
    codegenOrgId: newSettings.codegenOrgId,
    apiBaseUrl: newSettings.apiBaseUrl
  }
}, { deep: true })

const emit = defineEmits(['close'])

const handleSave = () => {
  // Update each setting individually
  updateSetting('codegenToken', localSettings.value.codegenToken)
  updateSetting('codegenOrgId', localSettings.value.codegenOrgId)
  updateSetting('apiBaseUrl', localSettings.value.apiBaseUrl)
  
  // Close the modal
  emit('close')
}
</script>

