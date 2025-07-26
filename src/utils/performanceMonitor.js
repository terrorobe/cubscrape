/**
 * Performance monitoring utilities for filter operations
 * Helps track query execution times and optimization effectiveness
 */

class PerformanceMonitor {
  constructor() {
    this.measurements = new Map()
    this.isEnabled = import.meta.env.DEV
  }

  startTimer(operationName) {
    if (!this.isEnabled) {
      return
    }

    this.measurements.set(operationName, {
      startTime: globalThis.performance?.now() || Date.now(),
      endTime: null,
      duration: null,
    })
  }

  endTimer(operationName) {
    if (!this.isEnabled) {
      return
    }

    const measurement = this.measurements.get(operationName)
    if (!measurement) {
      console.warn(`No start timer found for operation: ${operationName}`)
      return
    }

    measurement.endTime = globalThis.performance?.now() || Date.now()
    measurement.duration = measurement.endTime - measurement.startTime

    // Log performance if it's notable
    if (measurement.duration > 100) {
      console.warn(
        `🐌 Slow operation detected: ${operationName} took ${measurement.duration.toFixed(2)}ms`,
      )
    } else if (measurement.duration > 50) {
      console.log(
        `⚠️ ${operationName} took ${measurement.duration.toFixed(2)}ms`,
      )
    } else {
      console.log(
        `✅ ${operationName} completed in ${measurement.duration.toFixed(2)}ms`,
      )
    }

    return measurement.duration
  }

  measureAsync(operationName, asyncOperation) {
    if (!this.isEnabled) {
      return asyncOperation()
    }

    this.startTimer(operationName)
    return asyncOperation().finally(() => {
      this.endTimer(operationName)
    })
  }

  measureSync(operationName, syncOperation) {
    if (!this.isEnabled) {
      return syncOperation()
    }

    this.startTimer(operationName)
    try {
      const result = syncOperation()
      this.endTimer(operationName)
      return result
    } catch (error) {
      this.endTimer(operationName)
      throw error
    }
  }

  getStats() {
    if (!this.isEnabled) {
      return null
    }

    const stats = {}
    for (const [name, measurement] of this.measurements) {
      if (measurement.duration !== null) {
        stats[name] = {
          duration: measurement.duration,
          timestamp: measurement.startTime,
        }
      }
    }
    return stats
  }

  clear() {
    this.measurements.clear()
  }

  // Database query performance monitoring
  monitorDatabaseQuery(queryDescription, queryFn) {
    return this.measureSync(`DB Query: ${queryDescription}`, queryFn)
  }

  // Filter update performance monitoring
  monitorFilterUpdate(filterType, updateFn) {
    return this.measureSync(`Filter Update: ${filterType}`, updateFn)
  }

  // Render performance monitoring
  monitorRender(componentName, renderFn) {
    return this.measureSync(`Render: ${componentName}`, renderFn)
  }
}

// Create singleton instance
export const performanceMonitor = new PerformanceMonitor()

// React hook-like wrapper for Vue components
export function usePerformanceMonitoring() {
  return {
    startTimer: (name) => performanceMonitor.startTimer(name),
    endTimer: (name) => performanceMonitor.endTimer(name),
    measureAsync: (name, fn) => performanceMonitor.measureAsync(name, fn),
    measureSync: (name, fn) => performanceMonitor.measureSync(name, fn),
    monitorDatabaseQuery: (desc, fn) =>
      performanceMonitor.monitorDatabaseQuery(desc, fn),
    monitorFilterUpdate: (type, fn) =>
      performanceMonitor.monitorFilterUpdate(type, fn),
    getStats: () => performanceMonitor.getStats(),
  }
}
