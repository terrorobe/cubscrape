import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { createDatabaseRebuildPlugin } from './scripts/database-rebuild-plugin.js'
import { resolve } from 'path'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue(), createDatabaseRebuildPlugin()],
  base: '/cubscrape/',
  resolve: {
    alias: {
      '@': resolve(fileURLToPath(new URL('.', import.meta.url)), 'src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      ignored: [
        // Performance ignores
        '**/node_modules/**',
        '**/dist/**',
        '**/.git/**',

        // Development files that don't affect webapp runtime
        '**/scripts/**',
        '**/eslint.config.js',
        '**/package.json',
        '**/package-lock.json',
        '**/*.md',

        // Python backend files
        '**/scraper/**',
        '**/.venv/**',
        '**/__pycache__/**',
        '**/.mypy_cache/**',
        '**/*.py',
        '**/*.pyc',
        '**/uv.lock',
        '**/pyproject.toml',

        // Other non-webapp directories
        '**/.github/**',
        '**/archive/**',
      ],
    },
  },
})
