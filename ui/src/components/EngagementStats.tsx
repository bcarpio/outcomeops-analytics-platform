import { JourneysResponse } from '../api/analytics'

interface EngagementStatsProps {
  journeys: JourneysResponse
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${minutes}m ${secs}s`
}

function EngagementStats({ journeys }: EngagementStatsProps) {
  const cards = [
    {
      title: 'Bounce Rate',
      value: `${journeys.bounce_rate}%`,
      subtitle: '1 page, <10s',
      color: journeys.bounce_rate > 50 ? 'text-red-600' : 'text-gray-900',
    },
    {
      title: 'Engaged Sessions',
      value: `${journeys.engaged_sessions}`,
      subtitle: `${journeys.engaged_rate}% of sessions`,
      color: 'text-green-600',
    },
    {
      title: 'Avg Time on Blog',
      value: formatDuration(journeys.avg_blog_time),
      subtitle: `${journeys.blog_sessions} blog sessions`,
      color: 'text-gray-900',
    },
  ]

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-medium text-gray-900">Engagement Metrics</h3>
        <p className="text-sm text-gray-500">Session quality indicators</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-gray-200">
        {cards.map((card) => (
          <div key={card.title} className="px-6 py-5">
            <dt className="text-sm font-medium text-gray-500">{card.title}</dt>
            <dd className={`mt-1 text-2xl font-semibold ${card.color}`}>
              {card.value}
            </dd>
            <dd className="mt-1 text-xs text-gray-400">{card.subtitle}</dd>
          </div>
        ))}
      </div>
    </div>
  )
}

export default EngagementStats
