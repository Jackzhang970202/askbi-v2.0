import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const proxyTarget = 'http://localhost:8002'
const withRewrite = () => ({
  target: proxyTarget,
  rewrite: (path) => path.replace(/^\/askbi/, ''),
})

// https://vitejs.dev/config/
export default defineConfig({
  base: '/askbi/',
  plugins: [react()],
  server: {
    origin: 'http://localhost:5173',
    proxy: {
      '/askbi/ask': withRewrite(),
      '/askbi/create_chat': withRewrite(),
      '/askbi/progress': withRewrite(),
      '/askbi/stream': withRewrite(),
      '/askbi/upload_file': withRewrite(),
      '/askbi/excel': withRewrite(),
      '/askbi/bi': withRewrite(),
      '/askbi/skills': withRewrite(),
      '/askbi/agents': withRewrite(),
      '/askbi/datasources': withRewrite(),
      '/askbi/refer': withRewrite(),
      '/askbi/knowledge': withRewrite(),
      '/askbi/knowledge_bases': withRewrite(),
      '/askbi/global_configs': withRewrite(),
      '/askbi/auth': withRewrite(),
      '/askbi/suggestions': withRewrite(),
      '/askbi/reports': withRewrite(),
      '/askbi/report': withRewrite(),
      '/askbi/dashboard': withRewrite(),
      '/askbi/teams': withRewrite(),
      '/askbi/memory/': withRewrite(),
      '/askbi/chat': withRewrite(),
    }
  }
})
