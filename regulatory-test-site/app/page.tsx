'use client'

import { useEffect, useState } from 'react'

interface Update {
  id: string
  title: string
  published_at: string
  body: string
}

// Prefilled demo content (from docs/demo/assets/regulatory-push_23EC21_TC.md),
// so the presenter can just click 发布 during the demo.
const DEFAULT_TITLE =
  '證監會修訂《打擊洗錢及反恐怖分子資金籌集指引》（適用於持牌法團及發牌虛擬資產服務提供者）'
const DEFAULT_DATE = '2023-05-24'
const DEFAULT_BODY = `證券及期貨事務監察委員會（證監會）已修訂《打擊洗錢及反恐怖分子資金籌集指引（適用於持牌法團及證監會發牌虛擬資產服務提供者）》，以配合《2022年打擊洗錢及恐怖分子資金籌集（修訂）條例》，並自2023年6月1日起生效。

主要修訂包括：
1. 更新政治人物（PEP）及信託客戶受益所有人的定義，使其與修訂條例一致。
2. 容許對不再構成高風險的「曾任非香港政治人物」，豁免適用原有的特別規定及額外盡職審查措施。
3. 新增專章，闡述與虛擬資產相關的洗錢及恐怖分子資金籌集風險，以及相應的監管要求與標準。
4. 有關就電子資金轉賬即時向受益機構提交所需匯款人及收款人信息的規定（指引第12.11.10及12.11.13段），將自2024年1月1日起生效。

持牌法團及有聯繫實體應檢視其內部打擊洗錢及反恐怖分子資金籌集政策及程序，並因應本次修訂採取所需行動。`

export default function Home() {
  const [title, setTitle] = useState(DEFAULT_TITLE)
  const [body, setBody] = useState(DEFAULT_BODY)
  const [publishedAt, setPublishedAt] = useState(DEFAULT_DATE)
  const [updates, setUpdates] = useState<Update[]>([])
  const [submitting, setSubmitting] = useState(false)

  async function load() {
    const res = await fetch('/api/updates', { cache: 'no-store' })
    const data = await res.json()
    setUpdates(data.updates ?? [])
  }

  useEffect(() => {
    load()
  }, [])

  async function publish(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim() && !body.trim()) return
    setSubmitting(true)
    try {
      await fetch('/api/updates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, body, published_at: publishedAt || undefined }),
      })
      setTitle(DEFAULT_TITLE)
      setBody(DEFAULT_BODY)
      setPublishedAt(DEFAULT_DATE)
      await load()
    } finally {
      setSubmitting(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '10px 12px',
    marginBottom: 12,
    border: '1px solid #d0d5dd',
    borderRadius: 8,
    fontSize: 15,
    boxSizing: 'border-box',
  }

  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: '32px 20px' }}>
      <h1 style={{ fontSize: 24 }}>监管测试发布站</h1>
      <p style={{ color: '#667085' }}>
        用于演示：在此发布一条监管更新，知识库演示端会自动读取并做 AI 摘要与文档联动。
      </p>

      <form
        onSubmit={publish}
        style={{
          background: '#fff',
          padding: 20,
          borderRadius: 12,
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          marginBottom: 28,
        }}
      >
        <label style={{ fontWeight: 600 }}>标题</label>
        <input
          style={inputStyle}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="例如：关于加强客户身份识别的通知"
        />
        <label style={{ fontWeight: 600 }}>日期（可选）</label>
        <input
          style={inputStyle}
          value={publishedAt}
          onChange={(e) => setPublishedAt(e.target.value)}
          placeholder="YYYY-MM-DD，留空则用今天"
        />
        <label style={{ fontWeight: 600 }}>正文</label>
        <textarea
          style={{ ...inputStyle, minHeight: 120, resize: 'vertical' }}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="监管推送正文…"
        />
        <button
          type="submit"
          disabled={submitting}
          style={{
            padding: '10px 20px',
            background: '#1976d2',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontSize: 15,
            cursor: 'pointer',
          }}
        >
          {submitting ? '发布中…' : '发布'}
        </button>
      </form>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <h2 style={{ fontSize: 18, flexGrow: 1 }}>已发布（{updates.length}）</h2>
        {updates.length > 0 && (
          <button
            onClick={async () => {
              if (!confirm('清空所有已发布的监管推送？（用于彩排重置）')) return
              await fetch('/api/updates', { method: 'DELETE' })
              await load()
            }}
            style={{
              padding: '6px 14px',
              background: '#fff',
              color: '#d92d20',
              border: '1px solid #f2b8b5',
              borderRadius: 8,
              fontSize: 13,
              cursor: 'pointer',
            }}
          >
            清空全部
          </button>
        )}
      </div>
      {updates.map((u) => (
        <div
          key={u.id}
          style={{
            background: '#fff',
            padding: 16,
            borderRadius: 12,
            marginBottom: 12,
            boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
          }}
        >
          <div style={{ fontWeight: 600 }}>{u.title || '(无标题)'}</div>
          <div style={{ color: '#98a2b3', fontSize: 13 }}>{u.published_at}</div>
          <div style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>{u.body}</div>
        </div>
      ))}
    </main>
  )
}
