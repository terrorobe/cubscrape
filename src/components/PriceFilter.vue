<script setup lang="ts">
import { reactive, computed, watch } from 'vue'
import { PRICING } from '../config/index'

/**
 * Currency type
 */
export type Currency = 'eur' | 'usd'

/**
 * Price filter configuration
 */
export interface PriceFilterConfig {
  minPrice: number
  maxPrice: number
  includeFree: boolean
}

/**
 * Game statistics for price filtering
 */
export interface GameStats {
  totalGames: number
  freeGames: number
  maxPrice: number
}

/**
 * Price preset configuration
 */
export interface PricePreset {
  key: string
  label: string
  minPrice: number
  maxPrice: number
  includeFree: boolean
}

/**
 * Props interface for PriceFilter component
 */
export interface PriceFilterProps {
  currency?: Currency
  initialPriceFilter?: PriceFilterConfig
  gameStats?: GameStats
}

const props = withDefaults(defineProps<PriceFilterProps>(), {
  currency: 'eur',
  initialPriceFilter: () => ({
    minPrice: PRICING.MIN_PRICE,
    maxPrice: PRICING.DEFAULT_MAX_PRICE,
    includeFree: true,
  }),
  gameStats: () => ({
    totalGames: 0,
    freeGames: 0,
    maxPrice: PRICING.DEFAULT_MAX_PRICE,
  }),
})

const emit = defineEmits<{
  priceFilterChanged: [filter: PriceFilterConfig]
}>()
const maxPossiblePrice = computed(
  (): number => props.gameStats.maxPrice || PRICING.DEFAULT_MAX_PRICE,
)
const freeGameCount = computed((): number => props.gameStats.freeGames || 0)

const localPriceFilter = reactive<PriceFilterConfig>({
  minPrice: props.initialPriceFilter.minPrice || PRICING.MIN_PRICE,
  maxPrice: props.initialPriceFilter.maxPrice || maxPossiblePrice.value,
  includeFree: props.initialPriceFilter.includeFree !== false,
})

// Price presets based on common price ranges
const pricePresets = computed((): PricePreset[] => [
  {
    key: 'free',
    label: 'Free',
    minPrice: PRICING.MIN_PRICE,
    maxPrice: PRICING.MIN_PRICE,
    includeFree: true,
  },
  {
    key: 'under-5',
    label: '< $5',
    minPrice: PRICING.MIN_PRICE,
    maxPrice: 5,
    includeFree: false,
  },
  {
    key: 'under-10',
    label: '< $10',
    minPrice: PRICING.MIN_PRICE,
    maxPrice: 10,
    includeFree: false,
  },
  {
    key: '5-15',
    label: '$5-15',
    minPrice: 5,
    maxPrice: 15,
    includeFree: false,
  },
  {
    key: '10-30',
    label: '$10-30',
    minPrice: 10,
    maxPrice: 30,
    includeFree: false,
  },
  {
    key: '15-40',
    label: '$15-40',
    minPrice: 15,
    maxPrice: 40,
    includeFree: false,
  },
  {
    key: '30-plus',
    label: '$30+',
    minPrice: 30,
    maxPrice: maxPossiblePrice.value,
    includeFree: false,
  },
  {
    key: 'all',
    label: 'All',
    minPrice: PRICING.MIN_PRICE,
    maxPrice: maxPossiblePrice.value,
    includeFree: true,
  },
])

// Format price according to currency
const formatPrice = (price: number): string => {
  if (price === 0) {
    return 'Free'
  }

  const symbol = props.currency === 'eur' ? '€' : '$'
  return `${symbol}${price.toFixed(2)}`
}

// Check if a preset is currently active
const isPresetActive = (preset: PricePreset): boolean =>
  localPriceFilter.minPrice === preset.minPrice &&
  localPriceFilter.maxPrice === preset.maxPrice &&
  localPriceFilter.includeFree === preset.includeFree

// Select a price preset
const selectPreset = (preset: PricePreset): void => {
  localPriceFilter.minPrice = preset.minPrice
  localPriceFilter.maxPrice = preset.maxPrice
  localPriceFilter.includeFree = preset.includeFree
  emitFilterChanged()
}

// Handle min price changes (ensure min <= max)
const handleMinChange = (): void => {
  if (localPriceFilter.minPrice > localPriceFilter.maxPrice) {
    localPriceFilter.maxPrice = localPriceFilter.minPrice
  }
}

// Handle max price changes (ensure max >= min)
const handleMaxChange = (): void => {
  if (localPriceFilter.maxPrice < localPriceFilter.minPrice) {
    localPriceFilter.minPrice = localPriceFilter.maxPrice
  }
}

// Calculate the visual range fill style
const rangeStyle = computed((): { left: string; width: string } => {
  const minPercent = (localPriceFilter.minPrice / maxPossiblePrice.value) * 100
  const maxPercent = (localPriceFilter.maxPrice / maxPossiblePrice.value) * 100

  return {
    left: `${minPercent}%`,
    width: `${maxPercent - minPercent}%`,
  }
})

// Estimate filtered game count (simplified calculation)
const getFilteredGameCount = (): number => {
  // This is a simplified estimation - in reality you'd need access to the full dataset
  // For now, we'll provide a basic estimate
  const totalPaidGames = props.gameStats.totalGames - props.gameStats.freeGames
  let estimatedCount = 0

  if (localPriceFilter.includeFree && localPriceFilter.minPrice === 0) {
    estimatedCount += props.gameStats.freeGames
  }

  if (localPriceFilter.maxPrice > 0) {
    // Rough estimation based on price range
    const priceRangeFactor = Math.min(
      localPriceFilter.maxPrice / maxPossiblePrice.value,
      1,
    )
    estimatedCount += Math.round(totalPaidGames * priceRangeFactor)
  }

  return Math.min(estimatedCount, props.gameStats.totalGames)
}

// Emit filter changes
const emitFilterChanged = (): void => {
  emit('priceFilterChanged', {
    minPrice: localPriceFilter.minPrice,
    maxPrice: localPriceFilter.maxPrice,
    includeFree: localPriceFilter.includeFree,
  })
}

// Watch for prop changes
watch(
  () => props.initialPriceFilter,
  (newFilter: PriceFilterConfig) => {
    localPriceFilter.minPrice = newFilter.minPrice || PRICING.MIN_PRICE
    localPriceFilter.maxPrice = newFilter.maxPrice || maxPossiblePrice.value
    localPriceFilter.includeFree = newFilter.includeFree !== false
  },
  { deep: true },
)

// Watch max possible price changes
watch(maxPossiblePrice, (newMax: number) => {
  if (localPriceFilter.maxPrice > newMax) {
    localPriceFilter.maxPrice = newMax
    emitFilterChanged()
  }
})
</script>

<template>
  <div class="space-y-3">
    <h3 class="text-sm font-semibold text-text-primary">Price Filter</h3>

    <!-- Price Presets -->
    <div class="mb-3 flex flex-wrap gap-1.5">
      <button
        v-for="preset in pricePresets"
        :key="preset.key"
        @click="selectPreset(preset)"
        class="rounded-sm px-2 py-1 text-xs font-medium transition-colors"
        :class="[
          isPresetActive(preset)
            ? 'bg-accent text-white'
            : 'border border-gray-600 bg-bg-card text-text-secondary hover:border-accent hover:text-accent',
        ]"
      >
        {{ preset.label }}
      </button>
    </div>

    <!-- Free Games Toggle -->
    <div class="mb-3 flex items-center">
      <input
        id="include-free"
        v-model="localPriceFilter.includeFree"
        type="checkbox"
        class="mr-2 size-4 rounded-sm border-gray-600 bg-bg-card text-accent focus:ring-2 focus:ring-accent"
        @change="emitFilterChanged"
      />
      <label
        for="include-free"
        class="cursor-pointer text-sm text-text-primary"
      >
        Include free games ({{ freeGameCount }} games)
      </label>
    </div>

    <!-- Price Range Slider -->
    <div class="space-y-2">
      <div
        class="flex items-center justify-between text-xs text-text-secondary"
      >
        <span>{{ formatPrice(localPriceFilter.minPrice) }}</span>
        <span>{{ formatPrice(localPriceFilter.maxPrice) }}</span>
      </div>

      <!-- Custom dual-range slider -->
      <div class="relative h-6">
        <!-- Track -->
        <div
          class="absolute top-1/2 h-2 w-full -translate-y-1/2 rounded-full bg-gray-600"
        ></div>

        <!-- Range fill -->
        <div
          class="absolute top-1/2 h-2 -translate-y-1/2 rounded-full bg-accent"
          :style="rangeStyle"
        ></div>

        <!-- Min handle -->
        <input
          v-model.number="localPriceFilter.minPrice"
          type="range"
          :min="0"
          :max="maxPossiblePrice"
          :step="0.5"
          class="price-slider absolute top-1/2 h-6 w-full -translate-y-1/2 cursor-pointer appearance-none bg-transparent"
          @input="handleMinChange"
          @change="emitFilterChanged"
        />

        <!-- Max handle -->
        <input
          v-model.number="localPriceFilter.maxPrice"
          type="range"
          :min="0"
          :max="maxPossiblePrice"
          :step="0.5"
          class="price-slider absolute top-1/2 h-6 w-full -translate-y-1/2 cursor-pointer appearance-none bg-transparent"
          @input="handleMaxChange"
          @change="emitFilterChanged"
        />
      </div>

      <!-- Price input fields -->
      <div class="flex items-center gap-2 text-sm">
        <div class="flex items-center gap-1">
          <span class="text-text-secondary">Min:</span>
          <input
            v-model.number="localPriceFilter.minPrice"
            type="number"
            :min="0"
            :max="maxPossiblePrice"
            step="0.50"
            class="w-16 rounded-sm border border-gray-600 bg-bg-card px-2 py-1 text-text-primary focus:border-accent focus:outline-none"
            @input="handleMinChange"
            @change="emitFilterChanged"
          />
        </div>
        <span class="text-text-secondary">–</span>
        <div class="flex items-center gap-1">
          <span class="text-text-secondary">Max:</span>
          <input
            v-model.number="localPriceFilter.maxPrice"
            type="number"
            :min="0"
            :max="maxPossiblePrice"
            step="0.50"
            class="w-16 rounded-sm border border-gray-600 bg-bg-card px-2 py-1 text-text-primary focus:border-accent focus:outline-none"
            @input="handleMaxChange"
            @change="emitFilterChanged"
          />
        </div>
      </div>

      <!-- Price stats -->
      <div class="text-xs text-text-secondary">
        {{ getFilteredGameCount() }} games in range
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Custom slider styling */
.price-slider::-webkit-slider-thumb {
  appearance: none;
  height: 20px;
  width: 20px;
  border-radius: 50%;
  background: theme('colors.accent');
  border: 2px solid #fff;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  transition: transform 0.1s ease;
}

.price-slider::-webkit-slider-thumb:hover {
  transform: scale(1.1);
}

.price-slider::-webkit-slider-thumb:active {
  transform: scale(1.2);
}

.price-slider::-moz-range-thumb {
  height: 20px;
  width: 20px;
  border-radius: 50%;
  background: theme('colors.accent');
  border: 2px solid #fff;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  transition: transform 0.1s ease;
  border: none;
}

.price-slider::-moz-range-thumb:hover {
  transform: scale(1.1);
}

.price-slider::-moz-range-thumb:active {
  transform: scale(1.2);
}

.price-slider::-moz-range-track {
  background: transparent;
}

/* Ensure sliders are stacked properly */
.price-slider:nth-of-type(2) {
  z-index: 1;
}

.price-slider:nth-of-type(3) {
  z-index: 2;
}

/* Hide default slider track */
.price-slider::-webkit-slider-track {
  background: transparent;
}

/* Focus styles */
.price-slider:focus {
  outline: none;
}

.price-slider:focus::-webkit-slider-thumb {
  box-shadow: 0 0 0 3px theme('colors.accent') / 0.3;
}

.price-slider:focus::-moz-range-thumb {
  box-shadow: 0 0 0 3px theme('colors.accent') / 0.3;
}
</style>
