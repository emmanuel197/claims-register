import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// In development the app calls the same-origin `/api` and Vite proxies it to
// Django, so no CORS setup is needed locally. In production VITE_API_BASE_URL
// points at the hosted API.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: process.env.VITE_DEV_API_TARGET || 'http://localhost:8000', changeOrigin: true },
    },
  },
});
