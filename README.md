# 🏥 My Pain Clinic Global — AI WhatsApp Assistant

AI-powered WhatsApp assistant for **My Pain Clinic Global, Bandra** that automatically responds to patient queries during non-working hours.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Groq](https://img.shields.io/badge/LLM-Groq--Llama3.3-orange)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)

---

## ✨ Features

- 🤖 **AI Auto-Reply (Groq Engine)** — Superfast context-aware responses during non-working hours powered by Groq
- 🧠 **Intelligent Auto-Selector Router** — Automatically routes queries to Llama 3.1 8B (general queries) or Llama 3.3 70B (complex medical questions)
- 🧬 **Database Resilience** — Automatic pg connection health pre-pings and recycling to prevent pool socket timeouts
- 🧠 **Conversation Memory** — Remembers chat context (last 20 messages, 30-day retention)
- 📅 **Appointment Capture** — Collects patient name, pain type, preferred date/time
- 🚨 **Emergency Escalation** — Detects urgent keywords and notifies clinic staff via WhatsApp
- ⏰ **Time-Based Routing** — AI handles after-hours; staff acknowledgment during working hours
- 🔐 **Secure** — Webhook verification, API key auth, environment variable protection
- 📊 **Admin API & UI** — Dynamic spreadsheet dashboard displaying patient conversations and auto-routing badges

---

## 🏗 Architecture

```
WhatsApp User → Meta Cloud API → FastAPI Webhook → Message Handler
                                                        ↓
                                              ┌─────────┼─────────┐
                                              ↓         ↓         ↓
                                         Time Check  AI Router  Memory
                                              ↓         ↓         ↓
                                         Staff Reply  Groq Llama  PostgreSQL
                                                      (3.1/3.3)   + Redis
                                                        ↓
                                              ┌─────────┼─────────┐
                                              ↓                   ↓
                                        Appointment          Escalation
                                         Capture             + Staff Alert
                                              ↓
                                        WhatsApp Reply → Patient
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Meta WhatsApp Business API account
- OpenAI API key

### 1. Clone & Configure

```bash
git clone <your-repo-url>
cd whatsapp-bot-mpc

# Copy and edit environment variables
cp .env.example .env
# Edit .env with your actual API keys
```

### 2. Start Services

```bash
docker compose up --build
```

This starts:
- **FastAPI app** on `http://localhost:8000`
- **PostgreSQL** on port `5432`
- **Redis** on port `6379`

### 3. Setup Webhook

1. Go to [Meta Developer Dashboard](https://developers.facebook.com)
2. Navigate to your WhatsApp Business app → Webhooks
3. Set webhook URL: `https://your-domain.com/webhook`
4. Set verify token: (same as `VERIFY_TOKEN` in your `.env`)
5. Subscribe to `messages` field

**For local development**, use [ngrok](https://ngrok.com):
```bash
ngrok http 8000
# Use the HTTPS URL as your webhook URL
```

### 4. Verify

```bash
# Health check
curl http://localhost:8000/health

# Should return:
# {"status": "healthy", "services": {"database": "connected", "redis": "connected"}}
```

---

## 📁 Project Structure

```
project/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Settings from environment
│   ├── database/
│   │   ├── connection.py     # Async PostgreSQL (SQLAlchemy)
│   │   └── redis.py          # Async Redis client
│   ├── models/
│   │   ├── user.py           # Patient records
│   │   ├── conversation.py   # Chat history
│   │   ├── appointment.py    # Appointment leads
│   │   └── escalation.py     # Urgent case tracking
│   ├── services/
│   │   ├── whatsapp_service.py    # Meta API communication
│   │   ├── ai_service.py         # GPT-4.1 mini integration
│   │   ├── memory_service.py     # Conversation memory (Redis + PG)
│   │   ├── appointment_service.py # Appointment extraction & CRUD
│   │   ├── escalation_service.py  # Urgent case detection & alerts
│   │   └── message_handler.py    # Main orchestrator
│   ├── routes/
│   │   ├── webhook.py        # WhatsApp webhook endpoints
│   │   ├── health.py         # Health check
│   │   └── appointments.py   # Admin appointment API
│   └── utils/
│       ├── time_utils.py     # Working hours logic (IST)
│       └── security.py       # Auth & verification
├── alembic/                  # Database migrations
├── tests/                    # Unit tests
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/` | Service info | None |
| `GET` | `/health` | Health check | None |
| `GET` | `/webhook` | Meta verification | Verify Token |
| `POST` | `/webhook` | Receive messages | Meta Webhook |
| `GET` | `/api/appointments` | List appointments | API Key |
| `GET` | `/api/appointments/{id}` | Get appointment | API Key |
| `PATCH` | `/api/appointments/{id}` | Update status | API Key |

### Admin API Usage

```bash
# List pending appointments
curl -H "X-API-Key: your-admin-key" http://localhost:8000/api/appointments?status=pending

# Confirm an appointment
curl -X PATCH \
  -H "X-API-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmed"}' \
  http://localhost:8000/api/appointments/<uuid>
```

---

## ⏰ Working Hours Logic

| Time | Day | Behavior |
|------|-----|----------|
| 9 AM – 9 PM | Mon–Sat | Staff acknowledgment message |
| 9 PM – 9 AM | Mon–Sat | AI auto-reply |
| All day | Sunday | AI auto-reply |

---

## 🧪 Running Tests

```bash
# Inside Docker
docker compose exec app pytest tests/ -v

# Locally (with venv)
pip install -r requirements.txt
pytest tests/ -v
```

---

## 🚢 Production Deployment

### Render (Recommended Free Tier)

1. Push code to GitHub
2. Create a new **Web Service** on Render
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env.example`
6. Use **Supabase** for PostgreSQL and **Upstash** for Redis

### Environment Variables

See [.env.example](.env.example) for all required variables.

---

## 📝 License

Private — My Pain Clinic Global
