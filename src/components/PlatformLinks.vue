<script setup lang="ts">
import { computed } from 'vue'
import { PLATFORMS, type AvailablePlatform } from '@/config/platforms'

interface Props {
  /** Available platforms with URLs */
  platforms: Array<{ id: string; url: string }>
  /** Optional YouTube video URL */
  youtubeUrl?: string
  /** Show text link for primary platform: true (multi-platform only), 'always', or false */
  showTextLink?: boolean | 'always'
  /** Game data for enhanced YouTube tooltip */
  gameData?: {
    latest_video_title?: string
    latest_video_channel?: string
  }
}

const props = withDefaults(defineProps<Props>(), {
  youtubeUrl: undefined,
  showTextLink: true,
  gameData: undefined,
})

/**
 * Platforms sorted by priority with full configuration
 */
const sortedPlatforms = computed<AvailablePlatform[]>(() =>
  props.platforms
    .map((p) => ({
      ...PLATFORMS[p.id as keyof typeof PLATFORMS],
      url: p.url,
    }))
    .filter(Boolean) // Remove invalid platform IDs
    .sort((a, b) => a.priority - b.priority),
)

/**
 * Primary platform (highest priority)
 */
const primaryPlatform = computed(() =>
  props.showTextLink !== false ? sortedPlatforms.value[0] : null,
)

/**
 * Get CSS classes for platform logo container
 */
function platformClasses(platform: AvailablePlatform): string {
  const baseClasses = [
    'platform-logo',
    'rounded',
    'flex',
    'items-center',
    'justify-center',
    'hover:scale-105',
    'transition-transform',
    'duration-200',
  ]

  // Size based on priority
  if (platform.containerSize === 'primary') {
    baseClasses.push('w-7', 'h-7', 'platform-logo-primary')
  } else {
    baseClasses.push(
      'w-6',
      'h-6',
      'platform-logo-secondary',
      'opacity-80',
      'hover:opacity-100',
    )
  }

  // Platform-specific styling
  baseClasses.push(`platform-logo-${platform.id}`)

  return baseClasses.join(' ')
}

/**
 * Get icon size class based on platform priority
 */
function iconSize(platform: AvailablePlatform): string {
  return platform.containerSize === 'primary' ? 'text-sm' : 'text-xs'
}

/**
 * Get accessible title for platform
 */
function getPlatformTitle(platform: AvailablePlatform): string {
  const isPrimary = platform.containerSize === 'primary'
  return isPrimary
    ? `Available on ${platform.displayName} (Primary)`
    : `Also available on ${platform.displayName}`
}

/**
 * Get enhanced YouTube title with channel and video information
 */
const youtubeTitle = computed((): string => {
  if (!props.gameData) {
    return 'Watch gameplay video'
  }

  const { latest_video_title, latest_video_channel } = props.gameData

  // Build title parts
  const parts: string[] = []

  if (latest_video_title) {
    parts.push(`"${latest_video_title}"`)
  }

  if (latest_video_channel) {
    parts.push(`by ${latest_video_channel}`)
  }

  // Fallback if no data available
  if (parts.length === 0) {
    return 'Watch gameplay video'
  }

  return `Watch ${parts.join(' ')}`
})
</script>

<template>
  <div class="flex items-center gap-1.5">
    <!-- Platform logos with smart hierarchy -->
    <a
      v-for="platform in sortedPlatforms"
      :key="platform.id"
      :href="platform.url"
      target="_blank"
      rel="noopener noreferrer"
      :class="platformClasses(platform)"
      :title="getPlatformTitle(platform)"
      :aria-label="getPlatformTitle(platform)"
    >
      <span class="sr-only">{{ platform.displayName }}</span>
      <i :class="[platform.iconClass, iconSize(platform)]"></i>
    </a>

    <!-- YouTube video link (separate treatment) -->
    <template v-if="youtubeUrl">
      <span class="mx-1 text-xs opacity-50">•</span>
      <a
        :href="youtubeUrl"
        target="_blank"
        rel="noopener noreferrer"
        class="platform-logo platform-logo-youtube flex size-6 items-center justify-center rounded-sm transition-transform hover:scale-105"
        :title="youtubeTitle"
        :aria-label="youtubeTitle"
      >
        <span class="sr-only">YouTube</span>
        <i class="fab fa-youtube text-xs text-white"></i>
      </a>
    </template>

    <!-- Primary platform text link (only for multi-platform games or when explicitly needed) -->
    <template
      v-if="
        primaryPlatform &&
        (sortedPlatforms.length > 1 || showTextLink === 'always')
      "
    >
      <span class="mx-1 text-xs opacity-50">•</span>
      <a
        :href="primaryPlatform.url"
        target="_blank"
        rel="noopener noreferrer"
        class="text-xs text-accent hover:underline"
      >
        {{ primaryPlatform.displayName }}
      </a>
    </template>
  </div>
</template>

<style scoped>
/* Screen reader only text */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
