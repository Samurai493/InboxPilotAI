import { NextResponse } from 'next/server'

/**
 * Server-side snapshot of NEXT_PUBLIC_* for Settings autofill (reads frontend .env.local at runtime).
 * Does not expose a default user id (would aid cross-user targeting against the API).
 */
export async function GET() {
  return NextResponse.json({
    apiBaseUrl: process.env.NEXT_PUBLIC_API_URL?.trim() || '',
    googleClientId: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim() || '',
  })
}
