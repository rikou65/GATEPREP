import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    open: true,
  },
  build: {
    outDir: 'build',
    sourcemap: false,
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: 'vendor-react',
              test: /[\\/]node_modules[\\/](react|react-dom|react-router-dom|scheduler)[\\/]/,
            },
            {
              name: 'vendor-query',
              test: /[\\/]node_modules[\\/]@tanstack[\\/]react-query[\\/]/,
            },
            {
              name: 'vendor-charts',
              test: /[\\/]node_modules[\\/](recharts|d3-|victory-vendor)[\\/]/,
            },
            {
              name: 'vendor-pdf',
              test: /[\\/]node_modules[\\/](react-pdf|pdfjs-dist)[\\/]/,
            },
          ],
        },
      },
    },
  },
})
