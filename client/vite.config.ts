import tailwindcss from '@tailwindcss/vite'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import viteReact from '@vitejs/plugin-react'
import { resolve } from 'node:path'
import { defineConfig } from 'vite'

export default defineConfig(({ command }) => ({
  plugins: [
    tanstackRouter({ target: 'react', autoCodeSplitting: true }),
    viteReact(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'https://localhost:7070',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    sourcemap: command === 'serve',
  },
}))
