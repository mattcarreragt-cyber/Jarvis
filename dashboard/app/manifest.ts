import type { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'JARVIS OS',
    short_name: 'JARVIS',
    description: 'Assistant IA local-first — Just A Rather Very Intelligent System',
    start_url: '/',
    display: 'standalone',
    orientation: 'portrait',
    background_color: '#020d14',
    theme_color: '#00d4ff',
    icons: [
      { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
      { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  }
}
