<template>
  <div class="mb-8 rounded-lg bg-bg-secondary p-5">
    <div class="flex flex-wrap items-center gap-5">
      <!-- Release Status Filter -->
      <div class="flex flex-col gap-1">
        <label class="text-sm text-text-secondary">Release Status:</label>
        <select
          v-model="localFilters.releaseStatus"
          class="cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary hover:border-accent"
          @change="emitFiltersChanged"
        >
          <option value="all">All Games</option>
          <option value="released">Released Only</option>
          <option value="early-access">Early Access</option>
          <option value="coming-soon">Coming Soon</option>
        </select>
      </div>

      <!-- Platform Filter -->
      <div class="flex flex-col gap-1">
        <label class="text-sm text-text-secondary">Platform:</label>
        <select
          v-model="localFilters.platform"
          class="cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary hover:border-accent"
          @change="emitFiltersChanged"
        >
          <option value="all">All Platforms</option>
          <option value="steam">Steam</option>
          <option value="itch">Itch.io</option>
          <option value="crazygames">CrazyGames</option>
        </select>
      </div>

      <!-- Rating Filter -->
      <div class="flex flex-col gap-1">
        <label class="text-sm text-text-secondary">Minimum Rating:</label>
        <select
          v-model="localFilters.rating"
          class="cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary hover:border-accent"
          @change="emitFiltersChanged"
        >
          <option value="0">All Ratings</option>
          <option value="70">70%+ Positive</option>
          <option value="80">80%+ Positive</option>
          <option value="90">90%+ Positive</option>
        </select>
      </div>

      <!-- Tag Filter (Multi-Select) -->
      <div class="flex flex-col gap-1">
        <TagFilterMulti
          :tags-with-counts="tags"
          :initial-selected-tags="localFilters.selectedTags || []"
          :initial-tag-logic="localFilters.tagLogic || 'and'"
          @tags-changed="handleTagsChanged"
        />
      </div>

      <!-- Channel Filter -->
      <div class="flex flex-col gap-1">
        <label class="text-sm text-text-secondary">Channel:</label>
        <select
          v-model="localFilters.channel"
          class="cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary hover:border-accent"
          @change="emitFiltersChanged"
        >
          <option value="">All Channels</option>
          <option v-for="channel in channels" :key="channel" :value="channel">
            {{ formatChannelName(channel) }}
          </option>
        </select>
      </div>

      <!-- Sort Filter -->
      <div class="flex flex-col gap-1">
        <label class="text-sm text-text-secondary">Sort By:</label>
        <select
          v-model="localFilters.sortBy"
          class="cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary hover:border-accent"
          @change="emitFiltersChanged"
        >
          <option value="date">Video Date</option>
          <option value="rating-score">Rating Score</option>
          <option value="rating-category">Rating Category</option>
          <option value="name">Game Name</option>
          <option value="release-new">Release: Newest</option>
          <option value="release-old">Release: Oldest</option>
        </select>
      </div>

      <!-- Currency Filter -->
      <div class="flex flex-col gap-1">
        <label class="text-sm text-text-secondary">Currency:</label>
        <select
          v-model="localFilters.currency"
          class="cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary hover:border-accent"
          @change="emitFiltersChanged"
        >
          <option value="eur">EUR (€)</option>
          <option value="usd">USD ($)</option>
        </select>
      </div>
    </div>
  </div>
</template>

<script>
import { reactive } from 'vue'
import TagFilterMulti from './TagFilterMulti.vue'

export default {
  name: 'GameFilters',
  components: {
    TagFilterMulti,
  },
  props: {
    channels: {
      type: Array,
      default: () => [],
    },
    tags: {
      type: Array,
      default: () => [],
    },
    initialFilters: {
      type: Object,
      default: () => ({}),
    },
  },
  emits: ['filters-changed'],
  setup(props, { emit }) {
    const localFilters = reactive({
      releaseStatus: props.initialFilters.releaseStatus || 'all',
      platform: props.initialFilters.platform || 'all',
      rating: props.initialFilters.rating || '0',
      // Legacy single tag support for backward compatibility
      tag: props.initialFilters.tag || '',
      // New multi-tag support
      selectedTags:
        props.initialFilters.selectedTags ||
        (props.initialFilters.tag ? [props.initialFilters.tag] : []),
      tagLogic: props.initialFilters.tagLogic || 'and',
      channel: props.initialFilters.channel || '',
      sortBy: props.initialFilters.sortBy || 'date',
      currency: props.initialFilters.currency || 'eur',
    })

    const handleTagsChanged = (tagData) => {
      localFilters.selectedTags = tagData.selectedTags
      localFilters.tagLogic = tagData.tagLogic
      // Update legacy tag field for backward compatibility
      localFilters.tag =
        tagData.selectedTags.length === 1 ? tagData.selectedTags[0] : ''
      emitFiltersChanged()
    }

    const emitFiltersChanged = () => {
      emit('filters-changed', { ...localFilters })
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

    return {
      localFilters,
      handleTagsChanged,
      emitFiltersChanged,
      formatChannelName,
    }
  },
}
</script>
