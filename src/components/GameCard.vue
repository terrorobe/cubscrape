<script setup lang="ts">
import { ref, watch, computed, onUnmounted, type Ref } from 'vue'
import { useProgressiveLoading } from '../composables/useProgressiveLoading'
import {
  HIDDEN_GEM_CRITERIA,
  getRatingClass as getRatingClassConfig,
  getRatingStyle as getRatingStyleConfig,
  isHiddenGem as isHiddenGemConfig,
  type GameForRating,
} from '../utils/ratingConfig'
import {
  getAvailablePlatforms,
  getPlatformConfig,
  type AvailablePlatform,
} from '../config/platforms'
import type { ParsedGameData, VideoData } from '../types/database'
import { debug } from '../utils/debug'
import {
  getPrice as formatPrice,
  type PriceData,
} from '../utils/priceFormatter'
import PlatformLinks from './PlatformLinks.vue'

// Component props interface
interface Props {
  game: ParsedGameData
  currency?: 'eur' | 'usd'
  isHighlighted?: boolean
  selectedTags?: string[]
  loadGameVideos?: (gameId: string) => VideoData[]
}

// Component events interface
interface Emits {
  tagClick: [tag: string]
}

// Define props with defaults
const props = withDefaults(defineProps<Props>(), {
  currency: 'eur',
  isHighlighted: false,
  selectedTags: () => [],
  loadGameVideos: undefined,
})

// Define emits
const emit = defineEmits<Emits>()

// Progressive loading for images
const {
  elementRef: cardRef,
  shouldLoad: shouldLoadImage,
  isLoaded: imageLoaded,
  markAsLoaded,
} = useProgressiveLoading({
  rootMargin: '100px',
  threshold: 0.1,
})

// Progressive loading for detailed game information
// Start loading details immediately when image starts loading
const shouldLoadDetails = computed(() => shouldLoadImage.value)
const detailsLoaded = ref(false)

// Auto-load details after a short delay when they should load
watch(shouldLoadDetails, (newValue) => {
  if (newValue) {
    setTimeout(() => {
      detailsLoaded.value = true
    }, 200) // Small delay to create progressive loading effect
  }
})

// Use loadGameVideos function from props or provide fallback

interface ChannelGroup {
  name: string
  videos: VideoData[]
}

interface VideosByChannel {
  [channelName: string]: ChannelGroup
}

// Reactive state with proper typing
const showingVideos: Ref<Record<number, boolean>> = ref({})
const loadingVideos: Ref<Record<number, boolean>> = ref({})
const gameVideos: Ref<Record<number, VideoData[]>> = ref({})
const copyFeedback: Ref<boolean> = ref(false)
const showCopyOverlay: Ref<boolean> = ref(false)
const highlightFading: Ref<boolean> = ref(false)

// Check if game qualifies as a hidden gem
const isHiddenGem = computed((): boolean =>
  isHiddenGemConfig(props.game as GameForRating),
)

// Compute available platforms using centralized configuration
const availablePlatforms = computed((): AvailablePlatform[] =>
  getAvailablePlatforms(props.game),
)

// Platforms for the new PlatformLinks component
const platformsForLinks = computed(() =>
  availablePlatforms.value.map((platform) => ({
    id: platform.id,
    url: platform.url,
  })),
)

// YouTube video URL for PlatformLinks component
const youtubeVideoUrl = computed(() =>
  props.game.latest_video_id
    ? `https://www.youtube.com/watch?v=${props.game.latest_video_id}`
    : undefined,
)

const toggleVideos = async (gameId: number): Promise<void> => {
  if (showingVideos.value[gameId]) {
    showingVideos.value[gameId] = false
    return
  }

  showingVideos.value[gameId] = true

  // If videos already loaded, don't reload
  if (gameVideos.value[gameId]) {
    return
  }

  loadingVideos.value[gameId] = true

  try {
    if (props.loadGameVideos) {
      const videos = props.loadGameVideos(String(gameId))
      gameVideos.value[gameId] = videos
    } else {
      debug.warn('No loadGameVideos function provided to GameCard')
      gameVideos.value[gameId] = []
    }
  } catch (error) {
    debug.error('Error loading videos:', error)
    gameVideos.value[gameId] = []
  } finally {
    loadingVideos.value[gameId] = false
  }
}

const getChannelText = (game: ParsedGameData): string => {
  const uniqueChannels = game.unique_channels || []
  if (uniqueChannels.length === 0) {
    return 'Channel: Unknown'
  }
  return uniqueChannels.length > 1
    ? `Channels: ${uniqueChannels.join(', ')}`
    : `Channel: ${uniqueChannels[0]}`
}

const shouldShowRating = (game: ParsedGameData): boolean =>
  // Show if there's any rating info at all
  !!game.review_summary ||
  game.review_count !== undefined ||
  game.insufficient_reviews

const getRatingNumbers = (game: ParsedGameData): string => {
  // Handle "No user reviews" case
  if (game.review_summary === 'No user reviews' || game.review_count === 0) {
    return 'No user reviews'
  }

  // Handle "Too few reviews" case
  if (
    game.insufficient_reviews ||
    (game.review_count !== undefined &&
      game.review_count > 0 &&
      !game.positive_review_percentage)
  ) {
    return `Too few reviews (${game.review_count || 0})`
  }

  // Normal percentage display
  if (game.positive_review_percentage) {
    return `${game.positive_review_percentage}% ${game.review_count ? `(${game.review_count.toLocaleString()})` : ''}`
  }

  return ''
}

const getRatingSummary = (game: ParsedGameData): string => {
  // For "No user reviews" and "Too few reviews", don't show summary
  if (game.review_summary === 'No user reviews' || game.review_count === 0) {
    return ''
  }

  if (
    game.insufficient_reviews ||
    (game.review_count !== undefined &&
      game.review_count > 0 &&
      !game.positive_review_percentage)
  ) {
    return ''
  }

  // Show summary with inferred indicator
  const isInferred =
    game.is_inferred_summary ||
    (game.platform !== 'steam' && !!game.review_summary)
  return game.review_summary
    ? `${game.review_summary}${isInferred ? ' *' : ''}`
    : ''
}

const getRatingTooltip = (game: ParsedGameData): string => {
  let tooltipText = ''

  // Add tooltip for inferred summaries
  const isInferred =
    game.is_inferred_summary ||
    (game.platform !== 'steam' && !!game.review_summary)
  if (isInferred) {
    tooltipText = 'Review summary inferred from rating data'
  }

  // Add supplementary review info
  if (game.review_tooltip) {
    tooltipText = tooltipText
      ? `${tooltipText}. ${game.review_tooltip}`
      : game.review_tooltip
  }

  return tooltipText
}

const getRatingClass = (
  percentage?: number | null,
  reviewSummary?: string | null,
): string => getRatingClassConfig(percentage, reviewSummary)

const getRatingStyle = (
  percentage?: number | null,
  reviewSummary?: string | null,
): { backgroundColor: string } =>
  getRatingStyleConfig(percentage, reviewSummary)

const getPriceInfo = (game: ParsedGameData) => {
  // Use new price formatting utility
  const priceData: PriceData = {
    price_eur: game.price_eur,
    price_usd: game.price_usd,
    original_price_eur: game.original_price_eur,
    original_price_usd: game.original_price_usd,
    discount_percent: game.discount_percent ?? 0,
    is_free: game.is_free,
    is_on_sale: game.is_on_sale,
  }

  return formatPrice(priceData, props.currency)
}

const getReleaseInfo = (game: ParsedGameData): string => {
  // Platform-specific games - show release date if available
  if (game.platform === 'itch') {
    if (game.release_date) {
      return `Released ${game.release_date}`
    }
    return 'Available on Itch.io'
  }
  if (game.platform === 'crazygames') {
    if (game.release_date) {
      return `Released ${game.release_date}`
    }
    return 'Play on CrazyGames'
  }

  // Steam games - handle special cases first

  // If Steam game has Itch URL and is coming soon, Itch acts as demo
  if (game.itch_url && game.coming_soon) {
    const fullGameDate = game.planned_release_date || 'coming soon'
    return `Demo • ${fullGameDate}`
  }

  // Handle actual Steam demos
  if (game.is_demo) {
    if (game.coming_soon) {
      const fullGameDate = game.planned_release_date || 'coming soon'
      return `Demo • Full game ${fullGameDate}`
    }
    return 'Demo'
  }

  // For non-demo games, decouple release type and date
  const releaseType = getReleaseType(game)
  const releaseDate = getReleaseDate(game)

  if (releaseType && releaseDate) {
    return `${releaseType} • ${releaseDate}`
  }
  return releaseType || 'Released'
}

const getReleaseType = (game: ParsedGameData): string => {
  if (game.is_early_access) {
    return 'Early Access'
  }
  if (game.coming_soon) {
    return 'Unreleased'
  }
  return 'Released'
}

const getReleaseDate = (game: ParsedGameData): string | null => {
  // Priority order for date selection
  if (game.planned_release_date) {
    return game.planned_release_date
  }
  if (game.release_date) {
    return game.release_date
  }
  return null
}

const formatDate = (dateString?: string | null): string => {
  if (!dateString) {
    return ''
  }
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

// These functions are now handled by the PlatformLinks component
// Kept for reference if needed elsewhere, but prefixed with underscore to indicate they're unused
const _getMainPlatformUrl = (game: ParsedGameData): string | null => {
  // Use unified display links if available
  if (game.display_links && game.display_links.main) {
    return game.display_links.main
  }

  // Use platform configuration to get URL field name
  const platformConfig = getPlatformConfig(game.platform)
  if (platformConfig && platformConfig.urlField) {
    return (
      ((game as unknown as Record<string, unknown>)[
        platformConfig.urlField
      ] as string) || null
    )
  }

  // Fallback to steam_url if no configuration found
  return game.steam_url || null
}

const _getMainPlatformName = (game: ParsedGameData): string => {
  const platformConfig = getPlatformConfig(game.platform)
  return platformConfig ? platformConfig.displayName : 'Unknown Platform'
}

const getDemoUrl = (game: ParsedGameData): string | null => {
  // Use unified display links if available
  if (game.display_links && game.display_links.demo) {
    return game.display_links.demo
  }

  // Fallback to Steam demo URL
  if (game.demo_steam_app_id && game.demo_steam_url) {
    return game.demo_steam_url
  }

  return null
}

const getPlatformName = (platform: string): string => {
  const platformConfig = getPlatformConfig(platform)
  return platformConfig ? platformConfig.displayName : platform
}

const getSteamParentUrl = (game: ParsedGameData): string | null => {
  // For absorbed games, construct Steam URL from absorbed_into key
  if (game.is_absorbed && game.absorbed_into) {
    // absorbed_into contains the steam app ID
    return `https://store.steampowered.com/app/${game.absorbed_into}`
  }
  return null
}

const handleCardClick = async (event: MouseEvent): Promise<void> => {
  debug.log('Card clicked:', props.game.name)

  // Don't handle clicks on links, buttons, or video toggles
  if (
    (event.target as Element)?.closest('a') ||
    (event.target as Element)?.closest('button') ||
    (event.target as Element)?.closest('.video-expand-toggle')
  ) {
    debug.log('Click ignored - clicked on interactive element')
    return
  }

  event.preventDefault()

  const deeplinkUrl = generateDeeplink(props.game)
  if (!deeplinkUrl) {
    debug.warn('Could not generate deeplink for this game:', props.game)
    return
  }

  debug.log('Generated deeplink:', deeplinkUrl)

  // Check if clipboard API is available
  if (!navigator.clipboard) {
    debug.error('Clipboard API not available. Context:', {
      isSecureContext: window.isSecureContext,
      protocol: window.location.protocol,
      hostname: window.location.hostname,
    })
    return
  }

  try {
    await navigator.clipboard.writeText(deeplinkUrl)

    // Show visual feedback
    copyFeedback.value = true
    showCopyOverlay.value = true

    // Hide card scale feedback after short time
    setTimeout(() => {
      copyFeedback.value = false
    }, 300)

    // Hide overlay after animation completes
    setTimeout(() => {
      showCopyOverlay.value = false
    }, 600)

    debug.log('Successfully copied deeplink:', deeplinkUrl)
  } catch (err) {
    debug.error('Failed to copy link:', err)
  }
}

const slugifyForFragment = (text: string): string =>
  // RFC 3986 allowed characters in URL fragments:
  // unreserved: A-Z a-z 0-9 - . _ ~
  // sub-delims: ! $ & ' ( ) * + , ; =
  // also allowed in fragments: : @ / ?
  // Replace spaces with underscores, everything else forbidden gets replaced with hyphen

  text
    // First, replace spaces with underscores
    .replace(/ /g, '_')
    // Then replace any other forbidden characters with hyphens
    .replace(/[^A-Za-z0-9\-._~!$&'()*+,;=:@/?]/g, '-')
    // Replace multiple consecutive hyphens with single hyphen
    .replace(/-+/g, '-')
    // Remove leading/trailing hyphens
    .replace(/^-+|-+$/g, '')

const generateDeeplink = (game: ParsedGameData): string | null => {
  const baseUrl = window.location.origin + window.location.pathname
  const searchParams = window.location.search

  // Generate platform-specific deeplink with readable slug
  if (game.platform === 'steam' && game.steam_app_id) {
    const slug = slugifyForFragment(game.name)
    return `${baseUrl}${searchParams}#steam-${game.steam_app_id}-${slug}`
  }

  if (game.platform === 'itch' && game.itch_url) {
    // Extract game slug from itch URL
    const match = game.itch_url.match(/itch\.io\/games\/([^/?]+)/)
    if (match) {
      const slug = slugifyForFragment(game.name)
      return `${baseUrl}${searchParams}#itch-${match[1]}-${slug}`
    }
  }

  if (game.platform === 'crazygames' && game.crazygames_url) {
    // Extract game slug from CrazyGames URL
    const match = game.crazygames_url.match(/crazygames\.com\/game\/([^/?]+)/)
    if (match) {
      const slug = slugifyForFragment(game.name)
      return `${baseUrl}${searchParams}#crazygames-${match[1]}-${slug}`
    }
  }

  return null
}

const handleTagClick = (tag: string): void => {
  emit('tagClick', tag)
}

const isTagHighlighted = (tag: string): boolean =>
  props.selectedTags.includes(tag)

// Context-aware tag display
const isUserFilteringByTags = computed(() => props.selectedTags.length > 0)
const isHoveringTags = ref(false)
const hoverShowTimer = ref<NodeJS.Timeout | null>(null)
const hoverHideTimer = ref<NodeJS.Timeout | null>(null)

// Hover delay constants
const HOVER_DELAYS = {
  SHOW: 200, // 200ms delay before showing expanded tags
  HIDE: 0, // Immediate hide when leaving
}

const handleTagAreaMouseEnter = () => {
  // Clear any pending hide timer
  if (hoverHideTimer.value) {
    clearTimeout(hoverHideTimer.value)
    hoverHideTimer.value = null
  }

  // Set timer to show expanded tags after delay
  hoverShowTimer.value = setTimeout(() => {
    isHoveringTags.value = true
  }, HOVER_DELAYS.SHOW)
}

const handleTagAreaMouseLeave = () => {
  // Clear any pending show timer
  if (hoverShowTimer.value) {
    clearTimeout(hoverShowTimer.value)
    hoverShowTimer.value = null
  }

  // Hide immediately when leaving
  if (HOVER_DELAYS.HIDE === 0) {
    isHoveringTags.value = false
  } else {
    // Set timer to hide expanded tags with delay (if any)
    hoverHideTimer.value = setTimeout(() => {
      isHoveringTags.value = false
    }, HOVER_DELAYS.HIDE)
  }
}

// Calculate visible tags based on context and character budget
const getVisibleTags = (tags: string[]): string[] => {
  if (!tags || tags.length === 0) {
    return []
  }

  // Show all tags when user is filtering by tags
  if (isUserFilteringByTags.value) {
    return tags
  }

  // Show more tags on hover
  if (isHoveringTags.value) {
    // Show up to 10 tags on hover
    return tags.slice(0, 10)
  }

  // Use character budget approach while maintaining order
  const characterBudget = 46 // Approximately fits 4-6 tags depending on length
  const minTags = 3 // Always show at least 3 tags
  const maxTags = 7 // Never show more than 7 tags in compact mode

  const visibleTags: string[] = []
  let currentCharCount = 0

  // Process tags in original order
  for (let i = 0; i < tags.length; i++) {
    const tag = tags[i]
    const tagLength = tag.length + 4 // +4 for padding/spacing

    // Always include minimum tags
    if (visibleTags.length < minTags) {
      visibleTags.push(tag)
      currentCharCount += tagLength
    }
    // After minimum, only add if within budget AND under max
    else if (
      currentCharCount + tagLength <= characterBudget &&
      visibleTags.length < maxTags
    ) {
      visibleTags.push(tag)
      currentCharCount += tagLength
    } else {
      // Stop once we can't fit more tags
      break
    }
  }

  return visibleTags
}

const getRemainingTagCount = (tags: string[]): number => {
  if (!tags || isUserFilteringByTags.value || isHoveringTags.value) {
    return 0
  }
  const visibleCount = getVisibleTags(tags).length
  return tags.length - visibleCount
}

const groupVideosByChannel = (videos?: VideoData[]): VideosByChannel => {
  if (!videos || !Array.isArray(videos)) {
    return {}
  }

  const videosByChannel: VideosByChannel = {}

  videos.forEach((video) => {
    const channelKey = video.channel_name || 'Unknown Channel'
    if (!videosByChannel[channelKey]) {
      videosByChannel[channelKey] = {
        name: video.channel_name || 'Unknown Channel',
        videos: [],
      }
    }
    videosByChannel[channelKey].videos.push(video)
  })

  return videosByChannel
}

// Watch for highlight changes to manage fade-out animation
watch(
  () => props.isHighlighted,
  (newVal: boolean, oldVal: boolean) => {
    if (oldVal && !newVal) {
      // Starting to fade out
      highlightFading.value = true
      setTimeout(() => {
        highlightFading.value = false
      }, 1000) // Match CSS animation duration
    } else if (newVal) {
      // Reset fade state when highlighting
      highlightFading.value = false
    }
  },
)

// Cleanup hover timers on unmount
onUnmounted(() => {
  if (hoverShowTimer.value) {
    clearTimeout(hoverShowTimer.value)
  }
  if (hoverHideTimer.value) {
    clearTimeout(hoverHideTimer.value)
  }
})
</script>

<template>
  <div
    ref="cardRef"
    class="game-card relative flex w-full cursor-pointer flex-col justify-self-start overflow-hidden rounded-lg bg-bg-card transition-all duration-200 hover:-translate-y-1 hover:shadow-2xl"
    :class="{
      'scale-105': copyFeedback,
      highlighted: isHighlighted && !highlightFading,
      'highlight-fading': highlightFading,
    }"
    @click="handleCardClick"
  >
    <!-- Copy Feedback Overlay -->
    <div
      v-if="showCopyOverlay"
      class="pointer-events-none absolute top-1/2 left-1/2 z-50 -translate-1/2 transform animate-pulse rounded-full bg-green-600 px-4 py-2 text-sm font-bold text-white"
    >
      Link Copied!
    </div>
    <!-- Game Image with Progressive Loading -->
    <div class="flex h-[150px] w-full items-center justify-center bg-bg-card">
      <img
        v-if="game.header_image && shouldLoadImage"
        :src="game.header_image"
        :alt="game.name"
        class="size-full object-contain transition-opacity duration-300"
        :class="{ 'opacity-100': imageLoaded, 'opacity-0': !imageLoaded }"
        loading="lazy"
        @load="markAsLoaded"
        @error="markAsLoaded"
      />
      <!-- Loading placeholder -->
      <div
        v-else-if="game.header_image && !shouldLoadImage"
        class="flex size-full animate-pulse items-center justify-center bg-bg-secondary"
      >
        <div class="text-sm text-text-secondary">Loading...</div>
      </div>
      <!-- No image placeholder -->
      <div
        v-else
        class="flex size-full items-center justify-center bg-bg-secondary"
      >
        <div class="text-sm text-text-secondary">No image</div>
      </div>
    </div>

    <!-- Game Info -->
    <div class="flex min-h-0 flex-1 flex-col p-4">
      <div class="flex-1">
        <!-- Game Title -->
        <div class="mb-3 flex items-start gap-2">
          <h3 class="line-clamp-2 flex-1 overflow-hidden text-xl font-semibold">
            {{ game.name || 'Unknown Game' }}
          </h3>
          <!-- Hidden Gem Indicator -->
          <span
            v-if="isHiddenGem"
            :title="`Hidden Gem: High quality game (${HIDDEN_GEM_CRITERIA.MIN_RATING}%+ rating) with limited video coverage (${HIDDEN_GEM_CRITERIA.MIN_VIDEO_COUNT}-${HIDDEN_GEM_CRITERIA.MAX_VIDEO_COUNT} videos) and sufficient reviews (${HIDDEN_GEM_CRITERIA.MIN_REVIEW_COUNT}+)`"
            class="shrink-0 text-lg"
          >
            💎
          </span>
        </div>

        <!-- Absorption Indicator -->
        <div
          v-if="game.is_absorbed"
          class="mb-3 rounded-sm border border-yellow-300 bg-yellow-100 px-2 py-1"
        >
          <div class="text-xs font-medium text-yellow-800">
            🔗 Also available on Steam
          </div>
          <div class="mt-0.5 text-xs text-yellow-700">
            This {{ getPlatformName(game.platform).toLowerCase() }} game is also
            released on Steam with enhanced features
          </div>
        </div>

        <!-- Game Meta -->
        <div class="mb-3 flex flex-col gap-2">
          <!-- Top Row: Main Rating and Price -->
          <div class="flex items-center justify-between gap-3">
            <!-- Main Rating Display with Progressive Loading -->
            <div v-if="shouldLoadDetails && shouldShowRating(game)">
              <div
                v-if="detailsLoaded"
                :class="
                  getRatingClass(
                    game.positive_review_percentage,
                    game.review_summary,
                  )
                "
                :style="
                  getRatingStyle(
                    game.positive_review_percentage,
                    game.review_summary,
                  )
                "
                :title="getRatingTooltip(game)"
                class="inline-block rounded-sm px-2 py-1 transition-opacity duration-300"
              >
                <div class="mb-0.5 text-sm font-bold">
                  {{ getRatingNumbers(game) }}
                </div>
                <div class="text-xs font-normal opacity-90">
                  {{ getRatingSummary(game) }}
                </div>
              </div>
              <!-- Rating Skeleton -->
              <div
                v-else
                class="inline-block animate-pulse rounded-sm bg-bg-secondary px-2 py-1"
              >
                <div
                  class="mb-0.5 h-4 w-16 rounded-sm bg-text-secondary/20"
                ></div>
                <div class="h-3 w-20 rounded-sm bg-text-secondary/20"></div>
              </div>
            </div>

            <!-- Price Display (Steam-style) -->
            <div v-if="getPriceInfo(game).current">
              <!-- Sale Price Block -->
              <div
                v-if="game.is_on_sale && game.discount_percent"
                class="flex items-center"
              >
                <!-- Discount Percentage -->
                <div
                  class="rounded-l bg-green-700 px-2 py-1 text-sm font-bold text-white"
                >
                  -{{ game.discount_percent }}%
                </div>
                <!-- Price Block -->
                <div
                  class="flex flex-col items-end rounded-r bg-black/20 px-3 py-1"
                >
                  <!-- Original Price -->
                  <div
                    v-if="getPriceInfo(game).original"
                    class="text-[10px] leading-tight text-text-secondary line-through"
                  >
                    {{ getPriceInfo(game).original }}
                  </div>
                  <!-- Discounted Price -->
                  <div class="text-sm font-semibold text-green-400">
                    {{ getPriceInfo(game).current }}
                  </div>
                </div>
              </div>

              <!-- Regular Price (no sale) -->
              <div
                v-else
                class="rounded-sm bg-black/20 px-3 py-1 text-sm font-semibold text-text-primary"
              >
                {{ getPriceInfo(game).current }}
              </div>
            </div>
          </div>

          <!-- Bottom Row: Recent Reviews and Release Info -->
          <div
            v-if="
              (game.recent_review_percentage && game.recent_review_count) ||
              getReleaseInfo(game)
            "
            class="flex items-center justify-between gap-3"
          >
            <!-- Recent Reviews -->
            <div
              v-if="game.recent_review_percentage && game.recent_review_count"
              class="text-xs whitespace-nowrap text-text-secondary"
            >
              Recent: {{ game.recent_review_percentage }}% ({{
                game.recent_review_count.toLocaleString()
              }})
            </div>
            <div v-else></div>
            <!-- Spacer when no recent reviews -->

            <!-- Release Info -->
            <div
              v-if="getReleaseInfo(game)"
              class="text-right text-sm text-text-secondary"
            >
              <span v-if="getReleaseInfo(game).includes('•')">
                {{ getReleaseInfo(game).split(' • ')[0] }}<wbr /> • <wbr /><span
                  class="whitespace-nowrap"
                  >{{ getReleaseInfo(game).split(' • ')[1] }}</span
                >
              </span>
              <span v-else>
                {{ getReleaseInfo(game) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Tags -->
        <div
          class="mt-2 flex items-center gap-1"
          :class="{
            'overflow-hidden': !isHoveringTags && !isUserFilteringByTags,
            'flex-wrap': isHoveringTags || isUserFilteringByTags,
          }"
          @mouseenter="handleTagAreaMouseEnter"
          @mouseleave="handleTagAreaMouseLeave"
        >
          <TransitionGroup
            name="tag-fade"
            tag="div"
            :class="{
              'flex gap-1': !isHoveringTags && !isUserFilteringByTags,
              'flex flex-wrap gap-1': isHoveringTags || isUserFilteringByTags,
            }"
          >
            <button
              v-for="tag in getVisibleTags(game.tags || [])"
              :key="tag"
              class="rounded-full px-2 py-1 text-xs transition-all duration-200"
              :class="{
                'my-1 mr-1': isHoveringTags || isUserFilteringByTags,
                'bg-bg-secondary text-text-secondary hover:bg-accent hover:text-white':
                  !isTagHighlighted(tag),
                'bg-accent text-white': isTagHighlighted(tag),
              }"
              :title="tag"
              @click.stop="handleTagClick(tag)"
            >
              {{ tag }}
            </button>
          </TransitionGroup>
          <span
            v-if="getRemainingTagCount(game.tags || []) > 0"
            class="shrink-0 rounded-full px-2 py-1 text-xs text-text-secondary"
          >
            +{{ getRemainingTagCount(game.tags || []) }} more
          </span>
        </div>

        <!-- Video Info -->
        <div
          v-if="game.latest_video_title"
          class="mt-4 border-t border-gray-600 pt-3"
        >
          <div
            class="mb-2 line-clamp-2 overflow-hidden text-sm leading-tight text-text-secondary"
          >
            <a
              :href="`https://www.youtube.com/watch?v=${game.latest_video_id}`"
              target="_blank"
              rel="noopener noreferrer"
              class="text-text-primary hover:text-accent hover:underline"
            >
              {{ game.latest_video_title }}
            </a>
          </div>
          <div class="mt-1 text-xs text-text-secondary">
            Latest video: {{ formatDate(game.latest_video_date) }}
          </div>

          <!-- Channel Info -->
          <div class="mt-1 text-xs text-text-secondary">
            {{ getChannelText(game) }}
          </div>

          <!-- Multi Video Expand -->
          <div
            v-if="game.video_count > 1"
            class="mt-1 flex cursor-pointer items-center gap-1.5 text-xs text-accent hover:text-text-primary"
            @click.stop="toggleVideos(game.id)"
          >
            <span
              class="text-xs transition-transform duration-200"
              :class="{ 'rotate-90': showingVideos[game.id] }"
              >▶</span
            >
            <span>Featured in {{ game.video_count }} videos</span>
          </div>

          <!-- All Videos List -->
          <div
            v-if="showingVideos[game.id]"
            class="mt-2 rounded-sm bg-bg-secondary p-2"
          >
            <div
              v-if="loadingVideos[game.id]"
              class="text-xs text-text-secondary"
            >
              Loading videos...
            </div>
            <div v-else-if="gameVideos[game.id]" class="space-y-3">
              <div
                v-for="(channelGroup, channelName) in groupVideosByChannel(
                  gameVideos[game.id],
                )"
                :key="channelName"
                class="border-l-4 border-accent pl-2.5"
              >
                <!-- Channel Header -->
                <div
                  class="mb-2 text-xs font-bold tracking-wide text-accent uppercase"
                >
                  {{ channelGroup.name }} ({{ channelGroup.videos.length }})
                </div>

                <!-- Channel Videos -->
                <div class="ml-2.5 space-y-1">
                  <div
                    v-for="video in channelGroup.videos"
                    :key="video.video_id"
                    class="flex items-center justify-between border-b border-bg-card py-2 last:border-b-0"
                  >
                    <a
                      :href="`https://www.youtube.com/watch?v=${video.video_id}`"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="flex-1 pr-2 text-xs leading-tight text-text-primary hover:text-accent"
                    >
                      {{ video.video_title }}
                    </a>
                    <span class="text-xs text-text-secondary">
                      {{ formatDate(video.video_date) }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Game Footer -->
      <div class="mt-auto flex items-center justify-between pt-3">
        <!-- Left side: Platform links and demos -->
        <div class="flex items-center gap-1.5">
          <PlatformLinks
            :platforms="platformsForLinks"
            :youtube-url="youtubeVideoUrl"
            :game-data="{
              latest_video_title: game.latest_video_title,
              latest_video_channel: game.latest_video_channel,
            }"
            :show-text-link="false"
          />

          <!-- Demo badge integrated with platform hierarchy -->
          <template v-if="getDemoUrl(game)">
            <span class="mx-1 text-xs opacity-50">•</span>
            <a
              :href="getDemoUrl(game) ?? undefined"
              target="_blank"
              rel="noopener noreferrer"
              class="demo-badge flex items-center justify-center rounded-sm text-xs font-medium transition-all duration-200 hover:scale-105"
              title="Try the demo version on Steam"
              aria-label="Try the demo version on Steam"
            >
              <i class="fab fa-steam mr-1 text-xs"></i>
              Demo
            </a>
          </template>

          <!-- Playtest badge -->
          <template v-if="game.has_playtest">
            <span class="mx-1 text-xs opacity-50">•</span>
            <a
              :href="game.steam_url ?? undefined"
              target="_blank"
              rel="noopener noreferrer"
              class="demo-badge flex items-center justify-center rounded-sm text-xs font-medium transition-all duration-200 hover:scale-105"
              title="Join the playtest on Steam"
              aria-label="Join the playtest on Steam"
            >
              <i class="fab fa-steam mr-1 text-xs"></i>
              Playtest
            </a>
          </template>

          <!-- Absorbed game link -->
          <template v-if="game.is_absorbed && getSteamParentUrl(game)">
            <span class="mx-1 text-xs opacity-50">•</span>
            <a
              :href="getSteamParentUrl(game) ?? undefined"
              target="_blank"
              rel="noopener noreferrer"
              class="text-xs font-medium text-accent opacity-80 hover:underline"
            >
              Full Version
            </a>
          </template>
        </div>

        <!-- Right side: Timestamp -->

        <div
          v-if="game.last_updated"
          class="cursor-help text-xs text-text-secondary opacity-70"
          :title="`${getPlatformName(game.platform)} data last updated`"
        >
          {{ formatDate(game.last_updated) }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Deeplink highlighting styles - balanced performance and visibility */
.game-card.highlighted {
  outline: 3px solid #007bff;
  outline-offset: 2px;
  scroll-margin-top: 100px;
  animation: highlightPulse 3s ease-in-out;
  will-change: transform, filter;
}

@keyframes highlightPulse {
  0%,
  100% {
    transform: scale(1);
    filter: drop-shadow(0 0 5px rgb(0, 123, 255, 30%));
  }

  50% {
    transform: scale(1.01);
    filter: drop-shadow(0 0 15px rgb(0, 123, 255, 60%));
  }
}

.game-card.highlight-fading {
  outline: 3px solid #007bff;
  outline-offset: 2px;
  animation: highlightFadeOut 1s ease-out forwards;
  will-change: opacity, transform;
}

@keyframes highlightFadeOut {
  from {
    opacity: 100%;
    transform: scale(1);
  }

  to {
    opacity: 100%;
    transform: scale(1);
    outline-color: transparent;
  }
}

/* Tag transitions */
.tag-fade-enter-active,
.tag-fade-leave-active {
  transition: all 0.2s ease;
}

.tag-fade-enter-from {
  opacity: 0%;
  transform: scale(0.8);
}

.tag-fade-leave-to {
  opacity: 0%;
  transform: scale(0.8);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0%;
}
</style>
