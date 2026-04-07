import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Detect if running inside Tauri
const isTauri = !!process.env.TAURI_ENV_PLATFORM

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') }
  },
  build: {
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'index.html'),
        overlay: path.resolve(__dirname, 'overlay.html'),
      },
    },
  },
  server: {
    port: 5173,
    // In Tauri dev mode, the proxy is not needed (backend runs separately)
    proxy: isTauri ? undefined : {
      '/api': { target: 'http://localhost:8000', changeOrigin: true }
    },
    // Allow Tauri to connect
    strictPort: true,
  },
  // Prevent Vite from obscuring Rust errors
  clearScreen: false,
  // Env prefix for Tauri
  envPrefix: ['VITE_', 'TAURI_ENV_'],
})
