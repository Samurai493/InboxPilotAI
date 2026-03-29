'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { AppNav } from '@/components/AppNav'
import { getApiBaseUrl } from '@/lib/app-settings'
import { getAuthHeaders } from '@/lib/api'

interface HistoryEntry {
  checkpoint_id?: string
  values?: Record<string, unknown> | null
  metadata?: Record<string, unknown> | null
  parent_checkpoint_id?: string
}

interface ThreadHistory {
  thread_id: string
  history: HistoryEntry[]
  status: string
}

export default function ThreadTimelinePage() {
  const params = useParams()
  const threadId = params.threadId as string
  const [history, setHistory] = useState<ThreadHistory | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/api/v1/threads/${threadId}/history`, {
          method: 'GET',
          credentials: 'include',
          headers: {
            ...getAuthHeaders(),
            'Content-Type': 'application/json',
          },
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const data = await response.json()
        setHistory(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load history')
      } finally {
        setLoading(false)
      }
    }

    if (threadId) {
      fetchHistory()
    }
  }, [threadId])

  if (loading) {
    return (
      <>
        <AppNav layout="compact" />
        <main className="min-h-screen bg-gray-50 py-12">
          <div className="container mx-auto max-w-4xl px-4">
            <div className="rounded-lg bg-white p-8 text-center shadow-lg">
              <p className="text-gray-600">Loading timeline…</p>
            </div>
          </div>
        </main>
      </>
    )
  }

  if (error || !history) {
    return (
      <>
        <AppNav layout="compact" />
        <main className="min-h-screen bg-gray-50 py-12">
          <div className="container mx-auto max-w-4xl px-4">
            <div className="rounded-lg bg-white p-8 shadow-lg">
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
                {error || 'History not found'}
              </div>
            </div>
          </div>
        </main>
      </>
    )
  }

  return (
    <>
      <AppNav layout="compact" />
      <main className="min-h-screen bg-gray-50 py-12">
      <div className="container mx-auto max-w-4xl px-4">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">Thread Timeline</h1>
          <p className="text-gray-600 mb-8">Thread ID: {threadId}</p>

          {history.history.length === 0 ? (
            <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
              <p className="text-gray-600">No history available for this thread.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {history.history.map((entry, index) => (
                <div key={index} className="bg-gray-50 rounded-lg p-6 border border-gray-200">
                  <div className="mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">
                      Checkpoint {index + 1}
                    </h3>
                    {entry.checkpoint_id && (
                      <p className="text-sm text-gray-500">ID: {entry.checkpoint_id}</p>
                    )}
                  </div>

                  {entry.values && (
                    <div className="mb-4">
                      <h4 className="text-md font-medium text-gray-700 mb-2">State:</h4>
                      <div className="bg-white rounded p-4 border border-gray-200">
                        <pre className="text-xs text-gray-800 overflow-auto">
                          {JSON.stringify(entry.values, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}

                  {entry.metadata && (
                    <div>
                      <h4 className="text-md font-medium text-gray-700 mb-2">Metadata:</h4>
                      <div className="bg-white rounded p-4 border border-gray-200">
                        <pre className="text-xs text-gray-800 overflow-auto">
                          {JSON.stringify(entry.metadata, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="mt-8">
            <Link
              href={`/results/${encodeURIComponent(threadId)}`}
              className="font-semibold text-primary-600 hover:text-primary-700"
            >
              ← Back to results
            </Link>
          </div>
        </div>
      </div>
    </main>
    </>
  )
}
