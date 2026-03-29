/** @type {import('next').NextConfig} */
const isProd = process.env.NODE_ENV === 'production'
const nextConfig = {
  reactStrictMode: true,
  async headers() {
    // Production: drop unsafe-eval where Next allows (dev/HMR still needs eval).
    const scriptSrc = isProd
      ? "script-src 'self' 'unsafe-inline' https://accounts.google.com https://apis.google.com"
      : "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com https://apis.google.com"
    const csp = [
      "default-src 'self'",
      scriptSrc,
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https:",
      "connect-src 'self' http://127.0.0.1:8000 http://localhost:8000 http://127.0.0.1:3000 http://localhost:3000 http://127.0.0.1:3001 http://localhost:3001 http://127.0.0.1:3002 http://localhost:3002 https:",
      "frame-src https://accounts.google.com",
      "frame-ancestors 'none'",
      "base-uri 'self'",
    ].join('; ')
    return [
      {
        source: '/:path*',
        headers: [{ key: 'Content-Security-Policy', value: csp }],
      },
    ]
  },
}

module.exports = nextConfig
