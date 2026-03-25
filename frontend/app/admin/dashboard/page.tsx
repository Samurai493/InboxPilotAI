'use client'

import { useEffect, useState } from 'react'

interface Metrics {
  total_threads: number
  successful_threads: number
  failed_threads: number
  average_confidence: number | null
  total_reviews: number
  pending_reviews: number
  approved_reviews: number
  rejected_reviews: number
}

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchMetrics()
    // Refresh every 30 seconds
    const interval = setInterval(fetchMetrics, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchMetrics = async () => {
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${API_BASE_URL}/api/v1/metrics/summary`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setMetrics(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load metrics')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 py-12">
        <div className="container mx-auto px-4 max-w-6xl">
          <div className="bg-white rounded-lg shadow-lg p-8 text-center">
            <p className="text-gray-600">Loading metrics...</p>
          </div>
        </div>
      </main>
    )
  }

  if (error || !metrics) {
    return (
      <main className="min-h-screen bg-gray-50 py-12">
        <div className="container mx-auto px-4 max-w-6xl">
          <div className="bg-white rounded-lg shadow-lg p-8">
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error || 'Failed to load metrics'}
            </div>
          </div>
        </div>
      </main>
    )
  }

  const successRate = metrics.total_threads > 0
    ? (metrics.successful_threads / metrics.total_threads * 100).toFixed(1)
    : '0.0'

  return (
    <main className="min-h-screen bg-gray-50 py-12">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Admin Dashboard</h1>
          <p className="text-gray-600">Quality metrics and system overview</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Total Threads"
            value={metrics.total_threads}
            subtitle={`${metrics.successful_threads} successful, ${metrics.failed_threads} failed`}
            color="blue"
          />
          <MetricCard
            title="Success Rate"
            value={`${successRate}%`}
            subtitle={`${metrics.successful_threads} / ${metrics.total_threads}`}
            color="green"
          />
          <MetricCard
            title="Avg Confidence"
            value={metrics.average_confidence !== null ? `${(metrics.average_confidence * 100).toFixed(1)}%` : 'N/A'}
            subtitle="Across all drafts"
            color="yellow"
          />
          <MetricCard
            title="Pending Reviews"
            value={metrics.pending_reviews}
            subtitle={`${metrics.approved_reviews} approved, ${metrics.rejected_reviews} rejected`}
            color="red"
          />
        </div>

        <div className="bg-white rounded-lg shadow-lg p-8">
          <h2 className="text-2xl font-semibold text-gray-900 mb-6">Review Queue Status</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center p-4 bg-gray-50 rounded-lg">
              <span className="font-medium text-gray-700">Total Reviews</span>
              <span className="text-2xl font-bold text-gray-900">{metrics.total_reviews}</span>
            </div>
            <div className="flex justify-between items-center p-4 bg-yellow-50 rounded-lg">
              <span className="font-medium text-gray-700">Pending</span>
              <span className="text-2xl font-bold text-yellow-600">{metrics.pending_reviews}</span>
            </div>
            <div className="flex justify-between items-center p-4 bg-green-50 rounded-lg">
              <span className="font-medium text-gray-700">Approved</span>
              <span className="text-2xl font-bold text-green-600">{metrics.approved_reviews}</span>
            </div>
            <div className="flex justify-between items-center p-4 bg-red-50 rounded-lg">
              <span className="font-medium text-gray-700">Rejected</span>
              <span className="text-2xl font-bold text-red-600">{metrics.rejected_reviews}</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

function MetricCard({
  title,
  value,
  subtitle,
  color,
}: {
  title: string
  value: string | number
  subtitle: string
  color: 'blue' | 'green' | 'yellow' | 'red'
}) {
  const colorClasses = {
    blue: 'bg-blue-50 border-blue-200 text-blue-900',
    green: 'bg-green-50 border-green-200 text-green-900',
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-900',
    red: 'bg-red-50 border-red-200 text-red-900',
  }

  return (
    <div className={`bg-white rounded-lg shadow-lg p-6 border-2 ${colorClasses[color]}`}>
      <h3 className="text-sm font-medium mb-2">{title}</h3>
      <p className="text-3xl font-bold mb-1">{value}</p>
      <p className="text-sm opacity-75">{subtitle}</p>
    </div>
  )
}
