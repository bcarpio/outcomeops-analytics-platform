import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getStats, getPages, getReferrers, getHours,
  getJourneys, getSessions, getFlows, getHallucinations,
  StatsResponse, PagesResponse, ReferrersResponse, HoursResponse,
  JourneysResponse, SessionsResponse, FlowsResponse, HallucinationsResponse
} from '../api/analytics'
import { getUser, logout } from '../utils/auth'
import DateRangePicker from '../components/DateRangePicker'
import StatsCards from '../components/StatsCards'
import VisitorChart from '../components/VisitorChart'
import TopPages from '../components/TopPages'
import TopReferrers from '../components/TopReferrers'
import JourneyStats from '../components/JourneyStats'
import SessionsList from '../components/SessionsList'
import PageFlows from '../components/PageFlows'
import EngagementStats from '../components/EngagementStats'
import HourlyTraffic from '../components/HourlyTraffic'
import HallucinationStats from '../components/HallucinationStats'

const DOMAINS: string[] = (import.meta.env.VITE_DOMAINS || '').split(',').filter(Boolean)
type TabType = 'analytics' | 'journeys'

function Dashboard() {
  const [selectedDomain, setSelectedDomain] = useState(DOMAINS[0])
  const [dateRange, setDateRange] = useState({ from: '', to: '' })
  const [activeTab, setActiveTab] = useState<TabType>('analytics')
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [pages, setPages] = useState<PagesResponse | null>(null)
  const [referrers, setReferrers] = useState<ReferrersResponse | null>(null)
  const [hours, setHours] = useState<HoursResponse | null>(null)
  const [journeys, setJourneys] = useState<JourneysResponse | null>(null)
  const [sessions, setSessions] = useState<SessionsResponse | null>(null)
  const [flows, setFlows] = useState<FlowsResponse | null>(null)
  const [hallucinations, setHallucinations] = useState<HallucinationsResponse | null>(null)
  // Session filters
  const [sessionReferrerFilter, setSessionReferrerFilter] = useState('')
  const [sessionPageFilter, setSessionPageFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const user = getUser()

  useEffect(() => {
    // Set default date range (last 7 days)
    const to = new Date().toISOString().split('T')[0]
    const from = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
    setDateRange({ from, to })
  }, [])

  useEffect(() => {
    if (dateRange.from && dateRange.to) {
      loadData()
    }
  }, [selectedDomain, dateRange])

  // Reload sessions when filters change
  const loadSessions = useCallback(async () => {
    if (!dateRange.from || !dateRange.to) return
    try {
      const data = await getSessions(
        selectedDomain,
        dateRange.from,
        dateRange.to,
        sessionReferrerFilter || undefined,
        sessionPageFilter || undefined
      )
      setSessions(data)
    } catch (err) {
      console.error('Failed to load sessions:', err)
    }
  }, [selectedDomain, dateRange, sessionReferrerFilter, sessionPageFilter])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  async function loadData() {
    setLoading(true)
    setError('')
    try {
      const [statsData, pagesData, referrersData, hoursData, journeysData, sessionsData, flowsData, hallucinationsData] = await Promise.all([
        getStats(selectedDomain, dateRange.from, dateRange.to),
        getPages(selectedDomain, dateRange.from, dateRange.to),
        getReferrers(selectedDomain, dateRange.from, dateRange.to),
        getHours(selectedDomain, dateRange.from, dateRange.to),
        getJourneys(selectedDomain, dateRange.from, dateRange.to),
        getSessions(selectedDomain, dateRange.from, dateRange.to, sessionReferrerFilter || undefined, sessionPageFilter || undefined),
        getFlows(selectedDomain, dateRange.from, dateRange.to),
        getHallucinations(selectedDomain, dateRange.from, dateRange.to),
      ])
      setStats(statsData)
      setPages(pagesData)
      setReferrers(referrersData)
      setHours(hoursData)
      setJourneys(journeysData)
      setSessions(sessionsData)
      setFlows(flowsData)
      setHallucinations(hallucinationsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  function handleSessionFilterChange(referrer: string, page: string) {
    setSessionReferrerFilter(referrer)
    setSessionPageFilter(page)
  }

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">{user?.email}</span>
            <button
              onClick={handleLogout}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('analytics')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'analytics'
                  ? 'border-sky-500 text-sky-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Analytics
            </button>
            <button
              onClick={() => setActiveTab('journeys')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'journeys'
                  ? 'border-sky-500 text-sky-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Journeys
            </button>
          </nav>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap gap-4 mb-6">
          {/* Domain selector */}
          <div>
            <label htmlFor="domain" className="block text-sm font-medium text-gray-700 mb-1">
              Domain
            </label>
            <select
              id="domain"
              value={selectedDomain}
              onChange={(e) => setSelectedDomain(e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm"
            >
              {DOMAINS.map((domain) => (
                <option key={domain} value={domain}>
                  {domain}
                </option>
              ))}
            </select>
          </div>

          {/* Date range picker */}
          <DateRangePicker
            from={dateRange.from}
            to={dateRange.to}
            onChange={setDateRange}
          />
        </div>

        {error && (
          <div className="rounded-md bg-red-50 p-4 mb-6">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="text-gray-500">Loading...</div>
          </div>
        ) : activeTab === 'analytics' ? (
          <div className="space-y-6">
            {/* Stats cards */}
            {stats && <StatsCards stats={stats} />}

            {/* Visitor chart */}
            {stats && <VisitorChart data={stats.daily} />}

            {/* Engagement metrics */}
            {journeys && <EngagementStats journeys={journeys} />}

            {/* Tables and Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {pages && <TopPages pages={pages.pages} />}
              {referrers && <TopReferrers referrers={referrers.referrers} />}
            </div>

            {/* Hourly traffic */}
            {hours && <HourlyTraffic hours={hours} />}
          </div>
        ) : activeTab === 'journeys' ? (
          <div className="space-y-6">
            {/* Journey stats cards */}
            {journeys && <JourneyStats journeys={journeys} />}

            {/* Page flows */}
            {flows && (
              <PageFlows
                entryPages={flows.entry_pages}
                exitPages={flows.exit_pages}
                transitions={flows.transitions}
              />
            )}

            {/* AI Hallucination Detection */}
            {hallucinations && <HallucinationStats data={hallucinations} />}

            {/* All Sessions (unified view with filters) */}
            {sessions && (
              <SessionsList
                sessions={sessions.sessions}
                rollup={sessions.rollup}
                pageFilter={sessions.page_filter}
                referrerFilter={sessions.referrer_filter}
                domain={selectedDomain}
                onFilterChange={handleSessionFilterChange}
              />
            )}
          </div>
        ) : null}
      </main>
    </div>
  )
}

export default Dashboard
