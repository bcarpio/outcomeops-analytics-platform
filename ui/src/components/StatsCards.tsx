import { StatsResponse } from '../api/analytics'

interface StatsCardsProps {
  stats: StatsResponse
}

function StatsCards({ stats }: StatsCardsProps) {
  const cards = [
    {
      title: 'Total Requests',
      value: stats.total_requests.toLocaleString(),
    },
    {
      title: 'Unique Visitors',
      value: stats.unique_visitors.toLocaleString(),
    },
    {
      title: 'Days Tracked',
      value: Object.keys(stats.daily).length.toString(),
    },
    {
      title: 'Avg Daily Requests',
      value: Math.round(
        stats.total_requests / Math.max(Object.keys(stats.daily).length, 1)
      ).toLocaleString(),
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

export default StatsCards
