import { getToken } from '../utils/auth'

/**
 * Get API base URL based on current environment
 * - Development mode: use dev API
 * - Dev subdomain: use dev API
 * - Production: use production API
 */
const getApiBaseUrl = (): string => {
  if (import.meta.env.DEV) {
    return 'https://api.analytics.dev.outcomeops.ai'
  }
  if (window.location.hostname.includes('dev.outcomeops.ai')) {
    return 'https://api.analytics.dev.outcomeops.ai'
  }
  return 'https://api.analytics.outcomeops.ai'
}

const API_BASE_URL = getApiBaseUrl()

interface RequestOptions {
  method?: string
  body?: unknown
  requiresAuth?: boolean
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, requiresAuth = true } = options

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  if (requiresAuth) {
    const token = getToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Request failed' }))
    throw new Error(error.error || 'Request failed')
  }

  return response.json()
}

// Auth API
export interface MagicLinkResponse {
  message: string
}

export interface VerifyResponse {
  access_token: string
  user: {
    email: string
    name: string
  }
}

export async function requestMagicLink(email: string): Promise<MagicLinkResponse> {
  return request('/auth/magic-link', {
    method: 'POST',
    body: { email },
    requiresAuth: false,
  })
}

export async function verifyToken(token: string): Promise<VerifyResponse> {
  return request('/auth/verify', {
    method: 'POST',
    body: { token },
    requiresAuth: false,
  })
}

// Analytics API
export interface StatsResponse {
  domain: string
  from_date: string
  to_date: string
  total_requests: number
  unique_visitors: number
  daily: Record<string, number>
}

export interface PageData {
  path: string
  count: number
}

export interface PagesResponse {
  domain: string
  from_date: string
  to_date: string
  pages: PageData[]
}

export interface ReferrerData {
  domain: string
  count: number
}

export interface ReferrersResponse {
  domain: string
  from_date: string
  to_date: string
  referrers: ReferrerData[]
}

export interface CountryData {
  country: string
  count: number
}

export interface CountriesResponse {
  domain: string
  from_date: string
  to_date: string
  countries: CountryData[]
}

export async function getStats(
  domain: string,
  from?: string,
  to?: string
): Promise<StatsResponse> {
  const params = new URLSearchParams()
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  const query = params.toString() ? `?${params.toString()}` : ''
  return request(`/analytics/stats/${domain}${query}`)
}

export async function getPages(
  domain: string,
  from?: string,
  to?: string,
  limit = 10
): Promise<PagesResponse> {
  const params = new URLSearchParams()
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  params.set('limit', limit.toString())
  return request(`/analytics/pages/${domain}?${params.toString()}`)
}

export async function getReferrers(
  domain: string,
  from?: string,
  to?: string,
  limit = 10
): Promise<ReferrersResponse> {
  const params = new URLSearchParams()
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  params.set('limit', limit.toString())
  return request(`/analytics/referrers/${domain}?${params.toString()}`)
}

export async function getCountries(
  domain: string,
  from?: string,
  to?: string
): Promise<CountriesResponse> {
  const params = new URLSearchParams()
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  const query = params.toString() ? `?${params.toString()}` : ''
  return request(`/analytics/countries/${domain}${query}`)
}

// Hourly Traffic API
export interface HoursResponse {
  domain: string
  from_date: string
  to_date: string
  hourly: Record<string, number>
  peak_hour: string
  total: number
}

export async function getHours(
  domain: string,
  from?: string,
  to?: string
): Promise<HoursResponse> {
  const params = new URLSearchParams()
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  const query = params.toString() ? `?${params.toString()}` : ''
  return request(`/analytics/hours/${domain}${query}`)
}

// Journey Analytics API
export interface JourneysResponse {
  domain: string
  from_date: string
  to_date: string
  total_sessions: number
  total_pageviews: number
  avg_pages_per_session: number
  avg_session_duration: number
  bounce_rate: number
  engaged_sessions: number
  engaged_rate: number
  blog_sessions: number
  avg_blog_time: number
}

export interface SessionData {
  session_id: string
  timestamp: string
  referrer: string
  entry_page: string
  exit_page: string
  page_count: number
  duration: number
}

export interface RollupData {
  referrer: string
  count: number
}

export interface SessionsResponse {
  domain: string
  from_date: string
  to_date: string
  page_filter: string | null
  referrer_filter: string | null
  rollup: RollupData[]
  sessions: SessionData[]
}

export interface FlowData {
  path: string
  count: number
}

export interface TransitionData {
  flow: string
  count: number
}

export interface FlowsResponse {
  domain: string
  from_date: string
  to_date: string
  entry_pages: FlowData[]
  exit_pages: FlowData[]
  transitions: TransitionData[]
}

export async function getJourneys(
  domain: string,
  from?: string,
  to?: string
): Promise<JourneysResponse> {
  const params = new URLSearchParams()
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  const query = params.toString() ? `?${params.toString()}` : ''
  return request(`/analytics/journeys/${domain}${query}`)
}

export async function getSessions(
  domain: string,
  from?: string,
  to?: string,
  referrer?: string,
  page?: string,
  limit = 50
): Promise<SessionsResponse> {
  const params = new URLSearchParams()
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  if (referrer) params.set('referrer', referrer)
  if (page) params.set('page', page)
  params.set('limit', limit.toString())
  return request(`/analytics/sessions/${domain}?${params.toString()}`)
}

export async function getFlows(
  domain: string,
  from?: string,
  to?: string,
  limit = 10
): Promise<FlowsResponse> {
  const params = new URLSearchParams()
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  params.set('limit', limit.toString())
  return request(`/analytics/flows/${domain}?${params.toString()}`)
}

// Session Detail API
export interface SessionPageData {
  path: string
  timestamp: string
  referrer: string
}

export interface SessionDetailResponse {
  session_id: string
  domain: string
  start_time: string
  end_time: string
  duration: number
  page_count: number
  pages: SessionPageData[]
}

export async function getSessionDetail(
  domain: string,
  sessionId: string
): Promise<SessionDetailResponse> {
  return request(`/analytics/sessions/${domain}/${sessionId}`)
}

// AI Hallucination Metrics API
export interface HallucinationPattern {
  pattern: string
  count: number
}

export interface HallucinationPath {
  path: string
  count: number
  is_ai_pattern: boolean
  matched_pattern: string | null
}

export interface RecentHallucination {
  path: string
  timestamp: string
  referrer: string
  matched_pattern: string
}

export interface HallucinationsResponse {
  domain: string
  from_date: string
  to_date: string
  total_404s: number
  ai_hallucinations: number
  ai_percentage: number
  patterns: HallucinationPattern[]
  top_paths: HallucinationPath[]
  recent_hallucinations: RecentHallucination[]
}

export async function getHallucinations(
  domain: string,
  from?: string,
  to?: string
): Promise<HallucinationsResponse> {
  const params = new URLSearchParams()
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  const query = params.toString() ? `?${params.toString()}` : ''
  return request(`/analytics/hallucinations/${domain}${query}`)
}
