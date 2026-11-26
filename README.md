# Social-First AI Concierge

A full-stack hospitality operations app for capturing guest inquiries from WhatsApp, Instagram, SMS and USSD, turning them into bookings, collecting M-Pesa deposits, and giving staff one dashboard for conversations, reservations and payments.

## What is included

- **FastAPI backend** with PostgreSQL persistence and SQLAlchemy models for users, guest messages, bookings, properties and M-Pesa transactions.
- **Channel webhooks** for Meta WhatsApp/Instagram, Africa's Talking SMS/USSD, and an MTN-style USSD guide endpoint.
- **AI concierge flow** with intent detection, property/date validation, booking creation and guarded M-Pesa STK Push requests.
- **M-Pesa integration** with STK Push initiation, callback signature-free validation, amount/phone reconciliation, idempotent transaction handling and one-time airtime rewards.
- **Admin API** for dashboard metrics, booking/user/chat/property lists, and sending a human reply in a guest conversation.
- **React admin dashboard** with English/Swiss-English-style localisation (English and Kiswahili), Kenyan currency/date formatting, accessible tables, filters, live chat polling, API health status and mobile navigation.
- **Smoke tests** covering configuration, webhook signatures, admin replies and M-Pesa callback reconciliation.

## Architecture

```text
hospitality/
  backend/
    app entrypoint, config, database models, routers, services and tests
  frontend/
    React + Vite admin dashboard
```

The backend is the source of truth. The frontend reads from the admin and payment endpoints; it does not create bookings directly.

## Backend setup

Requirements: Python 3.11+, PostgreSQL.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env` and set at least:

```dotenv
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/hospitality_db
ADMIN_API_TOKEN=replace-with-a-long-random-token
ENVIRONMENT=development
```

Create the database in PostgreSQL, then start the API:

```bash
uvicorn main:app --reload --port 8000
```

Tables are created on startup with `Base.metadata.create_all`, then idempotent migrations add missing columns and safe unique indexes to existing databases. When `DEMO_MODE=true`, sample users, properties, bookings, chats and M-Pesa transactions are seeded.

Interactive API docs are available at `http://localhost:8000/docs`.

## Frontend setup

Requirements: Node.js 20.19+ or 22.12+.

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Set `VITE_API_URL` to the backend origin, normally `http://localhost:8000`. If `ADMIN_API_TOKEN` is configured on the backend, set the same value as `VITE_ADMIN_API_TOKEN`; the frontend sends it as the `X-Admin-Token` header.

Useful commands:

```bash
npm run lint
npm run build
npm run preview
```

## Configuration highlights

All backend settings are read from environment variables or `backend/.env`. See `backend/.env.example` for the complete list.

### Required in production

When `ENVIRONMENT=production` or `staging`, startup fails unless these are set:

- `ADMIN_API_TOKEN`
- `META_APP_SECRET`

### Channel credentials

- Meta: `META_APP_SECRET`, `META_VERIFY_TOKEN`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_PAGE_ID`
- Africa's Talking: `AT_USERNAME`, `AT_API_KEY`, `AT_SENDER_ID`, `AT_USSD_SERVICE_CODE`, `AT_WEBHOOK_SECRET`
- M-Pesa: `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_SHORTCODE`, `MPESA_PASSKEY`, `MPESA_CALLBACK_URL`

`MPESA_CALLBACK_URL` must end in `/mpesa/callback` when M-Pesa credentials are configured. It must be publicly reachable for callbacks; during development use a tunnel such as ngrok.

### AI and enrichment

- `AI_PROVIDER=none|openai|gemini`
- `OPENAI_API_KEY`, `OPENAI_MODEL`, `GEMINI_API_KEY`, `GEMINI_MODEL`
- `GOOGLE_PLACES_API_KEY`, `OPENWEATHER_API_KEY`, `DEFAULT_CITY`

The concierge still handles structured booking/payment flows when AI is disabled.

## Main endpoints

### Public

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Service metadata |
| `GET` | `/health` | API and database health |
| `POST` | `/` | Africa's Talking USSD entry point |
| `GET/POST` | `/webhooks/meta`, `/webhooks/whatsapp`, `/webhooks/instagram` | Meta webhook verification and events |
| `POST` | `/webhooks/at/sms`, `/webhooks/at/ussd` | Africa's Talking callbacks |
| `POST` | `/ussd` | Guided USSD booking flow |
| `POST` | `/mpesa/callback` | M-Pesa payment confirmation |

### Protected with `X-Admin-Token`

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/admin/stats` | Dashboard metrics and trends |
| `GET` | `/admin/bookings` | Bookings list |
| `GET` | `/admin/users` | Guests list |
| `GET` | `/admin/chats` | Conversation history |
| `POST` | `/admin/chats/{user_id}/reply` | Send an agent reply |
| `GET` | `/admin/properties` | Properties list |
| `POST` | `/chat/message` | Send a channel message |
| `GET` | `/chat/sessions` | Chat sessions |
| `POST` | `/stk-push` | Request an M-Pesa STK Push |
| `GET` | `/status/{checkout_request_id}` | Query STK status |
| `GET` | `/mpesa/transactions` | Payment transactions |

## Tests

```bash
cd backend
python -m pytest -q tests
```

The tests override `DATABASE_URL` with a temporary SQLite database, so they do not touch the configured PostgreSQL database. Production runtime still uses PostgreSQL.

## Security notes

- Never commit `.env` files or real API credentials.
- Rotate any credentials that were previously committed or shared in plain text.
- Keep webhook secrets configured so callback signatures are verified.
- Keep `ADMIN_API_TOKEN` configured outside development and set frontend origins explicitly in `CORS_ORIGINS`.
