import axios from 'axios'

// In dev we rely on Vite's /api -> localhost:8000 proxy (see vite.config.ts),
// so a relative baseURL works both when you open http://localhost:5173
// yourself AND when a colleague opens http://<this-machine-LAN-ip>:5173.
// Override with VITE_API_BASE_URL only if you need a different backend host.
const baseURL = (import.meta.env.VITE_API_BASE_URL ?? '') + '/api/v1'

const client = axios.create({ baseURL, timeout: 120_000 })

export interface Citation {
  page: number
  quote: string
}

export interface AskResponse {
  answer: string
  citations: Citation[]
  mode: 'answered' | 'insufficient'
}

export interface CustomerServiceResponse {
  answer: string
  citations: Citation[]
  mode: 'answered' | 'handoff'
  handoff_required: boolean
  handoff_label: string
}

export interface Suggestion {
  point: string
  rationale: string
  cited_pages: number[]
  quote: string
}

export interface AnalyzeResponse {
  summary: string
  relevance: string
  suggestions: Suggestion[]
}

export interface RegulatoryUpdate {
  id: string
  title: string
  published_at: string
  body: string
}

export interface UpdatesResponse {
  updates: RegulatoryUpdate[]
  source_ok: boolean
  error: string | null
}

export async function ask(docText: string, question: string): Promise<AskResponse> {
  const { data } = await client.post<AskResponse>('/demo/ask', {
    doc_text: docText,
    question,
  })
  return data
}

export async function customerAsk(
  docText: string,
  question: string,
): Promise<CustomerServiceResponse> {
  const { data } = await client.post<CustomerServiceResponse>('/demo/customer-service/ask', {
    doc_text: docText,
    question,
  })
  return data
}

export async function analyzeUpdate(
  docText: string,
  pushTitle: string,
  pushBody: string,
): Promise<AnalyzeResponse> {
  const { data } = await client.post<AnalyzeResponse>('/demo/regulatory/analyze', {
    doc_text: docText,
    push_title: pushTitle,
    push_body: pushBody,
  })
  return data
}

export async function getUpdates(): Promise<UpdatesResponse> {
  const { data } = await client.get<UpdatesResponse>('/demo/regulatory/updates')
  return data
}

// --- Compliance intake (pre-account-opening AML/KYC screening) ---

export type IntakeStatus = 'pass' | 'fail' | 'review'
export type IntakeOutcome = 'passed' | 'failed' | 'needs_review'

export interface ChecklistItem {
  key: string
  title: string
  status: IntakeStatus
  detail: string
  cited_page: number | null
  quote: string
}

export interface IntakeResponse {
  checklist: ChecklistItem[]
  outcome: IntakeOutcome
  issues: ChecklistItem[]
  summary: string
}

export async function intake(
  docText: string,
  clientData: Record<string, unknown>,
): Promise<IntakeResponse> {
  const { data } = await client.post<IntakeResponse>('/demo/intake', {
    doc_text: docText,
    client: clientData,
  })
  return data
}

// --- Transaction monitoring (post-onboarding suspicious-activity screening) ---

export interface DemoTransaction {
  id: string
  time: string
  client_id: string
  client_name: string
  type: 'buy' | 'sell' | 'deposit' | 'withdraw' | 'transfer'
  amount: number
  currency: string
  counterparty?: string
  suspect_flags?: string[]
}

export type RiskLevel = 'high' | 'medium' | 'low'

export interface TxnAnalyzeResponse {
  risk_level: RiskLevel
  signals: string[]
  client_context: string
  actions: string[]
  cited_page: number | null
  quote: string
  summary: string
}

export async function analyzeTransaction(
  docText: string,
  clientData: Record<string, unknown>,
  transaction: DemoTransaction,
): Promise<TxnAnalyzeResponse> {
  const { data } = await client.post<TxnAnalyzeResponse>('/demo/transaction/analyze', {
    doc_text: docText,
    client: clientData,
    transaction,
  })
  return data
}

// --- Regulatory impact on existing clients ---

export type ImpactLevel = 'high' | 'medium' | 'low'

export interface ClientImpact {
  client_id: string
  client_name: string
  impact_level: ImpactLevel
  impact_points: string[]
  recommended_action: string
  cited_page: number | null
  quote: string
}

export interface ImpactResponse {
  impacts: ClientImpact[]
  summary: string
}

export async function analyzeImpact(
  docText: string,
  pushTitle: string,
  pushBody: string,
  clients: Record<string, unknown>[],
): Promise<ImpactResponse> {
  const { data } = await client.post<ImpactResponse>('/demo/regulatory/impact', {
    doc_text: docText,
    push_title: pushTitle,
    push_body: pushBody,
    clients,
  })
  return data
}

// --- Compliance email generation (intake / transaction) ---

export interface EmailResponse {
  subject: string
  body: string
  scene: string
}

export async function generateEmail(
  scene: 'intake' | 'transaction',
  clientName: string,
  clientId: string,
  context: Record<string, unknown>,
): Promise<EmailResponse> {
  const { data } = await client.post<EmailResponse>('/demo/email/generate', {
    scene,
    client_name: clientName,
    client_id: clientId,
    context,
  })
  return data
}
