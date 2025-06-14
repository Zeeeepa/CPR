<template>
  <div class="min-h-screen bg-slate-950 dark">
    <div class="container mx-auto px-4 py-6">
      <header class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold text-white">CPR Application</h1>
        <button 
          @click="showSettings = true" 
          class="bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          Settings
        </button>
      </header>
      
      <NuxtRouteAnnouncer />
      <NuxtPage />
      
      <SettingsModal v-if="showSettings" @close="showSettings = false" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useSettings } from '~/composables/useSettings'

// Initialize settings
useSettings()

// Control settings modal visibility
const showSettings = ref(false)
</script>

