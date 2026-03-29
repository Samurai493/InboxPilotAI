'use client'

import { useState } from 'react'
import { AppNav } from '@/components/AppNav'
import { getApiBaseUrl } from '@/lib/app-settings'
import { getAuthHeaders } from '@/lib/api'

export default function TracesPage() {
  const [traceId, setTraceId] = useState('')
  const [loading, setLoading] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)

  const handleSearch = async () => {
    if (!traceId.trim()) return

    setLoading(true)
    setSearchError(null)
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/traces/${traceId.trim()}`, {
        credentials: 'include',
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
      setSearchError(err instanceof Error ? err.message : 'Failed to fetch trace')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <AppNav layout="compact" />
      <main className="min-h-screen bg-gray-50 py-12">
        <div className="container mx-auto max-w-4xl px-4">
          <div className="rounded-lg bg-white p-8 shadow-lg">
            <h1 className="mb-6 text-3xl font-bold text-gray-900">Trace inspector</h1>
            <p className="mb-8 text-gray-600">
              Search for traces by trace ID or thread ID to inspect graph execution.
            </p>

            <div className="space-y-4">
              <div>
                <label htmlFor="traceId" className="mb-2 block text-sm font-medium text-gray-700">
                  Trace ID or thread ID
                </label>
                <div className="flex flex-wrap gap-4">
                  <input
                    id="traceId"
                    type="text"
                    value={traceId}
                    onChange={(e) => setTraceId(e.target.value)}
                    className="min-w-[200px] flex-1 rounded-lg border border-gray-300 px-4 py-3 focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
                    placeholder="Enter trace ID or thread ID"
                    aria-invalid={!!searchError}
                    aria-describedby={searchError ? 'trace-search-error' : undefined}
                  />
                  <button
                    type="button"
                    onClick={() => void handleSearch()}
                    disabled={loading || !traceId.trim()}
                    className="rounded-lg bg-primary-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-primary-700 disabled:cursor-not-allowed disabled:bg-gray-400"
                  >
                    {loading ? 'Searching…' : 'Search'}
                  </button>
                </div>
              </div>

              {searchError ? (
                <div
                  id="trace-search-error"
                  role="alert"
                  className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
                >
                  {searchError}
                </div>
              ) : null}

              <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                <p className="text-sm text-blue-800">
                  <strong>Note:</strong> Trace inspection requires LangSmith API integration. Traces are
                  automatically logged when LANGSMITH_API_KEY is configured.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  )
}
