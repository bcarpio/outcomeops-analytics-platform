import { HoursResponse } from '../api/analytics'

interface HourlyTrafficProps {
  hours: HoursResponse
}

function HourlyTraffic({ hours }: HourlyTrafficProps) {
  // Group hours into time blocks for display
  const timeBlocks = [
    { label: '00-03', hours: ['00', '01', '02'] },
    { label: '03-06', hours: ['03', '04', '05'] },
    { label: '06-09', hours: ['06', '07', '08'] },
    { label: '09-12', hours: ['09', '10', '11'] },
    { label: '12-15', hours: ['12', '13', '14'] },
    { label: '15-18', hours: ['15', '16', '17'] },
    { label: '18-21', hours: ['18', '19', '20'] },
    { label: '21-24', hours: ['21', '22', '23'] },
  ]

  const blockCounts = timeBlocks.map(block => ({
    label: block.label,
    count: block.hours.reduce((sum, h) => sum + (hours.hourly[h] || 0), 0),
  }))

  const maxBlockCount = Math.max(...blockCounts.map(b => b.count), 1)

  // Format peak hour for display
  const peakHourFormatted = `${hours.peak_hour}:00 UTC`

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-medium text-gray-900">Traffic by Hour</h3>
        <p className="text-sm text-gray-500">
          Peak hour: {peakHourFormatted} ({hours.hourly[hours.peak_hour]} requests)
        </p>
      </div>
      <div className="px-6 py-4">
        <div className="space-y-2">
          {blockCounts.map((block) => {
            const percentage = (block.count / maxBlockCount) * 100
            return (
              <div key={block.label} className="flex items-center gap-3">
                <span className="text-sm text-gray-500 w-12 text-right font-mono">
                  {block.label}
                </span>
                <div className="flex-1 h-6 bg-gray-100 rounded overflow-hidden">
                  <div
                    className="h-full bg-sky-500 rounded transition-all duration-300"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <span className="text-sm text-gray-600 w-12 text-right">
                  {block.count}
                </span>
              </div>
            )
          })}
        </div>
        <p className="mt-4 text-xs text-gray-400 text-center">
          Times shown in UTC. Total: {hours.total} requests
        </p>
      </div>
    </div>
  )
}

export default HourlyTraffic
