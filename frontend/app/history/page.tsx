'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { getAuthHeaders, listWorkflowThreads } from '@/lib/api'
import type { WorkflowThreadSummary } from '@/lib/api'
import { getStoredUserId } from '@/lib/user-session'

export default function WorkflowHistoryPage() {
  const [threads, setThreads] = useState<WorkflowThreadSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    const uid = getStoredUserId()
    if (!uid || !getAuthHeaders().Authorization) {
      setError(
        'Sign in on the home page with Google (or complete session bootstrap) so your user id and auth token are available.',
      )
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await listWorkflowThreads(uid, 80)
      setThreads(res.threads)
    } catch (e) {
      setThreads([])
      setError(e instanceof Error ? e.message : 'Failed to load history')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <main className="min-h-screen bg-gray-50 py-10">
      <div className="container mx-auto max-w-3xl px-4">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-bold text-gray-900">Workflow history</h1>
          <Link
            href="/"
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
          >
            Back to inbox
          </Link>
        </div>
        <p className="mb-6 text-sm text-gray-600">
          Saved runs are stored in your database with the LangGraph thread id. Open a row to review
          drafts, tasks, and token usage without running the workflow again.
        </p>

        {loading ? (
          <p className="text-gray-600">Loading…</p>
        ) : error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {error}
          </div>
        ) : threads.length === 0 ? (
          <p className="text-gray-600">No saved workflows yet. Run InboxPilot on an email from the inbox.</p>
        ) : (
          <ul className="space-y-2">
            {threads.map((t) => (
              <li key={t.id}>
                <Link
                  href={`/results/${encodeURIComponent(t.thread_id)}`}
                  className="block rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition-colors hover:border-primary-300 hover:bg-primary-50/30"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="font-semibold text-gray-900">
                        {t.subject || '(no subject)'}
                      </div>
                      <div className="mt-1 text-xs text-gray-500">
                        {t.created_at ? new Date(t.created_at).toLocaleString() : ''}
                        {t.intent ? ` · ${t.intent}` : ''}
                        {t.selected_agent ? ` · ${t.selected_agent}` : ''}
                      </div>
                      <div className="mt-1 truncate font-mono text-xs text-gray-500">
                        Thread: {t.thread_id}
                      </div>
                      {t.gmail_message_id ? (
                        <div className="mt-0.5 truncate font-mono text-xs text-gray-400">
                          Gmail id: {t.gmail_message_id}
                        </div>
                      ) : null}
                    </div>
                    <span
                      className={[
                        'shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold',
                        t.status === 'completed'
                          ? 'bg-green-100 text-green-800'
                          : t.status === 'failed'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-gray-100 text-gray-700',
                      ].join(' ')}
                    >
                      {t.status}
                    </span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  )
}
