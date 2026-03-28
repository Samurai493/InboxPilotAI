'use client'

import { useState } from 'react'
import { getApiBaseUrl } from '@/lib/app-settings'
import { getAuthHeaders } from '@/lib/api'

export default function TracesPage() {
  const [traceId, setTraceId] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSearch = async () => {
    if (!traceId.trim()) return
    
    setLoading(true)
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/traces/${traceId}`, {
        method: 'GET',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      if (data.url) {
        window.open(data.url, '_blank')
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to fetch trace')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 py-12">
      <div className="container mx-auto px-4 max-w-4xl">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">Trace Inspector</h1>
          <p className="text-gray-600 mb-8">
            Search for traces by trace ID or thread ID to inspect graph execution.
          </p>

          <div className="space-y-4">
            <div>
              <label htmlFor="traceId" className="block text-sm font-medium text-gray-700 mb-2">
                Trace ID or Thread ID
              </label>
              <div className="flex gap-4">
                <input
                  id="traceId"
                  type="text"
                  value={traceId}
                  onChange={(e) => setTraceId(e.target.value)}
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  placeholder="Enter trace ID or thread ID"
                />
                <button
                  onClick={handleSearch}
                  disabled={loading || !traceId.trim()}
                  className="bg-primary-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-primary-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? 'Searching...' : 'Search'}
                </button>
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800">
                <strong>Note:</strong> Trace inspection requires LangSmith API integration. 
                Traces are automatically logged when LANGSMITH_API_KEY is configured.
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
