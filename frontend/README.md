# AI Workbench Frontend

This project provides the dashboard UI for the AI Workbench platform. It offers a three-panel operations dashboard, environment & model settings screens and WebSocket-powered live updates.

## Prerequisites

- Node.js 20+
- npm 10+
- Running backend that exposes the REST and WebSocket endpoints used in `src/lib/api.ts`

## Getting started

```bash
cd frontend
npm install
npm run dev
```

The development server starts on [http://localhost:5173](http://localhost:5173). The Vite dev server is configured with a proxy that forwards API requests to the backend running on port 8000. You can optionally override the backend URL via `VITE_API_BASE_URL` and the WebSocket endpoint via `VITE_WS_URL` by creating a `.env` file in this directory:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/jobs
```

**Note:** When running in development mode (via `npm run dev`), the proxy configuration in `vite.config.ts` handles routing `/api`, `/jobs`, `/tasks`, `/health`, and `/ws` requests to the backend at `http://localhost:8000`.

## Available scripts

- `npm run dev` – start the Vite development server with hot module replacement.
- `npm run build` – type-check and generate an optimized production build.
- `npm run preview` – locally preview the production build after running `npm run build`.
- `npm run lint` – run ESLint across the codebase.

## Architecture overview

- **React + TypeScript + Vite** for the application shell.
- **Tailwind CSS** with a dark-first theme for styling.
- **@tanstack/react-query** for data fetching, caching, and optimistic updates.
- **WebSocket** integration (see `useJobEvents`) for real-time job status updates.
- **Headless UI Tabs** on the settings page for the Environment and Model sections.

Core directories:

- `src/pages` – top-level pages (Dashboard, Settings).
- `src/components` – reusable UI, dashboard widgets, and settings forms.
- `src/lib` – API client and React Query configuration.
- `src/hooks` – shared hooks including WebSocket listeners.

## Backend integration

The frontend consumes the REST API paths defined in `src/lib/api.ts` and automatically derives the WebSocket endpoint. When running in development mode, requests are proxied through the Vite dev server to the backend on port 8000. Live job updates are merged into the React Query cache so the queue stays in sync with backend events.

## Testing checklist

Before shipping changes, verify the following:

- `npm run dev` starts without runtime errors.
- Settings → Environment correctly loads and saves variables.
- Settings → Models shows available providers and persists changes.
- Dashboard connects to the WebSocket endpoint (status pill shows "Live updates").
- New jobs can be created from the dashboard form and appear in the queue.
- The file browser panel lists backend artifacts and folders.

