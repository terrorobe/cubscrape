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
        '**/scraper/**',
        '**/.venv/**',
        '**/__pycache__/**',
        '**/.mypy_cache/**',
        '**/node_modules/**',
        '**/dist/**',
        '**/.git/**',
        '**/archive/**',
        '**/*.py',
        '**/*.pyc',
        '**/uv.lock',
        '**/pyproject.toml',
      ],
    },
  },
})
