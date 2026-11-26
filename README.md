# Social-First AI Concierge

A full-stack hospitality operations app for capturing guest inquiries from WhatsApp, Instagram, SMS and USSD, turning them into bookings, collecting M-Pesa deposits, and giving staff one dashboard for conversations, reservations and payments.

## What is included

- **FastAPI backend** with PostgreSQL persistence and SQLAlchemy models for users, guest messages, bookings, properties and M-Pesa transactions.
- **Channel webhooks**:
  - Meta WhatsApp/Instagram: `/webhooks/meta`, `/webhooks/whatsapp`, `/webhooks/instagram`.
  - Africa's Talking SMS: `/webhooks/at/sms`.
  - Africa's Talking customer USSD booking/payment flow: `/ussd` and `/webhooks/at/ussd`.
  - Guide portal USSD: `/guide/ussd` and legacy `POST /`.
- **AI concierge flow** with intent detection, property/date validation, booking creation and guarded M-Pesa STK Push requests.
- **M-Pesa integration** with STK Push initiation, public callback, amount/phone reconciliation, idempotent transaction handling and one-time airtime rewards.
- **Admin API** for dashboard metrics, booking/user/chat/property lists, and sending a human reply in a guest conversation.
- **React admin dashboard** with English/Kiswahili localisation, Kenyan currency/date formatting, accessible tables, filters, live chat polling, API health status and mobile navigation.
- **Smoke tests** covering configuration, webhook signatures, admin replies, USSD booking and M-Pesa callback reconciliation.

## Architecture

```text
hospitality/
  backend/
    FastAPI app, config, database models, routers, services and tests
  frontend/
    React + Vite admin dashboard
```

The backend is the source of truth. The frontend reads from the admin and payment endpoints; it does not create bookings directly.

## Quick start

### 1. Backend

Requirements: Python 3.11+, PostgreSQL.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux
```

Edit `backend/.env`. Minimum local configuration:

```dotenv
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/hospitality_db
ADMIN_API_TOKEN=replace-with-a-long-random-token
ENVIRONMENT=development
DEMO_MODE=true
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173
```

Create the `hospitality_db` database in PostgreSQL, then start the API on port `8001`:

```bash
python -m uvicorn main:app --reload --port 8001
```

Interactive API docs: `http://localhost:8001/docs`.

Tables are created on startup with `Base.metadata.create_all`, then idempotent migrations add missing columns and safe unique indexes to existing databases. When `DEMO_MODE=true`, sample users, properties, bookings, chats and M-Pesa transactions are seeded.

> If you choose a different backend port, update `VITE_API_URL` in the frontend and any CORS/tunnel URLs to match.

### 2. Frontend

Requirements: Node.js 20.19+ or 22.12+.

```bash
cd frontend
npm install
copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux
npm run dev
```

`frontend/.env` should contain:

```dotenv
VITE_API_URL=http://localhost:8001
VITE_ADMIN_API_TOKEN=replace-with-the-same-token-as-the-backend
```

If `ADMIN_API_TOKEN` is empty on the backend, `VITE_ADMIN_API_TOKEN` can stay empty. If it is configured, both values must match; the frontend sends it as `X-Admin-Token`.

Useful frontend commands:

```bash
npm run lint
npm run build
npm run preview
```

## Configuration highlights

All backend settings are read from environment variables or `backend/.env`. See `backend/.env.example` for the complete list.

Settings are cached at import time. After changing `.env`, restart the backend.

### Required in production

When `ENVIRONMENT=production` or `staging`, startup fails unless these are set:

- `ADMIN_API_TOKEN`
- `META_APP_SECRET`

In `development`, an invalid Meta webhook signature is accepted with a warning so local testing is easy. Production and staging always verify signatures.

### Database and API

- `DATABASE_URL`: PostgreSQL connection string; runtime data lives here.
- `ENVIRONMENT`: `development`, `staging` or `production`.
- `DEMO_MODE`: seeds demo data when `true`.
- `ADMIN_API_TOKEN`: protects admin/chat/payment-management endpoints.
- `CORS_ORIGINS`: comma-separated frontend origins. Include both `http://localhost:5173` and `http://localhost:4173` for dev and preview.

### Meta / WhatsApp

- `META_APP_SECRET`: used for webhook signature verification.
- `META_VERIFY_TOKEN`: the token you enter in the Meta webhook setup screen.
- `META_API_VERSION`: currently `v21.0`; it is supported until January 2027.
- `WHATSAPP_ACCESS_TOKEN`: temporary API Setup token; regenerate and restart when it expires.
- `WHATSAPP_PHONE_NUMBER_ID`: the WhatsApp number used to send replies.
- `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_PAGE_ID`.

#### Meta webhook setup

1. Start a public tunnel to the backend, for example:

   ```bash
   ngrok http 8001
   ```

2. In Meta App Dashboard → Webhooks → WhatsApp Business Account, set the callback URL to:

   ```text
   https://YOUR-TUNNEL-HOST/webhooks/whatsapp
   ```

3. Set the verify token to the same value as `META_VERIFY_TOKEN`.
4. Subscribe the `messages` field. The dashboard may offer `v27.0`; that is fine and does not require changing `META_API_VERSION`.
5. Click **Test** → **Send to server**. A successful test produces `POST /webhooks/whatsapp` with HTTP `200`.
6. **Critical:** subscribe the app to the WhatsApp Business Account. Configuring only the app-level webhook is not enough; without this step, messages arrive but outgoing replies are not delivered.

   ```bash
   curl -X POST \
     "https://graph.facebook.com/v21.0/WABA_ID/subscribed_apps" \
     -d "access_token=WHATSAPP_ACCESS_TOKEN" \
     -d "subscribed_fields=messages"
   ```

   Expected response:

   ```json
   {"success": true}
   ```

   Verify with:

   ```bash
   curl "https://graph.facebook.com/v21.0/WABA_ID/subscribed_apps?access_token=WHATSAPP_ACCESS_TOKEN"
   ```

   Your app must appear in that list.

If the app is in Development mode, only added testers/test numbers can exchange real messages. Publish the app for production access.

### Africa's Talking

- `AT_USERNAME`: usually `sandbox` in development.
- `AT_API_KEY`, `AT_SENDER_ID`.
- `AT_SANDBOX`: `true` in sandbox.
- `AT_USSD_SERVICE_CODE`: default `*389#`.
- `AT_WEBHOOK_SECRET`: optional callback secret.

Endpoints:

- SMS callback: `POST /webhooks/at/sms`.
- Customer USSD callback: `POST /ussd` or `POST /webhooks/at/ussd`. Both run the same booking/payment flow.
- Guide portal: `POST /guide/ussd`; legacy `POST /` also opens the guide portal.

If your simulator still shows `CON Welcome to the Guide Portal`, it is posting to `/` or `/guide/ussd`. Point it at `/ussd` (or `/webhooks/at/ussd`) for the guest booking flow.

### M-Pesa

- `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`.
- `MPESA_SHORTCODE`, `MPESA_PASSKEY`.
- `MPESA_TRANSACTION_TYPE`: default `CustomerPayBillOnline`.
- `MPESA_CALLBACK_URL`: must be publicly reachable and end with `/mpesa/callback`.
- `MPESA_SANDBOX`: `true` for sandbox.
- `REWARD_AIRTIME_AMOUNT`: optional one-time reward after successful payment.

Phone numbers are normalized to M-Pesa MSISDN format (`2547...`) before STK Push. The USSD and chat booking flows request a 50% deposit; callbacks reconcile amount and phone, then mark the transaction Paid and send the appropriate guest message.

### AI and enrichment

- `AI_PROVIDER=none|openai|gemini`.
- `OPENAI_API_KEY`, `OPENAI_MODEL`.
- `GEMINI_API_KEY`, `GEMINI_MODEL`.

Current working Gemini model: `gemini-3.5-flash-lite`. Older `gemini-2.0-flash` has been retired and returns `404`.

The concierge still handles structured booking/payment flows when AI is disabled or unavailable.

- `GOOGLE_PLACES_API_KEY`, `OPENWEATHER_API_KEY`, `DEFAULT_CITY` add optional property/weather enrichment.

## USSD guest booking flow

Dial `*389#` (or send the equivalent simulated text). The customer flow is:

| Input | Result |
| --- | --- |
| `""` | Main menu: My bookings / Book a stay / Help / Exit |
| `1` | List the guest's bookings |
| `2` | List available properties |
| `2*1` | Ask for check-in date in `DDMMYYYY` |
| `2*1*27062027` | Ask for check-out date in `DDMMYYYY` |
| `2*1*27062027*29062027` | Ask for guests, `1-20` |
| `2*1*27062027*29062027*2` | Show price summary and `1. Confirm and pay` |
| `...*1` | Create Pending booking + Pending transaction, then trigger M-Pesa STK Push |

Example summary response:

```text
CON Maasai Oasis Camp
2027-06-27 to 2027-06-29 - 2 guests
Total KES 19,600. Deposit KES 9,800
1. Confirm and pay
2. Choose another property
0. Cancel
```

A cancelled STK Push is recorded as `Failed` with `ResultCode 1032`. The user must approve the prompt on their phone for payment to complete.

## Main endpoints

### Public

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Service metadata |
| `GET` | `/health` | API and database health |
| `POST` | `/` | Legacy guide portal USSD entry point |
| `GET/POST` | `/webhooks/meta`, `/webhooks/whatsapp`, `/webhooks/instagram` | Meta webhook verification and events |
| `POST` | `/webhooks/at/sms` | Africa's Talking SMS callback |
| `GET/POST` | `/webhooks/at/ussd` | Customer USSD booking/payment flow |
| `POST` | `/ussd` | Customer USSD booking/payment flow used by the simulator |
| `POST` | `/guide/ussd` | Guide portal USSD |
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
| `POST` | `/mpesa/stk-push` | Request an M-Pesa STK Push |
| `GET` | `/mpesa/status/{checkout_request_id}` | Query STK status |
| `GET` | `/mpesa/transactions` | Payment transactions |

## Tests

```bash
cd backend
python -m pytest -q tests
```

Current suite: 10 smoke tests. Tests override `DATABASE_URL` with a temporary SQLite database, so they do not touch the configured PostgreSQL database. Production runtime still uses PostgreSQL.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| WhatsApp webhook shows HTTP `200` but no replies are delivered | App is not subscribed to the WABA. Run `POST /{WABA_ID}/subscribed_apps` with `subscribed_fields=messages`. |
| Meta dashboard shows "Not generated yet" for the token | Regenerate the temporary token, put it in `WHATSAPP_ACCESS_TOKEN`, restart the backend. |
| Gemini returns `404` model not found | Use `gemini-3.5-flash-lite`; `gemini-2.0-flash` is retired. |
| M-Pesa returns `400.002.02 Invalid PhoneNumber` | Phone must be `2547...`, not `+2547...`; normalization is built in. |
| Frontend conversations are empty | `VITE_API_URL` must be `http://localhost:8001`; `ADMIN_API_TOKEN` must match; frontend origin must be in `CORS_ORIGINS`. |
| USSD simulator shows Guide Portal | Point the callback to `/ussd` or `/webhooks/at/ussd`, not `/` or `/guide/ussd`. |
| Meta test event returns signature warning | Expected in `development`; production/staging enforces `META_APP_SECRET`. |

## Security notes

- Never commit `.env` files or real API credentials.
- Rotate any credentials that were previously committed or shared in plain text.
- Keep webhook secrets configured so callback signatures are verified in production.
- Keep `ADMIN_API_TOKEN` configured outside development and set frontend origins explicitly in `CORS_ORIGINS`.
- Meta API Setup tokens expire; treat them as short-lived development credentials.
