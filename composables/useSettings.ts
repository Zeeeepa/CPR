import { ref, reactive, watch } from 'vue'

interface Settings {
  codegenOrgId: string
  codegenToken: string
  apiBaseUrl: string
}

// Create a reactive settings object with default values
const settings = ref<Settings>({
  codegenOrgId: '',
  codegenToken: '',
  apiBaseUrl: ''
})

// Load settings from localStorage on initialization
const loadSettings = () => {
  const savedSettings = localStorage.getItem('cpr_settings')
  if (savedSettings) {
    try {
      const parsed = JSON.parse(savedSettings)
      settings.value = {
        ...settings.value,
        ...parsed
      }
    } catch (error) {
      console.error('Failed to parse saved settings:', error)
    }
  } else {
    // Try to load from environment variables if available
    const envOrgId = import.meta.env.VITE_CODEGEN_ORG_ID
    const envToken = import.meta.env.VITE_CODEGEN_TOKEN
    const envApiBaseUrl = import.meta.env.VITE_API_BASE_URL

    if (envOrgId || envToken || envApiBaseUrl) {
      settings.value = {
        codegenOrgId: envOrgId || '',
        codegenToken: envToken || '',
        apiBaseUrl: envApiBaseUrl || ''
      }
      // Save to localStorage for future use
      saveSettings()
    }
  }
}

// Save settings to localStorage
const saveSettings = () => {
  localStorage.setItem('cpr_settings', JSON.stringify(settings.value))
}

// Update a specific setting
const updateSetting = (key: keyof Settings, value: string) => {
  settings.value = {
    ...settings.value,
    [key]: value
  }
  saveSettings()
}

// Watch for changes and save to localStorage
watch(settings, () => {
  saveSettings()
}, { deep: true })

// Initialize settings on first import
loadSettings()

// Export the composable
export function useSettings() {
  return {
    settings,
    updateSetting,
    loadSettings,
    saveSettings
  }
}

