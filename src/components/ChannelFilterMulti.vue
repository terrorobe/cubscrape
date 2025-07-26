<template>
  <div class="flex flex-col gap-1">
    <label class="text-sm text-text-secondary">Channels:</label>

    <!-- Selected Channels Display -->
    <div v-if="selectedChannels.length > 0" class="mb-3">
      <div class="mb-2 flex items-center justify-between">
        <span class="text-sm font-medium"
          >Selected Channels ({{ selectedChannels.length }})</span
        >
        <button
          @click="clearAllChannels"
          class="text-sm text-accent hover:underline"
        >
          Clear All
        </button>
      </div>
      <div
        class="flex min-h-[3rem] flex-wrap gap-2 rounded-sm border border-gray-600 bg-bg-card p-3"
      >
        <span
          v-for="channel in selectedChannels"
          :key="channel"
          class="flex items-center gap-2 rounded-full bg-accent/20 px-3 py-1.5 text-sm text-accent"
        >
          {{ formatChannelName(channel) }}
          <button
            @click="removeChannel(channel)"
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
        placeholder="Search channels..."
        class="w-full rounded-sm border border-gray-600 bg-bg-card px-4 py-2 pl-10 text-sm transition-colors hover:border-accent focus:border-accent focus:outline-none"
        @focus="showDropdown = true"
        @input="filterChannels"
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

    <!-- Channel Grid/List Display -->
    <div class="mb-2">
      <!-- Desktop: Grid layout for larger screens -->
      <div class="hidden grid-cols-2 gap-3 sm:grid lg:grid-cols-4">
        <label
          v-for="channel in filteredChannels"
          :key="channel.name"
          :class="[
            'flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-all hover:border-accent/50',
            selectedChannels.includes(channel.name)
              ? 'border-accent/50 bg-accent/10'
              : 'border-gray-600 bg-bg-card hover:bg-bg-secondary',
          ]"
          @click="toggleChannel(channel.name)"
        >
          <input
            type="checkbox"
            :checked="selectedChannels.includes(channel.name)"
            @click.stop
            @change="toggleChannel(channel.name)"
            class="text-accent focus:ring-accent"
          />
          <div class="min-w-0 flex-1">
            <div class="mb-1 flex items-center gap-2">
              <div
                class="size-3 shrink-0 rounded-full"
                :class="getChannelColor(channel.name)"
              ></div>
              <span class="truncate text-sm font-medium">{{
                formatChannelName(channel.name)
              }}</span>
            </div>
            <div class="text-xs text-text-secondary">
              {{ channel.count }} games
            </div>
          </div>
        </label>
      </div>

      <!-- Mobile: List layout for smaller screens -->
      <div class="space-y-2 sm:hidden">
        <label
          v-for="channel in filteredChannels"
          :key="channel.name"
          :class="[
            'flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-all hover:border-accent/50',
            selectedChannels.includes(channel.name)
              ? 'border-accent/50 bg-accent/10'
              : 'border-gray-600 bg-bg-card hover:bg-bg-secondary',
          ]"
          @click="toggleChannel(channel.name)"
        >
          <input
            type="checkbox"
            :checked="selectedChannels.includes(channel.name)"
            @click.stop
            @change="toggleChannel(channel.name)"
            class="text-accent focus:ring-accent"
          />
          <div
            class="size-3 shrink-0 rounded-full"
            :class="getChannelColor(channel.name)"
          ></div>
          <div class="min-w-0 flex-1">
            <span class="text-sm font-medium">{{
              formatChannelName(channel.name)
            }}</span>
            <span class="ml-2 text-xs text-text-secondary"
              >({{ channel.count }} games)</span
            >
          </div>
        </label>
      </div>
    </div>

    <!-- Quick Select Actions -->
    <div v-if="!searchQuery && channelsWithCounts.length > 0" class="mb-2">
      <div class="flex flex-wrap gap-2 text-sm">
        <button @click="selectAllChannels" class="text-accent hover:underline">
          Select All
        </button>
        <span class="text-text-secondary">•</span>
        <button
          @click="selectPopularChannels"
          class="text-accent hover:underline"
        >
          Select Top 4
        </button>
      </div>
    </div>

    <!-- Result Preview -->
    <div
      v-if="selectedChannels.length > 0"
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
      v-if="channelsWithCounts.length === 0"
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
          d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
        ></path>
      </svg>
      <div class="text-sm">No channels available</div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

export default {
  name: 'ChannelFilterMulti',
  props: {
    channelsWithCounts: {
      type: Array,
      default: () => [],
    },
    initialSelectedChannels: {
      type: Array,
      default: () => [],
    },
  },
  emits: ['channels-changed'],
  setup(props, { emit }) {
    const searchInput = ref(null)
    const searchQuery = ref('')
    const showDropdown = ref(false)
    const selectedChannels = ref([...props.initialSelectedChannels])

    // Define consistent colors for channels
    const channelColors = {
      'videos-dextag': 'bg-red-500',
      'videos-nookrium': 'bg-blue-500',
      'videos-wanderbots': 'bg-green-500',
      'videos-aliensrock': 'bg-purple-500',
      'videos-olexa': 'bg-yellow-500',
      'videos-idlecub': 'bg-pink-500',
      'videos-orbitalpotato': 'bg-indigo-500',
      'videos-splattercatgaming': 'bg-orange-500',
    }

    const getChannelColor = (channelName) => {
      return channelColors[channelName] || 'bg-gray-500'
    }

    // Top channels by game count (for quick select)
    const popularChannels = computed(() => {
      return props.channelsWithCounts
        .slice()
        .sort((a, b) => b.count - a.count)
        .slice(0, 4)
    })

    // Filtered channels based on search query
    const filteredChannels = computed(() => {
      if (!searchQuery.value.trim()) {
        // Sort by popularity (game count) when not searching
        return props.channelsWithCounts
          .slice()
          .sort((a, b) => b.count - a.count)
      }

      const query = searchQuery.value.toLowerCase()
      return props.channelsWithCounts
        .filter((channel) => {
          const formattedName = formatChannelName(channel.name).toLowerCase()
          return (
            formattedName.includes(query) ||
            channel.name.toLowerCase().includes(query)
          )
        })
        .sort((a, b) => {
          // Exact matches first
          const aFormatted = formatChannelName(a.name).toLowerCase()
          const bFormatted = formatChannelName(b.name).toLowerCase()
          const aExact = aFormatted === query
          const bExact = bFormatted === query
          if (aExact && !bExact) {
            return -1
          }
          if (!aExact && bExact) {
            return 1
          }

          // Then by popularity
          return b.count - a.count
        })
    })

    // Preview text for result count
    const previewText = computed(() => {
      if (selectedChannels.value.length === 0) {
        return ''
      }
      if (selectedChannels.value.length === 1) {
        return `Games from ${formatChannelName(selectedChannels.value[0])}`
      }

      return `${selectedChannels.value.length} channels selected`
    })

    // Logic explanation
    const logicExplanation = computed(() => {
      if (selectedChannels.value.length <= 1) {
        return ''
      }

      const count = selectedChannels.value.length
      return `Games featured by any of the ${count} selected channels`
    })

    const toggleChannel = (channelName) => {
      const index = selectedChannels.value.indexOf(channelName)
      if (index > -1) {
        selectedChannels.value.splice(index, 1)
      } else {
        selectedChannels.value.push(channelName)
      }
      emitFiltersChanged()
    }

    const removeChannel = (channelName) => {
      const index = selectedChannels.value.indexOf(channelName)
      if (index > -1) {
        selectedChannels.value.splice(index, 1)
        emitFiltersChanged()
      }
    }

    const clearAllChannels = () => {
      selectedChannels.value = []
      emitFiltersChanged()
    }

    const selectAllChannels = () => {
      selectedChannels.value = props.channelsWithCounts.map((c) => c.name)
      emitFiltersChanged()
    }

    const selectPopularChannels = () => {
      // Add popular channels that aren't already selected
      const popularChannelNames = popularChannels.value.map((c) => c.name)
      popularChannelNames.forEach((channel) => {
        if (!selectedChannels.value.includes(channel)) {
          selectedChannels.value.push(channel)
        }
      })
      emitFiltersChanged()
    }

    const clearSearch = () => {
      searchQuery.value = ''
      if (searchInput.value) {
        searchInput.value.focus()
      }
    }

    const filterChannels = () => {
      // The filtering is handled by the computed property
      // This function exists for potential future enhancements
    }

    const formatChannelName = (channel) => {
      if (!channel || typeof channel !== 'string') {
        return 'Unknown Channel'
      }
      return channel
        .replace(/^videos-/, '')
        .replace(/-/g, ' ')
        .replace(/\b\w/g, (l) => l.toUpperCase())
    }

    const emitFiltersChanged = () => {
      emit('channels-changed', {
        selectedChannels: [...selectedChannels.value],
      })
    }

    // Handle clicking outside to close dropdown
    const handleClickOutside = (event) => {
      const input = searchInput.value
      if (input && !input.contains(event.target)) {
        showDropdown.value = false
      }
    }

    // Watch for changes in initial props
    watch(
      () => props.initialSelectedChannels,
      (newChannels) => {
        selectedChannels.value = [...newChannels]
      },
      { deep: true },
    )

    onMounted(() => {
      document.addEventListener('click', handleClickOutside)
    })

    onUnmounted(() => {
      document.removeEventListener('click', handleClickOutside)
    })

    return {
      searchInput,
      searchQuery,
      showDropdown,
      selectedChannels,
      popularChannels,
      filteredChannels,
      previewText,
      logicExplanation,
      toggleChannel,
      removeChannel,
      clearAllChannels,
      selectAllChannels,
      selectPopularChannels,
      clearSearch,
      filterChannels,
      formatChannelName,
      getChannelColor,
      emitFiltersChanged,
    }
  },
}
</script>
