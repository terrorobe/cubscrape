<template>
  <div class="space-y-4">
    <!-- Current Preset Indicator -->
    <div v-if="currentPresetName" class="rounded-sm bg-accent/20 p-3">
      <div class="flex items-center gap-2">
        <svg
          class="size-4 text-accent"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M5 13l4 4L19 7"
          ></path>
        </svg>
        <span class="text-sm font-medium text-accent"
          >Active: {{ currentPresetName }}</span
        >
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="grid grid-cols-2 gap-2">
      <button
        v-if="!isCurrentFiltersSaved && hasActiveFilters"
        @click="showSaveDialog = true"
        class="rounded-sm bg-accent px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
      >
        Save Current
      </button>
      <button
        v-if="hasActiveFilters"
        @click="shareCurrentFilters"
        class="rounded-sm border border-gray-600 bg-bg-primary px-3 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-bg-secondary"
      >
        Share Link
      </button>
    </div>

    <!-- Search -->
    <div>
      <input
        v-model="searchQuery"
        placeholder="Search presets..."
        class="w-full rounded-sm border border-gray-600 bg-bg-primary px-3 py-2 text-text-primary placeholder-text-secondary focus:border-accent focus:ring-1 focus:ring-accent focus:outline-none"
      />
    </div>

    <!-- Popular Presets -->
    <div v-if="filteredPopularPresets.length > 0">
      <h4
        class="mb-2 text-sm font-semibold tracking-wide text-text-secondary uppercase"
      >
        Popular Presets
      </h4>
      <div class="space-y-1">
        <button
          v-for="preset in filteredPopularPresets"
          :key="preset.id"
          @click="applyPreset(preset)"
          class="w-full rounded-sm border border-gray-600 bg-bg-primary p-3 text-left transition-colors hover:bg-bg-secondary"
          :class="{
            'border-accent bg-accent/10': isCurrentPreset(preset),
          }"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0 flex-1">
              <div class="font-medium text-text-primary">{{ preset.name }}</div>
              <div class="mt-1 text-xs text-text-secondary">
                {{ preset.description }}
              </div>
            </div>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="tag in preset.tags.slice(
                  0,
                  UI_LIMITS.PRESET_TAG_PREVIEW_COUNT,
                )"
                :key="tag"
                class="rounded-sm bg-accent/20 px-1.5 py-0.5 text-xs text-accent"
              >
                {{ tag }}
              </span>
            </div>
          </div>
        </button>
      </div>
    </div>

    <!-- User Presets -->
    <div v-if="filteredUserPresets.length > 0">
      <div class="mb-2 flex items-center justify-between">
        <h4
          class="text-sm font-semibold tracking-wide text-text-secondary uppercase"
        >
          My Presets
        </h4>
        <button
          @click="showManageOptions = !showManageOptions"
          class="text-xs text-accent hover:text-accent-hover"
        >
          {{ showManageOptions ? 'Hide' : 'Manage' }}
        </button>
      </div>

      <div class="space-y-1">
        <div
          v-for="preset in filteredUserPresets"
          :key="preset.id"
          class="overflow-hidden rounded-sm border border-gray-600 bg-bg-primary"
          :class="{
            'border-accent bg-accent/10': isCurrentPreset(preset),
          }"
        >
          <button
            @click="applyPreset(preset)"
            class="w-full p-3 text-left transition-colors hover:bg-bg-secondary"
          >
            <div class="font-medium text-text-primary">{{ preset.name }}</div>
            <div class="mt-1 text-xs text-text-secondary">
              {{ preset.description }}
            </div>
          </button>

          <!-- Management Options -->
          <div
            v-if="showManageOptions"
            class="border-t border-gray-600 bg-bg-secondary px-3 py-2"
          >
            <div class="flex gap-2">
              <button
                @click="editPreset(preset)"
                class="flex-1 rounded-sm px-2 py-1 text-xs text-accent transition-colors hover:bg-accent hover:text-white"
              >
                Edit
              </button>
              <button
                @click="sharePreset(preset)"
                class="flex-1 rounded-sm px-2 py-1 text-xs text-text-secondary transition-colors hover:bg-bg-primary hover:text-accent"
              >
                Share
              </button>
              <button
                @click="deletePreset(preset)"
                class="flex-1 rounded-sm px-2 py-1 text-xs text-red-400 transition-colors hover:bg-red-600 hover:text-white"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Import/Export -->
    <div class="grid grid-cols-2 gap-2">
      <button
        @click="showImportDialog = true"
        class="rounded-sm border border-gray-600 bg-bg-primary px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-bg-secondary hover:text-accent"
      >
        Import
      </button>
      <button
        @click="exportPresets"
        :disabled="userPresets.length === 0"
        class="rounded-sm border border-gray-600 bg-bg-primary px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-bg-secondary hover:text-accent disabled:cursor-not-allowed disabled:opacity-50"
      >
        Export
      </button>
    </div>

    <!-- No Results -->
    <div
      v-if="
        filteredPopularPresets.length === 0 && filteredUserPresets.length === 0
      "
      class="py-8 text-center text-text-secondary"
    >
      <div class="text-sm">No presets found</div>
      <div class="text-xs">Try adjusting your search terms</div>
    </div>

    <!-- Save Preset Dialog -->
    <div
      v-if="showSaveDialog"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      @click.self="showSaveDialog = false"
    >
      <div class="w-full max-w-sm rounded-lg bg-bg-card p-4 shadow-xl">
        <h3 class="mb-4 text-lg font-semibold text-text-primary">
          Save Preset
        </h3>
        <div class="space-y-3">
          <div>
            <label class="mb-1 block text-sm font-medium text-text-secondary"
              >Name</label
            >
            <input
              ref="saveNameInput"
              v-model="saveForm.name"
              placeholder="Enter preset name..."
              class="w-full rounded-sm border border-gray-600 bg-bg-primary px-3 py-2 text-text-primary placeholder-text-secondary focus:border-accent focus:ring-1 focus:ring-accent focus:outline-none"
              @keydown.enter="saveCurrentPreset"
            />
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-text-secondary"
              >Description</label
            >
            <textarea
              v-model="saveForm.description"
              placeholder="Describe this preset..."
              rows="2"
              class="w-full resize-none rounded-sm border border-gray-600 bg-bg-primary px-3 py-2 text-text-primary placeholder-text-secondary focus:border-accent focus:ring-1 focus:ring-accent focus:outline-none"
            ></textarea>
          </div>
        </div>

        <div class="mt-4 flex gap-2">
          <button
            @click="showSaveDialog = false"
            class="flex-1 rounded-sm bg-gray-600 px-3 py-2 text-sm text-white transition-colors hover:bg-gray-700"
          >
            Cancel
          </button>
          <button
            @click="saveCurrentPreset"
            :disabled="!saveForm.name.trim()"
            class="flex-1 rounded-sm bg-accent px-3 py-2 text-sm text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            Save
          </button>
        </div>
      </div>
    </div>

    <!-- Import Dialog -->
    <div
      v-if="showImportDialog"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      @click.self="showImportDialog = false"
    >
      <div class="w-full max-w-sm rounded-lg bg-bg-card p-4 shadow-xl">
        <h3 class="mb-4 text-lg font-semibold text-text-primary">
          Import Presets
        </h3>
        <div class="space-y-3">
          <div>
            <label class="mb-1 block text-sm font-medium text-text-secondary">
              JSON Data
            </label>
            <textarea
              v-model="importData"
              placeholder="Paste preset JSON here..."
              rows="3"
              class="w-full resize-none rounded-sm border border-gray-600 bg-bg-primary px-3 py-2 text-xs text-text-primary placeholder-text-secondary focus:border-accent focus:ring-1 focus:ring-accent focus:outline-none"
            ></textarea>
          </div>

          <div>
            <input
              ref="fileInput"
              type="file"
              accept=".json"
              @change="handleFileSelect"
              class="hidden"
            />
            <button
              @click="fileInput?.click()"
              class="w-full rounded-sm border border-gray-600 bg-bg-secondary px-3 py-2 text-sm text-text-primary transition-colors hover:bg-bg-primary"
            >
              Select File
            </button>
          </div>

          <div class="flex items-center">
            <input
              id="mobile-overwrite"
              v-model="importOverwrite"
              type="checkbox"
              class="size-4 border-gray-600 text-accent focus:ring-accent"
            />
            <label
              for="mobile-overwrite"
              class="ml-2 text-xs text-text-secondary"
            >
              Overwrite existing
            </label>
          </div>
        </div>

        <div class="mt-4 flex gap-2">
          <button
            @click="showImportDialog = false"
            class="flex-1 rounded-sm bg-gray-600 px-3 py-2 text-sm text-white transition-colors hover:bg-gray-700"
          >
            Cancel
          </button>
          <button
            @click="importUserPresets"
            :disabled="!importData.trim()"
            class="flex-1 rounded-sm bg-accent px-3 py-2 text-sm text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            Import
          </button>
        </div>
      </div>
    </div>

    <!-- Toast Notifications -->
    <div
      v-if="notification"
      class="fixed right-4 bottom-4 z-50 rounded-lg px-3 py-2 text-sm text-white shadow-lg transition-opacity"
      :class="{
        'bg-green-600': notification.type === 'success',
        'bg-red-600': notification.type === 'error',
        'bg-blue-600': notification.type === 'info',
      }"
    >
      {{ notification.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, type Ref } from 'vue'
import { UI_LIMITS } from '../config/index'
import {
  getAllPresets,
  saveUserPreset,
  deleteUserPreset as deleteUserPresetUtil,
  generateShareableURL,
  exportPresets as exportPresetsUtil,
  importPresets,
  findMatchingPreset,
  areFiltersEqual,
  createDefaultFilters,
  POPULAR_PRESETS,
  type Preset,
  type FilterConfig,
  type ImportResult,
} from '../utils/presetManager'

// Component props interface
interface Props {
  currentFilters: FilterConfig
}

// Component events interface
interface Emits {
  'apply-preset': [filters: FilterConfig]
}

// Define props
const props = defineProps<Props>()

// Define emits
const emit = defineEmits<Emits>()

// Notification interface
interface Notification {
  message: string
  type: 'success' | 'error' | 'info'
}

// Save form interface
interface SaveForm {
  name: string
  description: string
  category: string
}

// Reactive state with proper typing
const showSaveDialog: Ref<boolean> = ref(false)
const showImportDialog: Ref<boolean> = ref(false)
const showManageOptions: Ref<boolean> = ref(false)
const searchQuery: Ref<string> = ref('')
const saveNameInput: Ref<HTMLInputElement | null> = ref(null)
const fileInput: Ref<HTMLInputElement | null> = ref(null)
const notification: Ref<Notification | null> = ref(null)

const saveForm: Ref<SaveForm> = ref({
  name: '',
  description: '',
  category: 'custom',
})

const importData: Ref<string> = ref('')
const importOverwrite: Ref<boolean> = ref(false)

// Reactive preset data
const allPresets: Ref<Preset[]> = ref(getAllPresets())
const userPresets = computed((): Preset[] => allPresets.value.filter((p) => p.isUser))
const popularPresets = computed((): Preset[] => POPULAR_PRESETS)

// Filtered presets based on search
const filteredPopularPresets = computed((): Preset[] => {
  if (!searchQuery.value.trim()) {
    return popularPresets.value
  }

  const query = searchQuery.value.toLowerCase()
  return popularPresets.value.filter(
    (preset) =>
      preset.name.toLowerCase().includes(query) ||
      preset.description.toLowerCase().includes(query) ||
      preset.tags.some((tag) => tag.toLowerCase().includes(query)),
  )
})

const filteredUserPresets = computed((): Preset[] => {
  if (!searchQuery.value.trim()) {
    return userPresets.value
  }

  const query = searchQuery.value.toLowerCase()
  return userPresets.value.filter(
    (preset) =>
      preset.name.toLowerCase().includes(query) ||
      preset.description.toLowerCase().includes(query) ||
      (preset.tags &&
        preset.tags.some((tag) => tag.toLowerCase().includes(query))),
  )
})

// Current preset detection
const currentPreset = computed((): Preset | undefined => {
  return findMatchingPreset(props.currentFilters)
})

const currentPresetName = computed((): string | null => {
  return currentPreset.value?.name || null
})

const isCurrentFiltersSaved = computed((): boolean => {
  return currentPreset.value !== undefined
})

const hasActiveFilters = computed((): boolean => {
  const defaultFilters = createDefaultFilters()
  return !areFiltersEqual(props.currentFilters, defaultFilters)
})

// Methods with proper typing
const showNotification = (message: string, type: 'success' | 'error' | 'info' = 'info'): void => {
  notification.value = { message, type }
  setTimeout(() => {
    notification.value = null
  }, 3000)
}

const refreshPresets = (): void => {
  allPresets.value = getAllPresets()
}

const applyPreset = (preset: Preset): void => {
  emit('apply-preset', preset.filters)
  showNotification(`Applied: ${preset.name}`, 'success')
}

const isCurrentPreset = (preset: Preset): boolean => {
  return currentPreset.value?.id === preset.id
}

const saveCurrentPreset = async (): Promise<void> => {
  if (!saveForm.value.name.trim()) {
    return
  }

  const result = saveUserPreset(
    saveForm.value.name,
    saveForm.value.description,
    props.currentFilters,
    saveForm.value.category,
    [],
  )

  if (result) {
    refreshPresets()
    showSaveDialog.value = false
    saveForm.value = { name: '', description: '', category: 'custom' }
    showNotification(`Saved: ${result.name}`, 'success')
  } else {
    showNotification('Save failed', 'error')
  }
}

const editPreset = (preset: Preset): void => {
  saveForm.value = {
    name: preset.name,
    description: preset.description || '',
    category: preset.category || 'custom',
  }
  showSaveDialog.value = true
}

const deletePreset = async (preset: Preset): Promise<void> => {
  if (!confirm(`Delete "${preset.name}"?`)) {
    return
  }

  if (deleteUserPresetUtil(preset.id)) {
    refreshPresets()
    showNotification(`Deleted: ${preset.name}`, 'success')
  } else {
    showNotification('Delete failed', 'error')
  }
}

const shareCurrentFilters = async (): Promise<void> => {
  try {
    const url = generateShareableURL(props.currentFilters)
    await navigator.clipboard.writeText(url)
    showNotification('Link copied!', 'success')
  } catch (error) {
    console.error('Failed to copy to clipboard:', error)
    showNotification('Copy failed', 'error')
  }
}

const sharePreset = async (preset: Preset): Promise<void> => {
  try {
    const url = generateShareableURL(preset.filters)
    await navigator.clipboard.writeText(url)
    showNotification(`Link copied: ${preset.name}`, 'success')
  } catch (error) {
    console.error('Failed to copy to clipboard:', error)
    showNotification('Copy failed', 'error')
  }
}

const exportPresets = (): void => {
  const data = exportPresetsUtil()
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = `presets-${new Date().toISOString().split('T')[0]}.json`
  link.click()

  URL.revokeObjectURL(url)
  showNotification('Presets exported', 'success')
}

const handleFileSelect = (event: Event): void => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) {
    return
  }

  const reader = new FileReader()
  reader.onload = (e) => {
    importData.value = e.target?.result as string
  }
  reader.readAsText(file)
}

const importUserPresets = (): void => {
  if (!importData.value.trim()) {
    return
  }

  try {
    const data = JSON.parse(importData.value)
    const result: ImportResult = importPresets(data, { overwrite: importOverwrite.value })

    if (result.success) {
      refreshPresets()
      showImportDialog.value = false
      importData.value = ''
      importOverwrite.value = false
      showNotification(`Imported ${result.count}`, 'success')
    } else {
      showNotification(`Import failed: ${result.error}`, 'error')
    }
  } catch {
    showNotification('Invalid JSON', 'error')
  }
}

// Auto-focus name input when save dialog opens
const focusSaveInput = async (): Promise<void> => {
  if (showSaveDialog.value) {
    await nextTick()
    saveNameInput.value?.focus()
  }
}

// Watch for save dialog changes
watch(showSaveDialog, (newValue: boolean) => {
  if (newValue) {
    focusSaveInput()
  }
})
</script>

<style scoped>
/* Ensure modals appear above everything */
.z-50 {
  z-index: 50;
}

/* Better touch targets for mobile */
button {
  min-height: 44px;
}

/* Animation for notifications */
.transition-opacity {
  transition: opacity 0.3s ease;
}
</style>
