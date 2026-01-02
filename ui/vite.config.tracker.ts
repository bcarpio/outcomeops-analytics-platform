import { defineConfig } from 'vite'
import { resolve } from 'path'

// Build config for standalone tracker library
export default defineConfig({
  build: {
    lib: {
      entry: resolve(__dirname, 'src/tracker/outcomeops-tracker.ts'),
      name: 'OutcomeOpsTracker',
      fileName: 'tracker',
      formats: ['iife'],
    },
    outDir: 'dist-tracker',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
      },
    },
  },
})
