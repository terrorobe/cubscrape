#!/usr/bin/env node

import { createHash } from 'crypto'
import { readFileSync, writeFileSync } from 'fs'
import { glob } from 'glob'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const rootDir = join(__dirname, '..')

async function generateAppVersion() {
  // Get all Vue components, JS files, and CSS files
  const patterns = [
    'src/**/*.vue',
    'src/**/*.js',
    'src/**/*.css',
    'index.html',
    'vite.config.js'
  ]

  const files = []
  for (const pattern of patterns) {
    const matches = await glob(pattern, { cwd: rootDir })
    files.push(...matches)
  }

  // Sort files for consistent ordering
  files.sort()

  // Create hash of all file contents
  const hash = createHash('sha256')

  for (const file of files) {
    const filePath = join(rootDir, file)
    const content = readFileSync(filePath, 'utf8')
    hash.update(file) // Include filename in hash
    hash.update(content)
  }

  const appVersion = hash.digest('hex').substring(0, 12)

  // Write version file
  const versionInfo = {
    version: appVersion,
    timestamp: new Date().toISOString(),
    files: files.length
  }

  const outputPath = join(rootDir, 'public', 'app-version.json')
  writeFileSync(outputPath, JSON.stringify(versionInfo, null, 2))

  console.log(`Generated app version: ${appVersion}`)
  console.log(`Hashed ${files.length} files`)
  console.log(`Written to: ${outputPath}`)

  return appVersion
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  generateAppVersion().catch(console.error)
}

export { generateAppVersion }