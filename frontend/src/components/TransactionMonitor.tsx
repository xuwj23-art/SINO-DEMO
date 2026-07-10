import { useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Snackbar,
  Stack,
  Typography,
} from '@mui/material'
import ShowChartIcon from '@mui/icons-material/ShowChart'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import RadioButtonCheckedIcon from '@mui/icons-material/RadioButtonChecked'
import MailIcon from '@mui/icons-material/Mail'
import {
  analyzeTransaction,
  generateEmail,
  type DemoTransaction,
  type EmailResponse,
  type TxnAnalyzeResponse,
} from '../api/demo'
import { getClientData } from '../data/demoClients'
import { SUSPECT_LABELS, startStream, type StreamEvent } from '../data/demoTransactions'

interface TransactionMonitorProps {
  docText: string
  onCite: (page: number, quote: string) => void
}

interface DisplayTxn {
  txn: DemoTransaction
  suspect: boolean
}

const TYPE_LABEL: Record<DemoTransaction['type'], string> = {
  buy: '买入',
  sell: '卖出',
  deposit: '入金',
  withdraw: '出金',
  transfer: '转账',
}

const RISK_META = {
  high: { label: '高风险', color: 'error' as const },
  medium: { label: '中风险', color: 'warning' as const },
  low: { label: '低风险', color: 'success' as const },
}

// Defensive scrub: even though the backend prompt forbids English flag names,
// strip any residual identifiers (large_frequency / third_party / ctrlLevel / STR
// etc.) from model text before showing it to a non-technical audience.
const EN_SCRUB: [RegExp, string][] = [
  [/large_frequency/gi, '短时间多笔大额'],
  [/third_party/gi, '第三方账户'],
  [/income_mismatch/gi, '金额与收入不符'],
  [/rapid_movement/gi, '快进快出'],
  [/ctrlLevel\s*=?\s*\d*/gi, '限制交易'],
]
function scrubEn(s: string): string {
  let out = s
  for (const [re, rep] of EN_SCRUB) out = out.replace(re, rep)
  return out
}

export default function TransactionMonitor({ docText, onCite }: TransactionMonitorProps) {
  const [txns, setTxns] = useState<DisplayTxn[]>([])
  const [alert, setAlert] = useState<string | null>(null)
  // which card view is shown: 'stream' = live flow, 'pending' = flagged only
  const [view, setView] = useState<'stream' | 'pending'>('stream')
  // analysis results keyed by txn id
  const [analysis, setAnalysis] = useState<Record<string, TxnAnalyzeResponse>>({})
  // txns marked as handled (restricted / STR filed)
  const [handled, setHandled] = useState<Set<string>>(new Set())
  const analyzedForRef = useRef<string | null>(null)

  const total = txns.length
  const suspectCount = txns.filter((t) => t.suspect).length
  const pendingCount = suspectCount - handled.size

  // Start the synthetic stream on mount; stop on unmount.
  useEffect(() => {
    const stop = startStream((e: StreamEvent) => {
      setTxns((prev) => {
        const next = [{ txn: e.txn, suspect: e.suspect }, ...prev]
        if (next.length <= 60) return next
        // Keep EVERY suspect txn; only trim normal ones to stay within 60.
        const suspects = next.filter((t) => t.suspect)
        const normals = next.filter((t) => !t.suspect).slice(0, 60 - suspects.length)
        // Re-merge in newest-first order (a txn is suspect OR normal).
        const rank = new Map(next.map((t, i) => [t, i]))
        return [...suspects, ...normals]
          .sort((a, b) => (rank.get(a) ?? 0) - (rank.get(b) ?? 0))
      })
      if (e.suspect) {
        // Surface a top-of-page alert for the first flagged txn of a burst.
        setAlert(`可疑信号：${e.txn.client_name} ${TYPE_LABEL[e.txn.type]} ${e.txn.amount.toLocaleString()} 元（来自 ${e.txn.counterparty || '未知'}）`)
        // Auto-switch to the pending view so the audience focuses on the alert.
        setView('pending')
      }
    })
    return stop
  }, [])

  const analyzeMutation = useMutation({
    mutationFn: (txnId: string) => {
      const target = txns.find((t) => t.txn.id === txnId)?.txn
      const client = target ? getClientData(target.client_id) : null
      if (!target || !client) return Promise.reject(new Error('missing'))
      return analyzeTransaction(docText, client, target)
    },
    onSuccess: (data, txnId) => {
      setAnalysis((prev) => ({ ...prev, [txnId]: data }))
    },
  })

  function runAnalysis(txnId: string) {
    analyzedForRef.current = txnId
    analyzeMutation.mutate(txnId)
  }

  function markHandled(txnId: string) {
    setHandled((prev) => new Set(prev).add(txnId))
  }

  return (
    <Box>
      {/* Status bar — the two chips are clickable view switchers. */}
      <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1.5, flexWrap: 'wrap', gap: 1 }}>
        <Stack direction="row" spacing={0.75} alignItems="center">
          <RadioButtonCheckedIcon color="success" fontSize="small" sx={{ animation: 'pulse 2s infinite' }} />
          <Typography variant="body2" sx={{ fontWeight: 600 }}>监控中</Typography>
        </Stack>
        <Chip
          size="small"
          variant={view === 'stream' ? 'filled' : 'outlined'}
          color={view === 'stream' ? 'primary' : 'default'}
          label={`实时流水 · ${total} 笔`}
          onClick={() => setView('stream')}
          sx={{ cursor: 'pointer' }}
        />
        <Chip
          size="small"
          variant={view === 'pending' ? 'filled' : 'outlined'}
          color={pendingCount > 0 ? 'error' : view === 'pending' ? 'primary' : 'default'}
          icon={<WarningAmberIcon />}
          label={pendingCount > 0 ? `${pendingCount} 笔待研判` : '无待研判'}
          onClick={() => setView('pending')}
          sx={{ cursor: 'pointer' }}
        />
      </Stack>

      {!docText && (
        <Alert severity="warning" sx={{ mb: 1.5 }}>
          未上传政策文件，AI 风险研判将无法引用政策依据。请先在上方上传政策 PDF。
        </Alert>
      )}

      {/* Transaction stream / pending view. */}
      <Box
        sx={{
          maxHeight: 420,
          overflowY: 'auto',
          border: '1px solid',
          borderColor: view === 'pending' ? 'error.main' : 'divider',
          borderRadius: 2,
          bgcolor: view === 'pending' ? '#fffafb' : '#fbfcfd',
          p: 1,
        }}
      >
        {view === 'stream' && txns.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
            <CircularProgress size={16} sx={{ mr: 1, verticalAlign: 'middle' }} />
            正在接入交易流水…
          </Typography>
        )}
        {view === 'pending' && (
          <Typography variant="caption" color="error.main" sx={{ fontWeight: 600, display: 'block', px: 0.5, py: 0.5 }}>
            ⚠ 以下交易触发可疑信号，请逐一研判
          </Typography>
        )}
        <Stack spacing={0.5}>
          {(view === 'stream' ? txns : txns.filter((d) => d.suspect)).map((d) => (
            <TxnRow
              key={d.txn.id}
              txn={d.txn}
              suspect={d.suspect}
              handled={handled.has(d.txn.id)}
              result={analysis[d.txn.id]}
              loading={analyzeMutation.isPending && analyzedForRef.current === d.txn.id}
              onAnalyze={() => runAnalysis(d.txn.id)}
              onHandled={() => markHandled(d.txn.id)}
              onCite={onCite}
            />
          ))}
          {view === 'pending' && txns.filter((d) => d.suspect).length === 0 && (
            <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
              暂无可疑交易。系统持续监控中，出现异常将自动提醒。
            </Typography>
          )}
        </Stack>
      </Box>

      <Snackbar
        open={!!alert}
        autoHideDuration={6000}
        onClose={() => setAlert(null)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          severity="warning"
          icon={<WarningAmberIcon />}
          onClose={() => setAlert(null)}
          sx={{ boxShadow: 3, alignItems: 'center' }}
        >
          <Typography variant="body2" sx={{ fontWeight: 600 }}>{alert}</Typography>
        </Alert>
      </Snackbar>

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, textAlign: 'center' }}>
        <ShowChartIcon sx={{ fontSize: 12, verticalAlign: 'middle', mr: 0.5 }} />
        合成交易流（虚构数据）· 正常交易为主，AI 实时捕捉可疑信号
      </Typography>
    </Box>
  )
}

function TxnRow({
  txn,
  suspect,
  handled,
  result,
  loading,
  onAnalyze,
  onHandled,
  onCite,
}: {
  txn: DemoTransaction
  suspect: boolean
  handled: boolean
  result?: TxnAnalyzeResponse
  loading: boolean
  onAnalyze: () => void
  onHandled: () => void
  onCite: (page: number, quote: string) => void
}) {
  const [email, setEmail] = useState<EmailResponse | null>(null)
  const emailMutation = useMutation({
    mutationFn: () =>
      generateEmail('transaction', txn.client_name, txn.client_id, {
        risk_level: result?.risk_level,
        signals: result?.signals,
        actions: result?.actions,
        summary: result?.summary,
        amount: txn.amount,
        counterparty: txn.counterparty,
      }),
    onSuccess: (data) => setEmail(data),
  })

  if (suspect) {
    return (
      <Box>
        <Box
          sx={{
            p: 1,
            borderRadius: 1,
            border: '1px solid',
            borderColor: 'error.main',
            borderLeft: '3px solid',
            borderLeftColor: 'error.main',
            bgcolor: '#fdf2f2',
            animation: 'flash 1.2s ease-out',
            '@keyframes flash': {
              '0%': { bgcolor: '#ffcccc' },
              '100%': { bgcolor: '#fdf2f2' },
            },
          }}
        >
          <Stack direction="row" spacing={1} alignItems="center" sx={{ flexWrap: 'wrap', gap: 0.5 }}>
            <WarningAmberIcon color="error" fontSize="small" />
            <Typography variant="caption" sx={{ color: 'text.secondary', fontFamily: 'monospace' }}>{txn.time}</Typography>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>{txn.client_name}</Typography>
            <Chip label={TYPE_LABEL[txn.type]} size="small" color="error" sx={{ height: 18, fontSize: 11 }} />
            <Typography variant="body2" sx={{ fontWeight: 700, color: 'error.main' }}>
              {txn.currency} {txn.amount.toLocaleString()}
            </Typography>
            {txn.counterparty && (
              <Chip label={txn.counterparty} size="small" variant="outlined" sx={{ height: 18, fontSize: 11 }} />
            )}
            <Box sx={{ flex: 1 }} />
            {handled ? (
              <Chip label="已处置" size="small" color="success" sx={{ height: 20, fontSize: 11 }} />
            ) : (
              <Button size="small" variant="contained" color="error" disabled={loading} onClick={onAnalyze} sx={{ py: 0.2, fontSize: 12 }}>
                {loading ? '研判中…' : result ? '查看研判' : 'AI 风险研判'}
              </Button>
            )}
          </Stack>
          <Stack direction="row" spacing={0.5} sx={{ mt: 0.5, flexWrap: 'wrap', gap: 0.5 }}>
            {(txn.suspect_flags || []).map((f) => (
              <Chip key={f} label={SUSPECT_LABELS[f] || f} size="small" color="error" variant="outlined" sx={{ height: 16, fontSize: 10 }} />
            ))}
          </Stack>
        </Box>

        {result && (
          <Card variant="outlined" sx={{ mt: 0.5, bgcolor: '#fffafb' }}>
            <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                <Chip label={RISK_META[result.risk_level].label} color={RISK_META[result.risk_level].color} size="small" />
                <Typography variant="body2" sx={{ fontWeight: 600 }}>{scrubEn(result.summary)}</Typography>
              </Stack>
              {result.signals.length > 0 && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>风险信号：</Typography>
                  {result.signals.map((s, i) => (
                    <Typography key={i} variant="caption" sx={{ display: 'block', pl: 1.5, lineHeight: 1.5 }}>• {scrubEn(s)}</Typography>
                  ))}
                </Box>
              )}
              {result.client_context && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>客户背景关联：</Typography>
                  <Typography variant="caption" sx={{ display: 'block', pl: 1.5, lineHeight: 1.5 }}>{scrubEn(result.client_context)}</Typography>
                </Box>
              )}
              {result.actions.length > 0 && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>处置建议：</Typography>
                  {result.actions.map((a, i) => (
                    <Typography key={i} variant="caption" sx={{ display: 'block', pl: 1.5, lineHeight: 1.5 }}>• {scrubEn(a)}</Typography>
                  ))}
                </Box>
              )}
              {result.cited_page != null && (
                <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
                  <Chip
                    size="small"
                    color="primary"
                    variant="outlined"
                    label={result.quote ? `溯源 第 ${result.cited_page} 页原文` : `跳转 第 ${result.cited_page} 页`}
                    onClick={() => onCite(result.cited_page!, result.quote)}
                    sx={{ height: 22 }}
                  />
                </Stack>
              )}
              {!handled && (
                <Stack direction="row" spacing={1} sx={{ mt: 1.5, flexWrap: 'wrap', gap: 1 }}>
                  <Button size="small" variant="outlined" color="error" onClick={onHandled}>限制账户</Button>
                  <Button size="small" variant="outlined" onClick={onHandled}>提交可疑交易报告</Button>
                  <Button
                    size="small"
                    variant="contained"
                    color="primary"
                    startIcon={emailMutation.isPending ? undefined : <MailIcon />}
                    disabled={emailMutation.isPending}
                    onClick={() => emailMutation.mutate()}
                  >
                    {emailMutation.isPending ? '通知生成中…' : '生成通知'}
                  </Button>
                  <Button size="small" variant="text" onClick={onHandled}>标记已处理</Button>
                </Stack>
              )}
              {email && (
                <Box sx={{ mt: 1.5, p: 1.5, borderRadius: 1.5, border: '1px solid', borderColor: 'divider', bgcolor: '#fafbfe' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>郵件主旨：</Typography>
                  <Typography variant="body2" sx={{ mb: 1 }}>{email.subject}</Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>郵件正文：</Typography>
                  <Box component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 13, lineHeight: 1.7, m: 0, color: 'text.primary' }}>
                    {email.body}
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        )}
      </Box>
    )
  }

  // Normal transaction: compact, low-saturation — visual "background noise".
  return (
    <Stack direction="row" spacing={1} alignItems="center" sx={{ py: 0.3, px: 0.5, opacity: 0.75 }}>
      <Typography variant="caption" sx={{ color: 'text.disabled', fontFamily: 'monospace', minWidth: 64 }}>{txn.time}</Typography>
      <Typography variant="caption" sx={{ minWidth: 56, color: 'text.secondary' }}>{txn.client_name}</Typography>
      <Typography variant="caption" sx={{ color: 'text.disabled', minWidth: 32 }}>{TYPE_LABEL[txn.type]}</Typography>
      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
        {txn.currency} {txn.amount.toLocaleString()}
      </Typography>
    </Stack>
  )
}
