'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppNav } from '@/components/AppNav'
import { getApiBaseUrl } from '@/lib/app-settings'
import { getAuthHeaders } from '@/lib/api'

interface Review {
  id: string
  thread_id: string
  user_id: string
  draft_reply: string
  risk_flags?: string[]
  confidence_score?: number
  intent?: string
  status: string
  created_at: string
}

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<Review[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const fetchReviews = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/reviews/pending`, {
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
      setReviews(data.reviews || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reviews')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchReviews()
  }, [fetchReviews])

  const handleApprove = async (reviewId: string, editedDraft?: string) => {
    const response = await fetch(`${getApiBaseUrl()}/api/v1/reviews/${reviewId}/approve`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        approved: true,
        edited_draft: editedDraft || undefined,
      }),
    })

    if (!response.ok) {
      throw new Error(`Approve failed (HTTP ${response.status})`)
    }
    await fetchReviews()
  }

  const handleReject = async (reviewId: string, reason?: string) => {
    const response = await fetch(`${getApiBaseUrl()}/api/v1/reviews/${reviewId}/reject`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        approved: false,
        rejection_reason: reason || undefined,
      }),
    })

    if (!response.ok) {
      throw new Error(`Reject failed (HTTP ${response.status})`)
    }
    await fetchReviews()
  }

  return (
    <>
      <AppNav layout="compact" />
      <main className="min-h-screen bg-gray-50 py-12">
        <div className="container mx-auto max-w-6xl px-4">
          {loading ? (
            <div className="rounded-lg bg-white p-8 text-center shadow-lg">
              <p className="text-gray-600">Loading reviews…</p>
            </div>
          ) : error ? (
            <div className="rounded-lg bg-white p-8 shadow-lg">
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
                {error}
              </div>
              <button
                type="button"
                onClick={() => void fetchReviews()}
                className="mt-4 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700"
              >
                Retry
              </button>
            </div>
          ) : (
            <>
              <div className="mb-8">
                <h1 className="mb-2 text-3xl font-bold text-gray-900">Review queue</h1>
                <p className="text-gray-600">
                  {reviews.length} pending review{reviews.length !== 1 ? 's' : ''}
                </p>
              </div>

              {reviews.length === 0 ? (
                <div className="rounded-lg bg-white p-8 text-center shadow-lg">
                  <p className="text-gray-600">No pending reviews. Great job!</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {reviews.map((review) => (
                    <ReviewCard
                      key={review.id}
                      review={review}
                      onApprove={handleApprove}
                      onReject={handleReject}
                      onViewThread={() => router.push(`/results/${review.thread_id}`)}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </>
  )
}

function ReviewCard({
  review,
  onApprove,
  onReject,
  onViewThread,
}: {
  review: Review
  onApprove: (id: string, editedDraft?: string) => Promise<void>
  onReject: (id: string, reason?: string) => Promise<void>
  onViewThread: () => void
}) {
  const [showEdit, setShowEdit] = useState(false)
  const [editedDraft, setEditedDraft] = useState(review.draft_reply)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const runAction = async (fn: () => Promise<void>) => {
    setBusy(true)
    setActionError(null)
    try {
      await fn()
      setRejectOpen(false)
      setRejectReason('')
      setShowEdit(false)
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rounded-lg bg-white p-8 shadow-lg">
      {actionError ? (
        <div
          role="alert"
          className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
        >
          {actionError}
        </div>
      ) : null}

      <div className="mb-6">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="mb-2 text-xl font-semibold text-gray-900">
              Review #{review.id.slice(0, 8)}
            </h2>
            <div className="flex flex-wrap gap-2">
              {review.intent ? (
                <span className="rounded-full bg-primary-100 px-3 py-1 text-sm font-semibold text-primary-800">
                  {review.intent}
                </span>
              ) : null}
              {review.confidence_score !== undefined ? (
                <span className="rounded-full bg-yellow-100 px-3 py-1 text-sm font-semibold text-yellow-800">
                  Confidence: {(review.confidence_score * 100).toFixed(0)}%
                </span>
              ) : null}
            </div>
          </div>
          <button
            type="button"
            onClick={onViewThread}
            className="text-sm font-semibold text-primary-600 hover:text-primary-700"
          >
            View thread →
          </button>
        </div>

        {review.risk_flags && review.risk_flags.length > 0 ? (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
            <h3 className="mb-2 font-semibold text-red-900">Risk flags</h3>
            <ul className="list-inside list-disc text-red-800">
              {review.risk_flags.map((flag, idx) => (
                <li key={idx}>{flag}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>

      <div className="mb-6">
        <h3 className="mb-2 font-semibold text-gray-900">Draft reply</h3>
        {showEdit ? (
          <textarea
            value={editedDraft}
            onChange={(e) => setEditedDraft(e.target.value)}
            rows={10}
            className="w-full resize-none rounded-lg border border-gray-300 px-4 py-3 focus:ring-2 focus:ring-primary-500"
            disabled={busy}
            aria-label="Edited draft reply"
          />
        ) : (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <pre className="whitespace-pre-wrap font-sans text-gray-800">{review.draft_reply}</pre>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-4">
        <button
          type="button"
          disabled={busy}
          onClick={() =>
            void runAction(async () => {
              if (showEdit) {
                await onApprove(review.id, editedDraft)
              } else {
                await onApprove(review.id)
              }
            })
          }
          className="rounded-lg bg-green-600 px-6 py-2 font-semibold text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {showEdit ? 'Approve edited' : 'Approve'}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => setShowEdit(!showEdit)}
          className="rounded-lg bg-blue-600 px-6 py-2 font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {showEdit ? 'Cancel edit' : 'Edit'}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            setRejectReason('')
            setRejectOpen(true)
          }}
          className="rounded-lg bg-red-600 px-6 py-2 font-semibold text-white transition-colors hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Reject
        </button>
      </div>

      {rejectOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="reject-dialog-title"
          onClick={() => {
            if (!busy) {
              setRejectOpen(false)
              setRejectReason('')
            }
          }}
        >
          <div
            className="flex max-h-[90vh] w-full max-w-lg flex-col overflow-hidden rounded-xl bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-gray-200 px-4 py-3">
              <h2 id="reject-dialog-title" className="text-lg font-semibold text-gray-900">
                Reject review
              </h2>
              <p className="mt-1 text-sm text-gray-600">
                Optional note for the audit log (visible to your team).
              </p>
            </div>
            <div className="p-4">
              <label htmlFor="reject-reason" className="text-sm font-medium text-gray-800">
                Reason
              </label>
              <textarea
                id="reject-reason"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                rows={4}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"
                placeholder="Why is this draft being rejected?"
                disabled={busy}
              />
            </div>
            <div className="flex justify-end gap-2 border-t border-gray-100 px-4 py-3">
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setRejectOpen(false)
                  setRejectReason('')
                }}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void runAction(async () => onReject(review.id, rejectReason.trim() || undefined))}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60"
              >
                {busy ? 'Submitting…' : 'Confirm reject'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
