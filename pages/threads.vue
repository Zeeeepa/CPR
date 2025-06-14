<template>
  <div class="container mx-auto p-4">
    <h1 class="text-2xl font-bold mb-6">Thread Management</h1>
    
    <div class="mb-6">
      <p class="text-gray-700 mb-2">
        This page allows you to create and manage threads for communication with the Codegen SDK Agent.
      </p>
      <p class="text-gray-700">
        You can create new threads, send messages, and view responses in real-time.
      </p>
    </div>
    
    <ThreadManager />
  </div>
</template>

<script setup lang="ts">
import ThreadManager from '~/components/ThreadManager.vue'
</script>

