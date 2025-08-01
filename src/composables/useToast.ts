/**
 * Simple Toast Notification Composable
 * Provides toast notifications for user feedback
 */

import { ref, type Ref } from 'vue'

export interface ToastMessage {
  id: string
  message: string
  type: 'success' | 'error' | 'info'
  duration: number
}

const toasts: Ref<ToastMessage[]> = ref([])
let toastIdCounter = 0

/**
 * Toast notification composable
 * Provides methods to show and manage toast notifications
 */
export function useToast() {
  /**
   * Show a toast notification
   */
  const showToast = (
    message: string,
    type: 'success' | 'error' | 'info' = 'info',
    duration: number = 3000,
  ): void => {
    const id = `toast_${++toastIdCounter}`

    const toast: ToastMessage = {
      id,
      message,
      type,
      duration,
    }

    // Add toast to list
    toasts.value.push(toast)

    // Auto-remove after duration
    setTimeout(() => {
      removeToast(id)
    }, duration)
  }

  /**
   * Remove a specific toast
   */
  const removeToast = (id: string): void => {
    const index = toasts.value.findIndex((toast) => toast.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  /**
   * Clear all toasts
   */
  const clearToasts = (): void => {
    toasts.value = []
  }

  return {
    toasts,
    showToast,
    removeToast,
    clearToasts,
  }
}
