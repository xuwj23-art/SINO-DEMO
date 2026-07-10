import { useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  IconButton,
  LinearProgress,
  Stack,
  Typography,
} from '@mui/material'
import FactCheckIcon from '@mui/icons-material/FactCheck'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import CancelIcon from '@mui/icons-material/Cancel'
import PendingIcon from '@mui/icons-material/Pending'
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty'
import GavelIcon from '@mui/icons-material/Gavel'
import PersonIcon from '@mui/icons-material/Person'
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft'
import ChevronRightIcon from '@mui/icons-material/ChevronRight'
import MyLocationIcon from '@mui/icons-material/MyLocation'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import MailIcon from '@mui/icons-material/Mail'
import {
  generateEmail,
  intake,
  type ChecklistItem,
  type EmailResponse,
  type IntakeOutcome,
  type IntakeResponse,
  type IntakeStatus,
} from '../api/demo'
import {
  DEMO_CLIENT_METAS,
  getClientData,
  getClientMeta,
} from '../data/demoClients'

interface IntakePanelProps {
  /** uploaded policy PDF text (page-marked); empty if not uploaded */
  docText: string
  /** jump to a policy page + highlight a quote (shared with Q&A tab) */
  onCite: (page: number, quote: string) => void
}

// A checklist row is either still pending (waiting to be judged) or has a
// resolved status from the model.
type RevealedItem =
  | { kind: 'pending'; item: ChecklistItem }
  | { kind: 'resolved'; item: ChecklistItem }

// Flow:
//   idle        — pick a client
//   analyzing   — model call in progress (phase animation 1)
//   extracting  — model call in progress (phase animation 2)
//   reviewing   — model returned; checklist shown STATIC for staff to confirm
//                 (each row shows title + 溯源 button; verdicts hidden). A
//                 「开始」button starts the per-row audit animation.
//   checking    — per-row verdicts being revealed one by one
//   done        — outcome banner shown, full checklist visible
type Phase = 'idle' | 'analyzing' | 'extracting' | 'reviewing' | 'checking' | 'done'

type CardPage = 'profile' | 'checklist'

// Jittered durations so the phases feel like real work, not a fixed timer.
const ANALYZE_MS = () => 1100 + Math.random() * 800 // 1.1-1.9s
const ITEM_REVEAL_MS = () => 520 + Math.random() * 560 // 0.52-1.08s per item

const STATUS_META: Record<
  IntakeStatus,
  { label: string; color: 'success' | 'error' | 'warning'; Icon: typeof CheckCircleIcon }
> = {
  pass: { label: '通过', color: 'success', Icon: CheckCircleIcon },
  fail: { label: '不通过', color: 'error', Icon: CancelIcon },
  review: { label: '待复核', color: 'warning', Icon: PendingIcon },
}

const OUTCOME_META: Record<
  IntakeOutcome,
  { severity: 'success' | 'error' | 'warning'; title: string }
> = {
  passed: { severity: 'success', title: '开户审核无误，请人工复核' },
  failed: { severity: 'error', title: '开户审核未通过，请人工复核' },
  needs_review: { severity: 'warning', title: '存在待复核项，请人工介入' },
}

const PHASE_LABEL: Record<'analyzing' | 'extracting' | 'checking', string> = {
  analyzing: '正在分析政策文件…',
  extracting: '正在生成开户审核清单…',
  checking: '正在逐项核对客户资料…',
}

export default function IntakePanel({ docText, onCite }: IntakePanelProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [phase, setPhase] = useState<Phase>('idle')
  const [result, setResult] = useState<IntakeResponse | null>(null)
  // checklist frame: built once the model returns; rows flip pending→resolved
  // during the 'checking' phase.
  const [frame, setFrame] = useState<RevealedItem[] | null>(null)
  const [cardPage, setCardPage] = useState<CardPage>('profile')
  const [email, setEmail] = useState<EmailResponse | null>(null)
  const revealStartedRef = useRef(false)
  const timersRef = useRef<number[]>([])

  const meta = selectedId ? getClientMeta(selectedId) : null
  const clientData = selectedId ? getClientData(selectedId) : null

  function clearTimers() {
    timersRef.current.forEach((t) => window.clearTimeout(t))
    timersRef.current = []
  }
  useEffect(() => () => clearTimers(), [])

  function reset() {
    clearTimers()
    setPhase('idle')
    setResult(null)
    setFrame(null)
    setCardPage('profile')
    setEmail(null)
    revealStartedRef.current = false
  }

  function selectClient(id: string) {
    if (phase !== 'idle') return
    setSelectedId(id)
    setResult(null)
    setFrame(null)
    setCardPage('profile')
    revealStartedRef.current = false
  }

  const intakeMutation = useMutation({
    mutationFn: () => intake(docText, clientData as Record<string, unknown>),
    onSuccess: (data) => setResult(data),
  })

  const emailMutation = useMutation({
    mutationFn: () => {
      if (!result || !meta) return Promise.reject(new Error('missing'))
      return generateEmail('intake', meta.nameZh, meta.id, {
        outcome: result.outcome,
        summary: result.summary,
        issues: result.issues,
      })
    },
    onSuccess: (data) => setEmail(data),
  })

  function startIntake() {
    if (!clientData) return
    clearTimers()
    setResult(null)
    setFrame(null)
    revealStartedRef.current = false

    // Kick off the single model call; it runs in parallel with the analyze +
    // extract phase animations (model takes ~20-60s).
    intakeMutation.mutate()

    // Switch to the checklist card immediately so the audience sees the audit
    // stage, not the profile, while the model thinks.
    setCardPage('checklist')
    setPhase('analyzing')
    // Advance to 'extracting' after the analyze beat — but ONLY if we're still
    // analyzing. The model can return faster than ANALYZE_MS (e.g. a warm
    // request), in which case the effect below has already moved us to
    // 'reviewing'; an unguarded setPhase('extracting') here would clobber that
    // and strand the UI on a spinner with the checklist hidden.
    const t1 = window.setTimeout(() => {
      setPhase((p) => (p === 'analyzing' ? 'extracting' : p))
    }, ANALYZE_MS())
    timersRef.current.push(t1)
  }

  // When the model returns, build the static frame (all rows pending) and move
  // to 'reviewing' so staff can confirm the checklist before the audit runs.
  // Depends only on `result`: the frame is built exactly once per model
  // response (the `frame` guard short-circuits StrictMode's dev double-invoke
  // of this effect on mount, when result is still null anyway).
  useEffect(() => {
    if (!result || frame || phase === 'idle') return
    setFrame(result.checklist.map((item) => ({ kind: 'pending', item })))
    setPhase('reviewing')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result])

  // Staff confirmed the checklist → start the per-row reveal animation.
  function beginAudit() {
    if (!frame || !result) return
    revealStartedRef.current = true
    setPhase('checking')
    flipNext(0)
  }

  function flipNext(index: number) {
    if (!result) return
    const items = result.checklist
    if (index >= items.length) {
      setPhase('done')
      return
    }
    const t = window.setTimeout(() => {
      setFrame((prev) => {
        if (!prev) return prev
        const next = [...prev]
        next[index] = { kind: 'resolved', item: items[index] }
        return next
      })
      flipNext(index + 1)
    }, ITEM_REVEAL_MS())
    timersRef.current.push(t)
  }

  const error = intakeMutation.isError && phase !== 'idle' && !result
  const outcomeMeta = result ? OUTCOME_META[result.outcome] : null
  const waitingForModel = phase === 'extracting' && !frame
  const auditRunning = phase === 'checking'

  return (
    <Box>
      {/* Picker (only before a client is chosen) */}
      {!selectedId && (
        <>
          <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
            选择一份合成客户申请（全部为虚构数据）
          </Typography>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
              gap: 1.5,
            }}
          >
            {DEMO_CLIENT_METAS.map((c) => {
              const selected = c.id === selectedId
              return (
                <Card
                  key={c.id}
                  variant="outlined"
                  onClick={() => selectClient(c.id)}
                  sx={{
                    cursor: 'pointer',
                    borderColor: selected ? 'primary.main' : 'divider',
                    borderWidth: selected ? 2 : 1,
                    bgcolor: selected ? '#eef4ff' : '#fff',
                    '&:hover': { borderColor: 'primary.light' },
                  }}
                >
                  <CardContent sx={{ display: 'flex', gap: 1.5, py: 1.5, '&:last-child': { pb: 1.5 } }}>
                    <Avatar variant="rounded" sx={{ bgcolor: '#eef2ff', color: 'primary.main', width: 38, height: 38 }}>
                      <PersonIcon fontSize="small" />
                    </Avatar>
                    <Box sx={{ minWidth: 0 }}>
                      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.3 }}>
                        <Typography variant="subtitle2" sx={{ lineHeight: 1.2 }}>{c.nameZh}</Typography>
                        <Chip label={c.tag} size="small" variant="outlined" sx={{ height: 18, fontSize: 11 }} />
                      </Stack>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.3 }}>
                        {c.hint}
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              )
            })}
          </Box>
        </>
      )}

      {/* After a client is selected: paginated cards (profile / checklist) */}
      {selectedId && meta && clientData && (
        <Box>
          {/* Card switcher header */}
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
            <IconButton
              size="small"
              disabled={cardPage === 'profile'}
              onClick={() => setCardPage('profile')}
              title="客户档案"
            >
              <ChevronLeftIcon fontSize="small" />
            </IconButton>
            <Stack direction="row" spacing={0.5} sx={{ flex: 1, justifyContent: 'center' }}>
              <PageDot active={cardPage === 'profile'} label="客户档案" onClick={() => setCardPage('profile')} />
              <PageDot active={cardPage === 'checklist'} label="审核清单" onClick={() => setCardPage('checklist')} />
            </Stack>
            <IconButton
              size="small"
              disabled={cardPage === 'checklist'}
              onClick={() => setCardPage('checklist')}
              title="审核清单"
            >
              <ChevronRightIcon fontSize="small" />
            </IconButton>
          </Stack>

          {/* Profile card */}
          {cardPage === 'profile' && (
            <Card variant="outlined" sx={{ bgcolor: '#fafbfe' }}>
              <CardContent>
                <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1.5 }}>
                  <GavelIcon fontSize="small" color="action" />
                  <Typography variant="subtitle2">客户档案 · {meta.nameZh} ({meta.nameEn})</Typography>
                  <Chip label={meta.businessType} size="small" variant="outlined" />
                </Stack>
                <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
                  <FieldGroup title="交易系统账户（AccMast）" fields={clientData.account} />
                  <FieldGroup title="KYC 合规信息" fields={clientData.kyc} />
                </Box>
                {phase === 'idle' && (
                  <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mt: 2.5 }}>
                    <Button
                      variant="contained"
                      size="large"
                      startIcon={<FactCheckIcon />}
                      disabled={!docText || intakeMutation.isPending}
                      onClick={startIntake}
                    >
                      AI 开户审核
                    </Button>
                    {!docText && (
                      <Typography variant="caption" color="text.secondary">
                        请先在上方上传政策 PDF
                      </Typography>
                    )}
                  </Stack>
                )}
              </CardContent>
            </Card>
          )}

          {/* Checklist card */}
          {cardPage === 'checklist' && (
            <Box>
              {/* Running phases (model thinking) */}
              {(phase === 'analyzing' || phase === 'extracting' || waitingForModel) && (
                <Card variant="outlined">
                  <CardContent>
                    <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1 }}>
                      <CircularProgress size={18} />
                      <Typography variant="body2" sx={{ fontWeight: 600, flex: 1 }}>
                        {phase === 'analyzing' ? PHASE_LABEL.analyzing : PHASE_LABEL.extracting}
                      </Typography>
                      {waitingForModel && (
                        <Typography variant="caption" color="text.secondary">
                          AI 正在阅读政策与客户资料，约需 1 分钟…
                        </Typography>
                      )}
                    </Stack>
                    <LinearProgress />
                  </CardContent>
                </Card>
              )}

              {/* Static review: checklist shown for staff confirmation */}
              {phase === 'reviewing' && frame && (
                <Card variant="outlined">
                  <CardContent>
                    <Alert severity="info" icon={<FactCheckIcon />} sx={{ mb: 2 }}>
                      <Typography variant="subtitle2">AI 已生成开户审核清单，请确认无误后点击「开始」</Typography>
                      每项可点「溯源」查看政策依据原文。确认后开始逐项审核。
                    </Alert>
                    <Stack spacing={1} sx={{ mb: 2 }}>
                      {frame.map((row, i) => (
                        <StaticRow key={i} item={row.item} onCite={onCite} />
                      ))}
                    </Stack>
                    <Stack direction="row" spacing={1.5}>
                      <Button
                        variant="contained"
                        size="large"
                        startIcon={<PlayArrowIcon />}
                        onClick={beginAudit}
                      >
                        开始审核
                      </Button>
                      <Button variant="outlined" onClick={() => setCardPage('profile')}>
                        返回修改
                      </Button>
                    </Stack>
                  </CardContent>
                </Card>
              )}

              {/* Audit running: per-row reveal animation */}
              {auditRunning && frame && (
                <Card variant="outlined">
                  <CardContent>
                    <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1 }}>
                      <CircularProgress size={18} />
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {PHASE_LABEL.checking}
                      </Typography>
                    </Stack>
                    <LinearProgress sx={{ mb: 2 }} />
                    <Stack spacing={1}>
                      {frame.map((row, i) => (
                        <AuditRow key={i} row={row} onCite={onCite} />
                      ))}
                    </Stack>
                  </CardContent>
                </Card>
              )}

              {/* Done: outcome + full checklist */}
              {phase === 'done' && result && outcomeMeta && frame && (
                <Card variant="outlined">
                  <CardContent>
                    <Alert severity={outcomeMeta.severity} icon={<GavelIcon />} sx={{ mb: 2 }}>
                      <Typography variant="subtitle2">{outcomeMeta.title}</Typography>
                      {result.summary}
                    </Alert>
                    <Stack spacing={1} sx={{ mb: 2 }}>
                      {frame.map((row, i) => (
                        <AuditRow key={i} row={row} onCite={onCite} />
                      ))}
                    </Stack>
                    {(result.outcome === 'failed' || result.outcome === 'needs_review') && (
                      <Box sx={{ mb: 2 }}>
                        <Button
                          variant="contained"
                          color="primary"
                          startIcon={emailMutation.isPending ? undefined : <MailIcon />}
                          disabled={emailMutation.isPending}
                          onClick={() => emailMutation.mutate()}
                          sx={{ mb: email ? 1.5 : 0 }}
                        >
                          {emailMutation.isPending ? '郵件生成中…' : '一鍵生成郵件'}
                        </Button>
                        {email && (
                          <Box sx={{ p: 1.5, borderRadius: 1.5, border: '1px solid', borderColor: 'divider', bgcolor: '#fafbfe' }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>郵件主旨：</Typography>
                            <Typography variant="body2" sx={{ mb: 1 }}>{email.subject}</Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>郵件正文：</Typography>
                            <Box component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 13, lineHeight: 1.7, m: 0, color: 'text.primary' }}>
                              {email.body}
                            </Box>
                          </Box>
                        )}
                      </Box>
                    )}
                    <Button variant="outlined" onClick={reset} startIcon={<FactCheckIcon />}>
                      重新审核
                    </Button>
                  </CardContent>
                </Card>
              )}
            </Box>
          )}

          {/* Error fallback */}
          {error && (
            <Alert severity="error" sx={{ mt: 2 }} action={
              <Button color="inherit" size="small" onClick={reset}>重试</Button>
            }>
              开户审核调用失败，请检查后端服务与 API Key。
            </Alert>
          )}
        </Box>
      )}
    </Box>
  )
}

function PageDot({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <Chip
      label={label}
      size="small"
      color={active ? 'primary' : 'default'}
      variant={active ? 'filled' : 'outlined'}
      onClick={onClick}
      sx={{ cursor: 'pointer' }}
    />
  )
}

function FieldGroup({ title, fields }: { title: string; fields: Record<string, unknown> }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
        {title}
      </Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: 'auto 1fr', columnGap: 1.5, rowGap: 0.3 }}>
        {Object.entries(fields).map(([k, v]) => (
          <FieldRow key={k} k={k} v={v} />
        ))}
      </Box>
    </Box>
  )
}

function FieldRow({ k, v }: { k: string; v: unknown }) {
  const display = Array.isArray(v) ? v.join('、') : String(v)
  return (
    <>
      <Typography variant="caption" sx={{ color: 'text.secondary', fontFamily: 'monospace' }}>{k}</Typography>
      <Typography variant="caption" sx={{ wordBreak: 'break-all' }}>{display}</Typography>
    </>
  )
}

// Static review row: shows the check title + a 溯源 (trace-to-policy) button so
// staff can jump to the policy source and confirm the checklist is sound. The
// verdict is intentionally NOT shown yet — it's revealed after 「开始」.
function StaticRow({
  item,
  onCite,
}: {
  item: ChecklistItem
  onCite: (page: number, quote: string) => void
}) {
  const canTrace = item.cited_page != null
  return (
    <Box
      sx={{
        p: 1.25,
        borderRadius: 1.5,
        border: '1px solid',
        borderColor: 'divider',
        borderLeft: '3px solid',
        borderLeftColor: 'divider',
        bgcolor: '#fafbfc',
      }}
    >
      <Stack direction="row" spacing={1} alignItems="center">
        <FactCheckIcon fontSize="small" sx={{ color: 'text.disabled' }} />
        <Typography variant="body2" sx={{ fontWeight: 600, flex: 1 }}>
          {item.title}
        </Typography>
        {canTrace ? (
          <Button
            size="small"
            variant="text"
            color="primary"
            startIcon={<MyLocationIcon />}
            onClick={() => onCite(item.cited_page!, item.quote)}
            sx={{ textTransform: 'none' }}
          >
            溯源 第 {item.cited_page} 页
          </Button>
        ) : (
          <Chip label="无对应条款" size="small" variant="outlined" sx={{ height: 20, fontSize: 11, color: 'text.disabled' }} />
        )}
      </Stack>
    </Box>
  )
}

// Audit row: pending rows show a neutral "核对中" placeholder; resolved rows
// show the verdict icon + detail + policy citation chip.
function AuditRow({
  row,
  onCite,
}: {
  row: RevealedItem
  onCite: (page: number, quote: string) => void
}) {
  if (row.kind === 'pending') {
    return (
      <Box
        sx={{
          p: 1.25,
          borderRadius: 1.5,
          border: '1px solid',
          borderColor: 'divider',
          borderLeft: '3px solid',
          borderLeftColor: 'divider',
          bgcolor: '#fafbfc',
          opacity: 0.85,
        }}
      >
        <Stack direction="row" spacing={1} alignItems="center">
          <HourglassEmptyIcon fontSize="small" sx={{ color: 'text.disabled' }} />
          <Typography variant="body2" sx={{ fontWeight: 600, flex: 1, color: 'text.secondary' }}>
            {row.item.title}
          </Typography>
          <Chip label="核对中" size="small" variant="outlined" sx={{ height: 20, fontSize: 11, color: 'text.disabled' }} />
        </Stack>
      </Box>
    )
  }
  const item = row.item
  const sm = STATUS_META[item.status]
  const { Icon } = sm
  return (
    <Box
      sx={{
        p: 1.25,
        borderRadius: 1.5,
        border: '1px solid',
        borderColor: 'divider',
        borderLeft: '3px solid',
        borderLeftColor: `${sm.color}.main`,
        bgcolor: item.status === 'pass' ? '#f6fbf8' : item.status === 'fail' ? '#fdf5f5' : '#fffbf0',
      }}
    >
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.3 }}>
        <Icon color={sm.color} fontSize="small" />
        <Typography variant="body2" sx={{ fontWeight: 600, flex: 1 }}>{item.title}</Typography>
        <Chip label={sm.label} size="small" color={sm.color} variant="outlined" sx={{ height: 20, fontSize: 11 }} />
      </Stack>
      {item.detail && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.5, pl: 3 }}>
          {item.detail}
        </Typography>
      )}
      {item.cited_page != null && (
        <Stack direction="row" spacing={1} sx={{ mt: 0.75, pl: 3 }}>
          <Chip
            size="small"
            color="primary"
            variant="outlined"
            label={item.quote ? `溯源 第 ${item.cited_page} 页原文` : `跳转 第 ${item.cited_page} 页`}
            onClick={() => onCite(item.cited_page!, item.quote)}
            sx={{ height: 22 }}
          />
        </Stack>
      )}
    </Box>
  )
}
