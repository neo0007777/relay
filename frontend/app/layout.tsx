import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Relay — AI Agent Context Handoff Infrastructure & Benchmark',
  description: 'Structured Knowledge Checkpointing, Hybrid Retrieval, and RelayBench Evaluation.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
      </head>
      <body className="bg-brand-dark text-gray-100 antialiased min-h-screen">
        {children}
      </body>
    </html>
  )
}
