import { HallucinationsResponse } from '../api/analytics'

interface HallucinationStatsProps {
  data: HallucinationsResponse
}

function formatTimestamp(timestamp: string): string {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function HallucinationStats({ data }: HallucinationStatsProps) {
  const hasData = data.total_404s > 0

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-medium text-gray-900">
          AI Hallucination Detection
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          Tracks 404 errors from AI-generated URLs that don't exist
        </p>
      </div>

      <div className="p-6">
        {/* Summary Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <dt className="text-sm font-medium text-gray-500">Total 404s</dt>
            <dd className="mt-1 text-2xl font-semibold text-gray-900">
              {data.total_404s.toLocaleString()}
            </dd>
          </div>
          <div className="bg-amber-50 rounded-lg p-4">
            <dt className="text-sm font-medium text-amber-700">AI Hallucinations</dt>
            <dd className="mt-1 text-2xl font-semibold text-amber-900">
              {data.ai_hallucinations.toLocaleString()}
            </dd>
          </div>
          <div className="bg-amber-50 rounded-lg p-4">
            <dt className="text-sm font-medium text-amber-700">AI Percentage</dt>
            <dd className="mt-1 text-2xl font-semibold text-amber-900">
              {data.ai_percentage}%
            </dd>
          </div>
        </div>

        {!hasData ? (
          <div className="text-center py-8 text-gray-500">
            No 404 errors tracked in this period
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Pattern Breakdown */}
            {data.patterns.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-3">
                  AI Patterns Detected
                </h4>
                <div className="space-y-2">
                  {data.patterns.map((p) => (
                    <div
                      key={p.pattern}
                      className="flex items-center justify-between bg-amber-50 rounded px-3 py-2"
                    >
                      <code className="text-sm text-amber-800">{p.pattern}</code>
                      <span className="text-sm font-medium text-amber-700">
                        {p.count}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Top 404 Paths */}
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-3">
                Top 404 Paths
              </h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {data.top_paths.slice(0, 10).map((p) => (
                  <div
                    key={p.path}
                    className={`flex items-center justify-between rounded px-3 py-2 ${
                      p.is_ai_pattern ? 'bg-amber-50' : 'bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      {p.is_ai_pattern && (
                        <span className="flex-shrink-0 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-amber-200 text-amber-800">
                          AI
                        </span>
                      )}
                      <code className="text-sm text-gray-700 truncate">
                        {p.path}
                      </code>
                    </div>
                    <span className="text-sm font-medium text-gray-600 ml-2">
                      {p.count}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent AI Hallucinations */}
            {data.recent_hallucinations.length > 0 && (
              <div className="lg:col-span-2">
                <h4 className="text-sm font-medium text-gray-700 mb-3">
                  Recent AI Hallucinations
                </h4>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                          Time
                        </th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                          Path
                        </th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                          Pattern
                        </th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                          Referrer
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {data.recent_hallucinations.map((h, i) => (
                        <tr key={`${h.path}-${h.timestamp}-${i}`}>
                          <td className="px-3 py-2 text-sm text-gray-500 whitespace-nowrap">
                            {formatTimestamp(h.timestamp)}
                          </td>
                          <td className="px-3 py-2 text-sm">
                            <code className="text-amber-700">{h.path}</code>
                          </td>
                          <td className="px-3 py-2 text-sm text-gray-500">
                            {h.matched_pattern}
                          </td>
                          <td className="px-3 py-2 text-sm text-gray-500 truncate max-w-xs">
                            {h.referrer || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default HallucinationStats
