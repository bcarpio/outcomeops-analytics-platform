import { FlowData, TransitionData } from '../api/analytics'

interface PageFlowsProps {
  entryPages: FlowData[]
  exitPages: FlowData[]
  transitions: TransitionData[]
}

function PageFlows({ entryPages, exitPages, transitions }: PageFlowsProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Entry Pages */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Entry Pages</h3>
          <p className="text-sm text-gray-500">Where sessions start</p>
        </div>
        <div className="overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Path
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Count
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {entryPages.length === 0 ? (
                <tr>
                  <td colSpan={2} className="px-6 py-4 text-sm text-gray-500 text-center">
                    No data
                  </td>
                </tr>
              ) : (
                entryPages.map((page, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4 text-sm text-gray-900 truncate max-w-[150px]">
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

      {/* Exit Pages */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Exit Pages</h3>
          <p className="text-sm text-gray-500">Where sessions end</p>
        </div>
        <div className="overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Path
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Count
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {exitPages.length === 0 ? (
                <tr>
                  <td colSpan={2} className="px-6 py-4 text-sm text-gray-500 text-center">
                    No data
                  </td>
                </tr>
              ) : (
                exitPages.map((page, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4 text-sm text-gray-900 truncate max-w-[150px]">
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

      {/* Top Transitions */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Top Flows</h3>
          <p className="text-sm text-gray-500">Page to page navigation</p>
        </div>
        <div className="overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Flow
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Count
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {transitions.length === 0 ? (
                <tr>
                  <td colSpan={2} className="px-6 py-4 text-sm text-gray-500 text-center">
                    No data
                  </td>
                </tr>
              ) : (
                transitions.map((transition, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4 text-sm text-gray-900 truncate max-w-[200px]" title={transition.flow}>
                      {transition.flow}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 text-right">
                      {transition.count.toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default PageFlows
