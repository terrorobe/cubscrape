/**
 * Filter Presets Management System
 * Handles saving, loading, and managing filter presets for quick access
 */

const PRESET_STORAGE_KEY = 'cubscrape-filter-presets'
const PRESET_VERSION = '1.0'

/**
 * Filter configuration interface
 */
export interface FilterConfig {
  releaseStatus: string
  platform: string
  rating: string
  crossPlatform?: boolean
  hiddenGems?: boolean
  tag?: string
  selectedTags: string[]
  tagLogic: 'and' | 'or'
  channel?: string
  selectedChannels: string[]
  sortBy: string
  sortSpec: any
  currency: 'eur' | 'usd'
  timeFilter: {
    type: string | null
    preset: string | null
    startDate: string | null
    endDate: string | null
    smartLogic: string | null
  }
  priceFilter: {
    minPrice: number
    maxPrice: number
    includeFree: boolean
  }
}

/**
 * Preset interface
 */
export interface Preset {
  id: string
  name: string
  description: string
  filters: FilterConfig
  category: string
  tags: string[]
  isPopular: boolean
  isUser?: boolean
  createdAt?: string
  updatedAt?: string
}

/**
 * Preset storage data interface
 */
interface PresetStorageData {
  version: string
  presets: Preset[]
  lastUpdated: string
}

/**
 * Export data interface
 */
export interface ExportData {
  version: string
  exported: string
  presets: Preset[]
}

/**
 * Import result interface
 */
export interface ImportResult {
  success: boolean
  imported?: Preset[]
  count?: number
  error?: string
}

/**
 * Import options interface
 */
export interface ImportOptions {
  overwrite: boolean
}

/**
 * Category data interface
 */
export interface CategoryData {
  name: string
  count: number
  presets: Preset[]
}

/**
 * Popular preset configurations based on common discovery patterns
 */
export const POPULAR_PRESETS: Preset[] = [
  {
    id: 'weekend-indie',
    name: 'Weekend Indie Games',
    description: 'Recent indie games under $20 perfect for weekend browsing',
    filters: {
      releaseStatus: 'all',
      platform: 'all',
      rating: '70',
      selectedTags: ['Indie'],
      tagLogic: 'and',
      selectedChannels: [],
      sortBy: 'best-value',
      sortSpec: null,
      currency: 'eur',
      timeFilter: {
        type: 'video',
        preset: 'last-month',
        startDate: null,
        endDate: null,
        smartLogic: null,
      },
      priceFilter: {
        minPrice: 0,
        maxPrice: 20,
        includeFree: true,
      },
    },
    category: 'discovery',
    tags: ['casual', 'budget'],
    isPopular: true,
  },
  {
    id: 'new-releases',
    name: 'New Steam Releases',
    description: 'Recently released games with good ratings',
    filters: {
      releaseStatus: 'released',
      platform: 'steam',
      rating: '75',
      selectedTags: [],
      tagLogic: 'and',
      selectedChannels: [],
      sortBy: 'release-new',
      sortSpec: null,
      currency: 'eur',
      timeFilter: {
        type: 'release',
        preset: 'last-month',
        startDate: null,
        endDate: null,
        smartLogic: null,
      },
      priceFilter: {
        minPrice: 0,
        maxPrice: 70,
        includeFree: true,
      },
    },
    category: 'new',
    tags: ['steam', 'new'],
    isPopular: true,
  },
  {
    id: 'free-hidden-gems',
    name: 'Free Hidden Gems',
    description: 'High-rated free games with recent positive coverage',
    filters: {
      releaseStatus: 'all',
      platform: 'all',
      rating: '80',
      selectedTags: [],
      tagLogic: 'and',
      selectedChannels: [],
      sortBy: 'hidden-gems',
      sortSpec: null,
      currency: 'eur',
      timeFilter: {
        type: null,
        preset: null,
        startDate: null,
        endDate: null,
        smartLogic: null,
      },
      priceFilter: {
        minPrice: 0,
        maxPrice: 0,
        includeFree: true,
      },
    },
    category: 'value',
    tags: ['free', 'quality'],
    isPopular: true,
  },
  {
    id: 'creator-picks',
    name: 'Creator Consensus',
    description: 'Games featured by multiple top channels',
    filters: {
      releaseStatus: 'all',
      platform: 'all',
      rating: '75',
      selectedTags: [],
      tagLogic: 'and',
      selectedChannels: [],
      sortBy: 'creator-consensus',
      sortSpec: null,
      currency: 'eur',
      timeFilter: {
        type: null,
        preset: null,
        startDate: null,
        endDate: null,
        smartLogic: null,
      },
      priceFilter: {
        minPrice: 0,
        maxPrice: 70,
        includeFree: true,
      },
    },
    category: 'curated',
    tags: ['consensus', 'quality'],
    isPopular: true,
  },
  {
    id: 'hidden-treasures',
    name: 'Hidden Treasures',
    description: 'Older games with recent positive coverage',
    filters: {
      releaseStatus: 'all',
      platform: 'all',
      rating: '80',
      selectedTags: [],
      tagLogic: 'and',
      selectedChannels: [],
      sortBy: 'hidden-gems',
      sortSpec: null,
      currency: 'eur',
      timeFilter: {
        type: 'smart',
        preset: null,
        startDate: null,
        endDate: null,
        smartLogic: 'old-game-new-attention',
      },
      priceFilter: {
        minPrice: 0,
        maxPrice: 70,
        includeFree: true,
      },
    },
    category: 'discovery',
    tags: ['hidden', 'rediscovered'],
    isPopular: true,
  },
  {
    id: 'budget-gaming',
    name: 'Budget Gaming',
    description: 'High-rated free and cheap games under $10',
    filters: {
      releaseStatus: 'all',
      platform: 'all',
      rating: '75',
      selectedTags: [],
      tagLogic: 'and',
      selectedChannels: [],
      sortBy: 'best-value',
      sortSpec: null,
      currency: 'eur',
      timeFilter: {
        type: null,
        preset: null,
        startDate: null,
        endDate: null,
        smartLogic: null,
      },
      priceFilter: {
        minPrice: 0,
        maxPrice: 10,
        includeFree: true,
      },
    },
    category: 'value',
    tags: ['budget', 'value'],
    isPopular: true,
  },
  {
    id: 'trending-now',
    name: 'Trending Now',
    description: 'Games gaining momentum with recent coverage',
    filters: {
      releaseStatus: 'all',
      platform: 'all',
      rating: '70',
      selectedTags: [],
      tagLogic: 'and',
      selectedChannels: [],
      sortBy: 'trending',
      sortSpec: null,
      currency: 'eur',
      timeFilter: {
        type: 'smart',
        preset: null,
        startDate: null,
        endDate: null,
        smartLogic: 'multiple-videos-recent',
      },
      priceFilter: {
        minPrice: 0,
        maxPrice: 70,
        includeFree: true,
      },
    },
    category: 'trending',
    tags: ['trending', 'momentum'],
    isPopular: true,
  },
  {
    id: 'itch-discoveries',
    name: 'Itch.io Discoveries',
    description: 'Creative indie discoveries from itch.io',
    filters: {
      releaseStatus: 'all',
      platform: 'itch',
      rating: '0',
      selectedTags: ['Indie'],
      tagLogic: 'and',
      selectedChannels: [],
      sortBy: 'itch-discoveries',
      sortSpec: null,
      currency: 'eur',
      timeFilter: {
        type: 'video',
        preset: 'last-2-months',
        startDate: null,
        endDate: null,
        smartLogic: null,
      },
      priceFilter: {
        minPrice: 0,
        maxPrice: 70,
        includeFree: true,
      },
    },
    category: 'platform',
    tags: ['itch', 'creative'],
    isPopular: true,
  },
]

/**
 * Create a default filter object with all possible filter values
 */
export function createDefaultFilters(): FilterConfig {
  return {
    releaseStatus: 'all',
    platform: 'all',
    rating: '0',
    crossPlatform: false,
    hiddenGems: false,
    tag: '',
    selectedTags: [],
    tagLogic: 'and',
    channel: '',
    selectedChannels: [],
    sortBy: 'date',
    sortSpec: null,
    currency: 'eur',
    timeFilter: {
      type: null,
      preset: null,
      startDate: null,
      endDate: null,
      smartLogic: null,
    },
    priceFilter: {
      minPrice: 0,
      maxPrice: 70,
      includeFree: true,
    },
  }
}

/**
 * Load user presets from localStorage
 */
export function loadUserPresets(): Preset[] {
  try {
    const stored = localStorage.getItem(PRESET_STORAGE_KEY)
    if (!stored) {
      return []
    }

    const data: PresetStorageData = JSON.parse(stored)

    // Version check for future compatibility
    if (data.version !== PRESET_VERSION) {
      console.warn('Preset version mismatch, clearing old presets')
      return []
    }

    return Array.isArray(data.presets) ? data.presets : []
  } catch (error) {
    console.error('Error loading user presets:', error)
    return []
  }
}

/**
 * Save user presets to localStorage
 */
export function saveUserPresets(presets: Preset[]): boolean {
  try {
    const data: PresetStorageData = {
      version: PRESET_VERSION,
      presets: presets,
      lastUpdated: new Date().toISOString(),
    }
    localStorage.setItem(PRESET_STORAGE_KEY, JSON.stringify(data))
    return true
  } catch (error) {
    console.error('Error saving user presets:', error)
    return false
  }
}

/**
 * Create a new user preset
 */
export function createUserPreset(
  name: string,
  description: string,
  filters: FilterConfig,
  category: string = 'custom',
  tags: string[] = [],
): Preset {
  return {
    id: `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    name: name.trim(),
    description: description.trim(),
    filters: { ...createDefaultFilters(), ...filters },
    category: category,
    tags: tags,
    isPopular: false,
    isUser: true,
    createdAt: new Date().toISOString(),
  }
}

/**
 * Get all presets (popular + user)
 */
export function getAllPresets(): Preset[] {
  const userPresets = loadUserPresets()
  return [...POPULAR_PRESETS, ...userPresets]
}

/**
 * Get presets by category
 */
export function getPresetsByCategory(category: string): Preset[] {
  return getAllPresets().filter((preset) => preset.category === category)
}

/**
 * Search presets by name or description
 */
export function searchPresets(query: string): Preset[] {
  if (!query || query.trim() === '') {
    return getAllPresets()
  }

  const lowerQuery = query.toLowerCase().trim()
  return getAllPresets().filter(
    (preset) =>
      preset.name.toLowerCase().includes(lowerQuery) ||
      preset.description.toLowerCase().includes(lowerQuery) ||
      preset.tags.some((tag) => tag.toLowerCase().includes(lowerQuery)),
  )
}

/**
 * Save a new user preset
 */
export function saveUserPreset(
  name: string,
  description: string,
  filters: FilterConfig,
  category: string = 'custom',
  tags: string[] = [],
): Preset | null {
  const userPresets = loadUserPresets()
  const newPreset = createUserPreset(name, description, filters, category, tags)

  userPresets.push(newPreset)

  if (saveUserPresets(userPresets)) {
    return newPreset
  }
  return null
}

/**
 * Update an existing user preset
 */
export function updateUserPreset(id: string, updates: Partial<Preset>): boolean {
  const userPresets = loadUserPresets()
  const index = userPresets.findIndex((preset) => preset.id === id)

  if (index === -1) {
    return false
  }

  userPresets[index] = {
    ...userPresets[index],
    ...updates,
    updatedAt: new Date().toISOString(),
  }

  return saveUserPresets(userPresets)
}

/**
 * Delete a user preset
 */
export function deleteUserPreset(id: string): boolean {
  const userPresets = loadUserPresets()
  const filtered = userPresets.filter((preset) => preset.id !== id)

  return saveUserPresets(filtered)
}

/**
 * Generate a shareable URL for a filter configuration
 */
export function generateShareableURL(
  filters: FilterConfig,
  baseURL: string = window.location.origin + window.location.pathname,
): string {
  const params = new URLSearchParams()

  // Only include non-default values
  if (filters.releaseStatus !== 'all') {
    params.set('release', filters.releaseStatus)
  }
  if (filters.platform !== 'all') {
    params.set('platform', filters.platform)
  }
  if (filters.rating !== '0') {
    params.set('rating', filters.rating)
  }

  // Handle tags
  if (filters.selectedTags && filters.selectedTags.length > 0) {
    params.set('tags', filters.selectedTags.join(','))
    if (filters.selectedTags.length > 1 && filters.tagLogic !== 'and') {
      params.set('tagLogic', filters.tagLogic)
    }
  }

  // Handle channels
  if (filters.selectedChannels && filters.selectedChannels.length > 0) {
    params.set('channels', filters.selectedChannels.join(','))
  }

  // Handle sorting
  if (filters.sortBy !== 'date') {
    params.set('sort', filters.sortBy)
  }
  if (filters.sortSpec) {
    params.set('sortSpec', JSON.stringify(filters.sortSpec))
  }

  // Handle currency
  if (filters.currency !== 'eur') {
    params.set('currency', filters.currency)
  }

  // Handle time filter
  if (filters.timeFilter?.type) {
    params.set('timeType', filters.timeFilter.type)
    if (filters.timeFilter.preset) {
      params.set('timePreset', filters.timeFilter.preset)
    }
    if (filters.timeFilter.startDate) {
      params.set('timeStart', filters.timeFilter.startDate)
    }
    if (filters.timeFilter.endDate) {
      params.set('timeEnd', filters.timeFilter.endDate)
    }
    if (filters.timeFilter.smartLogic) {
      params.set('timeLogic', filters.timeFilter.smartLogic)
    }
  }

  // Handle price filter
  const pf = filters.priceFilter
  if (pf && (pf.minPrice > 0 || pf.maxPrice < 70 || !pf.includeFree)) {
    if (pf.minPrice > 0) {
      params.set('priceMin', pf.minPrice.toString())
    }
    if (pf.maxPrice < 70) {
      params.set('priceMax', pf.maxPrice.toString())
    }
    if (!pf.includeFree) {
      params.set('includeFree', 'false')
    }
  }

  const url = new URL(baseURL)
  params.forEach((value, key) => {
    url.searchParams.set(key, value)
  })

  return url.toString()
}

/**
 * Parse a shareable URL back into filter configuration
 */
export function parseShareableURL(url: string): FilterConfig {
  try {
    const urlObj = new URL(url)
    const params = urlObj.searchParams
    const filters = createDefaultFilters()

    // Parse basic filters
    if (params.has('release')) {
      filters.releaseStatus = params.get('release')!
    }
    if (params.has('platform')) {
      filters.platform = params.get('platform')!
    }
    if (params.has('rating')) {
      filters.rating = params.get('rating')!
    }

    // Parse tags
    if (params.has('tags')) {
      const tagsParam = params.get('tags')!
      if (tagsParam.includes(',')) {
        filters.selectedTags = tagsParam.split(',').filter((tag) => tag.trim())
      } else if (tagsParam) {
        filters.selectedTags = [tagsParam]
      }
    }
    if (params.has('tagLogic')) {
      filters.tagLogic = params.get('tagLogic') as 'and' | 'or'
    }

    // Parse channels
    if (params.has('channels')) {
      const channelsParam = params.get('channels')!
      if (channelsParam.includes(',')) {
        filters.selectedChannels = channelsParam
          .split(',')
          .filter((channel) => channel.trim())
      } else if (channelsParam) {
        filters.selectedChannels = [channelsParam]
      }
    }

    // Parse sorting
    if (params.has('sort')) {
      filters.sortBy = params.get('sort')!
    }
    if (params.has('sortSpec')) {
      try {
        filters.sortSpec = JSON.parse(params.get('sortSpec')!)
      } catch {
        console.warn('Invalid sortSpec in URL')
      }
    }

    // Parse currency
    if (params.has('currency')) {
      filters.currency = params.get('currency') as 'eur' | 'usd'
    }

    // Parse time filter
    if (params.has('timeType')) {
      filters.timeFilter = {
        type: params.get('timeType'),
        preset: params.get('timePreset') || null,
        startDate: params.get('timeStart') || null,
        endDate: params.get('timeEnd') || null,
        smartLogic: params.get('timeLogic') || null,
      }
    }

    // Parse price filter
    if (
      params.has('priceMin') ||
      params.has('priceMax') ||
      params.has('includeFree')
    ) {
      filters.priceFilter = {
        minPrice: params.has('priceMin')
          ? parseFloat(params.get('priceMin')!)
          : 0,
        maxPrice: params.has('priceMax')
          ? parseFloat(params.get('priceMax')!)
          : 70,
        includeFree: params.get('includeFree') !== 'false',
      }
    }

    return filters
  } catch (error) {
    console.error('Error parsing shareable URL:', error)
    return createDefaultFilters()
  }
}

/**
 * Export presets to JSON for sharing
 */
export function exportPresets(presetIds: string[] | null = null): ExportData {
  const allPresets = getAllPresets()
  const presetsToExport = presetIds
    ? allPresets.filter((preset) => presetIds.includes(preset.id))
    : allPresets.filter((preset) => preset.isUser)

  return {
    version: PRESET_VERSION,
    exported: new Date().toISOString(),
    presets: presetsToExport.map((preset) => ({
      ...preset,
      // Remove runtime-only properties
      isPopular: undefined as any,
      isUser: undefined as any,
    })),
  }
}

/**
 * Import presets from JSON
 */
export function importPresets(
  importData: ExportData,
  options: ImportOptions = { overwrite: false },
): ImportResult {
  try {
    if (!importData.presets || !Array.isArray(importData.presets)) {
      throw new Error('Invalid preset data format')
    }

    const userPresets = loadUserPresets()
    const imported: Preset[] = []

    for (const presetData of importData.presets) {
      // Validate preset structure
      if (!presetData.name || !presetData.filters) {
        console.warn('Skipping invalid preset:', presetData)
        continue
      }

      // Check for existing preset with same name
      const existingIndex = userPresets.findIndex(
        (p) => p.name === presetData.name,
      )

      if (existingIndex !== -1) {
        if (options.overwrite) {
          // Update existing preset
          userPresets[existingIndex] = {
            ...userPresets[existingIndex],
            ...presetData,
            id: userPresets[existingIndex].id, // Keep original ID
            isUser: true,
            updatedAt: new Date().toISOString(),
          }
          imported.push(userPresets[existingIndex])
        } else {
          // Skip existing preset
          console.warn('Preset already exists:', presetData.name)
        }
      } else {
        // Create new preset
        const newPreset = createUserPreset(
          presetData.name,
          presetData.description || '',
          presetData.filters,
          presetData.category || 'custom',
          presetData.tags || [],
        )
        userPresets.push(newPreset)
        imported.push(newPreset)
      }
    }

    if (saveUserPresets(userPresets)) {
      return { success: true, imported, count: imported.length }
    } else {
      return { success: false, error: 'Failed to save presets' }
    }
  } catch (error) {
    console.error('Error importing presets:', error)
    return { success: false, error: (error as Error).message }
  }
}

/**
 * Get preset categories with counts
 */
export function getPresetCategories(): CategoryData[] {
  const allPresets = getAllPresets()
  const categories = new Map<string, { count: number; presets: Preset[] }>()

  allPresets.forEach((preset) => {
    const category = preset.category || 'custom'
    if (!categories.has(category)) {
      categories.set(category, { count: 0, presets: [] })
    }
    categories.get(category)!.count++
    categories.get(category)!.presets.push(preset)
  })

  return Array.from(categories.entries()).map(([name, data]) => ({
    name,
    count: data.count,
    presets: data.presets,
  }))
}

/**
 * Check if two filter configurations are equivalent
 */
export function areFiltersEqual(
  filters1: FilterConfig,
  filters2: FilterConfig,
): boolean {
  if (!filters1 || !filters2) {
    return false
  }

  // Compare all filter properties
  const keys = Object.keys(createDefaultFilters()) as (keyof FilterConfig)[]

  return keys.every((key) => {
    if (key === 'timeFilter' || key === 'priceFilter') {
      // Deep comparison for nested objects
      return JSON.stringify(filters1[key]) === JSON.stringify(filters2[key])
    } else if (Array.isArray(filters1[key]) && Array.isArray(filters2[key])) {
      // Array comparison
      return (
        JSON.stringify((filters1[key] as string[]).sort()) ===
        JSON.stringify((filters2[key] as string[]).sort())
      )
    } else {
      // Simple value comparison
      return filters1[key] === filters2[key]
    }
  })
}

/**
 * Find preset that matches current filters
 */
export function findMatchingPreset(currentFilters: FilterConfig): Preset | undefined {
  return getAllPresets().find((preset) =>
    areFiltersEqual(currentFilters, preset.filters),
  )
}