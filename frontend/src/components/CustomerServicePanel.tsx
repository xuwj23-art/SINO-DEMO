import { useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Alert,
  Avatar,
  Box,
  Button,
  Chip,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import PersonIcon from '@mui/icons-material/Person'
import SmartToyIcon from '@mui/icons-material/SmartToy'
import SendIcon from '@mui/icons-material/Send'
import SupportAgentIcon from '@mui/icons-material/SupportAgent'
import MyLocationIcon from '@mui/icons-material/MyLocation'
import {
  customerAsk,
  type Citation,
  type CustomerServiceResponse,
} from '../api/demo'

interface CustomerServicePanelProps {
  docText: string
  onCite: (page: number, quote: string) => void
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  citations?: Citation[]
  handoffRequired?: boolean
  handoffLabel?: string
}

const HANDOFF_TEXT = '该问题无法回答，为您转接人工客服。'

export default function CustomerServicePanel({ docText, onCite }: CustomerServicePanelProps) {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [transferredIds, setTransferredIds] = useState<Set<string>>(new Set())
  const seqRef = useRef(0)

  function nextId(prefix: string) {
    seqRef.current += 1
    return `${prefix}-${seqRef.current}`
  }

  useEffect(() => {
    setQuestion('')
    setMessages([])
    setTransferredIds(new Set())
  }, [docText])

  const askMutation = useMutation<CustomerServiceResponse, Error, string>({
    mutationFn: (customerQuestion) => customerAsk(docText, customerQuestion),
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        {
          id: nextId('assistant'),
          role: 'assistant',
          text: data.answer,
          citations: data.citations,
          handoffRequired: data.handoff_required || data.mode === 'handoff',
          handoffLabel: data.handoff_label,
        },
      ])
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        {
          id: nextId('assistant'),
          role: 'assistant',
          text: HANDOFF_TEXT,
          citations: [],
          handoffRequired: true,
          handoffLabel: '转人工客服',
        },
      ])
    },
  })

  function submitQuestion(event?: React.FormEvent<HTMLFormElement>) {
    event?.preventDefault()
    const trimmed = question.trim()
    if (!trimmed || !docText || askMutation.isPending) return
    setMessages((prev) => [
      ...prev,
      { id: nextId('user'), role: 'user', text: trimmed },
    ])
    setQuestion('')
    askMutation.mutate(trimmed)
  }

  function transferToHuman(messageId: string) {
    setTransferredIds((prev) => new Set(prev).add(messageId))
  }

  return (
    <Box>
      {!docText && (
        <Alert severity="warning" sx={{ mb: 1.5 }}>
          请先上传材料 PDF 后再咨询 AI 客服。
        </Alert>
      )}

      <Box
        sx={{
          height: 420,
          overflowY: 'auto',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 2,
          bgcolor: '#fbfcfd',
          p: 1.5,
          mb: 1.5,
        }}
      >
        {messages.length === 0 ? (
          <Stack alignItems="center" justifyContent="center" sx={{ height: '100%', color: 'text.secondary' }}>
            <SupportAgentIcon sx={{ fontSize: 38, opacity: 0.45, mb: 1 }} />
            <Typography variant="body2">
              请输入客户问题
            </Typography>
          </Stack>
        ) : (
          <Stack spacing={1.25}>
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                transferred={transferredIds.has(message.id)}
                onTransfer={() => transferToHuman(message.id)}
                onCite={onCite}
              />
            ))}
            {askMutation.isPending && (
              <Stack direction="row" spacing={1} alignItems="center" sx={{ color: 'text.secondary', pl: 1 }}>
                <CircularProgress size={16} />
                <Typography variant="caption">AI 客服正在查阅材料…</Typography>
              </Stack>
            )}
          </Stack>
        )}
      </Box>

      <Stack
        component="form"
        direction={{ xs: 'column', sm: 'row' }}
        spacing={1}
        onSubmit={submitQuestion}
      >
        <TextField
          fullWidth
          multiline
          minRows={2}
          maxRows={4}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="例如：开户需要准备哪些材料？"
          disabled={!docText || askMutation.isPending}
        />
        <Button
          type="submit"
          variant="contained"
          endIcon={askMutation.isPending ? undefined : <SendIcon />}
          disabled={!docText || !question.trim() || askMutation.isPending}
          sx={{ minWidth: 112, alignSelf: { xs: 'stretch', sm: 'stretch' } }}
        >
          {askMutation.isPending ? '查询中…' : '发送'}
        </Button>
      </Stack>
    </Box>
  )
}

function MessageBubble({
  message,
  transferred,
  onTransfer,
  onCite,
}: {
  message: ChatMessage
  transferred: boolean
  onTransfer: () => void
  onCite: (page: number, quote: string) => void
}) {
  const isUser = message.role === 'user'
  const lines = splitMessage(message.text)
  return (
    <Stack direction="row" spacing={1} justifyContent={isUser ? 'flex-end' : 'flex-start'}>
      {!isUser && (
        <Avatar variant="rounded" sx={{ width: 30, height: 30, bgcolor: '#eef2ff', color: 'primary.main' }}>
          <SmartToyIcon fontSize="small" />
        </Avatar>
      )}
      <Box
        sx={{
          maxWidth: '82%',
          p: 1.25,
          borderRadius: 2,
          border: '1px solid',
          borderColor: isUser ? 'primary.light' : 'divider',
          bgcolor: isUser ? '#eaf3ff' : '#fff',
        }}
      >
        {lines.map((line, index) => (
          <Typography
            key={index}
            variant="body2"
            sx={{ lineHeight: 1.75, mb: index === lines.length - 1 ? 0 : 0.75 }}
          >
            {line}
          </Typography>
        ))}
        {!isUser && message.citations && message.citations.length > 0 && (
          <Stack direction="row" spacing={0.75} flexWrap="wrap" sx={{ mt: 1, gap: 0.75 }}>
            {message.citations.map((citation, index) => (
              <Chip
                key={`${citation.page}-${index}`}
                size="small"
                icon={<MyLocationIcon />}
                label={`依据 第 ${citation.page} 页`}
                variant="outlined"
                color="primary"
                onClick={() => onCite(citation.page, citation.quote)}
              />
            ))}
          </Stack>
        )}
        {!isUser && message.handoffRequired && (
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1.25, flexWrap: 'wrap', gap: 1 }}>
            <Button
              size="small"
              variant="contained"
              color="warning"
              startIcon={<SupportAgentIcon />}
              disabled={transferred}
              onClick={onTransfer}
            >
              {message.handoffLabel || '转人工客服'}
            </Button>
            {transferred && (
              <Chip size="small" color="success" label="已提交转接" />
            )}
          </Stack>
        )}
      </Box>
      {isUser && (
        <Avatar variant="rounded" sx={{ width: 30, height: 30, bgcolor: '#f5f5f5', color: 'text.secondary' }}>
          <PersonIcon fontSize="small" />
        </Avatar>
      )}
    </Stack>
  )
}

function splitMessage(text: string): string[] {
  const lines = text.includes('\n') ? text.split('\n') : text.split(/(?<=。)/)
  return lines.map((line) => line.trim()).filter(Boolean)
}
