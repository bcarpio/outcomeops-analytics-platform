import { JourneysResponse } from '../api/analytics'

interface JourneyStatsProps {
  journeys: JourneysResponse
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${minutes}m ${secs}s`
}

function JourneyStats({ journeys }: JourneyStatsProps) {
  const cards = [
    {
      title: 'Total Sessions',
      value: journeys.total_sessions.toLocaleString(),
    },
    {
      title: 'Total Pageviews',
      value: journeys.total_pageviews.toLocaleString(),
    },
    {
      title: 'Avg Pages/Session',
      value: journeys.avg_pages_per_session.toString(),
    },
    {
      title: 'Avg Duration',
      value: formatDuration(journeys.avg_session_duration),
    },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div
          key={card.title}
          className="bg-white rounded-lg shadow px-5 py-6"
        >
          <dt className="text-sm font-medium text-gray-500 truncate">
            {card.title}
          </dt>
          <dd className="mt-1 text-3xl font-semibold text-gray-900">
            {card.value}
          </dd>
        </div>
      ))}
    </div>
  )
}

export default JourneyStats
