import { apiClient, ApiError } from '../../lib/api'

// Types
export type WebsiteStatus = 'PENDING' | 'CRAWLING' | 'READY' | 'ERROR'
export type CrawlFrequency = 'MANUAL' | 'DAILY' | 'WEEKLY' | 'MONTHLY'
export type WidgetPosition = 'BOTTOM_RIGHT' | 'BOTTOM_LEFT' | 'TOP_RIGHT' | 'TOP_LEFT'
export type ResponseType = 'custom_qa' | 'rag' | 'no_context'
export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'none'

export interface Website {
  id: string
  user_id: string
  url: string
  name: string
  status: WebsiteStatus
  embed_token: string
  brand_color?: string
  logo_url?: string
  welcome_message?: string
  position: WidgetPosition
  language: string
  crawl_frequency: CrawlFrequency
  max_pages: number
  is_active: boolean
  pages_indexed: number
  last_crawled_at?: string
  crawl_error?: string
  created_at: string
  updated_at: string
}

export interface WebsiteCreate {
  url: string
  name?: string
  brand_color?: string
  logo_url?: string
  welcome_message?: string
  position?: WidgetPosition
  language?: string
  crawl_frequency?: CrawlFrequency
  max_pages?: number
}

export interface WebsiteUpdate {
  name?: string
  brand_color?: string
  logo_url?: string
  welcome_message?: string
  position?: WidgetPosition
  language?: string
  crawl_frequency?: CrawlFrequency
  max_pages?: number
  is_active?: boolean
}

export interface CustomQA {
  id: string
  website_id: string
  question: string
  answer: string
  priority: number
  category?: string
  keywords?: string
  created_at: string
  updated_at: string
}

export interface CustomQACreate {
  question: string
  answer: string
  priority?: number
  category?: string
  keywords?: string
}

export interface CrawlResponse {
  task_id: string
  status: string
  message: string
}

export interface CrawlExportInfo {
  filename: string
  crawled_at?: string
  page_count?: number
}

export interface WebsitePageRecord {
  id: string
  url: string
  title?: string
  content: string
  content_preview: string
  word_count: number
  page_metadata?: Record<string, unknown> | null
  last_crawled_at: string
  created_at: string
  updated_at: string
}

export interface WebsitePageCollection {
  pages: WebsitePageRecord[]
  export?: CrawlExportInfo
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  question: string
  conversation_history?: ChatMessage[]
  visitor_id?: string
}

export interface ChatSource {
  page_url: string
  score: number
  chunk_index: number
}

export interface ChatAction {
  action: 'SHOW_MAP' | 'OPEN_HOURS' | 'CONTACT_INFO' | 'HIGHLIGHT'
  data?: Record<string, unknown>
}

export interface ChatResponse {
  answer: string
  sources: ChatSource[]
  type: ResponseType
  confidence: ConfidenceLevel
  actions?: ChatAction
  suggested_questions: string[]
}

export interface UsageStats {
  date: string
  conversations_count: number
  messages_count: number
  tokens_used: number
  cost_usd: number
  avg_satisfaction_rating?: number
  total_ratings: number
}

// API Functions
export async function listWebsites(): Promise<Website[]> {
  return apiClient.get<Website[]>('/v1/rag/websites')
}

export async function getWebsite(websiteId: string): Promise<Website> {
  return apiClient.get<Website>(`/v1/rag/websites/${encodeURIComponent(websiteId)}`)
}

export async function createWebsite(data: WebsiteCreate): Promise<Website> {
  return apiClient.post<Website, WebsiteCreate>('/v1/rag/websites', data)
}

export async function updateWebsite(websiteId: string, data: WebsiteUpdate): Promise<Website> {
  return apiClient.put<Website, WebsiteUpdate>(
    `/v1/rag/websites/${encodeURIComponent(websiteId)}`,
    data
  )
}

export async function deleteWebsite(websiteId: string): Promise<void> {
  return apiClient.delete<void>(`/v1/rag/websites/${encodeURIComponent(websiteId)}`)
}

export async function triggerCrawl(websiteId: string): Promise<CrawlResponse> {
  return apiClient.post<CrawlResponse>(
    `/v1/rag/websites/${encodeURIComponent(websiteId)}/crawl`
  )
}

export async function listWebsitePages(websiteId: string): Promise<WebsitePageCollection> {
  return apiClient.get<WebsitePageCollection>(
    `/v1/rag/websites/${encodeURIComponent(websiteId)}/pages`
  )
}

export async function downloadWebsitePagesExport(
  websiteId: string
): Promise<{ blob: Blob; filename: string | null }> {
  const response = await apiClient.getRaw(
    `/v1/rag/websites/${encodeURIComponent(websiteId)}/pages/export`
  )

  if (!response.ok) {
    const message = await response.text()
    throw new ApiError(message || `Download failed with status ${response.status}`, response.status)
  }

  const disposition = response.headers.get('Content-Disposition')
  const filenameMatch = disposition?.match(/filename="?([^";]+)"?/i)
  const filename = filenameMatch?.[1] ?? null

  const blob = await response.blob()
  return { blob, filename }
}

export async function listCustomQAs(websiteId: string): Promise<CustomQA[]> {
  return apiClient.get<CustomQA[]>(
    `/v1/rag/websites/${encodeURIComponent(websiteId)}/qas`
  )
}

export async function createCustomQA(
  websiteId: string,
  data: CustomQACreate
): Promise<CustomQA> {
  return apiClient.post<CustomQA, CustomQACreate>(
    `/v1/rag/websites/${encodeURIComponent(websiteId)}/qas`,
    data
  )
}

export async function deleteCustomQA(websiteId: string, qaId: string): Promise<void> {
  return apiClient.delete<void>(
    `/v1/rag/websites/${encodeURIComponent(websiteId)}/qas/${encodeURIComponent(qaId)}`
  )
}

export async function getAnalytics(websiteId: string): Promise<UsageStats[]> {
  return apiClient.get<UsageStats[]>(
    `/v1/rag/websites/${encodeURIComponent(websiteId)}/analytics`
  )
}
