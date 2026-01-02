import { useState, useMemo } from 'react'
import { SessionData, RollupData, SessionDetailResponse, getSessionDetail } from '../api/analytics'

interface SessionsListProps {
  sessions: SessionData[]
  rollup: RollupData[]
  pageFilter: string | null
  referrerFilter: string | null
  domain: string
  onFilterChange: (referrer: string, page: string) => void
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (minutes < 60) return `${minutes}m ${secs}s`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours}h ${mins}m`
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatDetailTime(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function SessionsList({ sessions, rollup, pageFilter, referrerFilter, domain, onFilterChange }: SessionsListProps) {
  const [pageInput, setPageInput] = useState(pageFilter || '')
  const [selectedReferrer, setSelectedReferrer] = useState(referrerFilter || '')
  const [expandedSession, setExpandedSession] = useState<string | null>(null)
  const [sessionDetails, setSessionDetails] = useState<Record<string, SessionDetailResponse>>({})
  const [loadingSession, setLoadingSession] = useState<string | null>(null)

  // Get unique referrers from sessions for dropdown
  const uniqueReferrers = useMemo(() => {
    const refs = new Set<string>()
    sessions.forEach(s => refs.add(s.referrer))
    return Array.from(refs).sort((a, b) => {
      if (a === '(direct)') return -1
      if (b === '(direct)') return 1
      return a.localeCompare(b)
    })
  }, [sessions])

  // Get unique entry pages from sessions for dropdown
  const uniquePages = useMemo(() => {
    const pages = new Set<string>()
    sessions.forEach(s => pages.add(s.entry_page))
    return Array.from(pages).sort()
  }, [sessions])

  function handlePageSearch(e: React.FormEvent) {
    e.preventDefault()
    onFilterChange(selectedReferrer, pageInput.trim())
  }

  function handleReferrerChange(ref: string) {
    setSelectedReferrer(ref)
    onFilterChange(ref, pageInput.trim())
  }

  function handleClearFilters() {
    setPageInput('')
    setSelectedReferrer('')
    onFilterChange('', '')
  }

  async function handleRowClick(sessionId: string) {
    if (expandedSession === sessionId) {
      setExpandedSession(null)
      return
    }

    setExpandedSession(sessionId)

    // Fetch detail if not already cached
    if (!sessionDetails[sessionId]) {
      setLoadingSession(sessionId)
      try {
        const detail = await getSessionDetail(domain, sessionId)
        setSessionDetails(prev => ({ ...prev, [sessionId]: detail }))
      } catch (err) {
        console.error('Failed to fetch session detail:', err)
      } finally {
        setLoadingSession(null)
      }
    }
  }

  const hasFilters = pageFilter || referrerFilter

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <h3 className="text-lg font-medium text-gray-900">All Sessions</h3>
            {hasFilters && (
              <button
                onClick={handleClearFilters}
                className="text-sm text-sky-600 hover:text-sky-800"
              >
                Clear filters
              </button>
            )}
          </div>

          {/* Filter controls */}
          <div className="flex flex-wrap items-end gap-4">
            {/* Referrer filter dropdown */}
            <div>
              <label htmlFor="referrer-filter" className="block text-sm font-medium text-gray-700 mb-1">
                Referrer
              </label>
              <select
                id="referrer-filter"
                value={selectedReferrer}
                onChange={(e) => handleReferrerChange(e.target.value)}
                className="block w-40 rounded-md border-gray-300 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm"
              >
                <option value="">All Referrers</option>
                {uniqueReferrers.map((ref) => (
                  <option key={ref} value={ref}>{ref}</option>
                ))}
              </select>
            </div>

            {/* Entry page filter */}
            <form onSubmit={handlePageSearch} className="flex gap-2">
              <div>
                <label htmlFor="page-filter" className="block text-sm font-medium text-gray-700 mb-1">
                  Entry Page
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    id="page-filter"
                    value={pageInput}
                    onChange={(e) => setPageInput(e.target.value)}
                    placeholder="/blogs/..."
                    list="page-suggestions"
                    className="block w-64 rounded-md border-gray-300 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm"
                  />
                  <datalist id="page-suggestions">
                    {uniquePages.map((page) => (
                      <option key={page} value={page} />
                    ))}
                  </datalist>
                  <button
                    type="submit"
                    className="px-3 py-2 bg-sky-600 text-white text-sm rounded-md hover:bg-sky-700"
                  >
                    Filter
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>

        {/* Rollup summary when filtering by page */}
        {pageFilter && rollup.length > 0 && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <p className="text-sm font-medium text-gray-700 mb-2">
              Traffic to <span className="font-mono text-sky-700">{pageFilter}</span>
            </p>
            <div className="flex flex-wrap gap-2">
              {rollup.map(({ referrer, count }) => (
                <button
                  key={referrer}
                  onClick={() => handleReferrerChange(referrer)}
                  className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    selectedReferrer === referrer
                      ? 'bg-sky-600 text-white'
                      : 'bg-sky-100 text-sky-800 hover:bg-sky-200'
                  }`}
                >
                  {referrer}: {count}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-8"
              >
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Time
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Referrer
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Entry Page
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Pages
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Duration
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sessions.length === 0 ? (
              <tr>
                <td
                  colSpan={6}
                  className="px-6 py-4 text-sm text-gray-500 text-center"
                >
                  No sessions found
                </td>
              </tr>
            ) : (
              sessions.map((session) => {
                const isExpanded = expandedSession === session.session_id
                const detail = sessionDetails[session.session_id]
                const isLoading = loadingSession === session.session_id

                return (
                  <>
                    <tr
                      key={session.session_id}
                      onClick={() => handleRowClick(session.session_id)}
                      className="cursor-pointer hover:bg-gray-50 transition-colors"
                    >
                      <td className="px-6 py-4 text-sm text-gray-400">
                        <span className={`inline-block transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
                          {isLoading ? (
                            <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                          ) : (
                            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                          )}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 whitespace-nowrap">
                        {formatTime(session.timestamp)}
                      </td>
                      <td className="px-6 py-4 text-sm whitespace-nowrap">
                        <span
                          className={
                            session.referrer === '(direct)'
                              ? 'text-gray-400 italic'
                              : 'text-gray-900'
                          }
                        >
                          {session.referrer}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 truncate max-w-[250px]" title={session.entry_page}>
                        {session.entry_page}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 text-right">
                        {session.page_count}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 text-right whitespace-nowrap">
                        {formatDuration(session.duration)}
                      </td>
                    </tr>
                    {isExpanded && detail && (
                      <tr key={`${session.session_id}-detail`}>
                        <td colSpan={6} className="px-6 py-4 bg-gray-50">
                          <div className="ml-8">
                            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
                              Page Journey
                            </p>
                            <div className="space-y-2">
                              {detail.pages.map((page, idx) => (
                                <div
                                  key={`${page.timestamp}-${idx}`}
                                  className="flex items-center gap-3 text-sm"
                                >
                                  <span className="text-gray-400 font-mono text-xs w-20 flex-shrink-0">
                                    {formatDetailTime(page.timestamp)}
                                  </span>
                                  <span className="flex items-center gap-2">
                                    {idx > 0 && (
                                      <svg className="h-4 w-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                                      </svg>
                                    )}
                                    <span className={idx === 0 ? 'text-sky-700 font-medium' : 'text-gray-700'}>
                                      {page.path}
                                    </span>
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default SessionsList
