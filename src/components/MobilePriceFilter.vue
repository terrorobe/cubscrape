<template>
  <div class="space-y-4">
    <div class="mb-2 text-sm font-medium text-text-secondary">Price Filter</div>

    <!-- Free Games Toggle -->
    <label class="flex items-center justify-between">
      <span class="text-text-primary">Include Free Games</span>
      <input
        v-model="localIncludeFree"
        type="checkbox"
        class="size-4 text-accent"
        @change="handleChange"
      />
    </label>

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
          <label class="mb-1 block text-xs text-text-secondary">Min {{ currency.toUpperCase() }}:</label>
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
          <label class="mb-1 block text-xs text-text-secondary">Max {{ currency.toUpperCase() }}:</label>
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

<script>
import { ref, watch, computed } from 'vue'

export default {
  name: 'MobilePriceFilter',
  props: {
    initialPriceFilter: {
      type: Object,
      default: () => ({
        minPrice: 0,
        maxPrice: 70,
        includeFree: true,
      }),
    },
    currency: {
      type: String,
      default: 'eur',
    },
  },
  emits: ['price-filter-changed'],
  setup(props, { emit }) {
    const localMinPrice = ref(props.initialPriceFilter.minPrice)
    const localMaxPrice = ref(props.initialPriceFilter.maxPrice)
    const localIncludeFree = ref(props.initialPriceFilter.includeFree)

    const pricePresets = [
      { label: 'Free Only', min: 0, max: 0, includeFree: true },
      { label: 'Under $5', min: 0, max: 5, includeFree: true },
      { label: 'Under $10', min: 0, max: 10, includeFree: true },
      { label: 'Under $20', min: 0, max: 20, includeFree: true },
      { label: '$10-$30', min: 10, max: 30, includeFree: false },
      { label: '$30+', min: 30, max: 70, includeFree: false },
    ]

    const formatPrice = (price) => {
      if (price === 0) return 'Free'
      const symbol = props.currency === 'usd' ? '$' : '€'
      return `${symbol}${price}`
    }

    const getCurrentFilterDescription = () => {
      if (localMinPrice.value === 0 && localMaxPrice.value === 70 && localIncludeFree.value) {
        return 'All prices (including free)'
      }
      
      if (localMinPrice.value === 0 && localMaxPrice.value === 0) {
        return 'Free games only'
      }
      
      const minStr = formatPrice(localMinPrice.value)
      const maxStr = formatPrice(localMaxPrice.value)
      const freeNote = localIncludeFree.value ? ' (including free)' : ' (excluding free)'
      
      return `${minStr} to ${maxStr}${freeNote}`
    }

    const applyPreset = (preset) => {
      localMinPrice.value = preset.min
      localMaxPrice.value = preset.max
      localIncludeFree.value = preset.includeFree
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
        includeFree: localIncludeFree.value,
      }

      emit('price-filter-changed', priceFilter)
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
        if (newFilter.includeFree !== localIncludeFree.value) {
          localIncludeFree.value = newFilter.includeFree
        }
      },
      { deep: true },
    )

    return {
      localMinPrice,
      localMaxPrice,
      localIncludeFree,
      pricePresets,
      formatPrice,
      getCurrentFilterDescription,
      applyPreset,
      handleChange,
    }
  },
}
</script>