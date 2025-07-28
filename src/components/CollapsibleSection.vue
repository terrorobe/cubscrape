<template>
  <div class="rounded-lg border border-gray-600 bg-bg-card">
    <!-- Section Header -->
    <button
      @click="toggleExpanded"
      class="flex w-full items-center justify-between p-4 text-left transition-colors hover:bg-bg-secondary/50"
    >
      <div class="flex items-center gap-3">
        <h3 class="text-sm font-semibold text-text-primary">{{ title }}</h3>
        <!-- Active filter count badge -->
        <span
          v-if="activeCount > 0"
          class="flex size-5 items-center justify-center rounded-full bg-accent text-xs font-medium text-white"
        >
          {{ activeCount }}
        </span>
      </div>

      <!-- Expand/Collapse Arrow -->
      <svg
        class="size-4 text-text-secondary transition-transform duration-200"
        :class="{ 'rotate-90': isExpanded }"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M9 5l7 7-7 7"
        />
      </svg>
    </button>

    <!-- Section Content -->
    <div v-show="isExpanded" class="border-t border-gray-600 p-4 pt-3">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

/**
 * Props interface for CollapsibleSection component
 */
export interface CollapsibleSectionProps {
  title: string
  activeCount?: number
  defaultExpanded?: boolean
}

const props = withDefaults(defineProps<CollapsibleSectionProps>(), {
  activeCount: 0,
  defaultExpanded: true,
})

const isExpanded = ref(props.defaultExpanded)

const toggleExpanded = (): void => {
  isExpanded.value = !isExpanded.value
}
</script>
