import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,                          // aceita acessos de fora do seu PC
    allowedHosts: ['.devtunnels.ms'],    // libera o endereço do túnel do VS Code
    proxy: {
      '/api': 'http://localhost:8000',   // repassa /api/... para o backend
    },
  },
  preview: {
    host: true,
    allowedHosts: ['.devtunnels.ms'],
    proxy: { '/api': 'http://localhost:8000' },
  },
})
