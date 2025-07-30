import { ref, onMounted, onBeforeUnmount, type Ref } from 'vue'

export interface ProgressiveLoadingOptions {
  rootMargin?: string
  threshold?: number
  loadImmediately?: boolean
}

export function useProgressiveLoading(options: ProgressiveLoadingOptions = {}) {
  const {
    rootMargin = '100px',
    threshold = 0.1,
    loadImmediately = false
  } = options

  const elementRef: Ref<HTMLElement | undefined> = ref()
  const shouldLoad = ref(loadImmediately)
  const isLoaded = ref(false)
  let observer: IntersectionObserver | null = null

  const startLoading = () => {
    shouldLoad.value = true
  }

  const markAsLoaded = () => {
    isLoaded.value = true
  }

  onMounted(() => {
    if (loadImmediately || !elementRef.value) {
      shouldLoad.value = true
      return
    }

    observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            startLoading()
            // Disconnect after loading starts
            observer?.disconnect()
          }
        })
      },
      {
        rootMargin,
        threshold
      }
    )

    observer.observe(elementRef.value)
  })

  onBeforeUnmount(() => {
    observer?.disconnect()
  })

  return {
    elementRef,
    shouldLoad,
    isLoaded,
    startLoading,
    markAsLoaded
  }
}