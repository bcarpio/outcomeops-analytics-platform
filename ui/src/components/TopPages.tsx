import { PageData } from '../api/analytics'

interface TopPagesProps {
  pages: PageData[]
}

function TopPages({ pages }: TopPagesProps) {
  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-medium text-gray-900">Top Pages</h3>
      </div>
      <div className="overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Path
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Views
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {pages.length === 0 ? (
              <tr>
                <td
                  colSpan={2}
                  className="px-6 py-4 text-sm text-gray-500 text-center"
                >
                  No data available
                </td>
              </tr>
            ) : (
              pages.map((page, index) => (
                <tr key={index}>
                  <td className="px-6 py-4 text-sm text-gray-900 truncate max-w-xs">
                    {page.path}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 text-right">
                    {page.count.toLocaleString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default TopPages
