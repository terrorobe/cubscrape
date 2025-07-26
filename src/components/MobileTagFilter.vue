<template>
  <div class="space-y-4">
    <!-- Logic Toggle -->
    <div v-if="selectedTags.length > 1">
      <label class="mb-2 block text-sm font-medium text-text-secondary"
        >Match Logic</label
      >
      <div class="flex rounded-lg bg-bg-primary p-1">
        <button
          @click="tagLogic = 'and'"
          class="flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors"
          :class="
            tagLogic === 'and'
              ? 'bg-accent text-white'
              : 'text-text-secondary hover:text-text-primary'
          "
        >
          All Tags (AND)
        </button>
        <button
          @click="tagLogic = 'or'"
          class="flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors"
          :class="
            tagLogic === 'or'
              ? 'bg-accent text-white'
              : 'text-text-secondary hover:text-text-primary'
          "
        >
          Any Tag (OR)
        </button>
      </div>
    </div>

    <!-- Search -->
    <div>
      <label class="mb-2 block text-sm font-medium text-text-secondary"
        >Search Tags</label
      >
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Type to search tags..."
        class="w-full rounded-lg border border-gray-600 bg-bg-card p-3 text-text-primary placeholder-text-secondary focus:border-accent focus:ring-2 focus:ring-accent/50 focus:outline-none"
      />
    </div>

    <!-- Selected Tags -->
    <div v-if="selectedTags.length > 0">
      <label class="mb-2 block text-sm font-medium text-text-secondary">
        Selected Tags ({{ selectedTags.length }})
      </label>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="tag in selectedTags"
          :key="`selected-${tag}`"
          @click="toggleTag(tag)"
          class="flex items-center gap-2 rounded-full bg-accent px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover active:bg-accent-active"
        >
          {{ tag }}
          <svg
            class="size-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            ></path>
          </svg>
        </button>
      </div>
    </div>

    <!-- Available Tags -->
    <div>
      <label class="mb-2 block text-sm font-medium text-text-secondary">
        Available Tags ({{ filteredAvailableTags.length }})
      </label>

      <!-- Clear button for search -->
      <div v-if="searchQuery" class="mb-2">
        <button
          @click="searchQuery = ''"
          class="text-sm text-accent hover:text-accent-hover"
        >
          Clear search
        </button>
      </div>

      <!-- No results message -->
      <div
        v-if="filteredAvailableTags.length === 0"
        class="py-4 text-center text-text-secondary"
      >
        <p v-if="searchQuery">No tags found matching "{{ searchQuery }}"</p>
        <p v-else>All tags are selected</p>
      </div>

      <!-- Tag list -->
      <div v-else class="max-h-64 space-y-1 overflow-y-auto">
        <button
          v-for="tag in filteredAvailableTags"
          :key="`available-${tag.name}`"
          @click="toggleTag(tag.name)"
          class="flex w-full items-center justify-between rounded-lg bg-bg-card p-3 text-left text-text-primary transition-colors hover:bg-bg-primary active:bg-bg-primary"
        >
          <span class="font-medium">{{ tag.name }}</span>
          <span class="text-sm text-text-secondary"
            >{{ tag.count }} game{{ tag.count !== 1 ? 's' : '' }}</span
          >
        </button>
      </div>
    </div>

    <!-- Quick Actions -->
    <div v-if="selectedTags.length > 0" class="border-t border-gray-600 pt-4">
      <button
        @click="clearAllTags"
        class="w-full rounded-lg border border-gray-600 px-4 py-3 text-text-secondary transition-colors hover:border-accent hover:text-accent"
      >
        Clear All Tags
      </button>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue'

export default {
  name: 'MobileTagFilter',
  props: {
    tagsWithCounts: {
      type: Array,
      default: () => [],
    },
    initialSelectedTags: {
      type: Array,
      default: () => [],
    },
    initialTagLogic: {
      type: String,
      default: 'and',
    },
  },
  emits: ['tags-changed'],
  setup(props, { emit }) {
    const selectedTags = ref([...props.initialSelectedTags])
    const tagLogic = ref(props.initialTagLogic)
    const searchQuery = ref('')

    const filteredAvailableTags = computed(() => {
      const available = props.tagsWithCounts.filter(
        (tag) => !selectedTags.value.includes(tag.name),
      )

      if (!searchQuery.value) {
        return available
      }

      const query = searchQuery.value.toLowerCase()
      return available.filter((tag) => tag.name.toLowerCase().includes(query))
    })

    const toggleTag = (tagName) => {
      const index = selectedTags.value.indexOf(tagName)
      if (index > -1) {
        selectedTags.value.splice(index, 1)
      } else {
        selectedTags.value.push(tagName)
      }
      emitChange()
    }

    const clearAllTags = () => {
      selectedTags.value = []
      emitChange()
    }

    const emitChange = () => {
      emit('tags-changed', {
        selectedTags: [...selectedTags.value],
        tagLogic: tagLogic.value,
      })
    }

    // Watch for logic changes
    watch(tagLogic, () => {
      if (selectedTags.value.length > 1) {
        emitChange()
      }
    })

    // Watch for prop changes
    watch(
      () => props.initialSelectedTags,
      (newTags) => {
        selectedTags.value = [...newTags]
      },
      { deep: true },
    )

    watch(
      () => props.initialTagLogic,
      (newLogic) => {
        tagLogic.value = newLogic
      },
    )

    return {
      selectedTags,
      tagLogic,
      searchQuery,
      filteredAvailableTags,
      toggleTag,
      clearAllTags,
    }
  },
}
</script>

<style scoped>
/* Custom scrollbar for tag list */
.overflow-y-auto::-webkit-scrollbar {
  width: 4px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: theme('colors.bg.primary');
  border-radius: 2px;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: theme('colors.text.secondary');
  border-radius: 2px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: theme('colors.text.primary');
}

/* Active states for better touch feedback */
.active\:bg-accent-active:active {
  background-color: theme('colors.accent') / 0.8;
}

.active\:bg-bg-primary:active {
  background-color: theme('colors.bg.primary');
}
</style>
