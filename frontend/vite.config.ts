import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file from parent directory (project root)
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '');
  
  return {
    plugins: [react()],
    
    // Server configuration
    server: {
      port: parseInt(env.FRONTEND_PORT) || 3000,
      open: true,
      proxy: {
        // Proxy API requests to backend
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    
    // Build configuration
    build: {
      outDir: 'build',
      sourcemap: true,
    },
    
    // Resolve configuration
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    
    // Environment variables
    envDir: path.resolve(__dirname, '..'), // Load .env from project root
  };
});

