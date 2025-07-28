/**
 * Performance monitoring utilities for filter operations
 * Helps track query execution times and optimization effectiveness
 */

/**
 * Performance measurement data
 */
interface PerformanceMeasurement {
  startTime: number
  endTime: number | null
  duration: number | null
}

/**
 * Performance statistics
 */
interface PerformanceStats {
  [operationName: string]: {
    duration: number
    timestamp: number
  }
}

/**
 * Performance monitoring composable interface
 */
export interface PerformanceMonitoringComposable {
  startTimer: (name: string) => void
  endTimer: (name: string) => number | undefined
  measureAsync: <T>(name: string, fn: () => Promise<T>) => Promise<T>
  measureSync: <T>(name: string, fn: () => T) => T
  monitorDatabaseQuery: <T>(desc: string, fn: () => T) => T
  monitorFilterUpdate: <T>(type: string, fn: () => T) => T
  getStats: () => PerformanceStats | null
}

class PerformanceMonitor {
  private measurements = new Map<string, PerformanceMeasurement>()
  private readonly isEnabled: boolean

  constructor() {
    this.isEnabled = import.meta.env.DEV
  }

  startTimer(operationName: string): void {
    if (!this.isEnabled) {
      return
    }

    this.measurements.set(operationName, {
      startTime: globalThis.performance?.now() || Date.now(),
      endTime: null,
      duration: null,
    })
  }

  endTimer(operationName: string): number | undefined {
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

  async measureAsync<T>(
    operationName: string,
    asyncOperation: () => Promise<T>,
  ): Promise<T> {
    if (!this.isEnabled) {
      return asyncOperation()
    }

    this.startTimer(operationName)
    try {
      const result = await asyncOperation()
      this.endTimer(operationName)
      return result
    } catch (error) {
      this.endTimer(operationName)
      throw error
    }
  }

  measureSync<T>(operationName: string, syncOperation: () => T): T {
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

  getStats(): PerformanceStats | null {
    if (!this.isEnabled) {
      return null
    }

    const stats: PerformanceStats = {}
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

  clear(): void {
    this.measurements.clear()
  }

  // Database query performance monitoring
  monitorDatabaseQuery<T>(queryDescription: string, queryFn: () => T): T {
    return this.measureSync(`DB Query: ${queryDescription}`, queryFn)
  }

  // Filter update performance monitoring
  monitorFilterUpdate<T>(filterType: string, updateFn: () => T): T {
    return this.measureSync(`Filter Update: ${filterType}`, updateFn)
  }

  // Render performance monitoring
  monitorRender<T>(componentName: string, renderFn: () => T): T {
    return this.measureSync(`Render: ${componentName}`, renderFn)
  }
}

// Create singleton instance
export const performanceMonitor = new PerformanceMonitor()

// React hook-like wrapper for Vue components
export function usePerformanceMonitoring(): PerformanceMonitoringComposable {
  return {
    startTimer: (name: string) => performanceMonitor.startTimer(name),
    endTimer: (name: string) => performanceMonitor.endTimer(name),
    measureAsync: <T>(name: string, fn: () => Promise<T>) =>
      performanceMonitor.measureAsync(name, fn),
    measureSync: <T>(name: string, fn: () => T) =>
      performanceMonitor.measureSync(name, fn),
    monitorDatabaseQuery: <T>(desc: string, fn: () => T) =>
      performanceMonitor.monitorDatabaseQuery(desc, fn),
    monitorFilterUpdate: <T>(type: string, fn: () => T) =>
      performanceMonitor.monitorFilterUpdate(type, fn),
    getStats: () => performanceMonitor.getStats(),
  }
}