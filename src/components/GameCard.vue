<script setup lang="ts">
import { ref, watch, computed, type Ref } from 'vue'
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
import { UI_LIMITS } from '../config/index'
import type { ParsedGameData, VideoData } from '../types/database'
import { debug } from '../utils/debug'
import {
  getPrice as formatPrice,
  type PriceData,
} from '../utils/priceFormatter'

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

const getPrice = (game: ParsedGameData) => {
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

const getMainPlatformUrl = (game: ParsedGameData): string | null => {
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

const getMainPlatformName = (game: ParsedGameData): string => {
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
  // Don't handle clicks on links, buttons, or video toggles
  if (
    (event.target as Element)?.closest('a') ||
    (event.target as Element)?.closest('button') ||
    (event.target as Element)?.closest('.video-expand-toggle')
  ) {
    return
  }

  event.preventDefault()

  const deeplinkUrl = generateDeeplink(props.game)
  if (!deeplinkUrl) {
    debug.warn('Could not generate deeplink for this game')
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

    debug.log('Copied deeplink:', deeplinkUrl)
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

            <!-- Price with Sale Indicator -->
            <div v-if="getPrice(game)" class="flex flex-col items-end gap-1">
              <!-- Sale Badge -->
              <div
                v-if="game.is_on_sale && game.discount_percent"
                class="rounded-sm bg-red-600 px-2 py-1 text-xs font-bold text-white"
              >
                -{{ game.discount_percent }}%
              </div>

              <!-- Price Display -->
              <div class="flex items-center gap-2">
                <!-- Original Price (crossed out when on sale) -->
                <div
                  v-if="
                    game.is_on_sale &&
                    game.original_price_eur &&
                    props.currency === 'eur'
                  "
                  class="text-sm text-text-secondary line-through"
                >
                  {{ game.original_price_eur }}
                </div>
                <div
                  v-else-if="
                    game.is_on_sale &&
                    game.original_price_usd &&
                    props.currency === 'usd'
                  "
                  class="text-sm text-text-secondary line-through"
                >
                  {{ game.original_price_usd }}
                </div>

                <!-- Current Price -->
                <div
                  class="rounded-sm bg-accent/10 px-3 py-1 text-lg font-bold"
                  :class="game.is_on_sale ? 'text-red-600' : 'text-accent'"
                >
                  {{ getPrice(game) }}
                </div>
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
        <div class="mt-2 flex flex-wrap gap-1">
          <button
            v-for="tag in (game.tags || []).slice(
              0,
              UI_LIMITS.GAME_CARD_TAG_LIMIT,
            )"
            :key="tag"
            class="my-1 mr-1 rounded-full px-2 py-1 text-xs transition-colors"
            :class="{
              'bg-bg-secondary text-text-secondary hover:bg-accent hover:text-white':
                !isTagHighlighted(tag),
              'bg-accent text-white': isTagHighlighted(tag),
            }"
            :title="`Filter by ${tag}`"
            @click.stop="handleTagClick(tag)"
          >
            {{ tag }}
          </button>
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
        <div class="flex items-center gap-3">
          <!-- Platform availability indicators -->
          <div
            v-if="availablePlatforms.length > 1"
            class="flex items-center gap-1.5"
          >
            <span
              v-for="platform in availablePlatforms"
              :key="platform.name"
              :title="`Available on ${platform.displayName}`"
              class="inline-flex size-6 items-center justify-center rounded-sm bg-bg-secondary text-xs font-medium text-text-secondary"
            >
              {{ platform.icon }}
            </span>
          </div>

          <!-- Main platform link -->
          <a
            :href="getMainPlatformUrl(game) ?? undefined"
            target="_blank"
            rel="noopener noreferrer"
            class="text-sm text-accent hover:underline"
          >
            {{ getMainPlatformName(game) }}
          </a>

          <!-- Demo link -->
          <a
            v-if="getDemoUrl(game)"
            :href="getDemoUrl(game) ?? undefined"
            target="_blank"
            rel="noopener noreferrer"
            class="text-sm text-accent hover:underline"
          >
            Demo
          </a>

          <!-- Absorbed game link to Steam parent -->
          <a
            v-if="game.is_absorbed && getSteamParentUrl(game)"
            :href="getSteamParentUrl(game) ?? undefined"
            target="_blank"
            rel="noopener noreferrer"
            class="text-sm font-medium text-accent hover:underline"
          >
            Steam Version
          </a>

          <!-- Cross-platform links -->
          <a
            v-if="
              game.itch_url && game.platform !== 'itch' && !game.is_absorbed
            "
            :href="game.itch_url"
            target="_blank"
            rel="noopener noreferrer"
            class="text-sm text-accent hover:underline"
          >
            Itch.io
          </a>
          <a
            v-if="
              game.crazygames_url &&
              game.platform !== 'crazygames' &&
              !game.is_absorbed
            "
            :href="game.crazygames_url"
            target="_blank"
            rel="noopener noreferrer"
            class="text-sm text-accent hover:underline"
          >
            CrazyGames
          </a>

          <!-- YouTube link -->
          <a
            v-if="game.latest_video_id"
            :href="`https://www.youtube.com/watch?v=${game.latest_video_id}`"
            target="_blank"
            rel="noopener noreferrer"
            class="text-sm text-accent hover:underline"
          >
            YouTube
          </a>
        </div>

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
    filter: drop-shadow(0 0 5px rgba(0, 123, 255, 0.3));
  }
  50% {
    transform: scale(1.01);
    filter: drop-shadow(0 0 15px rgba(0, 123, 255, 0.6));
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
    opacity: 1;
    transform: scale(1);
  }
  to {
    opacity: 1;
    transform: scale(1);
    outline-color: transparent;
  }
}
</style>
