'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { getThreadState } from '@/lib/api'

interface ThreadState {
  thread_id: string
  state: {
    intent?: string
    urgency_score?: string
    draft_reply?: string
    extracted_tasks?: Array<{
      description: string
      due_date?: string
      priority?: string
    }>
    sender_profile?: {
      email?: string
      name?: string
      subject?: string
    }
    final_status?: string
  }
  status: string
}

export default function ResultsPage() {
  const params = useParams()
  const threadId = params.threadId as string
  const [threadState, setThreadState] = useState<ThreadState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchThread = async () => {
      try {
        const result = await getThreadState(threadId)
        setThreadState(result)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load thread')
      } finally {
        setLoading(false)
      }
    }

    if (threadId) {
      fetchThread()
    }
  }, [threadId])

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 py-12">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="bg-white rounded-lg shadow-lg p-8 text-center">
            <p className="text-gray-600">Loading results...</p>
          </div>
        </div>
      </main>
    )
  }

  if (error || !threadState) {
    return (
      <main className="min-h-screen bg-gray-50 py-12">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="bg-white rounded-lg shadow-lg p-8">
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error || 'Thread not found'}
            </div>
          </div>
        </div>
      </main>
    )
  }

  const state = threadState.state

  return (
    <main className="min-h-screen bg-gray-50 py-12">
      <div className="container mx-auto px-4 max-w-4xl space-y-6">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">Processing Results</h1>
          <p className="text-gray-600">Thread ID: {threadId}</p>
        </div>

        {/* Classification */}
        {state.intent && (
          <div className="bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Classification</h2>
            <div className="space-y-2">
              <div>
                <span className="font-medium text-gray-700">Intent: </span>
                <span className="px-3 py-1 bg-primary-100 text-primary-800 rounded-full text-sm font-semibold">
                  {state.intent}
                </span>
              </div>
              {state.urgency_score && (
                <div>
                  <span className="font-medium text-gray-700">Urgency: </span>
                  <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-semibold">
                    {state.urgency_score}
                  </span>
                </div>
              )}
              {state.sender_profile && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <p className="text-sm text-gray-600">
                    <strong>From:</strong> {state.sender_profile.name || state.sender_profile.email || 'Unknown'}
                  </p>
                  {state.sender_profile.subject && (
                    <p className="text-sm text-gray-600">
                      <strong>Subject:</strong> {state.sender_profile.subject}
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Draft Reply */}
        {state.draft_reply && (
          <div className="bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Draft Reply</h2>
            <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
              <pre className="whitespace-pre-wrap text-gray-800 font-sans">
                {state.draft_reply}
              </pre>
            </div>
          </div>
        )}

        {/* Extracted Tasks */}
        {state.extracted_tasks && state.extracted_tasks.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Extracted Tasks</h2>
            <div className="space-y-4">
              {state.extracted_tasks.map((task, index) => (
                <div key={index} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <p className="text-gray-800 mb-2">{task.description}</p>
                  <div className="flex gap-4 text-sm text-gray-600">
                    {task.priority && (
                      <span>
                        Priority: <span className="font-semibold">{task.priority}</span>
                      </span>
                    )}
                    {task.due_date && (
                      <span>
                        Due: <span className="font-semibold">{task.due_date}</span>
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* No tasks message */}
        {state.extracted_tasks && state.extracted_tasks.length === 0 && (
          <div className="bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Extracted Tasks</h2>
            <p className="text-gray-600">No tasks were extracted from this message.</p>
          </div>
        )}

        {/* Actions */}
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="flex gap-4">
            <a
              href="/inbox"
              className="bg-primary-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-primary-700 transition-colors"
            >
              Process Another Message
            </a>
          </div>
        </div>
      </div>
    </main>
  )
}
