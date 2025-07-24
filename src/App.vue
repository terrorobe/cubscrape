<template>
  <div class="min-h-screen bg-bg-primary text-text-primary">
    <div class="container mx-auto max-w-7xl p-5">
      <header class="mb-10 text-center">
        <h1 class="mb-2 text-4xl font-bold text-accent">Curated Steam Games</h1>
        <p class="text-lg text-text-secondary">
          Discovered from YouTube Gaming Channels
        </p>
      </header>

      <GameFilters
        :channels="channels"
        :tags="allTags"
        :initial-filters="filters"
        @filters-changed="updateFilters"
      />

      <div class="relative mb-5 text-text-secondary">
        <!-- Centered in screen -->
        <div class="text-center">
          <span>Showing {{ filteredGames.length }} games</span>
        </div>

        <!-- Database Status - Absolute positioned to right -->
        <div class="absolute top-0 right-0 flex items-center gap-4 text-sm">
          <div class="flex items-center gap-2">
            <span
              class="size-2 rounded-full"
              :class="databaseStatus.connected ? 'bg-green-500' : 'bg-red-500'"
            ></span>
            <span>{{ databaseStatus.games }} total</span>
          </div>
          <div class="text-xs text-text-secondary/70">
            <span v-if="databaseStatus.lastGenerated">
              Database:
              {{ formatTimestamp(databaseStatus.lastGenerated, true) }}
            </span>
            <span v-if="databaseStatus.lastChecked && !isDevelopment">
              • Last check: {{ formatTimestamp(databaseStatus.lastChecked) }}
            </span>
          </div>
        </div>
      </div>

      <div
        class="grid gap-5"
        style="grid-template-columns: repeat(auto-fill, minmax(300px, 1fr))"
      >
        <GameCard
          v-for="game in filteredGames"
          :key="game.id"
          :game="game"
          :currency="filters.currency"
          :is-highlighted="highlightedGameId === game.id"
          @click="clearHighlight"
        />
      </div>

      <div v-if="loading" class="py-10 text-center text-text-secondary">
        Loading games...
      </div>

      <div v-if="error" class="py-10 text-center text-red-500">
        Error loading games: {{ error }}
      </div>

      <div
        v-if="!loading && !error && filteredGames.length === 0"
        class="py-10 text-center text-text-secondary"
      >
        No games found matching your criteria.
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import GameCard from './components/GameCard.vue'
import GameFilters from './components/GameFilters.vue'
import { databaseManager } from './utils/databaseManager.js'

export default {
  name: 'App',
  components: {
    GameCard,
    GameFilters,
  },
  setup() {
    const loading = ref(true)
    const error = ref(null)
    const filters = ref({
      releaseStatus: 'all',
      platform: 'all',
      rating: '0',
      tag: '',
      channel: '',
      sortBy: 'date',
      currency: 'eur',
    })

    const channels = ref([])
    const allTags = ref([])
    const highlightedGameId = ref(null)
    const isDevelopment = import.meta.env.DEV
    const databaseStatus = ref({
      connected: false,
      games: 0,
      lastGenerated: null,
      lastChecked: null,
    })

    const loadChannelsAndTags = (database) => {
      // Get all unique channels
      const channelResults = database.exec(
        "SELECT DISTINCT unique_channels FROM games WHERE unique_channels IS NOT NULL AND unique_channels != '[]'",
      )
      const channelSet = new Set()
      if (channelResults.length > 0) {
        channelResults[0].values.forEach((row) => {
          try {
            const channelArray = JSON.parse(row[0] || '[]')
            channelArray.forEach((channel) => channelSet.add(channel))
          } catch {
            console.warn('Failed to parse channels:', row[0])
          }
        })
      }
      channels.value = Array.from(channelSet).sort()

      // Get all unique tags
      const tagResults = database.exec(
        "SELECT DISTINCT tags FROM games WHERE tags IS NOT NULL AND tags != '[]'",
      )
      const tagSet = new Set()
      if (tagResults.length > 0) {
        tagResults[0].values.forEach((row) => {
          try {
            const tags = JSON.parse(row[0] || '[]')
            tags.forEach((tag) => tagSet.add(tag))
          } catch {
            console.warn('Failed to parse tags:', row[0])
          }
        })
      }
      allTags.value = Array.from(tagSet).sort()
    }

    const filteredGames = ref([])

    const buildSQLQuery = (filterValues) => {
      console.log('Building query with filters:', filterValues)

      let query = `
        SELECT g.*,
               gv.video_title as latest_video_title,
               gv.video_id as latest_video_id
        FROM games g
        LEFT JOIN game_videos gv ON g.id = gv.game_id
        AND gv.video_date = g.latest_video_date
        WHERE 1=1
      `
      const params = []

      // For release date sorting, only include games with sortable dates
      if (
        filterValues.sortBy === 'release-new' ||
        filterValues.sortBy === 'release-old'
      ) {
        query += ' AND release_date_sortable IS NOT NULL'
      }

      // Platform filter
      if (filterValues.platform && filterValues.platform !== 'all') {
        if (filterValues.platform === 'itch') {
          query +=
            " AND (platform = ? OR (platform = 'steam' AND itch_url IS NOT NULL))"
          params.push(filterValues.platform)
        } else {
          query += ' AND platform = ?'
          params.push(filterValues.platform)
        }
      }

      // Release status filter
      if (filterValues.releaseStatus && filterValues.releaseStatus !== 'all') {
        if (filterValues.releaseStatus === 'released') {
          query +=
            " AND (platform IN ('itch', 'crazygames') OR (platform = 'steam' AND coming_soon = 0 AND is_early_access = 0 AND is_demo = 0))"
        } else if (filterValues.releaseStatus === 'early-access') {
          query +=
            " AND platform = 'steam' AND is_early_access = 1 AND coming_soon = 0"
        } else if (filterValues.releaseStatus === 'coming-soon') {
          query += " AND platform = 'steam' AND coming_soon = 1"
        }
      }

      // Rating filter
      if (filterValues.rating && filterValues.rating !== '0') {
        const ratingValue = parseInt(filterValues.rating)
        if (!isNaN(ratingValue)) {
          query += ' AND positive_review_percentage >= ?'
          params.push(ratingValue)
        }
      }

      // Tag filter
      if (filterValues.tag && filterValues.tag.trim()) {
        query += ' AND tags LIKE ?'
        params.push(`%"${filterValues.tag}"%`)
      }

      // Channel filter
      if (filterValues.channel && filterValues.channel.trim()) {
        query += ' AND unique_channels LIKE ?'
        params.push(`%"${filterValues.channel}"%`)
      }

      // Sorting
      const sortMappings = {
        'rating-score': 'positive_review_percentage DESC',
        'rating-category':
          'review_summary_priority ASC, positive_review_percentage DESC, review_count DESC',
        date: 'latest_video_date DESC',
        name: 'name ASC',
        'release-new': 'release_date_sortable DESC',
        'release-old': 'release_date_sortable ASC',
      }

      if (sortMappings[filterValues.sortBy]) {
        query += ` ORDER BY ${sortMappings[filterValues.sortBy]}`
      } else {
        query += ' ORDER BY latest_video_date DESC'
      }

      return { query, params }
    }

    const executeQuery = (db) => {
      const { query, params } = buildSQLQuery(filters.value)
      console.log('Executing query:', query)
      console.log('With params:', params)

      // Check for undefined params
      params.forEach((param, index) => {
        if (param === undefined) {
          console.error(`Parameter ${index} is undefined!`)
        }
      })

      const results = db.exec(query, params)

      if (results.length > 0) {
        const processedGames = []
        results[0].values.forEach((row) => {
          const columns = results[0].columns
          const gameData = {}

          columns.forEach((col, index) => {
            gameData[col] = row[index]
          })

          // Parse JSON columns
          try {
            gameData.genres = JSON.parse(gameData.genres || '[]')
            gameData.tags = JSON.parse(gameData.tags || '[]')
            gameData.developers = JSON.parse(gameData.developers || '[]')
            gameData.publishers = JSON.parse(gameData.publishers || '[]')
            gameData.unique_channels = JSON.parse(
              gameData.unique_channels || '[]',
            )
          } catch {
            console.warn(
              'Failed to parse JSON columns for game:',
              gameData.name,
            )
          }

          // Parse JSON fields that may contain display links
          try {
            gameData.display_links = gameData.display_links
              ? JSON.parse(gameData.display_links)
              : null
          } catch {
            gameData.display_links = null
          }

          // Create game object matching the original data structure
          const game = {
            id: gameData.id,
            name: gameData.name,
            steam_app_id: gameData.steam_app_id,
            header_image: gameData.header_image,
            price_eur: gameData.price_eur,
            price_usd: gameData.price_usd,
            is_free: gameData.is_free,
            release_date: gameData.release_date,
            review_summary: gameData.review_summary,
            review_summary_priority: gameData.review_summary_priority,
            positive_review_percentage: gameData.positive_review_percentage,
            review_count: gameData.review_count,
            steam_url: gameData.steam_url,
            itch_url: gameData.itch_url,
            crazygames_url: gameData.crazygames_url,
            demo_steam_app_id: gameData.demo_steam_app_id,
            demo_steam_url: gameData.demo_steam_url,
            display_links: gameData.display_links,
            tags: gameData.tags || [],
            platform: gameData.platform,
            last_updated: gameData.last_updated,
            latest_video_title: gameData.latest_video_title,
            latest_video_id: gameData.latest_video_id,
            latest_video_date: gameData.latest_video_date,
            newest_video_date: gameData.latest_video_date,
            unique_channels: gameData.unique_channels || [],
            video_count: gameData.video_count || 0,
            coming_soon: gameData.coming_soon,
            is_early_access: gameData.is_early_access,
            is_demo: gameData.is_demo,
            planned_release_date: gameData.planned_release_date,
            insufficient_reviews: gameData.insufficient_reviews,
            is_inferred_summary: gameData.is_inferred_summary,
            review_tooltip: gameData.review_tooltip,
            recent_review_percentage: gameData.recent_review_percentage,
            recent_review_count: gameData.recent_review_count,
          }

          processedGames.push(game)
        })
        filteredGames.value = processedGames
      } else {
        filteredGames.value = []
      }
    }

    let db = null

    const loadDatabase = async () => {
      await databaseManager.init()
      db = databaseManager.getDatabase()
    }

    const updateDatabaseStatus = () => {
      const stats = databaseManager.getStats()
      if (stats) {
        databaseStatus.value.connected = true
        databaseStatus.value.games = stats.games
        databaseStatus.value.lastGenerated = stats.lastModified
          ? new Date(stats.lastModified)
          : null
        databaseStatus.value.lastChecked = stats.lastCheckTime
      } else {
        databaseStatus.value.connected = false
        databaseStatus.value.games = 0
        databaseStatus.value.lastGenerated = null
        databaseStatus.value.lastChecked = null
      }
    }

    const formatTimestamp = (timestamp, useOld = false) => {
      if (!timestamp) {
        return 'Unknown'
      }
      const date = new Date(timestamp)
      const now = new Date()
      const diffMs = now - date
      const diffMins = Math.floor(diffMs / 60000)
      const diffHours = Math.floor(diffMs / 3600000)

      const suffix = useOld ? ' old' : ' ago'

      if (diffMins < 1) {
        return 'just now'
      }
      if (diffMins < 60) {
        return `${diffMins}m${suffix}`
      }
      if (diffHours < 24) {
        return `${diffHours}h${suffix}`
      }
      return date.toLocaleDateString()
    }

    const onDatabaseUpdate = (database) => {
      db = database
      loadChannelsAndTags(db)
      executeQuery(db)
      updateDatabaseStatus()
      console.log('🔄 UI updated with new database')
    }

    const loadGames = async () => {
      try {
        await loadDatabase()

        // Set up listener for database updates
        databaseManager.addUpdateListener(onDatabaseUpdate)

        loadChannelsAndTags(db)
        updateDatabaseStatus()

        // Load filters from URL before executing query
        loadFiltersFromURL()

        executeQuery(db)

        // Process deeplink after loading games
        await nextTick()
        await processDeeplink()
      } catch (err) {
        console.error('Error loading database:', err)
        error.value = err.message
      } finally {
        loading.value = false
      }
    }

    const processDeeplink = async () => {
      const hash = window.location.hash
      if (!hash || hash.length <= 1) {
        return
      }

      // Wait for next frame to ensure DOM is ready
      await new Promise((resolve) => requestAnimationFrame(resolve))

      // Parse deeplink format:
      // Old format: #steam-123456 or #itch-game-slug
      // New format: #steam-123456-Game-Name or #itch-game-slug-Game-Name
      const deeplinkParts = hash.substring(1).split('-')
      if (deeplinkParts.length < 2) {
        return
      }

      const platform = deeplinkParts[0]
      let gameId

      // For Steam, the ID is numeric, so we can detect where it ends
      if (platform === 'steam') {
        // Find the first non-numeric part after platform
        let idEndIndex = 1
        while (
          idEndIndex < deeplinkParts.length &&
          /^\d+$/.test(deeplinkParts[idEndIndex])
        ) {
          idEndIndex++
        }
        gameId = deeplinkParts.slice(1, idEndIndex).join('-')
      } else {
        // For other platforms, we need to be more careful
        // The game ID could contain hyphens, so we look for a part that looks like a slugified name
        // As a heuristic, if we have more than 2 parts, assume the last parts are the name slug
        // This maintains backward compatibility with old URLs
        if (deeplinkParts.length === 2) {
          // Old format: just platform and ID
          gameId = deeplinkParts[1]
        } else {
          // New format: try to intelligently split
          // For now, assume single-part IDs (can be refined based on platform patterns)
          gameId = deeplinkParts[1]
        }
      }

      // Find and scroll to the game
      await scrollToGame(platform, gameId)
    }

    const scrollToGame = async (platform, gameId) => {
      // Find the game in our current filtered list
      let targetGame = null

      if (platform === 'steam') {
        targetGame = filteredGames.value.find(
          (game) =>
            game.steam_app_id && game.steam_app_id.toString() === gameId,
        )
      } else if (platform === 'itch') {
        targetGame = filteredGames.value.find(
          (game) =>
            game.itch_url && game.itch_url.includes(`${gameId}.itch.io`),
        )
      } else if (platform === 'crazygames') {
        targetGame = filteredGames.value.find(
          (game) =>
            game.crazygames_url &&
            game.crazygames_url.includes(`crazygames.com/game/${gameId}`),
        )
      }

      if (!targetGame) {
        console.warn('Game not found:', platform, gameId)
        // Try to adjust filters to show the game
        await tryToShowGame(platform, gameId)
        return
      }

      // Highlight the game
      highlightGame(targetGame)

      // Wait for next tick to ensure the game card is rendered
      await nextTick()

      // Find the game card element and scroll to it
      const gameCards = document.querySelectorAll('.game-card')
      for (const card of gameCards) {
        // Find the card by checking if it contains our target game data
        const cardTitle = card.querySelector('h3')?.textContent
        if (cardTitle === targetGame.name) {
          card.scrollIntoView({
            behavior: 'smooth',
            block: 'center',
          })
          break
        }
      }
    }

    const tryToShowGame = async (platform, gameId) => {
      // If we can't find the game, it might be filtered out
      // Try setting platform filter and clearing others
      if (
        platform === 'steam' ||
        platform === 'itch' ||
        platform === 'crazygames'
      ) {
        const newFilters = {
          platform: platform,
          releaseStatus: 'all',
          rating: '0',
          tag: '',
          channel: '',
          sortBy: filters.value.sortBy,
          currency: filters.value.currency,
        }

        filters.value = newFilters

        // Re-execute query with new filters
        if (db) {
          executeQuery(db)
        }

        // Wait a moment then try again
        await new Promise((resolve) => setTimeout(resolve, 100))
        await scrollToGame(platform, gameId)
      }
    }

    const highlightGame = (game) => {
      // Clear any existing highlights
      clearHighlight()

      // Set highlighted game
      highlightedGameId.value = game.id

      // Set up auto-fade after 6 seconds (like original)
      setTimeout(() => {
        if (highlightedGameId.value === game.id) {
          // Start fade-out process
          highlightedGameId.value = null
        }
      }, 6000)
    }

    const clearHighlight = () => {
      highlightedGameId.value = null
    }

    const updateFilters = (newFilters) => {
      filters.value = { ...filters.value, ...newFilters }
      updateURLParams(filters.value)
      if (db) {
        executeQuery(db)
      }
    }

    const updateURLParams = (filterValues) => {
      const url = new URL(window.location)

      // Remove null/undefined values and update URL
      const params = {
        release:
          filterValues.releaseStatus !== 'all'
            ? filterValues.releaseStatus
            : null,
        platform:
          filterValues.platform !== 'all' ? filterValues.platform : null,
        rating: filterValues.rating !== '0' ? filterValues.rating : null,
        tag: filterValues.tag || null,
        channel: filterValues.channel || null,
        sort: filterValues.sortBy !== 'date' ? filterValues.sortBy : null,
        currency:
          filterValues.currency !== 'eur' ? filterValues.currency : null,
      }

      Object.keys(params).forEach((key) => {
        if (params[key] === null || params[key] === undefined) {
          url.searchParams.delete(key)
        } else {
          url.searchParams.set(key, params[key])
        }
      })

      // Update URL without page reload
      window.history.replaceState({}, '', url)
    }

    const loadFiltersFromURL = () => {
      const urlParams = new URLSearchParams(window.location.search)

      // Load each filter from URL if present
      const urlFilters = {}

      if (urlParams.has('release')) {
        urlFilters.releaseStatus = urlParams.get('release')
      }

      if (urlParams.has('platform')) {
        urlFilters.platform = urlParams.get('platform')
      }

      if (urlParams.has('rating')) {
        urlFilters.rating = urlParams.get('rating')
      }

      if (urlParams.has('tag')) {
        urlFilters.tag = urlParams.get('tag')
      }

      if (urlParams.has('channel')) {
        urlFilters.channel = urlParams.get('channel')
      }

      if (urlParams.has('sort')) {
        urlFilters.sortBy = urlParams.get('sort')
      }

      if (urlParams.has('currency')) {
        urlFilters.currency = urlParams.get('currency')
      }

      // Update filters with URL values
      if (Object.keys(urlFilters).length > 0) {
        filters.value = { ...filters.value, ...urlFilters }
      }
    }

    onMounted(() => {
      loadGames()

      // Set up keyboard handler for clearing highlights
      const handleKeydown = (e) => {
        if (e.key === 'Escape') {
          clearHighlight()
        }
      }

      document.addEventListener('keydown', handleKeydown)
    })

    onUnmounted(() => {
      // Cleanup database manager
      if (databaseManager.isLoaded()) {
        databaseManager.removeUpdateListener(onDatabaseUpdate)
        databaseManager.destroy()
      }

      // Remove keyboard handler
      const handleKeydown = (e) => {
        if (e.key === 'Escape') {
          clearHighlight()
        }
      }
      document.removeEventListener('keydown', handleKeydown)
    })

    return {
      loading,
      error,
      filters,
      channels,
      allTags,
      filteredGames,
      highlightedGameId,
      databaseStatus,
      isDevelopment,
      formatTimestamp,
      updateFilters,
      clearHighlight,
    }
  },
}
</script>
