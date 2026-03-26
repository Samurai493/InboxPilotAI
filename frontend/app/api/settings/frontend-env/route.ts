import { NextResponse } from 'next/server'

/**
 * Server-side snapshot of NEXT_PUBLIC_* for Settings autofill (reads frontend .env.local at runtime).
 */
export async function GET() {
  return NextResponse.json({
    apiBaseUrl: process.env.NEXT_PUBLIC_API_URL?.trim() || '',
    googleClientId: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim() || '',
    defaultUserId: process.env.NEXT_PUBLIC_DEFAULT_USER_ID?.trim() || '',
  })
}
