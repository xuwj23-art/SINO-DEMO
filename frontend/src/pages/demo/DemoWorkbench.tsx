import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Alert,
  AppBar,
  Avatar,
  Badge,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  LinearProgress,
  Paper,
  Snackbar,
  Stack,
  Tab,
  Tabs,
  TextField,
  Toolbar,
  Typography,
} from '@mui/material'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import DescriptionIcon from '@mui/icons-material/Description'
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'
import SendIcon from '@mui/icons-material/Send'
import RadarIcon from '@mui/icons-material/Radar'
import ShieldMoonIcon from '@mui/icons-material/ShieldMoon'
import CampaignIcon from '@mui/icons-material/Campaign'
import ArticleIcon from '@mui/icons-material/Article'
import FactCheckIcon from '@mui/icons-material/FactCheck'
import ShowChartIcon from '@mui/icons-material/ShowChart'
import SupportAgentIcon from '@mui/icons-material/SupportAgent'
import PeopleIcon from '@mui/icons-material/People'
import {
  analyzeImpact,
  analyzeUpdate,
  ask,
  getUpdates,
  type AnalyzeResponse,
  type AskResponse,
  type ImpactResponse,
  type RegulatoryUpdate,
} from '../../api/demo'
import PdfViewer from '../../components/PdfViewer'
import IntakePanel from '../../components/IntakePanel'
import TransactionMonitor from '../../components/TransactionMonitor'
import CustomerServicePanel from '../../components/CustomerServicePanel'
import { extractPdfText } from '../../lib/pdfText'
import { DEMO_CLIENTS } from '../../data/demoClients'

const IMPACT_META: Record<string, { label: string; color: 'error' | 'warning' | 'success'; bg: string }> = {
  high: { label: '高影响', color: 'error', bg: '#fdf2f2' },
  medium: { label: '中影响', color: 'warning', bg: '#fffbf0' },
  low: { label: '低影响', color: 'success', bg: '#f6fbf8' },
}

interface DocState {
  file: File
  text: string
  numPages: number
  filename: string
}

export default function DemoWorkbench() {
  const [doc, setDoc] = useState<DocState | null>(null)
  const [extracting, setExtracting] = useState(false)
  const [tab, setTab] = useState(0)

  const [pageNumber, setPageNumber] = useState(1)
  const [highlightQuote, setHighlightQuote] = useState<string | undefined>()

  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<AskResponse | null>(null)

  const [analysis, setAnalysis] = useState<Record<string, AnalyzeResponse>>({})
  const [impacts, setImpacts] = useState<Record<string, ImpactResponse>>({})
  const [newPush, setNewPush] = useState<RegulatoryUpdate | null>(null)
  const seenIds = useRef<Set<string> | null>(null)

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setExtracting(true)
    setAnswer(null)
    try {
      const { text, numPages } = await extractPdfText(file)
      setDoc({ file, text, numPages, filename: file.name })
      setPageNumber(1)
      setHighlightQuote(undefined)
    } catch (err) {
      console.error(err)
      alert('PDF 解析失败，请换一份文字型 PDF。')
    } finally {
      setExtracting(false)
    }
  }

  const askMutation = useMutation({
    mutationFn: () => ask(doc?.text ?? '', question),
    onSuccess: (data) => setAnswer(data),
  })

  const analyzeMutation = useMutation({
    mutationFn: (update: RegulatoryUpdate) =>
      analyzeUpdate(doc?.text ?? '', update.title, update.body).then((res) => ({
        id: update.id,
        res,
      })),
    onSuccess: ({ id, res }) => setAnalysis((prev) => ({ ...prev, [id]: res })),
  })

  const impactMutation = useMutation({
    mutationFn: (update: RegulatoryUpdate) =>
      analyzeImpact(doc?.text ?? '', update.title, update.body, DEMO_CLIENTS as unknown as Record<string, unknown>[]).then((res) => ({
        id: update.id,
        res,
      })),
    onSuccess: ({ id, res }) => setImpacts((prev) => ({ ...prev, [id]: res })),
  })

  const updatesQuery = useQuery({
    queryKey: ['demo-updates'],
    queryFn: getUpdates,
    refetchInterval: 8000,
  })

  useEffect(() => {
    const updates = updatesQuery.data?.updates
    if (!updates) return
    if (seenIds.current === null) {
      seenIds.current = new Set(updates.map((u) => u.id))
      return
    }
    const fresh = updates.find((u) => !seenIds.current!.has(u.id))
    if (fresh) {
      updates.forEach((u) => seenIds.current!.add(u.id))
      setNewPush(fresh)
      setTab(1)
    }
  }, [updatesQuery.data])

  function jumpToCitation(page: number, quote: string) {
    setPageNumber(page)
    setHighlightQuote(quote)
  }

  const updates = updatesQuery.data?.updates ?? []
  const unseenCount = updatesQuery.data && seenIds.current
    ? updates.filter((u) => !seenIds.current!.has(u.id)).length
    : 0

  return (
    <Box sx={{ bgcolor: 'background.default', minHeight: '100vh' }}>
      <AppBar position="sticky" elevation={0}>
        <Toolbar sx={{ gap: 1.5 }}>
          <Avatar
            variant="rounded"
            sx={{ bgcolor: 'primary.main', width: 34, height: 34, fontSize: 18 }}
          >
            <ShieldMoonIcon fontSize="small" />
          </Avatar>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="subtitle1" sx={{ lineHeight: 1.2, color: '#fff' }}>
              合规知识库 · AI 助手
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>
              单文档智能问答 · 动态监管联动
            </Typography>
          </Box>
          {doc && (
            <Chip
              icon={<DescriptionIcon sx={{ color: '#fff !important' }} />}
              label={`${doc.filename} · ${doc.numPages} 页`}
              sx={{
                bgcolor: 'rgba(255,255,255,0.12)',
                color: '#fff',
                fontWeight: 500,
                '.MuiChip-icon': { color: '#fff' },
              }}
            />
          )}
        </Toolbar>
      </AppBar>

      <Box
        sx={{
          maxWidth: 1400,
          mx: 'auto',
          display: 'flex',
          gap: 2.5,
          p: { xs: 2, md: 3 },
          alignItems: 'flex-start',
        }}
      >
        {/* Left column */}
        <Box sx={{ flex: '1 1 52%', minWidth: 0 }}>
          {/* Upload */}
          <Card sx={{ mb: 2.5 }}>
            <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Avatar variant="rounded" sx={{ bgcolor: '#eef2ff', color: 'primary.main' }}>
                <ArticleIcon />
              </Avatar>
              <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                <Typography variant="subtitle1">当前文档</Typography>
                <Typography variant="body2" color="text.secondary" noWrap>
                  {doc
                    ? `${doc.filename} — ${doc.numPages} 页 · ${doc.text.length.toLocaleString()} 字符`
                    : '上传一份文字型 PDF 作为问答与监管联动的依据'}
                </Typography>
              </Box>
              <Button
                variant="contained"
                component="label"
                startIcon={<UploadFileIcon />}
                disabled={extracting}
              >
                {extracting ? '解析中…' : doc ? '更换' : '上传 PDF'}
                <input hidden type="file" accept="application/pdf" onChange={handleUpload} />
              </Button>
            </CardContent>
            {extracting && <LinearProgress />}
          </Card>

          <Paper variant="outlined" sx={{ borderColor: 'divider', overflow: 'hidden' }}>
            <Tabs
              value={tab}
              onChange={(_, v) => setTab(v)}
              sx={{ px: 1, borderBottom: '1px solid', borderColor: 'divider' }}
            >
              <Tab icon={<AutoAwesomeIcon fontSize="small" />} iconPosition="start" label="文档问答" />
              <Tab
                icon={
                  <Badge color="error" badgeContent={unseenCount} max={9}>
                    <RadarIcon fontSize="small" />
                  </Badge>
                }
                iconPosition="start"
                label="监管雷达"
              />
              <Tab icon={<FactCheckIcon fontSize="small" />} iconPosition="start" label="开户审核" />
              <Tab icon={<ShowChartIcon fontSize="small" />} iconPosition="start" label="交易监控" />
              <Tab icon={<SupportAgentIcon fontSize="small" />} iconPosition="start" label="AI 客服" />
            </Tabs>

            {tab === 0 && (
              <Box sx={{ p: 2.5 }}>
                <TextField
                  fullWidth
                  multiline
                  minRows={2}
                  placeholder="针对该文档提问，例如：我们现行政策对曾任政治人物如何处理？"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  disabled={!doc}
                  sx={{ mb: 1.5 }}
                />
                <Button
                  variant="contained"
                  endIcon={askMutation.isPending ? undefined : <SendIcon />}
                  disabled={!doc || !question.trim() || askMutation.isPending}
                  onClick={() => askMutation.mutate()}
                >
                  {askMutation.isPending ? '思考中…' : '提问'}
                </Button>

                {askMutation.isError && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    调用失败，请检查后端服务与 API Key。
                  </Alert>
                )}

                {answer && (
                  <Card variant="outlined" sx={{ mt: 2.5, bgcolor: '#fafbfe' }}>
                    <CardContent>
                      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                        <AutoAwesomeIcon fontSize="small" color="primary" />
                        <Typography variant="subtitle2" color="primary">
                          AI 回答
                        </Typography>
                      </Stack>
                      {answer.mode === 'insufficient' && (
                        <Alert severity="warning" sx={{ mb: 1.5 }}>
                          文档中依据不足，未作臆测。
                        </Alert>
                      )}
                      <Box>
                        {(answer.answer.includes('\n')
                          ? answer.answer.split('\n')
                          : answer.answer.split(/(?<=。)/)
                        )
                          .map((line) => line.trim())
                          .filter(Boolean)
                          .map((line, i) => (
                            <Typography key={i} sx={{ lineHeight: 1.85, mb: 1.2 }}>
                              {line}
                            </Typography>
                          ))}
                      </Box>
                      {answer.citations.length > 0 && (
                        <>
                          <Divider sx={{ my: 1.5 }} />
                          <Typography variant="caption" color="text.secondary">
                            引用来源（点击跳转并高亮原文）
                          </Typography>
                          <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 1 }}>
                            {answer.citations.map((c, i) => (
                              <Chip
                                key={i}
                                size="small"
                                label={`[${i + 1}] 第 ${c.page} 页`}
                                color="primary"
                                variant="outlined"
                                onClick={() => jumpToCitation(c.page, c.quote)}
                                sx={{ mb: 1, fontWeight: 600 }}
                              />
                            ))}
                          </Stack>
                        </>
                      )}
                    </CardContent>
                  </Card>
                )}
              </Box>
            )}

            {tab === 1 && (
              <Box sx={{ p: 2.5 }}>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
                  <CampaignIcon fontSize="small" color="action" />
                  <Typography variant="body2" color="text.secondary" sx={{ flexGrow: 1 }}>
                    每 8 秒自动检查监管发布站的新推送
                  </Typography>
                  {updatesQuery.isFetching && <CircularProgress size={14} />}
                </Stack>
                {updatesQuery.data && !updatesQuery.data.source_ok && (
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    监管发布站不可达（{updatesQuery.data.error ?? '未知'}）。请确认已启动并配置
                    REGULATORY_TEST_SITE_URL。
                  </Alert>
                )}
                {updates.length === 0 ? (
                  <Box
                    sx={{
                      py: 6,
                      textAlign: 'center',
                      color: 'text.secondary',
                      border: '1px dashed',
                      borderColor: 'divider',
                      borderRadius: 2,
                    }}
                  >
                    <RadarIcon sx={{ fontSize: 36, opacity: 0.4 }} />
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      暂无监管推送。到发布站发布一条即可实时出现。
                    </Typography>
                  </Box>
                ) : (
                  <Stack spacing={2}>
                    {updates.map((u) => {
                      const res = analysis[u.id]
                      return (
                        <Card key={u.id} variant="outlined">
                          <CardContent>
                            <Stack direction="row" spacing={1.5} alignItems="flex-start">
                              <Avatar
                                variant="rounded"
                                sx={{ bgcolor: '#fff7ed', color: 'warning.main', width: 36, height: 36 }}
                              >
                                <CampaignIcon fontSize="small" />
                              </Avatar>
                              <Box sx={{ minWidth: 0 }}>
                                <Typography variant="subtitle1" sx={{ lineHeight: 1.3 }}>
                                  {u.title || '(无标题)'}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {u.published_at}
                                </Typography>
                              </Box>
                            </Stack>
                            <Typography variant="body2" sx={{ mt: 1.5, whiteSpace: 'pre-wrap', color: 'text.secondary' }}>
                              {u.body}
                            </Typography>

                            <Button
                              size="small"
                              variant="contained"
                              startIcon={<AutoAwesomeIcon />}
                              sx={{ mt: 2 }}
                              disabled={!doc || analyzeMutation.isPending}
                              onClick={() => analyzeMutation.mutate(u)}
                            >
                              {analyzeMutation.isPending ? '分析中…' : '分析对当前文档的影响'}
                            </Button>
                            {!doc && (
                              <Typography variant="caption" color="text.secondary" sx={{ ml: 1.5 }}>
                                请先上传文档
                              </Typography>
                            )}

                            {res && (
                              <Box sx={{ mt: 2.5 }}>
                                <Alert severity="info" icon={<AutoAwesomeIcon />} sx={{ mb: 1.5 }}>
                                  <Typography variant="subtitle2" gutterBottom>
                                    AI 摘要
                                  </Typography>
                                  {res.summary}
                                </Alert>
                                {res.relevance && (
                                  <Typography variant="body2" sx={{ mb: 1.5 }}>
                                    <Box component="span" sx={{ fontWeight: 600 }}>
                                      与当前文档的相关性：
                                    </Box>
                                    {res.relevance}
                                  </Typography>
                                )}
                                {res.suggestions.length > 0 ? (
                                  <Stack spacing={1.5}>
                                    <Typography variant="subtitle2" color="secondary.main">
                                      建议的修改点（{res.suggestions.length}）
                                    </Typography>
                                    {res.suggestions.map((s, i) => (
                                      <Box
                                        key={i}
                                        sx={{
                                          p: 1.5,
                                          borderRadius: 2,
                                          border: '1px solid',
                                          borderColor: 'divider',
                                          borderLeft: '3px solid',
                                          borderLeftColor: 'secondary.main',
                                          bgcolor: '#f6fbfa',
                                        }}
                                      >
                                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                          {i + 1}. {s.point}
                                        </Typography>
                                        {s.rationale && (
                                          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                                            {s.rationale}
                                          </Typography>
                                        )}
                                        {s.cited_pages.length > 0 && (
                                          <Stack
                                            direction="row"
                                            spacing={1}
                                            alignItems="center"
                                            sx={{ mt: 1 }}
                                          >
                                            {s.cited_pages.map((p) => (
                                              <Chip
                                                key={p}
                                                size="small"
                                                variant="outlined"
                                                color="secondary"
                                                label={
                                                  s.quote
                                                    ? `高亮定位 第 ${p} 页原文`
                                                    : `跳转 第 ${p} 页`
                                                }
                                                onClick={() => jumpToCitation(p, s.quote ?? '')}
                                              />
                                            ))}
                                          </Stack>
                                        )}
                                      </Box>
                                    ))}
                                  </Stack>
                                ) : (
                                  <Typography variant="body2" color="text.secondary">
                                    该推送与当前文档相关性较低，暂无具体改进建议。
                                  </Typography>
                                )}
                              </Box>
                            )}

                            {/* Impact on existing clients (reuses the 4 demo clients) */}
                            {res && (
                              <Box sx={{ mt: 2 }}>
                                <Divider sx={{ mb: 1.5 }} />
                                <Button
                                  size="small"
                                  variant="outlined"
                                  color="secondary"
                                  startIcon={<PeopleIcon />}
                                  disabled={!doc || impactMutation.isPending}
                                  onClick={() => impactMutation.mutate(u)}
                                >
                                  {impactMutation.isPending && impactMutation.variables?.id === u.id
                                    ? '分析客户影响面中…'
                                    : '分析对存量客户的影响'}
                                </Button>
                                {impacts[u.id] && (
                                  <Box sx={{ mt: 1.5 }}>
                                    <Alert severity="info" icon={<PeopleIcon />} sx={{ mb: 1.5 }}>
                                      <Typography variant="subtitle2">客户影响面</Typography>
                                      {impacts[u.id].summary}
                                    </Alert>
                                    <Stack spacing={1}>
                                      {impacts[u.id].impacts.map((ci, i) => {
                                        const lv = IMPACT_META[ci.impact_level]
                                        return (
                                          <Box
                                            key={i}
                                            sx={{
                                              p: 1.25,
                                              borderRadius: 1.5,
                                              border: '1px solid',
                                              borderColor: 'divider',
                                              borderLeft: '3px solid',
                                              borderLeftColor: `${lv.color}.main`,
                                              bgcolor: lv.bg,
                                            }}
                                          >
                                            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.3 }}>
                                              <Chip label={lv.label} size="small" color={lv.color} sx={{ height: 20, fontSize: 11 }} />
                                              <Typography variant="body2" sx={{ fontWeight: 600 }}>{ci.client_name}</Typography>
                                            </Stack>
                                            {ci.impact_points.map((p, j) => (
                                              <Typography key={j} variant="caption" color="text.secondary" sx={{ display: 'block', pl: 1.5, lineHeight: 1.5 }}>• {p}</Typography>
                                            ))}
                                            {ci.recommended_action && (
                                              <Typography variant="caption" sx={{ display: 'block', pl: 1.5, mt: 0.3, color: 'secondary.main' }}>
                                                建议：{ci.recommended_action}
                                              </Typography>
                                            )}
                                            {ci.cited_page != null && (
                                              <Stack direction="row" spacing={1} sx={{ mt: 0.5, pl: 1.5 }}>
                                                <Chip
                                                  size="small"
                                                  color="primary"
                                                  variant="outlined"
                                                  label={`溯源 第 ${ci.cited_page} 页`}
                                                  onClick={() => jumpToCitation(ci.cited_page!, ci.quote)}
                                                  sx={{ height: 20, fontSize: 11 }}
                                                />
                                              </Stack>
                                            )}
                                          </Box>
                                        )
                                      })}
                                    </Stack>
                                  </Box>
                                )}
                              </Box>
                            )}
                            {analyzeMutation.isPending && analyzeMutation.variables?.id === u.id && (
                              <LinearProgress sx={{ mt: 2 }} />
                            )}
                          </CardContent>
                        </Card>
                      )
                    })}
                  </Stack>
                )}
              </Box>
            )}

            {tab === 2 && (
              <Box sx={{ p: 2.5 }}>
                <IntakePanel docText={doc?.text ?? ''} onCite={jumpToCitation} />
              </Box>
            )}

            {tab === 3 && (
              <Box sx={{ p: 2.5 }}>
                <TransactionMonitor docText={doc?.text ?? ''} onCite={jumpToCitation} />
              </Box>
            )}

            {tab === 4 && (
              <Box sx={{ p: 2.5 }}>
                <CustomerServicePanel docText={doc?.text ?? ''} onCite={jumpToCitation} />
              </Box>
            )}
          </Paper>
        </Box>

        {/* Right column: PDF */}
        <Box sx={{ flex: '1 1 48%', minWidth: 0, position: 'sticky', top: 88 }}>
          <PdfViewer
            file={doc?.file ?? null}
            pageNumber={pageNumber}
            highlightQuote={highlightQuote}
            onPageChange={(p) => {
              setPageNumber(p)
              setHighlightQuote(undefined)
            }}
          />
        </Box>
      </Box>

      <Snackbar
        open={!!newPush}
        autoHideDuration={6000}
        onClose={() => setNewPush(null)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert severity="info" icon={<CampaignIcon />} onClose={() => setNewPush(null)} sx={{ boxShadow: 3 }}>
          收到新监管推送：{newPush?.title}
        </Alert>
      </Snackbar>
    </Box>
  )
}
