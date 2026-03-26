# InboxPilot AI Frontend

Next.js 14 frontend for InboxPilot AI.

## Prerequisites

- Node.js 18+
- A running backend API (default `http://localhost:8000`) — see the [root README](../README.md#backend-server)

## Install and run

```bash
npm install
npm run dev
```

Open the URL printed in the terminal (often [http://localhost:3000](http://localhost:3000); Next.js may use another port if 3000 is busy).

## Environment variables

Create `frontend/.env.local`:

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes (for real API) | Backend base URL, e.g. `http://localhost:8000` |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Recommended | Google OAuth **Web client** ID (same as `GOOGLE_CLIENT_ID` in the backend). Used for Google Sign-In (JWT to the backend). If omitted, the app may still read the client ID from `GET /api/v1/auth/config` when the backend exposes it. |

Example:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

Optional:

```bash
# If you need a fixed user UUID without signing in (debug only)
# NEXT_PUBLIC_DEFAULT_USER_ID=...
```

## Features tied to the backend

- **Google Sign-In** + **Gmail**: Configure Google OAuth on the backend (`GOOGLE_*`, `FRONTEND_URL`, `SECRET_KEY`) and allow your frontend origin in Google Cloud **Authorized JavaScript origins** and the backend redirect URI in **Authorized redirect URIs**. Details are in the root README.

## Build

```bash
npm run build
npm start
```
