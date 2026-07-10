import { pdfjs } from 'react-pdf'

// Configure the pdf.js worker once, shared by both extraction and <PdfViewer>.
// The worker version must match react-pdf's bundled pdfjs-dist.
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()

export interface ExtractResult {
  text: string
  numPages: number
}

/**
 * Extract text from a PDF File in the browser, with per-page markers so the
 * backend can cite page numbers. Marker format: `===== Page N =====`.
 */
export async function extractPdfText(file: File): Promise<ExtractResult> {
  const buffer = await file.arrayBuffer()
  const doc = await pdfjs.getDocument({ data: new Uint8Array(buffer) }).promise
  const parts: string[] = []

  for (let pageNum = 1; pageNum <= doc.numPages; pageNum++) {
    const page = await doc.getPage(pageNum)
    const content = await page.getTextContent()
    const pageText = content.items
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .map((item: any) => ('str' in item ? item.str : ''))
      .join(' ')
      .replace(/\s+/g, ' ')
      .trim()
    parts.push(`===== Page ${pageNum} =====\n${pageText}`)
  }

  await doc.destroy()
  return { text: parts.join('\n\n'), numPages: doc.numPages }
}
