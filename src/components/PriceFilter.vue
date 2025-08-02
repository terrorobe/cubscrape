<script setup lang="ts">
import { reactive, computed, watch, ref } from 'vue'
import { PRICING } from '../config/index'
import type { ProcessedGameData } from '../services/GameDataProcessingService'

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
}

/**
 * Props interface for PriceFilter component
 */
export interface PriceFilterProps {
  currency?: Currency
  initialPriceFilter?: PriceFilterConfig
  gameStats?: GameStats
  filteredGames?: ProcessedGameData[]
  getLiveCount?: (priceFilter: PriceFilterConfig) => number
}

const props = withDefaults(defineProps<PriceFilterProps>(), {
  currency: 'eur',
  initialPriceFilter: () => ({
    minPrice: PRICING.MIN_PRICE,
    maxPrice: PRICING.DEFAULT_MAX_PRICE,
  }),
  gameStats: () => ({
    totalGames: 0,
    freeGames: 0,
    maxPrice: PRICING.DEFAULT_MAX_PRICE,
  }),
  filteredGames: () => [],
  getLiveCount: undefined,
})

const emit = defineEmits<{
  priceFilterChanged: [filter: PriceFilterConfig]
}>()
const maxPossiblePrice = computed(
  (): number => props.gameStats.maxPrice || PRICING.DEFAULT_MAX_PRICE,
)

const localPriceFilter = reactive<PriceFilterConfig>({
  minPrice: props.initialPriceFilter.minPrice ?? PRICING.MIN_PRICE,
  maxPrice: props.initialPriceFilter.maxPrice ?? maxPossiblePrice.value,
})

// Slider interaction state
const isDragging = ref(false)
const dragTarget = ref<'min' | 'max' | null>(null)
const sliderRef = ref<HTMLElement>()
const hoveredHandle = ref<'min' | 'max' | null>(null)

// Price presets based on common price ranges
const pricePresets = computed((): PricePreset[] => [
  {
    key: 'free',
    label: 'Free',
    minPrice: PRICING.MIN_PRICE,
    maxPrice: PRICING.MIN_PRICE,
  },
  {
    key: 'under-5',
    label: '< $5',
    minPrice: PRICING.MIN_PRICE,
    maxPrice: 5,
  },
  {
    key: 'under-10',
    label: '< $10',
    minPrice: PRICING.MIN_PRICE,
    maxPrice: 10,
  },
  {
    key: '5-15',
    label: '$5-15',
    minPrice: 5,
    maxPrice: 15,
  },
  {
    key: '10-30',
    label: '$10-30',
    minPrice: 10,
    maxPrice: 30,
  },
  {
    key: '15-40',
    label: '$15-40',
    minPrice: 15,
    maxPrice: 40,
  },
  {
    key: '30-plus',
    label: '$30+',
    minPrice: 30,
    maxPrice: maxPossiblePrice.value,
  },
  {
    key: 'all',
    label: 'All',
    minPrice: PRICING.MIN_PRICE,
    maxPrice: maxPossiblePrice.value,
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
  localPriceFilter.maxPrice === preset.maxPrice

// Select a price preset
const selectPreset = (preset: PricePreset): void => {
  localPriceFilter.minPrice = preset.minPrice
  localPriceFilter.maxPrice = preset.maxPrice
  emitFilterChanged()
}

// Handle min price changes (ensure min <= max)
const handleMinChange = (): void => {
  // Allow users to exit free-only mode via number inputs
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

// Detect if we're in "free only" mode
const isFreeOnlyMode = computed(
  (): boolean =>
    localPriceFilter.minPrice === 0 && localPriceFilter.maxPrice === 0,
)

// Calculate the visual range fill style
const rangeStyle = computed((): { left: string; width: string } => {
  const minPercent = (localPriceFilter.minPrice / maxPossiblePrice.value) * 100
  const maxPercent = (localPriceFilter.maxPrice / maxPossiblePrice.value) * 100

  return {
    left: `${minPercent}%`,
    width: `${Math.max(maxPercent - minPercent, 2)}%`, // Minimum 2% width for visibility
  }
})

// Calculate handle positions
const minHandleStyle = computed((): { left: string } => {
  const percent = (localPriceFilter.minPrice / maxPossiblePrice.value) * 100
  return { left: `${percent}%` }
})

const maxHandleStyle = computed((): { left: string } => {
  const percent = (localPriceFilter.maxPrice / maxPossiblePrice.value) * 100
  return { left: `${percent}%` }
})

// Convert mouse position to price value
const getValueFromMousePosition = (event: MouseEvent): number => {
  if (!sliderRef.value) {
    return 0
  }

  const rect = sliderRef.value.getBoundingClientRect()
  const percentage = Math.max(
    0,
    Math.min(1, (event.clientX - rect.left) / rect.width),
  )
  return Math.round(percentage * maxPossiblePrice.value * 2) / 2 // Round to nearest 0.5
}

// Calculate distance between mouse position and handle
const getDistanceToHandle = (
  event: MouseEvent,
  handleType: 'min' | 'max',
): number => {
  if (!sliderRef.value) {
    return Infinity
  }

  const rect = sliderRef.value.getBoundingClientRect()
  const mousePercent = (event.clientX - rect.left) / rect.width

  const handleValue =
    handleType === 'min' ? localPriceFilter.minPrice : localPriceFilter.maxPrice
  const handlePercent = handleValue / maxPossiblePrice.value

  return Math.abs(mousePercent - handlePercent)
}

// Check if mouse is over a handle (within 24px radius)
const isOverHandle = (
  event: MouseEvent,
  handleType: 'min' | 'max',
): boolean => {
  if (!sliderRef.value) {
    return false
  }

  const rect = sliderRef.value.getBoundingClientRect()

  const handleValue =
    handleType === 'min' ? localPriceFilter.minPrice : localPriceFilter.maxPrice
  const handlePercent = handleValue / maxPossiblePrice.value

  const handlePixelPos = handlePercent * rect.width
  const mousePixelPos = event.clientX - rect.left

  return Math.abs(mousePixelPos - handlePixelPos) <= 12 // 24px diameter handle
}

// Handle slider track clicks and drags
const handleSliderMouseDown = (event: MouseEvent): void => {
  if (!sliderRef.value) {
    return
  }

  event.preventDefault()

  // Check if clicking on a handle
  const overMinHandle = isOverHandle(event, 'min')
  const overMaxHandle = isOverHandle(event, 'max')

  if (overMinHandle && !overMaxHandle) {
    // Start dragging min handle
    isDragging.value = true
    dragTarget.value = 'min'
  } else if (overMaxHandle && !overMinHandle) {
    // Start dragging max handle
    isDragging.value = true
    dragTarget.value = 'max'
  } else if (overMinHandle && overMaxHandle) {
    // Both handles are overlapping (free-only mode at 0%)
    // Default to dragging the max handle to allow expanding the range
    isDragging.value = true
    dragTarget.value = 'max'
  } else {
    // Clicking on track - move the closer handle
    const newValue = getValueFromMousePosition(event)
    const minDistance = Math.abs(newValue - localPriceFilter.minPrice)
    const maxDistance = Math.abs(newValue - localPriceFilter.maxPrice)

    if (minDistance <= maxDistance) {
      localPriceFilter.minPrice = Math.min(newValue, localPriceFilter.maxPrice)
      dragTarget.value = 'min'
    } else {
      localPriceFilter.maxPrice = Math.max(newValue, localPriceFilter.minPrice)
      dragTarget.value = 'max'
    }

    isDragging.value = true
    emitFilterChanged()
  }

  // Add global mouse event listeners
  document.addEventListener('mousemove', handleSliderMouseMove)
  document.addEventListener('mouseup', handleSliderMouseUp)
}

const handleSliderMouseMove = (event: MouseEvent): void => {
  if (!isDragging.value || !dragTarget.value) {
    return
  }

  const newValue = getValueFromMousePosition(event)

  if (dragTarget.value === 'min') {
    localPriceFilter.minPrice = Math.max(
      0,
      Math.min(newValue, localPriceFilter.maxPrice),
    )
  } else {
    localPriceFilter.maxPrice = Math.min(
      maxPossiblePrice.value,
      Math.max(newValue, localPriceFilter.minPrice),
    )
  }

  emitFilterChanged()
}

const handleSliderMouseUp = (): void => {
  isDragging.value = false
  dragTarget.value = null

  // Remove global event listeners
  document.removeEventListener('mousemove', handleSliderMouseMove)
  document.removeEventListener('mouseup', handleSliderMouseUp)
}

// Handle mouse hover for visual feedback
const handleSliderHover = (event: MouseEvent): void => {
  if (isDragging.value) {
    // Don't update hover state while dragging
    return
  }

  const overMinHandle = isOverHandle(event, 'min')
  const overMaxHandle = isOverHandle(event, 'max')

  if (overMinHandle && !overMaxHandle) {
    hoveredHandle.value = 'min'
  } else if (overMaxHandle && !overMinHandle) {
    hoveredHandle.value = 'max'
  } else if (overMinHandle && overMaxHandle) {
    // Both handles close, show the closer one
    const minDistance = getDistanceToHandle(event, 'min')
    const maxDistance = getDistanceToHandle(event, 'max')
    hoveredHandle.value = minDistance <= maxDistance ? 'min' : 'max'
  } else {
    hoveredHandle.value = null
  }
}

const handleSliderMouseLeave = (): void => {
  if (!isDragging.value) {
    hoveredHandle.value = null
  }
}

// Calculate actual filtered game count based on price range
const filteredGameCount = computed((): number => {
  // Use live count if available (provides accurate count for all filters)
  if (props.getLiveCount) {
    return props.getLiveCount({
      minPrice: localPriceFilter.minPrice,
      maxPrice: localPriceFilter.maxPrice,
    })
  }

  // Fallback to local JavaScript filtering of pre-filtered games
  if (!props.filteredGames || props.filteredGames.length === 0) {
    return 0
  }

  return props.filteredGames.filter((game) => {
    // Get the price based on current currency
    const priceField = props.currency === 'usd' ? 'price_usd' : 'price_eur'
    const price = game[priceField] ?? (game.is_free ? 0 : null)

    // If price is null, skip this game
    if (price === null) {
      return false
    }

    return (
      price >= localPriceFilter.minPrice && price <= localPriceFilter.maxPrice
    )
  }).length
})

// Emit filter changes
const emitFilterChanged = (): void => {
  emit('priceFilterChanged', {
    minPrice: localPriceFilter.minPrice,
    maxPrice: localPriceFilter.maxPrice,
  })
}

// Watch for prop changes
watch(
  () => props.initialPriceFilter,
  (newFilter: PriceFilterConfig) => {
    // Use proper null/undefined checks instead of falsy checks to preserve 0 values
    localPriceFilter.minPrice = newFilter.minPrice ?? PRICING.MIN_PRICE
    localPriceFilter.maxPrice = newFilter.maxPrice ?? maxPossiblePrice.value
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

    <!-- Price Range Slider -->
    <div class="space-y-2">
      <div
        class="flex items-center justify-between text-xs text-text-secondary"
      >
        <span>{{ formatPrice(localPriceFilter.minPrice) }}</span>
        <span>{{ formatPrice(localPriceFilter.maxPrice) }}</span>
      </div>

      <!-- Custom intelligent dual-range slider -->
      <div
        ref="sliderRef"
        class="relative h-6 cursor-pointer"
        @mousedown="handleSliderMouseDown"
        @mousemove="handleSliderHover"
        @mouseleave="handleSliderMouseLeave"
      >
        <!-- Track -->
        <div
          class="absolute top-1/2 h-2 w-full -translate-y-1/2 rounded-full bg-gray-600"
        ></div>

        <!-- Range fill -->
        <div
          class="absolute top-1/2 h-2 -translate-y-1/2 rounded-full"
          :class="{
            'bg-accent': !isFreeOnlyMode,
            'bg-gradient-to-r from-green-500 to-green-400': isFreeOnlyMode,
            'transition-all duration-150': !isDragging,
          }"
          :style="rangeStyle"
        ></div>

        <!-- Free Only Text Label -->
        <div
          v-if="isFreeOnlyMode"
          class="pointer-events-none absolute top-1/2 left-4 -translate-y-1/2 rounded-sm bg-white/90 px-2 py-0.5 text-xs font-medium text-green-600 shadow-sm"
        >
          FREE ONLY
        </div>

        <!-- Min handle -->
        <div
          class="absolute top-1/2 size-5 -translate-1/2 rounded-full border-2 border-white shadow-md"
          :class="{
            'bg-accent': !isFreeOnlyMode,
            'bg-green-500': isFreeOnlyMode,
            'scale-110 shadow-lg':
              hoveredHandle === 'min' || dragTarget === 'min',
            'cursor-grab': hoveredHandle === 'min' && !isDragging,
            'cursor-grabbing': dragTarget === 'min',
            'transition-all duration-150': !isDragging,
          }"
          :style="minHandleStyle"
        ></div>

        <!-- Max handle -->
        <div
          class="absolute top-1/2 size-5 -translate-1/2 rounded-full border-2 border-white shadow-md"
          :class="{
            'bg-accent': !isFreeOnlyMode,
            'bg-green-500': isFreeOnlyMode,
            'scale-110 shadow-lg':
              hoveredHandle === 'max' || dragTarget === 'max',
            'cursor-grab': hoveredHandle === 'max' && !isDragging,
            'cursor-grabbing': dragTarget === 'max',
            'transition-all duration-150': !isDragging,
          }"
          :style="maxHandleStyle"
        ></div>
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
      <div
        class="text-xs"
        :class="
          isFreeOnlyMode ? 'font-medium text-green-600' : 'text-text-secondary'
        "
      >
        <template v-if="isFreeOnlyMode">
          {{ filteredGameCount }} free games available
        </template>
        <template v-else> {{ filteredGameCount }} games in range </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Custom dual-range slider styling */
.cursor-grab {
  cursor: grab;
}

.cursor-grabbing {
  cursor: grabbing;
}

/* Smooth transitions for better UX */
.transition-all {
  transition-property: all;
}
</style>
