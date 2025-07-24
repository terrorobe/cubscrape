<template>
  <div
    class="game-card relative flex h-full cursor-pointer flex-col overflow-hidden rounded-lg bg-bg-card transition-all duration-200 hover:-translate-y-1 hover:shadow-2xl"
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
    <!-- Game Image -->
    <img
      v-if="game.header_image"
      :src="game.header_image"
      :alt="game.name"
      class="h-[150px] w-full bg-bg-card object-contain"
      loading="lazy"
    />

    <!-- Game Info -->
    <div class="flex min-h-0 flex-1 flex-col p-4">
      <div class="flex-1">
        <!-- Game Title -->
        <h3 class="mb-3 line-clamp-2 overflow-hidden text-xl font-semibold">
          {{ game.name || 'Unknown Game' }}
        </h3>

        <!-- Game Meta -->
        <div class="mb-3 flex items-center justify-between gap-3">
          <!-- Rating -->
          <div v-if="shouldShowRating(game)" class="flex flex-col gap-1">
            <!-- Main Rating Display -->
            <div
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
              class="inline-block rounded-sm px-2 py-1"
            >
              <div class="mb-0.5 text-sm font-bold">
                {{ getRatingNumbers(game) }}
              </div>
              <div class="text-xs font-normal opacity-90">
                {{ getRatingSummary(game) }}
              </div>
            </div>

            <!-- Recent Reviews -->
            <div
              v-if="game.recent_review_percentage && game.recent_review_count"
              class="text-xs text-text-secondary"
            >
              Recent: {{ game.recent_review_percentage }}% ({{
                game.recent_review_count.toLocaleString()
              }})
            </div>
          </div>
        </div>

        <!-- Price Line -->
        <div class="my-3 flex min-h-8 items-center justify-between">
          <div class="flex items-center">
            <div
              v-if="getPrice(game)"
              class="rounded-sm bg-accent/10 p-3 text-lg font-bold text-accent"
            >
              {{ getPrice(game) }}
            </div>
          </div>
          <div class="flex items-center justify-end">
            <div
              v-if="getReleaseInfo(game)"
              class="text-right text-sm text-text-secondary"
            >
              {{ getReleaseInfo(game) }}
            </div>
          </div>
        </div>

        <!-- Tags -->
        <div class="mt-2 flex flex-wrap gap-1">
          <span
            v-for="tag in (game.tags || []).slice(0, 5)"
            :key="tag"
            class="my-1 mr-1 rounded-full bg-bg-secondary px-2 py-1 text-xs text-text-secondary"
          >
            {{ tag }}
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
        <div class="flex gap-3">
          <!-- Main platform link -->
          <a
            :href="getMainPlatformUrl(game)"
            target="_blank"
            class="text-sm text-accent hover:underline"
          >
            {{ getMainPlatformName(game) }}
          </a>

          <!-- Demo link -->
          <a
            v-if="getDemoUrl(game)"
            :href="getDemoUrl(game)"
            target="_blank"
            class="text-sm text-accent hover:underline"
          >
            Demo
          </a>

          <!-- Cross-platform links -->
          <a
            v-if="game.itch_url && game.platform !== 'itch'"
            :href="game.itch_url"
            target="_blank"
            class="text-sm text-accent hover:underline"
          >
            Itch.io
          </a>
          <a
            v-if="game.crazygames_url && game.platform !== 'crazygames'"
            :href="game.crazygames_url"
            target="_blank"
            class="text-sm text-accent hover:underline"
          >
            CrazyGames
          </a>

          <!-- YouTube link -->
          <a
            v-if="game.latest_video_id"
            :href="`https://www.youtube.com/watch?v=${game.latest_video_id}`"
            target="_blank"
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

<script>
import { ref, watch } from 'vue'

export default {
  name: 'GameCard',
  props: {
    game: {
      type: Object,
      required: true,
    },
    currency: {
      type: String,
      default: 'eur',
    },
    isHighlighted: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    const showingVideos = ref({})
    const loadingVideos = ref({})
    const gameVideos = ref({})
    const copyFeedback = ref(false)
    const showCopyOverlay = ref(false)
    const highlightFading = ref(false)

    const toggleVideos = async (gameId) => {
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
        // Get database instance from parent
        const db = window.gameDatabase
        if (!db) {
          console.error('Database not available')
          return
        }

        const query = `
          SELECT video_title, video_id, video_date, channel_name
          FROM game_videos
          WHERE game_id = ?
          ORDER BY video_date DESC
        `
        const results = db.exec(query, [gameId])

        if (results.length > 0) {
          const videos = results[0].values.map((row) => ({
            video_title: row[0],
            video_id: row[1],
            video_date: row[2],
            channel_name: row[3],
          }))
          gameVideos.value[gameId] = videos
        } else {
          gameVideos.value[gameId] = []
        }
      } catch (error) {
        console.error('Error loading videos:', error)
        gameVideos.value[gameId] = []
      } finally {
        loadingVideos.value[gameId] = false
      }
    }

    const getChannelText = (game) => {
      const uniqueChannels = game.unique_channels || []
      if (uniqueChannels.length === 0) {
        return 'Channel: Unknown'
      }
      return uniqueChannels.length > 1
        ? `Channels: ${uniqueChannels.join(', ')}`
        : `Channel: ${uniqueChannels[0]}`
    }

    const shouldShowRating = (game) => {
      // Show if there's any rating info at all
      return (
        game.review_summary ||
        game.review_count !== undefined ||
        game.insufficient_reviews
      )
    }

    const getRatingNumbers = (game) => {
      // Handle "No user reviews" case
      if (
        game.review_summary === 'No user reviews' ||
        game.review_count === 0
      ) {
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

    const getRatingSummary = (game) => {
      // For "No user reviews" and "Too few reviews", don't show summary
      if (
        game.review_summary === 'No user reviews' ||
        game.review_count === 0
      ) {
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
        (game.platform !== 'steam' && game.review_summary)
      return game.review_summary
        ? `${game.review_summary}${isInferred ? ' *' : ''}`
        : ''
    }

    const getRatingTooltip = (game) => {
      let tooltipText = ''

      // Add tooltip for inferred summaries
      const isInferred =
        game.is_inferred_summary ||
        (game.platform !== 'steam' && game.review_summary)
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

    const getRatingClass = (percentage, reviewSummary) => {
      // Handle special cases first
      if (reviewSummary === 'No user reviews' || !percentage) {
        return 'bg-gray-500 text-white'
      }

      // Use review summary for more specific classification when available
      if (reviewSummary) {
        const summary = reviewSummary.toLowerCase()
        if (summary.includes('overwhelmingly positive')) {
          // hsl(120, 70%, 40%) - Deep green
          return 'text-black'
        }
        if (summary.includes('very positive')) {
          // hsl(100, 60%, 50%)
          return 'text-black'
        }
        if (summary.includes('mostly positive')) {
          // hsl(80, 60%, 50%)
          return 'text-black'
        }
        if (summary.includes('positive')) {
          // hsl(60, 60%, 50%)
          return 'text-black'
        }
        if (summary.includes('mixed')) {
          // hsl(45, 60%, 50%) - Yellow-orange
          return 'text-black'
        }
        if (summary.includes('mostly negative')) {
          // hsl(20, 60%, 50%) - Orange-red
          return 'text-white'
        }
        if (summary.includes('overwhelmingly negative')) {
          // hsl(0, 80%, 40%) - Deep red
          return 'text-white'
        }
        if (summary.includes('very negative')) {
          // hsl(10, 70%, 50%)
          return 'text-white'
        }
        if (summary.includes('negative')) {
          // Default negative
          return 'text-white'
        }
      }

      // Fallback to percentage-based classification
      if (percentage >= 80) {
        return 'text-black'
      }
      if (percentage >= 50) {
        return 'text-black'
      }
      return 'text-white'
    }

    const getRatingStyle = (percentage, reviewSummary) => {
      if (!percentage) {
        return { backgroundColor: 'hsl(0, 0%, 50%)' } // gray
      }

      // Use review summary for more specific classification when available
      if (reviewSummary) {
        const summary = reviewSummary.toLowerCase()
        if (summary.includes('overwhelmingly positive')) {
          return { backgroundColor: 'hsl(120, 70%, 40%)' }
        }
        if (summary.includes('very positive')) {
          return { backgroundColor: 'hsl(100, 60%, 50%)' }
        }
        if (summary.includes('mostly positive')) {
          return { backgroundColor: 'hsl(80, 60%, 50%)' }
        }
        if (summary.includes('positive')) {
          return { backgroundColor: 'hsl(60, 60%, 50%)' }
        }
        if (summary.includes('mixed')) {
          return { backgroundColor: 'hsl(45, 60%, 50%)' }
        }
        if (summary.includes('mostly negative')) {
          return { backgroundColor: 'hsl(20, 60%, 50%)' }
        }
        if (summary.includes('overwhelmingly negative')) {
          return { backgroundColor: 'hsl(0, 80%, 40%)' }
        }
        if (summary.includes('very negative')) {
          return { backgroundColor: 'hsl(10, 70%, 50%)' }
        }
        if (summary.includes('negative')) {
          return { backgroundColor: 'hsl(15, 65%, 45%)' }
        }
      }

      // Fallback to percentage-based classification
      if (percentage >= 80) {
        return { backgroundColor: 'hsl(120, 70%, 40%)' }
      }
      if (percentage >= 50) {
        return { backgroundColor: 'hsl(45, 60%, 50%)' }
      }
      return { backgroundColor: 'hsl(0, 80%, 40%)' }
    }

    const getPrice = (game) => {
      if (game.is_free) {
        return 'Free'
      }

      // Get the appropriate price based on selected currency
      if (game.display_price !== undefined) {
        return game.display_price
      } else if (props.currency === 'usd' && game.price_usd) {
        return game.price_usd
      } else {
        return game.price_eur // Default to EUR
      }
    }

    const getReleaseInfo = (game) => {
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

    const getReleaseType = (game) => {
      if (game.is_early_access) {
        return 'Early Access'
      }
      if (game.coming_soon) {
        return 'Unreleased'
      }
      return 'Released'
    }

    const getReleaseDate = (game) => {
      // Priority order for date selection
      if (game.planned_release_date) {
        return game.planned_release_date
      }
      if (game.release_date) {
        return game.release_date
      }
      return null
    }

    const formatDate = (dateString) => {
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

    const getMainPlatformUrl = (game) => {
      // Use unified display links if available
      if (game.display_links && game.display_links.main) {
        return game.display_links.main
      }

      // Fallback to platform-specific URLs
      if (game.platform === 'itch') {
        return game.itch_url
      }
      if (game.platform === 'crazygames') {
        return game.crazygames_url
      }
      return game.steam_url
    }

    const getMainPlatformName = (game) => {
      if (game.platform === 'itch') {
        return 'Itch.io'
      }
      if (game.platform === 'crazygames') {
        return 'CrazyGames'
      }
      return 'Steam'
    }

    const getDemoUrl = (game) => {
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

    const getPlatformName = (platform) => {
      if (platform === 'itch') {
        return 'Itch.io'
      }
      if (platform === 'crazygames') {
        return 'CrazyGames'
      }
      if (platform === 'steam') {
        return 'Steam'
      }
      return platform
    }

    const handleCardClick = async (event) => {
      // Don't handle clicks on links, buttons, or video toggles
      if (
        event.target.closest('a') ||
        event.target.closest('button') ||
        event.target.closest('.video-expand-toggle')
      ) {
        return
      }

      event.preventDefault()

      const deeplinkUrl = generateDeeplink(props.game)
      if (!deeplinkUrl) {
        console.warn('Could not generate deeplink for this game')
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

        console.log('Copied deeplink:', deeplinkUrl)
      } catch (err) {
        console.error('Failed to copy link:', err)
      }
    }

    const slugifyForFragment = (text) => {
      // RFC 3986 allowed characters in URL fragments:
      // unreserved: A-Z a-z 0-9 - . _ ~
      // sub-delims: ! $ & ' ( ) * + , ; =
      // also allowed in fragments: : @ / ?
      // Replace spaces with underscores, everything else forbidden gets replaced with hyphen

      return (
        text
          // First, replace spaces with underscores
          .replace(/ /g, '_')
          // Then replace any other forbidden characters with hyphens
          .replace(/[^A-Za-z0-9\-._~!$&'()*+,;=:@/?]/g, '-')
          // Replace multiple consecutive hyphens with single hyphen
          .replace(/-+/g, '-')
          // Remove leading/trailing hyphens
          .replace(/^-+|-+$/g, '')
      )
    }

    const generateDeeplink = (game) => {
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
        const match = game.crazygames_url.match(
          /crazygames\.com\/game\/([^/?]+)/,
        )
        if (match) {
          const slug = slugifyForFragment(game.name)
          return `${baseUrl}${searchParams}#crazygames-${match[1]}-${slug}`
        }
      }

      return null
    }

    const groupVideosByChannel = (videos) => {
      if (!videos || !Array.isArray(videos)) {
        return {}
      }

      const videosByChannel = {}

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
      (newVal, oldVal) => {
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

    return {
      showingVideos,
      loadingVideos,
      gameVideos,
      copyFeedback,
      showCopyOverlay,
      highlightFading,
      toggleVideos,
      handleCardClick,
      slugifyForFragment,
      generateDeeplink,
      getChannelText,
      groupVideosByChannel,
      shouldShowRating,
      getRatingNumbers,
      getRatingSummary,
      getRatingTooltip,
      getRatingClass,
      getRatingStyle,
      getPrice,
      getReleaseInfo,
      getReleaseType,
      getReleaseDate,
      formatDate,
      getMainPlatformUrl,
      getMainPlatformName,
      getDemoUrl,
      getPlatformName,
    }
  },
}
</script>

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
