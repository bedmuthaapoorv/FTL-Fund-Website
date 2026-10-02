import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Emit every asset (incl. small font subsets) as a file: the CSP allows
  // fonts/images from 'self' only, never data: URIs.
  build: { assetsInlineLimit: 0 },
  server: {
    port: 5180,
    strictPort: true,
    proxy: { '/api': 'http://127.0.0.1:8100' },
  },
})
