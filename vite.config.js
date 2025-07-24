import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { createDatabaseRebuildPlugin } from './scripts/database-rebuild-plugin.js'

export default defineConfig({
  plugins: [vue(), createDatabaseRebuildPlugin()],
  base: '/cubscrape/',
  server: {
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
