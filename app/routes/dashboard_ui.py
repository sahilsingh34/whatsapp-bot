"""
Dashboard UI — Admin panel for viewing customer conversations.
Spreadsheet-style view of all patient interactions with the bot.
Designed following Impeccable design principles:
- OKLCH color space, no purple gradients
- Outfit font (not Inter), proper typographic scale
- Intentional whitespace and vertical rhythm
- No nested cards, no gradient text
"""

import logging
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/panel", tags=["panel"])
logger = logging.getLogger(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MPC Dashboard — Customer Conversations</title>
    <meta name="description" content="Admin dashboard for My Pain Clinic Global WhatsApp bot conversations">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        /* ---- Reset & Foundation ---- */
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        :root {
            /* OKLCH Light/White Theme — premium paper aesthetic */
            --surface-0: oklch(0.98 0.005 240);    /* Clean white background */
            --surface-1: oklch(0.96 0.008 240);    /* Soft cream/light-gray for panels */
            --surface-2: oklch(0.92 0.012 240);    /* Slightly deeper tone for cards/headers */
            --surface-3: oklch(0.87 0.015 240);    /* Extra depth for active items/inputs */
            --surface-hover: oklch(0.94 0.01 240); /* Interactive hover */

            --text-primary: oklch(0.25 0.02 240);   /* Deep slate primary text */
            --text-secondary: oklch(0.45 0.02 240); /* Cool slate secondary text */
            --text-muted: oklch(0.60 0.015 240);    /* Clean gray for labels */

            --accent: oklch(0.55 0.15 160);         /* Premium emerald accent */
            --accent-dim: oklch(0.93 0.04 160);     /* Soft pastel accent background */
            --accent-text: oklch(0.25 0.08 160);    /* Deep accent text */

            --warn: oklch(0.65 0.14 65);
            --danger: oklch(0.58 0.16 25);
            --success: oklch(0.55 0.15 145);
            --info: oklch(0.55 0.12 240);

            --border: oklch(0.88 0.01 240);         /* Clean light border */
            --border-subtle: oklch(0.94 0.008 240);  /* Soft separator */

            /* Typography Scale — 1.2 ratio */
            --font-sans: 'Outfit', system-ui, -apple-system, sans-serif;
            --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

            --text-xs: 0.694rem;
            --text-sm: 0.833rem;
            --text-base: 1rem;
            --text-lg: 1.2rem;
            --text-xl: 1.44rem;
            --text-2xl: 1.728rem;
            --text-3xl: 2.074rem;

            /* Spacing — 4px base */
            --space-1: 4px;
            --space-2: 8px;
            --space-3: 12px;
            --space-4: 16px;
            --space-5: 20px;
            --space-6: 24px;
            --space-8: 32px;
            --space-10: 40px;
            --space-12: 48px;

            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 14px;
        }

        body {
            font-family: var(--font-sans);
            font-size: var(--text-base);
            line-height: 1.5;
            color: var(--text-primary);
            background: var(--surface-0);
            -webkit-font-smoothing: antialiased;
            overflow: hidden; /* Avoid whole body scroll */
        }

        /* ---- Layout ---- */
        .app {
            display: grid;
            grid-template-rows: auto auto 1fr; /* Explicitly define heights for topbar, stats-strip, and main */
            height: 100vh; /* Contain strictly within viewport */
            overflow: hidden;
        }

        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--space-4) var(--space-8);
            background: var(--surface-1);
            border-bottom: 1px solid var(--border-subtle);
            z-index: 100;
        }

        .topbar-left {
            display: flex;
            align-items: center;
            gap: var(--space-4);
        }

        .topbar h1 {
            font-size: var(--text-lg);
            font-weight: 600;
            letter-spacing: -0.01em;
        }

        .topbar-badge {
            font-size: var(--text-xs);
            font-weight: 500;
            padding: var(--space-1) var(--space-3);
            background: var(--accent-dim);
            color: var(--accent);
            border-radius: 999px;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .topbar-right {
            display: flex;
            align-items: center;
            gap: var(--space-4);
        }

        .topbar-link {
            font-size: var(--text-sm);
            color: var(--text-secondary);
            text-decoration: none;
            padding: var(--space-2) var(--space-3);
            border-radius: var(--radius-sm);
            transition: color 0.15s, background 0.15s;
        }

        .topbar-link:hover {
            color: var(--text-primary);
            background: var(--surface-2);
        }

        /* ---- Stats Strip ---- */
        .stats-strip {
            display: flex;
            gap: var(--space-4);
            padding: var(--space-5) var(--space-8);
            border-bottom: 1px solid var(--border-subtle);
            background: var(--surface-1);
            overflow-x: auto;
            flex-shrink: 0; /* Never shrink or stretch */
        }

        .stat-cell {
            flex: 1;
            min-width: 140px;
            max-height: 80px; /* Restrict height from stretching */
            padding: var(--space-3) var(--space-4);
            background: var(--surface-2);
            border-radius: var(--radius-md);
            border: 1px solid var(--border-subtle);
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .stat-label {
            font-size: var(--text-xs);
            font-weight: 500;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: var(--space-1);
        }

        .stat-value {
            font-size: var(--text-xl);
            font-weight: 700;
            letter-spacing: -0.02em;
            font-variant-numeric: tabular-nums;
        }

        .stat-value.accent { color: var(--accent); }
        .stat-value.warn { color: var(--warn); }
        .stat-value.info { color: var(--info); }

        /* ---- Main Content ---- */
        .main {
            display: grid;
            grid-template-columns: 1fr 420px;
            height: 100%;
            overflow: hidden;
        }

        /* ---- Table ---- */
        .table-area {
            overflow-y: auto;
            height: 100%;
            padding: 0 var(--space-8) var(--space-8) var(--space-8);
        }

        .table-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-top: var(--space-6);
            margin-bottom: var(--space-5);
        }

        .table-header h2 {
            font-size: var(--text-lg);
            font-weight: 600;
        }

        .search-box {
            display: flex;
            align-items: center;
            gap: var(--space-2);
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            padding: var(--space-2) var(--space-3);
        }

        .search-box svg {
            width: 16px;
            height: 16px;
            color: var(--text-muted);
            flex-shrink: 0;
        }

        .search-box input {
            background: none;
            border: none;
            outline: none;
            color: var(--text-primary);
            font-family: var(--font-sans);
            font-size: var(--text-sm);
            width: 200px;
        }

        .search-box input::placeholder { color: var(--text-muted); }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: var(--text-sm);
        }

        th {
            position: sticky;
            top: 0;
            z-index: 10;
            text-align: left;
            padding: var(--space-3) var(--space-4);
            background: var(--surface-2);
            color: var(--text-muted);
            font-weight: 500;
            font-size: var(--text-xs);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            border-bottom: 1px solid var(--border);
            white-space: nowrap;
            user-select: none;
        }

        th:first-child { border-radius: var(--radius-sm) 0 0 0; }
        th:last-child { border-radius: 0 var(--radius-sm) 0 0; }

        td {
            padding: var(--space-3) var(--space-4);
            border-bottom: 1px solid var(--border-subtle);
            vertical-align: middle;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        tr {
            cursor: pointer;
            transition: background 0.12s;
        }

        tr:hover td { background: var(--surface-hover); }
        tr.active td { background: var(--surface-2); }

        .name-cell {
            font-weight: 500;
            color: var(--text-primary);
        }

        .phone-cell {
            font-family: var(--font-mono);
            font-size: var(--text-xs);
            color: var(--text-secondary);
        }

        .count-cell {
            font-variant-numeric: tabular-nums;
            font-weight: 500;
        }

        .status-badge {
            display: inline-block;
            font-size: var(--text-xs);
            font-weight: 500;
            padding: 2px var(--space-2);
            border-radius: 999px;
            letter-spacing: 0.02em;
        }

        .status-badge.pending {
            background: oklch(0.94 0.04 65);
            color: var(--warn);
        }
        .status-badge.confirmed {
            background: oklch(0.92 0.04 145);
            color: var(--success);
        }
        .status-badge.none {
            background: var(--surface-3);
            color: var(--text-muted);
        }

        .topic-tag {
            display: inline-block;
            font-size: 10px;
            font-weight: 500;
            padding: 1px 6px;
            border-radius: 4px;
            background: var(--surface-3);
            color: var(--text-secondary);
            margin-right: 3px;
            margin-bottom: 2px;
            white-space: nowrap;
        }

        .topics-cell {
            max-width: 260px;
            white-space: normal;
            line-height: 1.8;
        }

        /* ---- Detail Panel ---- */
        .detail-panel {
            background: var(--surface-1);
            border-left: 1px solid var(--border-subtle);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            height: 100%;
            min-height: 0;
        }

        #detailContent {
            display: flex;
            flex-direction: column;
            height: 100%;
            min-height: 0;
            overflow: hidden;
        }

        .detail-header {
            padding: var(--space-5) var(--space-6);
            border-bottom: 1px solid var(--border-subtle);
            background: var(--surface-1);
            flex-shrink: 0;
        }

        .detail-header h3 {
            font-size: var(--text-base);
            font-weight: 600;
            margin-bottom: var(--space-1);
        }

        .detail-meta {
            font-size: var(--text-xs);
            color: var(--text-muted);
            font-family: var(--font-mono);
        }

        .detail-empty {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: var(--text-muted);
            font-size: var(--text-sm);
        }

        .thread {
            flex: 1;
            min-height: 0;
            overflow-y: auto;
            padding: var(--space-4) var(--space-6);
            display: flex;
            flex-direction: column;
            gap: var(--space-3);
            background: var(--surface-0);
        }

        .thread-msg {
            max-width: 85%;
            padding: var(--space-3) var(--space-4);
            border-radius: var(--radius-md);
            font-size: var(--text-sm);
            line-height: 1.55;
            word-wrap: break-word;
            position: relative;
        }

        .thread-msg.user {
            align-self: flex-end;
            background: oklch(0.92 0.04 145); /* Warm soft green for patient messages */
            color: oklch(0.25 0.08 145);
            border-bottom-right-radius: 4px;
        }

        .thread-msg.assistant {
            align-self: flex-start;
            background: var(--surface-2);
            color: var(--text-primary);
            border-bottom-left-radius: 4px;
            border: 1px solid var(--border-subtle);
        }

        .thread-time {
            font-size: 10px;
            color: var(--text-muted);
            margin-top: var(--space-1);
            text-align: right;
        }

        .thread-msg.user .thread-time { color: oklch(0.45 0.06 145); }

        /* ---- Loading / Empty ---- */
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: var(--space-12);
            color: var(--text-muted);
        }

        .spinner {
            width: 20px;
            height: 20px;
            border: 2px solid var(--border);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
            margin-right: var(--space-3);
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        .empty-state {
            text-align: center;
            padding: var(--space-12);
            color: var(--text-muted);
        }

        /* ---- Responsive ---- */
        @media (max-width: 900px) {
            .app {
                overflow: auto;
                height: auto;
            }
            .main {
                grid-template-columns: 1fr;
                height: auto;
                overflow: visible;
            }
            .detail-panel {
                border-left: none;
                border-top: 1px solid var(--border);
                height: 50vh;
            }
            .stats-strip {
                padding: var(--space-4);
                gap: var(--space-3);
            }
            .table-area {
                padding: var(--space-4);
                height: auto;
                overflow: visible;
            }
        }
    </style>
</head>
<body>
    <div class="app">
        <!-- Top Bar -->
        <div class="topbar">
            <div class="topbar-left">
                <h1>MPC Dashboard</h1>
                <span class="topbar-badge">Self-Learning AI</span>
            </div>
            <div class="topbar-right">
                <a href="/demo/" class="topbar-link">Demo Chat</a>
                <a href="/insights/" class="topbar-link">Learned Insights</a>
                <a href="/insights/stats" class="topbar-link">AI Stats</a>
                <a href="/docs" class="topbar-link">API Docs</a>
            </div>
        </div>

        <!-- Stats Strip -->
        <div class="stats-strip" id="statsStrip">
            <div class="stat-cell">
                <div class="stat-label">Customers</div>
                <div class="stat-value accent" id="statCustomers">—</div>
            </div>
            <div class="stat-cell">
                <div class="stat-label">Messages</div>
                <div class="stat-value" id="statMessages">—</div>
            </div>
            <div class="stat-cell">
                <div class="stat-label">Appointments</div>
                <div class="stat-value info" id="statAppointments">—</div>
            </div>
            <div class="stat-cell">
                <div class="stat-label">Pending</div>
                <div class="stat-value warn" id="statPending">—</div>
            </div>
            <div class="stat-cell">
                <div class="stat-label">Avg Msgs/Customer</div>
                <div class="stat-value" id="statAvg">—</div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="main">
            <!-- Table Area -->
            <div class="table-area">
                <div class="table-header">
                    <h2>Customer Conversations</h2>
                    <div class="search-box">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.45 4.39l4.26 4.26a.75.75 0 11-1.06 1.06l-4.26-4.26A7 7 0 012 9z" clip-rule="evenodd"/></svg>
                        <input type="text" id="searchInput" placeholder="Search by name or phone...">
                    </div>
                </div>
                <div id="tableContainer">
                    <div class="loading"><div class="spinner"></div>Loading conversations...</div>
                </div>
            </div>

            <!-- Detail Panel -->
            <div class="detail-panel">
                <div id="detailContent">
                    <div class="detail-empty">Select a customer to view their conversation</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let allConversations = [];
        let activeRow = null;
        let selectedUserId = null;

        // ---- Load Stats ----
        async function loadStats() {
            try {
                const res = await fetch('/dashboard/api/stats');
                const data = await res.json();
                document.getElementById('statCustomers').textContent = data.total_customers;
                document.getElementById('statMessages').textContent = data.total_messages;
                document.getElementById('statAppointments').textContent = data.total_appointments;
                document.getElementById('statPending').textContent = data.pending_appointments;
                document.getElementById('statAvg').textContent = data.avg_messages_per_customer;
            } catch (e) {
                console.error('Stats load failed:', e);
            }
        }

        // ---- Load Conversations ----
        async function loadConversations() {
            // 1. Initial Load from LocalStorage (Instant visual load)
            try {
                const cached = localStorage.getItem('mpc_conversations');
                if (cached) {
                    allConversations = JSON.parse(cached);
                    sortConversations();
                    renderTable(allConversations);
                }
            } catch (e) {
                console.error('Failed to load from localStorage cache:', e);
            }

            // 2. Fetch incremental updates from backend
            await syncConversations();
        }

        function sortConversations() {
            allConversations.sort((a, b) => {
                const timeA = a.updated_at || a.last_activity || "";
                const timeB = b.updated_at || b.last_activity || "";
                return timeB.localeCompare(timeA);
            });
        }

        async function syncConversations() {
            try {
                const lastSync = localStorage.getItem('mpc_last_sync') || '';
                let url = '/dashboard/api/conversations?limit=100';
                if (lastSync) {
                    url += `&updated_since=${encodeURIComponent(lastSync)}`;
                }

                const res = await fetch(url);
                const data = await res.json();
                const newConversations = data.conversations || [];

                if (newConversations.length > 0) {
                    // Merge new conversations into the existing list
                    const convMap = {};
                    allConversations.forEach(c => {
                        convMap[c.user_id] = c;
                    });

                    let maxUpdatedAt = lastSync;
                    newConversations.forEach(c => {
                        convMap[c.user_id] = c;
                        if (c.updated_at && (!maxUpdatedAt || c.updated_at > maxUpdatedAt)) {
                            maxUpdatedAt = c.updated_at;
                        }
                    });

                    allConversations = Object.values(convMap);
                    sortConversations();

                    // Save merged result
                    localStorage.setItem('mpc_conversations', JSON.stringify(allConversations));
                    if (maxUpdatedAt) {
                        localStorage.setItem('mpc_last_sync', maxUpdatedAt);
                    }

                    // Render table with the newly merged data
                    renderTable(allConversations);

                    // If a conversation is selected, update its details pane in real-time
                    if (selectedUserId) {
                        const updatedConvIndex = allConversations.findIndex(c => c.user_id === selectedUserId);
                        if (updatedConvIndex !== -1) {
                            selectRow(updatedConvIndex, null, false);
                        }
                    }
                } else if (allConversations.length === 0) {
                    // If no conversations found initially and cache was empty
                    document.getElementById('tableContainer').innerHTML =
                        '<div class="empty-state">No conversations found</div>';
                }

                // If this is the very first successful fetch, update the last sync time to protect future calls
                if (!lastSync && newConversations.length > 0) {
                    let maxTime = '';
                    newConversations.forEach(c => {
                        if (c.updated_at && (!maxTime || c.updated_at > maxTime)) {
                            maxTime = c.updated_at;
                        }
                    });
                    if (maxTime) {
                        localStorage.setItem('mpc_last_sync', maxTime);
                    } else {
                        localStorage.setItem('mpc_last_sync', new Date().toISOString());
                    }
                }
            } catch (e) {
                console.error('Incremental sync failed:', e);
                if (allConversations.length === 0) {
                    document.getElementById('tableContainer').innerHTML =
                        '<div class="empty-state">Failed to load conversations</div>';
                }
            }
        }

        // ---- Render Table ----
        function renderTable(conversations) {
            if (conversations.length === 0) {
                document.getElementById('tableContainer').innerHTML =
                    '<div class="empty-state">No conversations found</div>';
                return;
            }

            let html = `<table>
                <thead><tr>
                    <th>Customer</th>
                    <th>Phone</th>
                    <th>Messages</th>
                    <th>Status</th>
                    <th>Topics</th>
                    <th>Last Active</th>
                </tr></thead><tbody>`;

            conversations.forEach((conv, i) => {
                const statusClass = conv.appointment_status || 'none';
                const statusLabel = conv.appointment_status === 'none' ? 'No Appt' :
                    conv.appointment_status.charAt(0).toUpperCase() + conv.appointment_status.slice(1);

                const topics = (conv.key_topics || [])
                    .map(t => `<span class="topic-tag">${t}</span>`).join('');

                const isActive = selectedUserId === conv.user_id ? 'active' : '';

                html += `<tr data-index="${i}" data-id="${conv.user_id}" class="${isActive}" onclick="selectRow(${i}, this)">
                    <td class="name-cell">${escHtml(conv.patient_name || conv.name)}</td>
                    <td class="phone-cell">${escHtml(conv.phone)}</td>
                    <td class="count-cell">${conv.message_count}</td>
                    <td><span class="status-badge ${statusClass}">${statusLabel}</span></td>
                    <td class="topics-cell">${topics || '<span style="color:var(--text-muted)">—</span>'}</td>
                    <td style="color:var(--text-secondary)">${conv.last_activity}</td>
                </tr>`;
            });

            html += '</tbody></table>';
            document.getElementById('tableContainer').innerHTML = html;
        }

        // ---- Select Row ----
        function selectRow(index, rowEl, updateSelection = true) {
            const conv = allConversations[index];
            if (!conv) return;

            if (updateSelection) {
                selectedUserId = conv.user_id;
            }

            // Highlight
            if (activeRow) activeRow.classList.remove('active');
            
            // If rowEl is not provided, look it up via selector
            if (!rowEl && selectedUserId) {
                rowEl = document.querySelector(`tr[data-id="${selectedUserId}"]`);
            }

            if (rowEl) {
                rowEl.classList.add('active');
                activeRow = rowEl;
            }

            let detailHtml = `
                <div class="detail-header">
                    <h3>${escHtml(conv.patient_name || conv.name)}</h3>
                    <div class="detail-meta">${escHtml(conv.phone)} &middot; ${conv.message_count} messages</div>
                </div>
                <div class="thread">`;

            if (conv.thread && conv.thread.length > 0) {
                conv.thread.forEach(msg => {
                    if (!msg.message) return;
                    detailHtml += `
                        <div class="thread-msg ${msg.role}">
                            ${escHtml(msg.message)}
                            <div class="thread-time">${msg.time}</div>
                        </div>`;
                });
            } else {
                detailHtml += '<div class="detail-empty">No messages</div>';
            }

            detailHtml += '</div>';
            document.getElementById('detailContent').innerHTML = detailHtml;

            // Scroll thread to bottom
            const threadEl = document.querySelector('.thread');
            if (threadEl) {
                threadEl.scrollTop = threadEl.scrollHeight;
            }
        }

        // ---- Search ----
        document.getElementById('searchInput').addEventListener('input', function() {
            const q = this.value.toLowerCase();
            if (!q) {
                renderTable(allConversations);
                return;
            }
            const filtered = allConversations.filter(c =>
                (c.name || '').toLowerCase().includes(q) ||
                (c.patient_name || '').toLowerCase().includes(q) ||
                (c.phone || '').toLowerCase().includes(q)
            );
            renderTable(filtered);
        });

        // ---- Helpers ----
        function escHtml(str) {
            if (!str) return '';
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        // ---- Init ----
        loadStats();
        loadConversations();

        // ---- Auto-sync polling every 5 seconds ----
        setInterval(async () => {
            await syncConversations();
            await loadStats();
        }, 5000);
    </script>
</body>
</html>
"""


@router.get("/")
async def get_dashboard():
    """Return the admin dashboard UI."""
    return HTMLResponse(content=DASHBOARD_HTML)
