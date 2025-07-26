<template>
  <div class="flex flex-col gap-1">
    <label class="text-sm text-text-secondary">Price Range:</label>

    <!-- Price Presets -->
    <div class="mb-3 flex flex-wrap gap-1.5">
      <button
        v-for="preset in pricePresets"
        :key="preset.key"
        @click="selectPreset(preset)"
        :class="[
          'rounded-sm px-2 py-1 text-xs font-medium transition-colors',
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

<script>
import { reactive, computed, watch } from 'vue'

export default {
  name: 'PriceFilter',
  props: {
    currency: {
      type: String,
      default: 'eur',
      validator: (value) => ['eur', 'usd'].includes(value),
    },
    initialPriceFilter: {
      type: Object,
      default: () => ({
        minPrice: 0,
        maxPrice: 70,
        includeFree: true,
      }),
    },
    // Game statistics for showing filtered counts
    gameStats: {
      type: Object,
      default: () => ({
        totalGames: 0,
        freeGames: 0,
        maxPrice: 70,
      }),
    },
  },
  emits: ['price-filter-changed'],
  setup(props, { emit }) {
    const maxPossiblePrice = computed(() => props.gameStats.maxPrice || 70)
    const freeGameCount = computed(() => props.gameStats.freeGames || 0)

    const localPriceFilter = reactive({
      minPrice: props.initialPriceFilter.minPrice || 0,
      maxPrice: props.initialPriceFilter.maxPrice || maxPossiblePrice.value,
      includeFree: props.initialPriceFilter.includeFree !== false,
    })

    // Price presets based on common price ranges
    const pricePresets = computed(() => [
      {
        key: 'free',
        label: 'Free',
        minPrice: 0,
        maxPrice: 0,
        includeFree: true,
      },
      {
        key: 'under-5',
        label: '< $5',
        minPrice: 0,
        maxPrice: 5,
        includeFree: false,
      },
      {
        key: 'under-10',
        label: '< $10',
        minPrice: 0,
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
        minPrice: 0,
        maxPrice: maxPossiblePrice.value,
        includeFree: true,
      },
    ])

    // Format price according to currency
    const formatPrice = (price) => {
      if (price === 0) {
        return 'Free'
      }

      const symbol = props.currency === 'eur' ? '€' : '$'
      return `${symbol}${price.toFixed(2)}`
    }

    // Check if a preset is currently active
    const isPresetActive = (preset) => {
      return (
        localPriceFilter.minPrice === preset.minPrice &&
        localPriceFilter.maxPrice === preset.maxPrice &&
        localPriceFilter.includeFree === preset.includeFree
      )
    }

    // Select a price preset
    const selectPreset = (preset) => {
      localPriceFilter.minPrice = preset.minPrice
      localPriceFilter.maxPrice = preset.maxPrice
      localPriceFilter.includeFree = preset.includeFree
      emitFilterChanged()
    }

    // Handle min price changes (ensure min <= max)
    const handleMinChange = () => {
      if (localPriceFilter.minPrice > localPriceFilter.maxPrice) {
        localPriceFilter.maxPrice = localPriceFilter.minPrice
      }
    }

    // Handle max price changes (ensure max >= min)
    const handleMaxChange = () => {
      if (localPriceFilter.maxPrice < localPriceFilter.minPrice) {
        localPriceFilter.minPrice = localPriceFilter.maxPrice
      }
    }

    // Calculate the visual range fill style
    const rangeStyle = computed(() => {
      const minPercent =
        (localPriceFilter.minPrice / maxPossiblePrice.value) * 100
      const maxPercent =
        (localPriceFilter.maxPrice / maxPossiblePrice.value) * 100

      return {
        left: `${minPercent}%`,
        width: `${maxPercent - minPercent}%`,
      }
    })

    // Estimate filtered game count (simplified calculation)
    const getFilteredGameCount = () => {
      // This is a simplified estimation - in reality you'd need access to the full dataset
      // For now, we'll provide a basic estimate
      const totalPaidGames =
        props.gameStats.totalGames - props.gameStats.freeGames
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
    const emitFilterChanged = () => {
      emit('price-filter-changed', {
        minPrice: localPriceFilter.minPrice,
        maxPrice: localPriceFilter.maxPrice,
        includeFree: localPriceFilter.includeFree,
      })
    }

    // Watch for prop changes
    watch(
      () => props.initialPriceFilter,
      (newFilter) => {
        localPriceFilter.minPrice = newFilter.minPrice || 0
        localPriceFilter.maxPrice = newFilter.maxPrice || maxPossiblePrice.value
        localPriceFilter.includeFree = newFilter.includeFree !== false
      },
      { deep: true },
    )

    // Watch max possible price changes
    watch(maxPossiblePrice, (newMax) => {
      if (localPriceFilter.maxPrice > newMax) {
        localPriceFilter.maxPrice = newMax
        emitFilterChanged()
      }
    })

    return {
      localPriceFilter,
      maxPossiblePrice,
      freeGameCount,
      pricePresets,
      formatPrice,
      isPresetActive,
      selectPreset,
      handleMinChange,
      handleMaxChange,
      rangeStyle,
      getFilteredGameCount,
      emitFilterChanged,
    }
  },
}
</script>

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
