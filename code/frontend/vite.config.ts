import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// `127.0.0.1`, nunca `localhost`.
//
// O uvicorn escuta em 127.0.0.1 (IPv4). O Node 17+ mudou a ordem de resolução
// de DNS e passou a preferir IPv6, então `localhost` resolve para `::1` e o
// proxy morre com `connect ECONNREFUSED ::1:8000` — sem nenhuma pista de que o
// problema é a pilha de rede e não o servidor.
const BACKEND = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Todo tráfego da API passa por aqui. Isso mantém o frontend usando caminho
    // relativo (ver src/api/client.ts), o que elimina o CORS em dev e evita o
    // mesmo problema de IPv6 no browser.
    proxy: {
      '/runs': {
        target: BACKEND,
        changeOrigin: true,
        // O SSE precisa de stream, não de resposta bufferizada: sem isto a
        // timeline do Console só apareceria quando o run terminasse.
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
              proxyRes.headers['x-accel-buffering'] = 'no'
            }
          })
        },
      },
      '/health': { target: BACKEND, changeOrigin: true },
    },
  },
})
