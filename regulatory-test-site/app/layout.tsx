import type { ReactNode } from 'react'

export const metadata = {
  title: '监管测试发布站',
  description: 'Demo regulatory publishing test site',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body
        style={{
          margin: 0,
          fontFamily:
            'system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif',
          background: '#f4f5f7',
          color: '#1a1a1a',
        }}
      >
        {children}
      </body>
    </html>
  )
}
