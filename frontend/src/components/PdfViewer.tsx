import { useCallback, useMemo, useState } from 'react'
import { Document, Page } from 'react-pdf'
import 'react-pdf/dist/Page/TextLayer.css'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import { Box, Button, Stack, Typography } from '@mui/material'
// Side-effect import configures the shared pdf.js worker.
import '../lib/pdfText'

interface PdfViewerProps {
  file: File | null
  pageNumber: number
  highlightQuote?: string
  onPageChange: (page: number) => void
}

interface TextItem {
  str: string
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

/**
 * Locate `sq` (whitespace-stripped quote) inside the stripped page text.
 *
 * Returns a [start, end) char range, or null. The model's quote is usually
 * verbatim but can differ by a punctuation char at either boundary, so if the
 * exact quote is not found we retry with a few leading/trailing chars trimmed
 * and take the fullest match.
 */
function findSpan(stripped: string, sq: string): [number, number] | null {
  const n = sq.length
  for (let trimStart = 0; trimStart <= 6 && trimStart < n; trimStart++) {
    for (let trimEnd = 0; trimEnd <= 6 && trimStart + trimEnd < n; trimEnd++) {
      const cand = sq.slice(trimStart, n - trimEnd)
      if (cand.length < 8) continue
      const pos = stripped.indexOf(cand)
      if (pos !== -1) return [pos, pos + cand.length]
    }
  }
  return null
}

/**
 * Find which text-layer item indices are covered by `quote`.
 *
 * pdf.js splits a page into many text items; the quote may span several of
 * them and differ only in whitespace. We concatenate the items (dropping
 * whitespace, keeping a char->item map), locate the quote as one contiguous
 * run, and return exactly the items in that run — so the highlight is a single
 * continuous span instead of scattered fragment matches.
 */
function computeHighlightItems(items: TextItem[], quote: string): Set<number> {
  const result = new Set<number>()
  const strippedQuote = quote.replace(/\s+/g, '')
  if (!strippedQuote) return result

  let stripped = ''
  const charToItem: number[] = []
  items.forEach((item, idx) => {
    for (const ch of item.str) {
      if (!/\s/.test(ch)) {
        stripped += ch
        charToItem.push(idx)
      }
    }
  })

  const span = findSpan(stripped, strippedQuote)
  if (!span) return result
  for (let i = span[0]; i < span[1]; i++) {
    result.add(charToItem[i])
  }
  return result
}

export default function PdfViewer({
  file,
  pageNumber,
  highlightQuote,
  onPageChange,
}: PdfViewerProps) {
  const [numPages, setNumPages] = useState(0)
  const [items, setItems] = useState<TextItem[]>([])

  const highlightSet = useMemo(
    () => computeHighlightItems(items, highlightQuote ?? ''),
    [items, highlightQuote],
  )

  const textRenderer = useCallback(
    (layer: { str: string; itemIndex: number }) => {
      if (highlightSet.has(layer.itemIndex)) {
        // Semi-transparent bg so the glyphs on the canvas below stay readable
        // (react-pdf renders the text layer transparent for selection).
        return `<mark style="background-color:rgba(255,206,26,0.42);color:inherit;padding:0;border-radius:2px;">${escapeHtml(layer.str)}</mark>`
      }
      return escapeHtml(layer.str)
    },
    [highlightSet],
  )

  if (!file) {
    return (
      <Box
        sx={{
          height: '100%',
          minHeight: 480,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'text.secondary',
          border: '1px dashed',
          borderColor: 'divider',
          borderRadius: 2,
          bgcolor: '#fff',
        }}
      >
        <Typography>上传 PDF 后在此预览，点击引用可跳转并高亮</Typography>
      </Box>
    )
  }

  return (
    <Box>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
        <Button
          size="small"
          variant="outlined"
          disabled={pageNumber <= 1}
          onClick={() => onPageChange(pageNumber - 1)}
        >
          上一页
        </Button>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          第 {pageNumber} / {numPages || '…'} 页
        </Typography>
        <Button
          size="small"
          variant="outlined"
          disabled={numPages > 0 && pageNumber >= numPages}
          onClick={() => onPageChange(pageNumber + 1)}
        >
          下一页
        </Button>
      </Stack>
      <Box
        sx={{
          maxHeight: '78vh',
          overflow: 'auto',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 2,
          bgcolor: '#525659',
          p: 1.5,
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <Document
          file={file}
          onLoadSuccess={({ numPages }) => setNumPages(numPages)}
          loading={<Typography sx={{ color: '#fff', p: 2 }}>加载 PDF…</Typography>}
          error={<Typography sx={{ color: '#fff', p: 2 }}>无法加载 PDF</Typography>}
        >
          <Page
            key={pageNumber}
            pageNumber={pageNumber}
            width={640}
            customTextRenderer={textRenderer}
            onGetTextSuccess={({ items }) => setItems(items as TextItem[])}
            renderTextLayer
            renderAnnotationLayer={false}
          />
        </Document>
      </Box>
    </Box>
  )
}
