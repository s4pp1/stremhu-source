// Test-only profiling build, copied to an isolated client checkout by the runner.
// Production Vite configuration and sources are not changed.
import tailwindcss from '@tailwindcss/vite'
import viteReact from '@vitejs/plugin-react'
import { resolve } from 'node:path'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    {
      name: 'cr-g04-render-counters',
      enforce: 'pre',
      transform(code, id) {
        const path = id.replaceAll('\\', '/')
        if (path.endsWith('/relay/torrents/index.tsx')) {
          return code.replace(
            'function RouteComponent() {',
            'function RouteComponent() { globalThis.__crG04.routeRenders++;',
          )
        }
        if (path.endsWith('/relay/torrents/-components/torrent.tsx')) {
          return code.replace(
            'const { torrent } = props',
            'const { torrent } = props; globalThis.__crG04.rowRenders[torrent.infoHash] = (globalThis.__crG04.rowRenders[torrent.infoHash] || 0) + 1',
          )
        }
      },
    },
    viteReact(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': resolve(import.meta.dirname, 'src'),
      'react-dom/client': resolve(
        import.meta.dirname,
        'node_modules/react-dom/profiling.js',
      ),
    },
  },
  build: {
    outDir: 'dist-g04',
    emptyOutDir: false,
    rollupOptions: { input: resolve(import.meta.dirname, '__cr_g04__/index.html') },
  },
})
