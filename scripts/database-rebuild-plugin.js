import { spawn } from 'child_process'
import { join } from 'path'
import { existsSync } from 'fs'

/**
 * Custom Vite plugin to watch JSON files and rebuild database with queuing
 *
 * Features:
 * - Queues file changes instead of dropping them
 * - Respects cubscrape lock files to avoid conflicts
 * - Retries when cubscrape is running
 * - Only triggers HMR after successful builds that happen after all changes
 * - Proper error handling for different exit codes
 */
export function createDatabaseRebuildPlugin() {
  let isRebuilding = false
  let rebuildQueue = []
  let lastChangeTime = 0
  let lastSuccessfulBuildTime = 0

  const processQueue = async (server) => {
    if (isRebuilding || rebuildQueue.length === 0) {
      return
    }

    // Check if cubscrape is currently running
    const lockFile = join(process.cwd(), 'data', '.cubscrape.lock')
    if (existsSync(lockFile)) {
      console.log('\n⚠️  Cubscrape is currently running, rebuild queued...')
      // Retry after a delay
      setTimeout(() => processQueue(server), 2000)
      return
    }

    isRebuilding = true
    const queuedFiles = [...rebuildQueue]
    rebuildQueue = []

    console.log(`\n🔄 Processing queued changes for ${queuedFiles.length} file(s)`)
    console.log('📦 Rebuilding database...')

    try {
      const buildStartTime = Date.now()

      await new Promise((resolve, reject) => {
        const proc = spawn('uv', ['run', 'cubscrape', 'build-db'], {
          stdio: 'inherit',
          shell: true
        })

        proc.on('close', (code) => {
          if (code === 0) {
            lastSuccessfulBuildTime = buildStartTime
            console.log('✅ Database rebuilt successfully\n')
            resolve()
          } else if (code === 1) {
            // Exit code 1 typically means lock file conflict
            console.log('⚠️  Build-db failed due to lock conflict, requeueing...\n')
            // Re-queue the files for retry
            rebuildQueue.push(...queuedFiles)
            resolve() // Don't treat as fatal error
          } else {
            reject(new Error(`Database rebuild failed with exit code ${code}`))
          }
        })

        proc.on('error', (error) => {
          reject(new Error(`Failed to spawn build-db process: ${error.message}`))
        })
      })

      // Database rebuild completed - the SQLite file watcher will handle browser updates
      if (lastSuccessfulBuildTime >= lastChangeTime) {
        console.log('✅ Database rebuild completed - browser will update when SQLite file changes\n')
      } else {
        console.log('⚠️  More changes detected during build, requeueing...\n')
        // Don't trigger anything, let the next build handle it
      }

    } catch (error) {
      console.error('❌ Database rebuild failed:', error.message)
      // Re-queue the files for retry
      rebuildQueue.push(...queuedFiles)
    } finally {
      isRebuilding = false

      // Process any items that were queued during this rebuild
      if (rebuildQueue.length > 0) {
        setTimeout(() => processQueue(server), 1000)
      }
    }
  }

  return {
    name: 'database-rebuild',
    configureServer(server) {
      // Watch for changes in data/*.json files (for database rebuilds)
      server.watcher.add(join(process.cwd(), 'data', '*.json'))

      // Watch for changes in the SQLite database file (for browser updates)
      server.watcher.add(join(process.cwd(), 'data', 'games.db'))

      server.watcher.on('change', async (file) => {
        if (file.endsWith('games.db')) {
          // SQLite database changed - notify browser
          server.ws.send({
            type: 'custom',
            event: 'database-updated',
            data: { timestamp: Date.now() }
          })
          console.log('🔄 Database file updated, sent HMR event to clients')
        } else if (file.includes('/data/') && !file.includes('/public/data/') && file.endsWith('.json')) {
          // JSON file changed - queue database rebuild (no browser update yet)
          lastChangeTime = Date.now()

          // Add to queue if not already present
          if (!rebuildQueue.includes(file)) {
            rebuildQueue.push(file)
            console.log(`\n📝 Queued database rebuild for: ${file}`)
          }

          // Start processing the queue
          setTimeout(() => processQueue(server), 500) // Small delay to batch rapid changes
        }
      })
    },

    // Prevent default HMR for data JSON files - we handle them custom
    handleHotUpdate(ctx) {
      // Block HMR for data directory JSON files
      if (ctx.file.includes('/data/') && ctx.file.endsWith('.json')) {
        console.log('🚫 Blocked default HMR for:', ctx.file)
        return [] // Return empty array to prevent HMR
      }
      // Let other files use default HMR
      return undefined
    }
  }
}