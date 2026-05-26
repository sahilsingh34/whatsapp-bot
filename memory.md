# Project Memory & Work History

## Current State
The backend infrastructure is fully operational locally and prepared for deployment to Railway. The database is initialized via Alembic on Supabase, and the Redis cache is securely connected via Upstash. The AI receptionist (Priya) is converted to a highly responsive, **general inquiry-only assistant** to keep operations simple. The admin dashboard is clean, fast, and completely free of obsolete booking statistics, status badges, filters, and JS exceptions.

---

## 🏆 Recent Milestones & Enhancements (This Session)

### 1. General Inquiry Bot Conversion
*   **Feature:** Simplified `SYSTEM_PROMPT` in `ai_service.py` to remove proactive slot-checking, step-by-step patient info extraction, and the old `[APPOINTMENT_COLLECTED]` tags.
*   **Outcome:** 
    *   **Booking Redirection Protocol**: Priya acts as a warm, empathetic receptionist who handles all clinical inquiries but redirects bookings to the clinic's reception phone numbers (+91 81694 00907 / +91 81694 00903) or the website booking page.
    *   **Reduced Latency**: Bypassed live slot querying and website API integrations inside the message generation flow to optimize response time.

### 2. Streamlined Admin Panel & Dashboard (`/panel/`)
*   **Feature:** Simplified and cleaned the admin dashboard (`app/routes/dashboard_ui.py`).
*   **Outcome:**
    *   **Clean Visuals**: Removed booking stats counters ("Appointments" and "Pending") and the spreadsheet "Status" column to keep focus solely on patient communications.
    *   **Bypassed Legacy tabs & filters**: Removed the "Appointments" tab from the patient details drawer, rendering the live chat thread immediately. Removed "Pending/Confirmed" status filters to maximize space.
    *   **Bug & Performance Fixes**: Added the missing `<div class="stats-strip">` HTML container tag. Corrected a JavaScript syntax error (missing brace) in row selection, and removed dead/obsolete JS methods (`switchTab`, `setFilter`, `updateAppointmentStatus`) to prevent client-side runtime errors.

### 3. Unit Test Restoration & Green Suite
*   **Feature:** Diagnosed and fixed the missing `app/services/escalation_service.py` dependency that was breaking the pipeline.
*   **Outcome:** Created the missing service file, restoring all 27 unit tests to a 100% green, compiled, and successfully passing state.

### 4. Dynamic Phrasing & Conversational Intelligence Refinement
*   **Feature:** Configured strict rules for dynamic phrasing and high conversational variance inside `ai_service.py`'s `SYSTEM_PROMPT`.
*   **Outcome:** Priya now dynamically rotates and formats greetings, explanations, and booking redirections on every single response turn, making her chat highly natural and organic. Factual reference accuracy (telephone numbers, website) remains perfectly intact.

### 5. Conversational Self-Learning System (Preserved)
*   **Feature:** Maintained the asynchronous background-processing system (`app/services/learning_service.py`) that extracts patient-specific **Insights** (e.g., pain severity, topics) to dynamically personalize subsequent interactions.

---

## 🛠️ Past Fixes & Core Milestones

### 1. Database Connectivity (Supabase + Asyncpg)
*   **Issue:** Supabase uses PgBouncer for its connection pooling (Port 6543). When `asyncpg` tries to use prepared statements, it crashes with a `DuplicatePreparedStatementError`.
*   **Fix:** Added `?prepared_statement_cache_size=0` to the database URL in `.env` and modified `app/database/connection.py` to explicitly set `connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}` in the SQLAlchemy `create_async_engine()`.

### 2. Redis Authentication
*   **Issue:** The FastAPI server crashed on startup (`invalid username-password pair` and `SSL: WRONG_VERSION_NUMBER`).
*   **Fix:** Verified that the Upstash database was a standard connection (not TLS). Updated `.env` to use the non-TLS protocol `redis://` and passed the correct exact password with the username `default`.

---

## 🎯 Next Action Items
1.  **Staging Deployment**: Push changes to GitHub to trigger automatic re-deployment to Railway.app.
2.  **Verify Production Environment**: Ensure environment variables (`NVIDIA_API_KEY`, `REDIS_URL`, `DATABASE_URL`) are successfully configured on the production host.

