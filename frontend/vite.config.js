// vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    allowedHosts: ['http', 'localhost', '127.0.0.1', '0.0.0.0', 'myapp.local'],
    watch: {
      usePolling: true
    }
  }
})
