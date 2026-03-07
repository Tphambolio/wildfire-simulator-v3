import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Separate the large mapping library
          'maplibre': ['maplibre-gl'],
          // Separate React framework
          'react-framework': ['react', 'react-dom'],
        }
      }
    },
    // Increase chunk size warning limit since maplibre is inherently large
    chunkSizeWarningLimit: 1000,
    // Enable sourcemaps for debugging
    sourcemap: true
  }
})
