# Admin dashboard

React + Vite admin interface for the Social-First AI Concierge API.

## Setup

```bash
npm install
cp .env.example .env
npm run dev
```

Configuration:

- `VITE_API_URL`: backend origin, normally `http://localhost:8000`.
- `VITE_ADMIN_API_TOKEN`: optional admin token sent as `X-Admin-Token` when the backend requires it.
- `VITE_DEFAULT_LOCALE`: `en` or `sw`.

## Features

- Operations overview with payment, booking, guest and conversion metrics.
- Accessible booking filters and payment tables.
- Guest conversation list with polling and agent replies.
- English/Kiswahili language switcher and Kenya-specific formatting.
- API health status, loading/error states, keyboard navigation and mobile layout.

## Commands

```bash
npm run dev
npm run lint
npm run build
npm run preview
```
