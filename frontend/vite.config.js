import fs from 'node:fs';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
var httpsKeyPath = process.env.VITE_HTTPS_KEY_PATH;
var httpsCertPath = process.env.VITE_HTTPS_CERT_PATH;
var useHttps = Boolean(httpsKeyPath && httpsCertPath);
export default defineConfig({
    plugins: [react()],
    server: {
        host: '0.0.0.0',
        port: 3000,
        https: useHttps
            ? {
                key: fs.readFileSync(httpsKeyPath),
                cert: fs.readFileSync(httpsCertPath),
            }
            : undefined,
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            '/photos': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            }
        }
    },
    build: {
        outDir: 'dist',
        sourcemap: true,
    }
});
