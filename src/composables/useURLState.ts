/**
 * URL State Management Composable
 * Handles synchronization between application filters and URL parameters
 */

import type { Ref } from 'vue'
import { PRICING } from '../config/index'
import {
  serializeSortSpec,
  deserializeSortSpec,
  type SortSpec,
} from '../types/sorting'

/**
 * Interface for application filters (matches App.vue AppFilters)
 */
export interface URLFilters extends Record<string, unknown> {
  releaseStatus: string
  platform: string
  rating: string
  crossPlatform: boolean
  hiddenGems: boolean
  selectedTags: string[]
  tagLogic: 'and' | 'or'
  selectedChannels: string[]
  sortBy: string
  sortSpec: unknown
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
  searchQuery?: string
  searchInVideoTitles?: boolean
}

/**
 * URL State Management composable
 * Provides functions to sync filters with URL parameters
 */
export function useURLState() {
  /**
   * Update URL parameters based on current filter values
   */
  const updateURLParams = (
    filterValues: URLFilters,
    currentPage: Ref<number>,
    pageSize: Ref<number>,
  ): void => {
    const url = new URL(window.location.href)

    // Remove null/undefined values and update URL
    const params: Record<string, string | null> = {
      release:
        filterValues.releaseStatus !== 'all'
          ? filterValues.releaseStatus
          : null,
      platform: filterValues.platform !== 'all' ? filterValues.platform : null,
      rating: filterValues.rating !== '0' ? filterValues.rating : null,
      crossPlatform: filterValues.crossPlatform ? 'true' : null,
      hiddenGems: filterValues.hiddenGems ? 'true' : null,
      // Multi-tag format
      tags:
        filterValues.selectedTags && filterValues.selectedTags.length > 0
          ? filterValues.selectedTags.join(',')
          : null,
      tagLogic:
        filterValues.selectedTags &&
        filterValues.selectedTags.length > 1 &&
        filterValues.tagLogic !== 'and'
          ? filterValues.tagLogic
          : null,
      // Multi-channel format
      channels:
        filterValues.selectedChannels &&
        filterValues.selectedChannels.length > 0
          ? filterValues.selectedChannels.join(',')
          : null,
      sort: filterValues.sortBy !== 'date' ? filterValues.sortBy : null,
      sortSpec:
        filterValues.sortSpec &&
        typeof filterValues.sortSpec === 'object' &&
        filterValues.sortSpec !== null &&
        Object.keys(filterValues.sortSpec).length > 0
          ? serializeSortSpec(filterValues.sortSpec as SortSpec)
          : null,
      currency: filterValues.currency !== 'eur' ? filterValues.currency : null,
      // Time filter parameters
      timeType: filterValues.timeFilter.type ?? null,
      timePreset: filterValues.timeFilter.preset ?? null,
      timeStart: filterValues.timeFilter.startDate ?? null,
      timeEnd: filterValues.timeFilter.endDate ?? null,
      timeLogic: filterValues.timeFilter.smartLogic ?? null,
      // Price filter parameters
      priceMin:
        filterValues.priceFilter.minPrice > 0
          ? filterValues.priceFilter.minPrice.toString()
          : null,
      priceMax:
        filterValues.priceFilter.maxPrice < PRICING.DEFAULT_MAX_PRICE
          ? filterValues.priceFilter.maxPrice.toString()
          : null,
      includeFree:
        filterValues.priceFilter.includeFree === false ? 'false' : null,
      // Search parameters
      search: filterValues.searchQuery ? filterValues.searchQuery.trim() : null,
      searchVideos: filterValues.searchInVideoTitles === true ? 'true' : null,
      // Pagination parameters
      page: currentPage.value > 1 ? currentPage.value.toString() : null,
      size: pageSize.value !== 150 ? pageSize.value.toString() : null,
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

  /**
   * Load filter values from URL parameters
   */
  const loadFiltersFromURL = (
    searchQuery: Ref<string>,
    debouncedSearchQuery: Ref<string>,
    searchInVideoTitles: Ref<boolean>,
    currentPage: Ref<number>,
    pageSize: Ref<number>,
  ): Partial<URLFilters> => {
    const urlParams = new URLSearchParams(window.location.search)

    // Load each filter from URL if present
    const urlFilters: Partial<URLFilters> = {}

    if (urlParams.has('release')) {
      urlFilters.releaseStatus = urlParams.get('release') ?? undefined
    }

    if (urlParams.has('platform')) {
      urlFilters.platform = urlParams.get('platform') ?? undefined
    }

    if (urlParams.has('rating')) {
      urlFilters.rating = urlParams.get('rating') ?? undefined
    }

    if (urlParams.has('crossPlatform')) {
      urlFilters.crossPlatform = urlParams.get('crossPlatform') === 'true'
    }

    if (urlParams.has('hiddenGems')) {
      urlFilters.hiddenGems = urlParams.get('hiddenGems') === 'true'
    }

    // Handle tags parameter
    if (urlParams.has('tags')) {
      const tagsParam = urlParams.get('tags')
      if (tagsParam?.includes(',')) {
        // Multi-tag format: "tag1,tag2,tag3"
        urlFilters.selectedTags = tagsParam
          .split(',')
          .filter((tag) => tag.trim())
      } else if (tagsParam) {
        // Single tag format
        urlFilters.selectedTags = [tagsParam]
      }
    }

    if (urlParams.has('tagLogic')) {
      const tagLogic = urlParams.get('tagLogic')
      if (tagLogic === 'and' || tagLogic === 'or') {
        urlFilters.tagLogic = tagLogic
      }
    }

    // Handle channels parameter
    if (urlParams.has('channels')) {
      const channelsParam = urlParams.get('channels')
      if (channelsParam?.includes(',')) {
        // Multi-channel format: "channel1,channel2,channel3"
        urlFilters.selectedChannels = channelsParam
          .split(',')
          .filter((channel) => channel.trim())
      } else if (channelsParam) {
        // Single channel format
        urlFilters.selectedChannels = [channelsParam]
      }
    }

    if (urlParams.has('sort')) {
      urlFilters.sortBy = urlParams.get('sort') ?? undefined
    }

    if (urlParams.has('sortSpec')) {
      const sortSpecParam = urlParams.get('sortSpec')
      if (sortSpecParam) {
        urlFilters.sortSpec = deserializeSortSpec(sortSpecParam)
      }
    }

    if (urlParams.has('currency')) {
      const currency = urlParams.get('currency')
      if (currency === 'eur' || currency === 'usd') {
        urlFilters.currency = currency
      }
    }

    // Handle time filter parameters
    if (
      urlParams.has('timeType') ||
      urlParams.has('timePreset') ||
      urlParams.has('timeStart') ||
      urlParams.has('timeEnd') ||
      urlParams.has('timeLogic')
    ) {
      urlFilters.timeFilter = {
        type: urlParams.get('timeType') ?? null,
        preset: urlParams.get('timePreset') ?? null,
        startDate: urlParams.get('timeStart') ?? null,
        endDate: urlParams.get('timeEnd') ?? null,
        smartLogic: urlParams.get('timeLogic') ?? null,
      }
    }

    // Handle price filter parameters
    if (
      urlParams.has('priceMin') ||
      urlParams.has('priceMax') ||
      urlParams.has('includeFree')
    ) {
      urlFilters.priceFilter = {
        minPrice: urlParams.has('priceMin')
          ? parseFloat(urlParams.get('priceMin') ?? '0')
          : 0,
        maxPrice: urlParams.has('priceMax')
          ? parseFloat(
              urlParams.get('priceMax') ?? PRICING.DEFAULT_MAX_PRICE.toString(),
            )
          : PRICING.DEFAULT_MAX_PRICE,
        includeFree: urlParams.get('includeFree') !== 'false',
      }
    }

    // Handle search parameters
    if (urlParams.has('search')) {
      const searchParam = urlParams.get('search')
      if (searchParam) {
        urlFilters.searchQuery = searchParam
        searchQuery.value = searchParam
        debouncedSearchQuery.value = searchParam
      }
    }

    if (urlParams.has('searchVideos')) {
      urlFilters.searchInVideoTitles = urlParams.get('searchVideos') === 'true'
      searchInVideoTitles.value = urlParams.get('searchVideos') === 'true'
    }

    // Handle pagination parameters
    if (urlParams.has('page')) {
      const pageParam = urlParams.get('page')
      const pageNumber = pageParam ? parseInt(pageParam, 10) : 1
      if (pageNumber > 0) {
        currentPage.value = pageNumber
      }
    }

    if (urlParams.has('size')) {
      const sizeParam = urlParams.get('size')
      const sizeNumber = sizeParam ? parseInt(sizeParam, 10) : 150
      if ([50, 100, 150, 200].includes(sizeNumber)) {
        pageSize.value = sizeNumber
      }
    }

    return urlFilters
  }

  return {
    updateURLParams,
    loadFiltersFromURL,
  }
}
