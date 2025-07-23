import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/cubscrape/',
  server: {
    port: 5173,
  },
})
