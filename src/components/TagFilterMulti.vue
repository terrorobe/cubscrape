<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import {
  useProgressiveOptions,
  type OptionWithCount,
} from '../composables/useProgressiveOptions'
import type { ProcessedGameData } from '../services/GameDataProcessingService'

/**
 * Tag item interface with name, count and popularity indicator
 */
export interface TagWithCount extends OptionWithCount {
  isPopular?: boolean
}

/**
 * Tag logic type for filtering
 */
export type TagLogic = 'and' | 'or'

/**
 * Tag filter change event payload
 */
export interface TagFilterChangeEvent {
  selectedTags: string[]
  tagLogic: TagLogic
}

/**
 * Props interface for TagFilterMulti component
 */
export interface TagFilterMultiProps {
  tagsWithCounts?: TagWithCount[]
  initialSelectedTags?: string[]
  initialTagLogic?: TagLogic
  loadTags?: () => void
  filteredGames?: ProcessedGameData[]
}

const props = withDefaults(defineProps<TagFilterMultiProps>(), {
  tagsWithCounts: () => [],
  initialSelectedTags: () => [],
  initialTagLogic: 'and',
  loadTags: undefined,
  filteredGames: () => [],
})

// Loading state for lazy loading
const isLoading = ref<boolean>(false)

const emit = defineEmits<{
  tagsChanged: [event: TagFilterChangeEvent]
}>()
const searchInput = ref<HTMLInputElement | null>(null)
const searchQuery = ref<string>('')
const showDropdown = ref<boolean>(false)

// Track if tags have been loaded for lazy loading
const hasLoadedTags = ref<boolean>(props.tagsWithCounts.length > 0)
const selectedTags = ref<string[]>([...props.initialSelectedTags])
const tagLogic = ref<TagLogic>(props.initialTagLogic)

// Dynamic tag counts based on current filter mode and filtered games
const dynamicTagCounts = computed((): TagWithCount[] => {
  // In OR mode or when no filtered games available, use original counts
  if (
    tagLogic.value === 'or' ||
    !props.filteredGames ||
    props.filteredGames.length === 0
  ) {
    return props.tagsWithCounts.map((tag) => ({
      ...tag,
      isPopular: false, // No longer using popular tags feature
    }))
  }

  // In AND mode, calculate counts based on filtered result set
  const tagCountMap = new Map<string, number>()

  // Count occurrences of each tag in the filtered games
  props.filteredGames.forEach((game) => {
    if (game.tags && Array.isArray(game.tags)) {
      game.tags.forEach((tag: string) => {
        tagCountMap.set(tag, (tagCountMap.get(tag) || 0) + 1)
      })
    }
  })

  // Update counts while preserving all original tags (including zero-count ones)
  return props.tagsWithCounts.map((tag) => ({
    ...tag,
    count: tagCountMap.get(tag.name) || 0,
    isPopular: false,
  }))
})

// All tags with metadata
const tagsWithMetadata = computed((): TagWithCount[] => dynamicTagCounts.value)

// Filtered tags based on search query
const filteredTags = computed((): TagWithCount[] => {
  if (!searchQuery.value.trim()) {
    return [...tagsWithMetadata.value].sort((a, b) => {
      // Sort by popularity first, then by count, then alphabetically
      if (a.isPopular && !b.isPopular) {
        return -1
      }
      if (!a.isPopular && b.isPopular) {
        return 1
      }
      if (a.count !== b.count) {
        return b.count - a.count
      }
      return a.name.localeCompare(b.name)
    })
  }

  const query = searchQuery.value.toLowerCase()
  return tagsWithMetadata.value
    .filter((tag) => tag.name.toLowerCase().includes(query))
    .sort((a, b) => {
      // Exact matches first
      const aExact = a.name.toLowerCase() === query
      const bExact = b.name.toLowerCase() === query
      if (aExact && !bExact) {
        return -1
      }
      if (!aExact && bExact) {
        return 1
      }

      // Then by popularity
      if (a.isPopular && !b.isPopular) {
        return -1
      }
      if (!a.isPopular && b.isPopular) {
        return 1
      }

      // Then by count
      return b.count - a.count
    })
})

// Progressive loading for tags
const {
  visibleOptions: visibleFilteredTags,
  isLoading: isLoadingTags,
  hasMore: hasMoreTags,
  loadMore: loadMoreTags,
  updateSearch: updateTagSearch,
} = useProgressiveOptions(filteredTags, 20, 15)

// Additional computed properties for UI
const remainingTagCount = computed(
  (): number => filteredTags.value.length - visibleFilteredTags.value.length,
)

// Preview text for result count
const previewText = computed((): string => {
  if (selectedTags.value.length === 0) {
    return ''
  }
  if (selectedTags.value.length === 1) {
    return `Games with "${selectedTags.value[0]}"`
  }

  const logic = tagLogic.value.toUpperCase()
  return `${logic} filter active`
})

// Logic explanation
const logicExplanation = computed((): string => {
  if (selectedTags.value.length <= 1) {
    return ''
  }

  const count = selectedTags.value.length
  if (tagLogic.value === 'and') {
    return `Games must have all ${count} selected tags`
  } else {
    return `Games must have any of the ${count} selected tags`
  }
})

const toggleTag = (tagName: string): void => {
  const index = selectedTags.value.indexOf(tagName)
  if (index > -1) {
    selectedTags.value.splice(index, 1)
  } else {
    selectedTags.value.push(tagName)
  }
  emitFiltersChanged()
}

const removeTag = (tagName: string): void => {
  const index = selectedTags.value.indexOf(tagName)
  if (index > -1) {
    selectedTags.value.splice(index, 1)
    emitFiltersChanged()
  }
}

const clearAllTags = (): void => {
  selectedTags.value = []
  emitFiltersChanged()
}

const clearSearch = (): void => {
  searchQuery.value = ''
  if (searchInput.value) {
    searchInput.value.focus()
  }
  // Keep dropdown visible after clearing search
  showDropdown.value = true
}

const filterTags = (): void => {
  // Update the progressive loading search
  updateTagSearch(searchQuery.value)
  // Show dropdown when typing
  if (!showDropdown.value) {
    showDropdown.value = true
  }
}

// Watch for search changes to update progressive loading
watch(searchQuery, (newQuery: string) => {
  updateTagSearch(newQuery)
})

// Watch for tags prop changes to update loading state
watch(
  () => props.tagsWithCounts,
  (newTags: TagWithCount[]) => {
    if (newTags.length > 0 && !hasLoadedTags.value) {
      hasLoadedTags.value = true
      isLoading.value = false
    }
  },
  { deep: true },
)

// Handle lazy loading when dropdown is opened
const handleDropdownOpen = async (): Promise<void> => {
  showDropdown.value = true

  if (!hasLoadedTags.value && props.loadTags) {
    isLoading.value = true
    props.loadTags()
  }
}

const emitFiltersChanged = (): void => {
  emit('tagsChanged', {
    selectedTags: [...selectedTags.value],
    tagLogic: tagLogic.value,
  })
}

// Handle clicking outside to close dropdown
const handleClickOutside = (event: Event): void => {
  const input = searchInput.value
  const dropdown = input?.parentElement?.nextElementSibling

  if (
    input &&
    event.target &&
    !input.contains(event.target as Node) &&
    dropdown &&
    !dropdown.contains(event.target as Node)
  ) {
    showDropdown.value = false
  }
}

// Watch for changes in initial props
watch(
  () => props.initialSelectedTags,
  (newTags: string[]) => {
    selectedTags.value = [...newTags]
  },
  { deep: true },
)

watch(
  () => props.initialTagLogic,
  (newLogic: TagLogic) => {
    tagLogic.value = newLogic
  },
)

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div class="space-y-3">
    <!-- Logic Toggle -->
    <div
      class="mb-3 flex items-center gap-4 rounded-lg border border-gray-600 bg-bg-card p-3"
    >
      <span class="text-sm text-text-secondary">Match:</span>
      <div class="flex gap-4">
        <label
          class="flex min-w-[3.5rem] cursor-pointer items-center gap-1.5"
          title="Games must have ANY of the selected tags"
        >
          <input
            type="radio"
            value="or"
            v-model="tagLogic"
            @change="emitFiltersChanged"
            class="text-accent focus:ring-accent"
          />
          <span class="text-sm font-medium">Any</span>
        </label>
        <label
          class="flex min-w-[3.5rem] cursor-pointer items-center gap-1.5"
          title="Games must have ALL of the selected tags"
        >
          <input
            type="radio"
            value="and"
            v-model="tagLogic"
            @change="emitFiltersChanged"
            class="text-accent focus:ring-accent"
          />
          <span class="text-sm font-medium">All</span>
        </label>
      </div>
    </div>

    <!-- Selected Tags Display -->
    <div v-if="selectedTags.length > 0" class="mb-3">
      <div class="mb-2 flex items-center justify-between">
        <span class="text-sm font-medium"
          >Selected Tags ({{ selectedTags.length }})</span
        >
        <button
          @click="clearAllTags"
          class="text-sm text-accent hover:underline"
        >
          Clear All
        </button>
      </div>
      <div
        class="flex min-h-[3rem] flex-wrap gap-2 rounded-sm border border-gray-600 bg-bg-card p-3"
      >
        <span
          v-for="tag in selectedTags"
          :key="tag"
          class="flex items-center gap-2 rounded-full bg-accent/20 px-3 py-1.5 text-sm text-accent"
        >
          {{ tag }}
          <button
            @click="removeTag(tag)"
            class="flex size-4 items-center justify-center rounded-full text-xs text-accent/70 transition-colors hover:bg-accent/20 hover:text-accent"
          >
            ×
          </button>
        </span>
      </div>
    </div>

    <!-- Search Input -->
    <div class="relative mb-2">
      <input
        ref="searchInput"
        type="text"
        v-model="searchQuery"
        placeholder="Search tags..."
        class="w-full rounded-sm border border-gray-600 bg-bg-card px-4 py-2 pl-10 text-sm transition-colors hover:border-accent focus:border-accent focus:outline-none"
        @focus="handleDropdownOpen"
        @input="filterTags"
      />
      <svg
        class="pointer-events-none absolute top-2.5 left-3 size-4 text-text-secondary"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        ></path>
      </svg>
      <button
        v-if="searchQuery"
        @click="clearSearch"
        class="absolute top-2.5 right-3 size-4 text-text-secondary transition-colors hover:text-text-primary"
      >
        ×
      </button>
    </div>

    <!-- Loading indicator -->
    <div v-if="isLoading" class="py-4 text-center text-sm text-text-secondary">
      Loading tags...
    </div>

    <!-- Tag Dropdown -->
    <div
      v-show="showDropdown && (filteredTags.length > 0 || !hasLoadedTags)"
      class="relative z-10"
    >
      <div
        class="max-h-64 overflow-hidden rounded-sm border border-gray-600 bg-bg-card shadow-lg"
      >
        <div class="max-h-64 overflow-y-auto">
          <!-- Show loading message when tags are being fetched -->
          <div
            v-if="isLoading && !hasLoadedTags"
            class="p-4 text-center text-sm text-text-secondary"
          >
            Loading tags...
          </div>
          <div
            v-else
            v-for="tag in visibleFilteredTags"
            :key="tag.name"
            class="flex cursor-pointer items-center gap-3 rounded-sm p-2 transition-colors hover:bg-bg-secondary"
            @click="toggleTag(tag.name)"
          >
            <input
              type="checkbox"
              :checked="selectedTags.includes(tag.name)"
              @click.stop="toggleTag(tag.name)"
              class="text-accent focus:ring-accent"
            />
            <span class="flex-1 text-sm">{{ tag.name }}</span>
            <div class="flex items-center gap-2">
              <span class="text-xs text-text-secondary">({{ tag.count }})</span>
              <div
                v-if="tag.isPopular"
                class="size-2 rounded-full bg-green-500"
                title="Popular tag"
              ></div>
            </div>
          </div>

          <!-- Load More Button -->
          <div
            v-if="hasMoreTags && !searchQuery && hasLoadedTags"
            class="border-t border-gray-600 p-2"
          >
            <button
              @click.stop="loadMoreTags"
              :disabled="isLoadingTags"
              class="w-full rounded-sm bg-bg-secondary p-2 text-sm text-text-secondary transition-colors hover:bg-accent/10 hover:text-accent disabled:opacity-50"
            >
              <span v-if="isLoadingTags">Loading...</span>
              <span v-else
                >Load More Tags ({{ remainingTagCount }} remaining)</span
              >
            </button>
          </div>
        </div>

        <!-- Tags Count Footer -->
        <div
          v-if="filteredTags.length > 0 && hasLoadedTags"
          class="border-t border-gray-600 bg-bg-secondary p-3 text-center"
        >
          <span class="text-sm text-text-secondary">
            {{ visibleFilteredTags.length }} of {{ filteredTags.length }} tags
            shown
          </span>
        </div>
      </div>
    </div>

    <!-- Result Preview -->
    <div
      v-if="selectedTags.length > 0"
      class="mt-2 rounded-sm border border-gray-600 bg-bg-card p-3"
    >
      <div class="text-sm text-text-secondary">
        <div class="flex items-center justify-between">
          <span>Filter Preview:</span>
          <span class="font-medium text-accent">{{ previewText }}</span>
        </div>
        <div class="mt-1 text-xs">
          {{ logicExplanation }}
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-if="tagsWithCounts.length === 0 && hasLoadedTags && !isLoading"
      class="py-8 text-center text-text-secondary"
    >
      <svg
        class="mx-auto mb-3 size-12 opacity-50"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
        ></path>
      </svg>
      <div class="text-sm">No tags available</div>
    </div>
  </div>
</template>
