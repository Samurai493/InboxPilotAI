'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
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

  useEffect(() => {
    fetchReviews()
  }, [])

  const fetchReviews = async () => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/reviews/pending`, {
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
      setReviews(data.reviews || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reviews')
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async (reviewId: string, editedDraft?: string) => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/reviews/${reviewId}/approve`, {
        method: 'POST',
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
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      // Refresh reviews
      fetchReviews()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to approve review')
    }
  }

  const handleReject = async (reviewId: string, reason?: string) => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/reviews/${reviewId}/reject`, {
        method: 'POST',
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
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      // Refresh reviews
      fetchReviews()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to reject review')
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 py-12">
        <div className="container mx-auto px-4 max-w-6xl">
          <div className="bg-white rounded-lg shadow-lg p-8 text-center">
            <p className="text-gray-600">Loading reviews...</p>
          </div>
        </div>
      </main>
    )
  }

  if (error) {
    return (
      <main className="min-h-screen bg-gray-50 py-12">
        <div className="container mx-auto px-4 max-w-6xl">
          <div className="bg-white rounded-lg shadow-lg p-8">
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-gray-50 py-12">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Review Queue</h1>
          <p className="text-gray-600">
            {reviews.length} pending review{reviews.length !== 1 ? 's' : ''}
          </p>
        </div>

        {reviews.length === 0 ? (
          <div className="bg-white rounded-lg shadow-lg p-8 text-center">
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
      </div>
    </main>
  )
}

function ReviewCard({
  review,
  onApprove,
  onReject,
  onViewThread,
}: {
  review: Review
  onApprove: (id: string, editedDraft?: string) => void
  onReject: (id: string, reason?: string) => void
  onViewThread: () => void
}) {
  const [showEdit, setShowEdit] = useState(false)
  const [editedDraft, setEditedDraft] = useState(review.draft_reply)

  return (
    <div className="bg-white rounded-lg shadow-lg p-8">
      <div className="mb-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Review #{review.id.slice(0, 8)}
            </h2>
            <div className="flex gap-2 flex-wrap">
              {review.intent && (
                <span className="px-3 py-1 bg-primary-100 text-primary-800 rounded-full text-sm font-semibold">
                  {review.intent}
                </span>
              )}
              {review.confidence_score !== undefined && (
                <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-semibold">
                  Confidence: {(review.confidence_score * 100).toFixed(0)}%
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onViewThread}
            className="text-primary-600 hover:text-primary-700 font-semibold text-sm"
          >
            View Thread →
          </button>
        </div>

        {review.risk_flags && review.risk_flags.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <h3 className="font-semibold text-red-900 mb-2">Risk Flags:</h3>
            <ul className="list-disc list-inside text-red-800">
              {review.risk_flags.map((flag, idx) => (
                <li key={idx}>{flag}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="mb-6">
        <h3 className="font-semibold text-gray-900 mb-2">Draft Reply:</h3>
        {showEdit ? (
          <textarea
            value={editedDraft}
            onChange={(e) => setEditedDraft(e.target.value)}
            rows={10}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
          />
        ) : (
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <pre className="whitespace-pre-wrap text-gray-800 font-sans">
              {review.draft_reply}
            </pre>
          </div>
        )}
      </div>

      <div className="flex gap-4">
        <button
          onClick={() => {
            if (showEdit) {
              onApprove(review.id, editedDraft)
              setShowEdit(false)
            } else {
              onApprove(review.id)
            }
          }}
          className="bg-green-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-green-700 transition-colors"
        >
          {showEdit ? 'Approve Edited' : 'Approve'}
        </button>
        <button
          onClick={() => setShowEdit(!showEdit)}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
        >
          {showEdit ? 'Cancel Edit' : 'Edit'}
        </button>
        <button
          onClick={() => {
            const reason = prompt('Rejection reason (optional):')
            onReject(review.id, reason || undefined)
          }}
          className="bg-red-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-red-700 transition-colors"
        >
          Reject
        </button>
      </div>
    </div>
  )
}
