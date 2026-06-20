import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'J.A.R.V.I.S.',
  description: 'Just A Rather Very Intelligent System',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className="h-full">
      <body className="h-full">{children}</body>
    </html>
  )
}
