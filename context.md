# Project Context & Architecture

## System Overview
"My Pain Clinic Global" WhatsApp AI Assistant is an automated customer service and appointment booking system designed to interact with patients via Meta's WhatsApp API. It provides 24/7 support during non-working hours, answering queries regarding pain management, treatments, and pricing.

## Tech Stack
*   **Backend Framework:** FastAPI (Python 3.14)
*   **AI Engine:** NVIDIA NIM (`meta/llama-3.3-70b-instruct`) via OpenAI SDK
*   **Database:** PostgreSQL (Hosted on Supabase, connected via `asyncpg` and SQLAlchemy 2.0 using the Supabase Transaction Pooler port 6543)
*   **Memory/Caching:** Upstash Cloud Redis (Sync connection, used for storing conversation histories)
*   **Deployment:** Railway.app (via `Procfile`)

## Core Components
1.  **Webhook Router (`app/routes/webhook.py`):**
    *   Listens to incoming `POST` requests from Meta's WhatsApp API.
    *   Verifies Meta's `GET` requests using `VERIFY_TOKEN`.
    *   Extracts the phone number and message body from the JSON payload and sends it to the message handler.

2.  **Message Handler (`app/services/message_handler.py`):**
    *   The central orchestrator. Checks if the clinic is currently open (working hours). If open, sends a manual fallback message.
    *   If closed, it pulls the user's conversation history from Redis, passes the new message to the AI, and generates a response.
    *   Detects if the AI gathered appointment details or triggered an escalation.

3.  **AI Service (`app/services/ai_service.py`):**
    *   Contains the master `SYSTEM_PROMPT` containing all clinic knowledge (address, timings, doctors, services, prices).
    *   Enforces a strict **Multi-Language Protocol** (replies exactly in English, Hindi, Marathi, or Hinglish).
    *   Enforces a strict **Conciseness Protocol** (WhatsApp style texting: short 1-3 sentences, no AI robotic disclaimers, no upfront direct pricing).

4.  **Memory Service (`app/services/memory_service.py`):**
    *   Creates/fetches the `User` from PostgreSQL.
    *   Stores the latest 20 messages of conversation context in Upstash Redis so the AI remembers what was said previously.

5.  **Appointment Service (`app/services/appointment_service.py`):**
    *   Parses the AI's response for the `[APPOINTMENT_COLLECTED]{...}` JSON tag.
    *   Saves the extracted appointment (Name, Issue, Date, Time) into the PostgreSQL database for the clinic staff to view later.

6.  **Demo UI (`app/routes/demo.py`):**
    *   A web-based WhatsApp clone located at `http://localhost:8000/demo`.
    *   Bypasses Meta's API to allow safe local testing of the AI Prompt and Multi-language logic.

## Environment Variables Required
*   `WHATSAPP_TOKEN`: Meta API Bearer Token
*   `PHONE_NUMBER_ID`: Meta API Phone Number ID
*   `VERIFY_TOKEN`: Custom string for Meta Webhook setup
*   `NVIDIA_API_KEY`: NVIDIA NIM Token for Llama 3.3
*   `DATABASE_URL`: Supabase URL (requires `?prepared_statement_cache_size=0`)
*   `REDIS_URL`: Upstash Redis Connection String
