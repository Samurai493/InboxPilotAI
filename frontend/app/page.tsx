'use client'

import Link from 'next/link'

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            InboxPilot AI
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Transform your messy inbox into structured, reviewable workflows
          </p>
          <p className="text-lg text-gray-500 mb-12">
            Powered by LangGraph • Classify • Draft • Extract • Review
          </p>
          
          <div className="flex gap-4 justify-center">
            <Link
              href="/inbox"
              className="bg-primary-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-primary-700 transition-colors"
            >
              Get Started
            </Link>
            <Link
              href="/inbox"
              className="border-2 border-primary-600 text-primary-600 px-8 py-3 rounded-lg font-semibold hover:bg-primary-50 transition-colors"
            >
              Try Demo
            </Link>
          </div>

          <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-xl font-semibold mb-3">Classify</h3>
              <p className="text-gray-600">
                Automatically classify incoming messages by intent and urgency
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-xl font-semibold mb-3">Draft</h3>
              <p className="text-gray-600">
                Generate context-aware reply drafts tailored to each message type
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-xl font-semibold mb-3">Extract</h3>
              <p className="text-gray-600">
                Identify action items, deadlines, and tasks automatically
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
