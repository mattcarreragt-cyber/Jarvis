import type { Metadata, Viewport } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'J.A.R.V.I.S.',
  description: 'Just A Rather Very Intelligent System',
  manifest: '/manifest.webmanifest',
  appleWebApp: { capable: true, statusBarStyle: 'black-translucent', title: 'JARVIS' },
}

export const viewport: Viewport = {
  themeColor: '#00d4ff',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className="h-full">
      <body className="h-full">{children}</body>
    </html>
  )
}
