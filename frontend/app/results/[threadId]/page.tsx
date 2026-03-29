'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { AppNav } from '@/components/AppNav'
import { getThreadState } from '@/lib/api'
import { loadCachedThreadState } from '@/lib/thread-state-cache'
import { WorkflowKnowledgeViz } from '@/components/WorkflowKnowledgeViz'
import type { KgEntity, KgRelation } from '@/components/WorkflowKnowledgeViz'

interface LlmTokenCall {
  run_id?: string | null
  name?: string | null
  tags?: unknown
  model?: string | null
  input_tokens?: number
  output_tokens?: number
  total_tokens?: number
}

interface LlmTokenUsage {
  totals?: {
    input_tokens?: number
    output_tokens?: number
    total_tokens?: number
    llm_calls?: number
  }
  calls?: LlmTokenCall[]
}

interface ThreadState {
  thread_id: string
  state: {
    intent?: string
    urgency_score?: string
    selected_agent?: string
    orchestration_rationale?: string
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
    audit_log?: Array<Record<string, unknown>>
    knowledge_hits?: { entities?: KgEntity[]; relations?: KgRelation[] }
    knowledge_written?: { entities?: KgEntity[]; relations?: KgRelation[] }
    email_context?: string | null
    email_summary?: string | null
    email_substance?: string | null
    sender_request?: string | null
    response_thinking?: string | null
    follow_ups?: string[] | null
    llm_token_usage?: LlmTokenUsage | null
  } | null
  status: string
}

export default function ResultsPage() {
  const params = useParams()
  const threadId = params.threadId as string
  const [threadState, setThreadState] = useState<ThreadState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stateLoadSource, setStateLoadSource] = useState<string | null>(null)

  const loadThread = useCallback(async () => {
    if (!threadId) return
    setLoading(true)
    setError(null)
    try {
      const result = await getThreadState(threadId)
      if (result.state) {
        setStateLoadSource(result.source ?? null)
        setThreadState({
          thread_id: result.thread_id,
          state: result.state as ThreadState['state'],
          status: result.status,
        })
      } else {
        setStateLoadSource(null)
        const cached = loadCachedThreadState(threadId)
        setThreadState(
          cached
            ? { thread_id: threadId, state: cached as ThreadState['state'], status: 'found' }
            : {
                thread_id: result.thread_id,
                state: null,
                status: result.status,
              },
        )
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load thread')
    } finally {
      setLoading(false)
    }
  }, [threadId])

  useEffect(() => {
    void loadThread()
  }, [loadThread])

  if (loading) {
    return (
      <>
        <AppNav layout="compact" />
        <main className="min-h-screen bg-gray-50 py-12">
          <div className="container mx-auto max-w-4xl px-4">
            <div className="rounded-lg bg-white p-8 text-center shadow-lg">
              <p className="text-gray-600">Loading results…</p>
            </div>
          </div>
        </main>
      </>
    )
  }

  if (error || !threadState) {
    return (
      <>
        <AppNav layout="compact" />
        <main className="min-h-screen bg-gray-50 py-12">
          <div className="container mx-auto max-w-4xl px-4">
            <div className="rounded-lg bg-white p-8 shadow-lg">
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
                {error || 'Thread not found'}
              </div>
              <button
                type="button"
                onClick={() => void loadThread()}
                className="mt-4 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700"
              >
                Retry
              </button>
            </div>
          </div>
        </main>
      </>
    )
  }

  if (!threadState.state) {
    return (
      <>
        <AppNav layout="compact" />
        <main className="min-h-screen bg-gray-50 py-12">
          <div className="container mx-auto max-w-4xl px-4">
            <div className="rounded-lg bg-white p-8 shadow-lg">
              <p className="text-gray-700">
                No workflow state found for this thread. The server may have restarted (in-memory
                checkpointer), or this id is invalid. If you enabled database persistence, ensure the API
                can reach Postgres and that this thread was saved after a run.
              </p>
              <p className="mt-2 text-sm text-gray-500">Thread ID: {threadId}</p>
              <button
                type="button"
                onClick={() => void loadThread()}
                className="mt-4 rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-800 hover:bg-gray-50"
              >
                Retry load
              </button>
            </div>
          </div>
        </main>
      </>
    )
  }

  const state = threadState.state

  return (
    <>
      <AppNav layout="compact" />
      <main className="min-h-screen bg-gray-50 py-12">
      <div className="container mx-auto max-w-4xl space-y-6 px-4">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">Processing Results</h1>
          <p className="text-gray-600">Thread ID: {threadId}</p>
          {stateLoadSource === 'database' ? (
            <p className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
              Loaded from saved history (database snapshot). No additional LLM calls were made.
            </p>
          ) : null}
        </div>

        {state.llm_token_usage?.totals ? (
          <div className="bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">LLM token usage (this run)</h2>
            <p className="text-sm text-gray-600 mb-4">
              Summed across every chat-model call in the workflow (classification, synthesis, routing,
              draft, extract, scoring, etc.). Provider-reported counts when available.
            </p>
            {(() => {
              const t = state.llm_token_usage!.totals!
              const calls = state.llm_token_usage?.calls?.length ?? 0
              const hasCounts =
                (t.input_tokens ?? 0) > 0 || (t.output_tokens ?? 0) > 0 || (t.total_tokens ?? 0) > 0
              return (
                <>
                  <div className="flex flex-wrap gap-4">
                    <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
                      <div className="text-xs font-medium uppercase tracking-wide text-gray-500">
                        Input tokens
                      </div>
                      <div className="text-2xl font-semibold text-gray-900">{t.input_tokens ?? 0}</div>
                    </div>
                    <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
                      <div className="text-xs font-medium uppercase tracking-wide text-gray-500">
                        Output tokens
                      </div>
                      <div className="text-2xl font-semibold text-gray-900">{t.output_tokens ?? 0}</div>
                    </div>
                    <div className="rounded-lg border border-primary-200 bg-primary-50 px-4 py-3">
                      <div className="text-xs font-medium uppercase tracking-wide text-primary-800">
                        Total tokens
                      </div>
                      <div className="text-2xl font-semibold text-primary-900">
                        {t.total_tokens ?? (t.input_tokens ?? 0) + (t.output_tokens ?? 0)}
                      </div>
                    </div>
                    <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
                      <div className="text-xs font-medium uppercase tracking-wide text-gray-500">
                        LLM calls counted
                      </div>
                      <div className="text-2xl font-semibold text-gray-900">
                        {t.llm_calls ?? calls}
                      </div>
                    </div>
                  </div>
                  {!hasCounts && calls === 0 ? (
                    <p className="mt-4 text-sm text-amber-800">
                      No usage metadata was returned by the provider for this run. If you expected
                      counts, check your LangChain / provider versions and tracing settings.
                    </p>
                  ) : null}
                  {state.llm_token_usage?.calls && state.llm_token_usage.calls.length > 0 ? (
                    <details className="mt-6">
                      <summary className="cursor-pointer text-sm font-semibold text-gray-800">
                        Per-call breakdown
                      </summary>
                      <ul className="mt-3 space-y-2 text-sm text-gray-700">
                        {state.llm_token_usage.calls.map((c, i) => (
                          <li
                            key={c.run_id ?? i}
                            className="rounded border border-gray-100 bg-gray-50/80 px-3 py-2"
                          >
                            <span className="font-medium">
                              #{i + 1}
                              {c.model ? ` · ${c.model}` : ''}
                              {c.name ? ` · ${String(c.name)}` : ''}
                            </span>
                            <span className="ml-2 text-gray-600">
                              in {c.input_tokens ?? 0} / out {c.output_tokens ?? 0} / total{' '}
                              {c.total_tokens ?? (c.input_tokens ?? 0) + (c.output_tokens ?? 0)}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  ) : null}
                </>
              )
            })()}
          </div>
        ) : null}

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
              {state.selected_agent && (
                <div>
                  <span className="font-medium text-gray-700">Orchestration agent: </span>
                  <span className="px-3 py-1 bg-slate-100 text-slate-800 rounded-full text-sm font-semibold">
                    {state.selected_agent}
                  </span>
                </div>
              )}
              {state.orchestration_rationale && (
                <p className="text-sm text-gray-600 mt-2">
                  <span className="font-medium text-gray-700">Rationale: </span>
                  {state.orchestration_rationale}
                </p>
              )}
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

        {/* KG-backed synthesis (feeds drafts) */}
        {(state.email_summary ||
          state.email_substance ||
          state.sender_request ||
          state.response_thinking ||
          state.email_context ||
          (state.follow_ups && state.follow_ups.length > 0)) && (
          <div className="bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Email summary</h2>
            <p className="text-sm text-gray-600 mb-6">
              Synthesized from the message, your preferences, and knowledge-graph context. This block also feeds draft
              generation.
            </p>
            {state.email_summary ? (
              <div className="mb-5">
                <h3 className="text-sm font-semibold text-gray-800">At a glance</h3>
                <p className="mt-1 text-gray-800 font-medium">{state.email_summary}</p>
              </div>
            ) : null}
            {state.email_substance ? (
              <div className="mb-5">
                <h3 className="text-sm font-semibold text-gray-800">What the email contains</h3>
                <p className="mt-1 text-gray-700 whitespace-pre-wrap">{state.email_substance}</p>
              </div>
            ) : null}
            {state.sender_request ? (
              <div className="mb-5">
                <h3 className="text-sm font-semibold text-gray-800">What they&apos;re asking for</h3>
                <p className="mt-1 text-gray-700 whitespace-pre-wrap">{state.sender_request}</p>
              </div>
            ) : null}
            {state.response_thinking ? (
              <div className="mb-5">
                <h3 className="text-sm font-semibold text-gray-800">Thought process for the reply</h3>
                <p className="mt-1 text-gray-700 whitespace-pre-wrap">{state.response_thinking}</p>
              </div>
            ) : null}
            {state.email_context ? (
              <div className="mb-5">
                <h3 className="text-sm font-semibold text-gray-800">Memory &amp; graph context</h3>
                <p className="mt-1 text-gray-700 whitespace-pre-wrap">{state.email_context}</p>
              </div>
            ) : null}
            {state.follow_ups && state.follow_ups.length > 0 ? (
              <div>
                <h3 className="text-sm font-semibold text-gray-800">Suggested follow-ups</h3>
                <ul className="mt-2 list-disc pl-5 text-gray-700 space-y-1">
                  {state.follow_ups.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        )}

        <WorkflowKnowledgeViz
          auditLog={state.audit_log}
          knowledgeHits={state.knowledge_hits ?? null}
          knowledgeWritten={state.knowledge_written ?? null}
          selectedAgent={state.selected_agent ?? null}
        />

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
        <div className="rounded-lg bg-white p-8 shadow-lg">
          <div className="flex flex-wrap gap-4">
            <Link
              href="/"
              className="rounded-lg border border-gray-300 px-6 py-3 font-semibold text-gray-800 transition-colors hover:bg-gray-50"
            >
              Back to inbox
            </Link>
            <Link
              href="/inbox"
              className="rounded-lg bg-primary-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-primary-700"
            >
              Paste another message
            </Link>
          </div>
        </div>
      </div>
    </main>
    </>
  )
}
