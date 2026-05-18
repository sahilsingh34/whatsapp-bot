# Project Memory & Work History

## Current State
The backend infrastructure is fully operational locally and prepared for deployment to Railway. The database is initialized via Alembic on Supabase, and the Redis cache is securely connected via Upstash. The AI is fully capable of multi-language processing and follows strict clinic guidelines.

## Recent Fixes & Milestones

### 1. Database Connectivity (Supabase + Asyncpg)
*   **Issue:** Supabase uses PgBouncer for its connection pooling (Port 6543). When `asyncpg` tries to use prepared statements, it crashes with a `DuplicatePreparedStatementError` or throws transactional errors because PgBouncer in transaction mode does not support them well.
*   **Fix:** Added `?prepared_statement_cache_size=0` to the database URL in `.env` and modified `app/database/connection.py` to explicitly set `connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}` in the SQLAlchemy `create_async_engine()`.

### 2. Redis Authentication
*   **Issue:** The FastAPI server crashed on startup (`invalid username-password pair` and `SSL: WRONG_VERSION_NUMBER`).
*   **Fix:** Verified that the Upstash database was a standard connection (not TLS). Updated `.env` to use the non-TLS protocol `redis://` and passed the correct exact password with the username `default` (e.g., `redis://default:<password>@<host>:<port>`).

### 3. AI Persona & Prompt Engineering
*   **Multi-Language / Hinglish Bug:** The Llama-3.3 model would auto-translate "Hinglish" text (Hindi written in English letters) into Devanagari script (हिंदी) automatically.
*   **Fix:** Added a `CRITICAL` tag to the system prompt explicitly telling the AI: "If the patient uses Hinglish, you MUST reply in Hinglish. DO NOT reply in Devanagari script unless the patient uses Devanagari script first."
*   **Pricing Bug:** The bot was offering exact prices upfront, stopping patients from consulting doctors.
*   **Fix:** Instructed the AI to NEVER offer prices directly and to ALWAYS push for a Rs.499 doctor consultation first, only revealing prices if the user strictly demands it.

### 4. Development Workflow
*   **Demo UI:** Built a local HTML/JS mock WhatsApp interface at `http://localhost:8000/demo` to allow the user to test the AI's logic without needing Meta API verification or webhook tunnels.
*   **Deployment Setup:** Created a `Procfile` containing `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT` and pushed to GitHub for seamless 1-click deploy to Railway.app.

## Next Action Items
1.  Verify Meta Webhook configuration using the live Railway URL.
2.  Begin building the Admin Dashboard (React/Next.js) to connect to Supabase and view the `appointments` table that the AI is generating.
