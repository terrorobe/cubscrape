/**
 * Debug utility for development and production debugging
 *
 * In development: All debug.* calls work normally
 * In production: Only debug.error works, others are no-ops
 * Emergency production debugging: Set VITE_DEBUG=true or localStorage.debug='true'
 */

const DEBUG =
  import.meta.env.DEV ||
  (import.meta.env as Record<string, unknown>).VITE_DEBUG === 'true' ||
  (typeof localStorage !== 'undefined' &&
    localStorage.getItem('debug') === 'true')

export const debug = {
  /**
   * Debug-level logging (development only)
   */
  log: (...args: unknown[]) => DEBUG && console.log(...args),

  /**
   * Info-level logging (development only)
   */
  info: (...args: unknown[]) => DEBUG && console.info(...args),

  /**
   * Warning-level logging (development only)
   */
  warn: (...args: unknown[]) => DEBUG && console.warn(...args),

  /**
   * Error-level logging (always shown)
   */
  error: (...args: unknown[]) => console.error(...args),

  /**
   * Check if debug mode is enabled
   */
  enabled: DEBUG,
}
