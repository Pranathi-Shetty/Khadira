import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import net from 'node:net'

let activeBackendPort = 8000

function probePort(port) {
  return new Promise((resolve) => {
    const s = new net.Socket()
    s.setTimeout(150)
    s.on('connect', () => {
      s.destroy()
      resolve(true)
    })
    s.on('timeout', () => {
      s.destroy()
      resolve(false)
    })
    s.on('error', () => {
      s.destroy()
      resolve(false)
    })
    s.connect(port, '127.0.0.1')
  })
}

async function refreshActivePort() {
  if (await probePort(8000)) {
    activeBackendPort = 8000
    return 8000
  }
  if (await probePort(8011)) {
    activeBackendPort = 8011
    return 8011
  }
  activeBackendPort = 8000
  return 8000
}

export default defineConfig(({ command }) => {
  if (command === 'serve') {
    refreshActivePort()
    const timer = setInterval(refreshActivePort, 2000)
    if (timer && timer.unref) {
      timer.unref()
    }
  }

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          router: () => `http://127.0.0.1:${activeBackendPort}`,
        },
      },
    },
  }
})
