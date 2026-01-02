interface DateRangePickerProps {
  from: string
  to: string
  onChange: (range: { from: string; to: string }) => void
}

function DateRangePicker({ from, to, onChange }: DateRangePickerProps) {
  function setPreset(days: number) {
    const toDate = new Date().toISOString().split('T')[0]
    const fromDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
    onChange({ from: fromDate, to: toDate })
  }

  return (
    <div className="flex flex-wrap items-end gap-4">
      <div>
        <label htmlFor="from" className="block text-sm font-medium text-gray-700 mb-1">
          From
        </label>
        <input
          type="date"
          id="from"
          value={from}
          onChange={(e) => onChange({ from: e.target.value, to })}
          className="block rounded-md border-gray-300 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm"
        />
      </div>
      <div>
        <label htmlFor="to" className="block text-sm font-medium text-gray-700 mb-1">
          To
        </label>
        <input
          type="date"
          id="to"
          value={to}
          onChange={(e) => onChange({ from, to: e.target.value })}
          className="block rounded-md border-gray-300 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm"
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => setPreset(7)}
          className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          7 days
        </button>
        <button
          onClick={() => setPreset(30)}
          className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          30 days
        </button>
        <button
          onClick={() => setPreset(60)}
          className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          60 days
        </button>
        <button
          onClick={() => setPreset(90)}
          className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          90 days
        </button>
      </div>
    </div>
  )
}

export default DateRangePicker
