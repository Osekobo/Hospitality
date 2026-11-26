# Admin dashboard

React + Vite admin interface for the Social-First AI Concierge API.

## Setup

Requirements: Node.js 20.19+ or 22.12+.

```bash
npm install
copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux
npm run dev
```

The backend must be running on the origin configured below. The current development setup uses port `8001`:

```bash
cd ../backend
python -m uvicorn main:app --reload --port 8001
```

## Configuration

`frontend/.env`:

```dotenv
VITE_API_URL=http://localhost:8001
VITE_ADMIN_API_TOKEN=
VITE_DEFAULT_LOCALE=en
```

- `VITE_API_URL`: backend origin. Use `http://localhost:8001` for the current local setup. Change it if you run the backend on another port.
- `VITE_ADMIN_API_TOKEN`: must match the backend `ADMIN_API_TOKEN` when that token is configured. The frontend sends it as `X-Admin-Token`; leave empty if the backend token is empty.
- `VITE_DEFAULT_LOCALE`: `en` or `sw`.

The backend must allow this origin in `CORS_ORIGINS`. Development default is `http://localhost:5173`; preview uses `http://localhost:4173`.

## Features

- Operations overview with payment, booking, guest and conversion metrics.
- Accessible booking filters and payment tables.
- Guest conversation list with live polling and agent replies from `/admin/chats` and `/admin/chats/{user_id}/reply`.
- English/Kiswahili language switcher and Kenya-specific currency/date formatting.
- API health status, loading/error states, keyboard navigation and mobile layout.
- No direct booking creation: bookings originate from WhatsApp, SMS, USSD or the concierge flow.

## Commands

```bash
npm run dev
npm run lint
npm run build
npm run preview
```

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Conversations list is empty | `VITE_API_URL` should be `http://localhost:8001`; backend `ADMIN_API_TOKEN` and `VITE_ADMIN_API_TOKEN` must match. |
| API health shows offline | Start the backend on port `8001` or update `VITE_API_URL`. |
| CORS error in browser console | Add the frontend origin to backend `CORS_ORIGINS`, then restart the backend. |
| Build fails on Node version | Use Node.js 20.19+ or 22.12+. |
