<script setup lang="ts">
import {
  ref,
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  watch,
  type Ref,
} from 'vue'
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
import { debug } from '../utils/debug'

// Component props interface
interface Props {
  currentFilters: FilterConfig
}

// Component events interface
interface Emits {
  applyPreset: [filters: FilterConfig]
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
const showDropdown: Ref<boolean> = ref(false)
const showSaveDialog: Ref<boolean> = ref(false)
const showImportDialog: Ref<boolean> = ref(false)
const showManageDialog: Ref<boolean> = ref(false)
const searchQuery: Ref<string> = ref('')
const searchInput: Ref<HTMLInputElement | null> = ref(null)
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
const userPresets = computed((): Preset[] =>
  allPresets.value.filter((p) => p.isUser),
)
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
const currentPreset = computed((): Preset | undefined =>
  findMatchingPreset(props.currentFilters),
)

const currentPresetName = computed(
  (): string | null => currentPreset.value?.name || null,
)

const isCurrentFiltersSaved = computed(
  (): boolean => currentPreset.value !== undefined,
)

const hasActiveFilters = computed((): boolean => {
  const defaultFilters = createDefaultFilters()
  return !areFiltersEqual(props.currentFilters, defaultFilters)
})

// Methods
const showNotification = (
  message: string,
  type: 'success' | 'error' | 'info' = 'info',
): void => {
  notification.value = { message, type }
  setTimeout(() => {
    notification.value = null
  }, 3000)
}

const refreshPresets = (): void => {
  allPresets.value = getAllPresets()
}

const handleBlur = (event: FocusEvent): void => {
  // Delay hiding dropdown to allow clicking on dropdown items
  setTimeout(() => {
    if (!(event?.relatedTarget as Element)?.closest('.absolute')) {
      showDropdown.value = false
    }
  }, 200)
}

const applyPreset = (preset: Preset): void => {
  emit('applyPreset', preset.filters)
  showDropdown.value = false
  showNotification(`Applied preset: ${preset.name}`, 'success')
}

const isCurrentPreset = (preset: Preset): boolean =>
  currentPreset.value?.id === preset.id

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
    showNotification(`Saved preset: ${result.name}`, 'success')
  } else {
    showNotification('Failed to save preset', 'error')
  }
}

const editPreset = (preset: Preset): void => {
  saveForm.value = {
    name: preset.name,
    description: preset.description || '',
    category: preset.category || 'custom',
  }
  showSaveDialog.value = true
  showDropdown.value = false
}

const deletePreset = async (preset: Preset): Promise<void> => {
  if (!confirm(`Delete preset "${preset.name}"?`)) {
    return
  }

  if (deleteUserPresetUtil(preset.id)) {
    refreshPresets()
    showNotification(`Deleted preset: ${preset.name}`, 'success')
  } else {
    showNotification('Failed to delete preset', 'error')
  }
}

const shareCurrentFilters = async (): Promise<void> => {
  try {
    const url = generateShareableURL(props.currentFilters)
    await navigator.clipboard.writeText(url)
    showNotification('Share URL copied to clipboard!', 'success')
  } catch (error) {
    debug.error('Failed to copy to clipboard:', error)
    showNotification('Failed to copy share URL', 'error')
  }
  showDropdown.value = false
}

const exportPresets = (): void => {
  const data = exportPresetsUtil()
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = `cubscrape-presets-${new Date().toISOString().split('T')[0]}.json`
  link.click()

  URL.revokeObjectURL(url)
  showDropdown.value = false
  showNotification('Presets exported successfully', 'success')
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
    const result: ImportResult = importPresets(data, {
      overwrite: importOverwrite.value,
    })

    if (result.success) {
      refreshPresets()
      showImportDialog.value = false
      importData.value = ''
      importOverwrite.value = false
      showNotification(
        `Imported ${result.count} presets successfully`,
        'success',
      )
    } else {
      showNotification(`Import failed: ${result.error}`, 'error')
    }
  } catch {
    showNotification('Invalid JSON data', 'error')
  }
}

// Handle clicks outside to close dropdown
const handleDocumentClick = (event: Event): void => {
  if (!(event.target as Element)?.closest('.relative')) {
    showDropdown.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
})

onUnmounted(() => {
  document.removeEventListener('click', handleDocumentClick)
})

// Auto-focus search when dropdown opens
const focusSearch = async (): Promise<void> => {
  if (showDropdown.value) {
    await nextTick()
    searchInput.value?.focus()
  }
}

// Auto-focus name input when save dialog opens
const focusSaveInput = async (): Promise<void> => {
  if (showSaveDialog.value) {
    await nextTick()
    saveNameInput.value?.focus()
  }
}

// Watch for dropdown changes
watch(showDropdown, (newValue: boolean) => {
  if (newValue) {
    focusSearch()
  } else {
    searchQuery.value = ''
  }
})

// Watch for save dialog changes
watch(showSaveDialog, (newValue: boolean) => {
  if (newValue) {
    focusSaveInput()
  }
})
</script>

<template>
  <div class="space-y-3">
    <h3 class="text-sm font-semibold text-text-primary">Filter Presets</h3>

    <!-- Preset Dropdown -->
    <div class="relative">
      <button
        @click="showDropdown = !showDropdown"
        @blur="handleBlur"
        class="w-full cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-left text-text-primary hover:border-accent focus:border-accent focus:ring-1 focus:ring-accent focus:outline-none"
        :class="{ 'border-accent': showDropdown }"
      >
        <div class="flex items-center justify-between">
          <span class="truncate">
            {{ currentPresetName || 'Select a preset...' }}
          </span>
          <div class="flex items-center gap-2">
            <!-- Save current filters as preset -->
            <button
              v-if="!isCurrentFiltersSaved && hasActiveFilters"
              @click.stop="showSaveDialog = true"
              class="rounded-sm px-2 py-1 text-xs text-accent transition-colors hover:bg-accent hover:text-white"
              title="Save current filters as preset"
            >
              Save
            </button>
            <!-- Share current filters -->
            <button
              v-if="hasActiveFilters"
              @click.stop="shareCurrentFilters"
              class="rounded-sm px-2 py-1 text-xs text-text-secondary transition-colors hover:text-accent"
              title="Share current filter configuration"
            >
              <svg
                class="size-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z"
                ></path>
              </svg>
            </button>
            <!-- Dropdown arrow -->
            <svg
              class="size-4 transition-transform"
              :class="{ 'rotate-180': showDropdown }"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 9l-7 7-7-7"
              ></path>
            </svg>
          </div>
        </div>
      </button>

      <!-- Dropdown Content -->
      <div
        v-if="showDropdown"
        class="absolute top-full right-0 left-0 z-50 mt-1 max-h-96 overflow-y-auto rounded-sm border border-gray-600 bg-bg-card shadow-lg"
      >
        <!-- Search Bar -->
        <div class="border-b border-gray-600 p-2">
          <input
            ref="searchInput"
            v-model="searchQuery"
            placeholder="Search presets..."
            class="w-full rounded-sm border border-gray-600 bg-bg-primary px-2 py-1 text-sm text-text-primary placeholder-text-secondary focus:border-accent focus:ring-1 focus:ring-accent focus:outline-none"
          />
        </div>

        <!-- Preset Categories -->
        <div class="max-h-80 overflow-y-auto">
          <!-- Popular Presets -->
          <div v-if="filteredPopularPresets.length > 0">
            <div class="border-b border-gray-600 bg-bg-secondary px-3 py-2">
              <h4
                class="text-xs font-semibold tracking-wide text-text-secondary uppercase"
              >
                Popular Presets
              </h4>
            </div>
            <div class="divide-y divide-gray-600">
              <button
                v-for="preset in filteredPopularPresets"
                :key="preset.id"
                @click="applyPreset(preset)"
                class="w-full px-3 py-2 text-left transition-colors hover:bg-bg-secondary focus:bg-bg-secondary focus:outline-none"
                :class="{ 'bg-accent/20': isCurrentPreset(preset) }"
              >
                <div class="flex items-center justify-between">
                  <div class="min-w-0 flex-1">
                    <div class="truncate font-medium text-text-primary">
                      {{ preset.name }}
                    </div>
                    <div class="truncate text-xs text-text-secondary">
                      {{ preset.description }}
                    </div>
                  </div>
                  <div class="ml-2 flex items-center gap-1">
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
            <div class="border-b border-gray-600 bg-bg-secondary px-3 py-2">
              <div class="flex items-center justify-between">
                <h4
                  class="text-xs font-semibold tracking-wide text-text-secondary uppercase"
                >
                  My Presets
                </h4>
                <button
                  @click="showManageDialog = true"
                  class="text-xs text-accent hover:text-accent-hover"
                >
                  Manage
                </button>
              </div>
            </div>
            <div class="divide-y divide-gray-600">
              <div
                v-for="preset in filteredUserPresets"
                :key="preset.id"
                class="flex items-center transition-colors hover:bg-bg-secondary"
                :class="{ 'bg-accent/20': isCurrentPreset(preset) }"
              >
                <button
                  @click="applyPreset(preset)"
                  class="flex-1 px-3 py-2 text-left focus:outline-none"
                >
                  <div class="truncate font-medium text-text-primary">
                    {{ preset.name }}
                  </div>
                  <div class="truncate text-xs text-text-secondary">
                    {{ preset.description }}
                  </div>
                </button>
                <div class="flex items-center gap-1 px-2">
                  <button
                    @click="editPreset(preset)"
                    class="rounded-sm p-1 text-text-secondary transition-colors hover:bg-bg-primary hover:text-accent"
                    title="Edit preset"
                  >
                    <svg
                      class="size-3"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                      ></path>
                    </svg>
                  </button>
                  <button
                    @click="deletePreset(preset)"
                    class="rounded-sm p-1 text-text-secondary transition-colors hover:bg-bg-primary hover:text-red-500"
                    title="Delete preset"
                  >
                    <svg
                      class="size-3"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      ></path>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- No Results -->
          <div
            v-if="
              filteredPopularPresets.length === 0 &&
              filteredUserPresets.length === 0
            "
            class="px-3 py-6 text-center text-text-secondary"
          >
            <div class="text-sm">No presets found</div>
            <div class="text-xs">Try adjusting your search terms</div>
          </div>
        </div>

        <!-- Footer Actions -->
        <div class="border-t border-gray-600 p-2">
          <div class="flex gap-2">
            <button
              @click="showImportDialog = true"
              class="flex-1 rounded-sm px-3 py-1 text-xs text-text-secondary transition-colors hover:bg-bg-secondary hover:text-accent"
            >
              Import
            </button>
            <button
              @click="exportPresets"
              class="flex-1 rounded-sm px-3 py-1 text-xs text-text-secondary transition-colors hover:bg-bg-secondary hover:text-accent"
              :disabled="userPresets.length === 0"
            >
              Export
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Save Preset Dialog -->
    <div
      v-if="showSaveDialog"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="showSaveDialog = false"
    >
      <div class="w-full max-w-md rounded-lg bg-bg-card p-6 shadow-xl">
        <h3 class="mb-4 text-lg font-semibold text-text-primary">
          Save Filter Preset
        </h3>
        <div class="space-y-4">
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
              placeholder="Describe what this preset is for..."
              rows="2"
              class="w-full resize-none rounded-sm border border-gray-600 bg-bg-primary px-3 py-2 text-text-primary placeholder-text-secondary focus:border-accent focus:ring-1 focus:ring-accent focus:outline-none"
            ></textarea>
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-text-secondary"
              >Category</label
            >
            <select
              v-model="saveForm.category"
              class="w-full rounded-sm border border-gray-600 bg-bg-primary px-3 py-2 text-text-primary focus:border-accent focus:ring-1 focus:ring-accent focus:outline-none"
            >
              <option value="custom">Custom</option>
              <option value="discovery">Discovery</option>
              <option value="value">Value</option>
              <option value="trending">Trending</option>
              <option value="platform">Platform</option>
            </select>
          </div>
        </div>

        <div class="mt-6 flex gap-3">
          <button
            @click="showSaveDialog = false"
            class="flex-1 rounded-sm bg-gray-600 px-4 py-2 text-white transition-colors hover:bg-gray-700"
          >
            Cancel
          </button>
          <button
            @click="saveCurrentPreset"
            :disabled="!saveForm.name.trim()"
            class="flex-1 rounded-sm bg-accent px-4 py-2 text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            Save
          </button>
        </div>
      </div>
    </div>

    <!-- Import Dialog -->
    <div
      v-if="showImportDialog"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="showImportDialog = false"
    >
      <div class="w-full max-w-md rounded-lg bg-bg-card p-6 shadow-xl">
        <h3 class="mb-4 text-lg font-semibold text-text-primary">
          Import Presets
        </h3>
        <div class="space-y-4">
          <div>
            <label class="mb-1 block text-sm font-medium text-text-secondary">
              Paste JSON data or select file
            </label>
            <textarea
              v-model="importData"
              placeholder="Paste preset JSON data here..."
              rows="4"
              class="w-full resize-none rounded-sm border border-gray-600 bg-bg-primary px-3 py-2 text-text-primary placeholder-text-secondary focus:border-accent focus:ring-1 focus:ring-accent focus:outline-none"
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
              class="w-full rounded-sm border border-gray-600 bg-bg-secondary px-3 py-2 text-text-primary transition-colors hover:bg-bg-primary"
            >
              Select JSON File
            </button>
          </div>

          <div class="flex items-center">
            <input
              id="overwrite"
              v-model="importOverwrite"
              type="checkbox"
              class="size-4 border-gray-600 text-accent focus:ring-accent"
            />
            <label for="overwrite" class="ml-2 text-sm text-text-secondary">
              Overwrite existing presets with same name
            </label>
          </div>
        </div>

        <div class="mt-6 flex gap-3">
          <button
            @click="showImportDialog = false"
            class="flex-1 rounded-sm bg-gray-600 px-4 py-2 text-white transition-colors hover:bg-gray-700"
          >
            Cancel
          </button>
          <button
            @click="importUserPresets"
            :disabled="!importData.trim()"
            class="flex-1 rounded-sm bg-accent px-4 py-2 text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            Import
          </button>
        </div>
      </div>
    </div>

    <!-- Toast Notifications -->
    <div
      v-if="notification"
      class="fixed right-4 bottom-4 z-50 rounded-lg px-4 py-2 text-white shadow-lg transition-opacity"
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

<style scoped>
/* Ensure dropdown appears above all other elements */
.z-50 {
  z-index: 50;
}

/* Custom scrollbar for dropdown */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.5);
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: rgba(156, 163, 175, 0.7);
}

/* Animation for dropdown */
.absolute {
  animation: slideDown 0.2s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Better focus states */
button:focus-visible {
  outline: 2px solid theme('colors.accent');
  outline-offset: 2px;
}
</style>
