<script>
import { ref, watch } from 'vue'

export default {
  name: 'MobilePriceFilter',
  props: {
    initialPriceFilter: {
      type: Object,
      default: () => ({
        minPrice: 0,
        maxPrice: 70,
      }),
    },
    currency: {
      type: String,
      default: 'eur',
    },
  },
  emits: ['priceFilterChanged'],
  setup(props, { emit }) {
    const localMinPrice = ref(props.initialPriceFilter.minPrice)
    const localMaxPrice = ref(props.initialPriceFilter.maxPrice)

    const symbol = props.currency === 'usd' ? '$' : '€'
    const pricePresets = [
      { label: 'Free Only', min: 0, max: 0 },
      { label: `Under ${symbol}5`, min: 0, max: 5 },
      { label: `Under ${symbol}10`, min: 0, max: 10 },
      { label: `Under ${symbol}20`, min: 0, max: 20 },
      { label: `${symbol}10-${symbol}30`, min: 10, max: 30 },
      { label: `${symbol}30+`, min: 30, max: 70 },
    ]

    const formatPrice = (price) => {
      if (price === 0) {
        return 'Free'
      }
      const symbol = props.currency === 'usd' ? '$' : '€'
      return `${symbol}${price}`
    }

    const getCurrentFilterDescription = () => {
      if (localMinPrice.value === 0 && localMaxPrice.value === 70) {
        return 'All prices'
      }

      if (localMinPrice.value === 0 && localMaxPrice.value === 0) {
        return 'Free games only'
      }

      const minStr = formatPrice(localMinPrice.value)
      const maxStr = formatPrice(localMaxPrice.value)

      return `${minStr} to ${maxStr}`
    }

    const applyPreset = (preset) => {
      localMinPrice.value = preset.min
      localMaxPrice.value = preset.max
      handleChange()
    }

    const handleChange = () => {
      // Ensure min <= max
      if (localMinPrice.value > localMaxPrice.value) {
        localMaxPrice.value = localMinPrice.value
      }

      const priceFilter = {
        minPrice: localMinPrice.value,
        maxPrice: localMaxPrice.value,
      }

      emit('priceFilterChanged', priceFilter)
    }

    // Watch for prop changes
    watch(
      () => props.initialPriceFilter,
      (newFilter) => {
        if (newFilter.minPrice !== localMinPrice.value) {
          localMinPrice.value = newFilter.minPrice
        }
        if (newFilter.maxPrice !== localMaxPrice.value) {
          localMaxPrice.value = newFilter.maxPrice
        }
      },
      { deep: true },
    )

    return {
      localMinPrice,
      localMaxPrice,
      pricePresets,
      formatPrice,
      getCurrentFilterDescription,
      applyPreset,
      handleChange,
    }
  },
}
</script>

<template>
  <div class="space-y-4">
    <div class="mb-2 text-sm font-medium text-text-secondary">Price Filter</div>

    <!-- Price Range Display -->
    <div class="space-y-2">
      <label class="text-sm text-text-secondary">Price Range:</label>
      <div class="flex items-center justify-between text-sm">
        <span class="text-text-primary">{{ formatPrice(localMinPrice) }}</span>
        <span class="text-text-secondary">to</span>
        <span class="text-text-primary">{{ formatPrice(localMaxPrice) }}</span>
      </div>
    </div>

    <!-- Price Range Sliders for Mobile -->
    <div class="space-y-3">
      <div>
        <label class="mb-2 block text-sm text-text-secondary">
          Minimum Price: {{ formatPrice(localMinPrice) }}
        </label>
        <input
          v-model.number="localMinPrice"
          type="range"
          min="0"
          max="70"
          step="1"
          class="w-full accent-accent"
          @input="handleChange"
        />
      </div>

      <div>
        <label class="mb-2 block text-sm text-text-secondary">
          Maximum Price: {{ formatPrice(localMaxPrice) }}
        </label>
        <input
          v-model.number="localMaxPrice"
          type="range"
          min="0"
          max="70"
          step="1"
          class="w-full accent-accent"
          @input="handleChange"
        />
      </div>
    </div>

    <!-- Price Presets -->
    <div class="space-y-2">
      <label class="text-sm text-text-secondary">Quick Presets:</label>
      <div class="grid grid-cols-2 gap-2">
        <button
          v-for="preset in pricePresets"
          :key="preset.label"
          @click="applyPreset(preset)"
          class="rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-sm text-text-primary transition-colors hover:bg-accent/10 hover:text-accent"
        >
          {{ preset.label }}
        </button>
      </div>
    </div>

    <!-- Manual Price Input -->
    <div class="space-y-2">
      <label class="text-sm text-text-secondary">Manual Entry:</label>
      <div class="grid grid-cols-2 gap-2">
        <div>
          <label class="mb-1 block text-xs text-text-secondary"
            >Min {{ currency.toUpperCase() }}:</label
          >
          <input
            v-model.number="localMinPrice"
            type="number"
            min="0"
            max="70"
            step="1"
            class="min-h-12 w-full rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary"
            @change="handleChange"
          />
        </div>
        <div>
          <label class="mb-1 block text-xs text-text-secondary"
            >Max {{ currency.toUpperCase() }}:</label
          >
          <input
            v-model.number="localMaxPrice"
            type="number"
            min="0"
            max="70"
            step="1"
            class="min-h-12 w-full rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary"
            @change="handleChange"
          />
        </div>
      </div>
    </div>

    <!-- Current Selection Summary -->
    <div class="rounded-sm border border-gray-600 bg-bg-card p-3">
      <div class="text-xs text-text-secondary">Current Filter:</div>
      <div class="text-sm text-text-primary">
        {{ getCurrentFilterDescription() }}
      </div>
    </div>
  </div>
</template>
