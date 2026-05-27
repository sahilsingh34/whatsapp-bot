import asyncio
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.services import ai_service, memory_service, appointment_service
from app.services import learning_service

router = APIRouter(prefix="/demo", tags=["demo"])
logger = logging.getLogger(__name__)

# --- HTML TEMPLATE (WhatsApp Style) ---
CHAT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MPC AI Demo Chat</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        body { background-color: #efeae2; display: flex; justify-content: center; height: 100vh; }
        #chat-container { width: 100%; max-width: 450px; background-image: url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png'); background-color: #e5ddd5; display: flex; flex-direction: column; position: relative; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        #chat-header { background-color: #075e54; color: white; padding: 15px; display: flex; align-items: center; gap: 10px; z-index: 10;}
        #chat-header img { width: 40px; height: 40px; border-radius: 50%; background: #fff; }
        #chat-header-info { display: flex; flex-direction: column; }
        #chat-header-info h2 { font-size: 16px; font-weight: 600; }
        #chat-header-info p { font-size: 12px; opacity: 0.8; }
        
        #chat-messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
        .message { max-width: 85%; padding: 8px 12px; border-radius: 8px; font-size: 14.2px; line-height: 19px; position: relative; word-wrap: break-word; white-space: pre-wrap; box-shadow: 0 1px 0.5px rgba(0,0,0,0.13); }
        .message.bot { background-color: #ffffff; align-self: flex-start; border-top-left-radius: 0; }
        .message.user { background-color: #dcf8c6; align-self: flex-end; border-top-right-radius: 0; }
        .time { font-size: 11px; color: #999; float: right; margin-top: 5px; margin-left: 10px; }
        
        #chat-input-container { background-color: #f0f0f0; padding: 10px; display: flex; gap: 10px; align-items: center; }
        #chat-input { flex: 1; padding: 12px 15px; border: none; border-radius: 24px; font-size: 15px; outline: none; }
        #send-btn { background-color: #008f68; color: white; border: none; width: 45px; height: 45px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
        #send-btn:disabled { background-color: #ccc; cursor: not-allowed; }
        
        /* Loading dots */
        .typing { display: none; padding: 12px 16px; background-color: #fff; border-radius: 20px; align-self: flex-start; margin-bottom: 10px; box-shadow: 0 1px 0.5px rgba(0,0,0,0.13); }
        .dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background-color: #999; margin: 0 2px; animation: bounce 1.4s infinite ease-in-out both; }
        .dot:nth-child(1) { animation-delay: -0.32s; }
        .dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }
    </style>
</head>
<body>
    <div id="chat-container">
        <div id="chat-header">
            <img src="https://ui-avatars.com/api/?name=MPC&background=fff&color=075e54" alt="Avatar">
            <div id="chat-header-info">
                <h2>My Pain Clinic Global</h2>
                <p>AI Assistant • Typically replies instantly</p>
            </div>
        </div>
        
        <!-- Active Models Info Card -->
        <div style="background-color: #f7f9f8; padding: 10px 14px; border-bottom: 1px solid #d4ddd8; font-size: 12.5px; color: #2d3e35; z-index: 5;">
            <p style="font-weight: 700; font-size: 10px; text-transform: uppercase; color: #075e54; margin-bottom: 5px; letter-spacing: 0.8px;">Model Selector (Auto-Selected)</p>
            <div style="display: flex; flex-direction: column; gap: 4px; line-height: 1.4;">
                <div style="display: flex; align-items: flex-start; gap: 6px;">
                    <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background-color: #075e54; margin-top: 5px; flex-shrink: 0;"></span>
                    <span><strong>Llama 3.1 8B</strong> <span style="color: #666;">(recommended for most clinic queries)</span></span>
                </div>
                <div style="display: flex; align-items: flex-start; gap: 6px;">
                    <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background-color: #075e54; margin-top: 5px; flex-shrink: 0;"></span>
                    <span><strong>Llama 3.3 70B</strong> <span style="color: #666;">(for complex medical questions)</span></span>
                </div>
            </div>
        </div>
        
        <div id="chat-messages">
            <div class="message bot">
                Hi! Welcome to the AI Demo. Type a message below to test the clinic assistant.
                <div class="time">Just now</div>
            </div>
        </div>
        
        <div class="typing" id="typing-indicator">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>
        
        <div id="chat-input-container">
            <input type="text" id="chat-input" placeholder="Type a message..." autocomplete="off">
            <button id="send-btn">➤</button>
        </div>
    </div>

    <script>
        const input = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');
        const messagesDiv = document.getElementById('chat-messages');
        const typingIndicator = document.getElementById('typing-indicator');
        
        // Random session phone number to isolate chat history for testing
        const phone = "demo-" + Math.floor(Math.random() * 1000000);

        function scrollToBottom() {
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function getTime() {
            const now = new Date();
            return now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
        }

        function addMessage(text, type, model = null) {
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${type}`;
            msgDiv.innerText = text;
            
            if (model && type === 'bot') {
                const modelBadge = document.createElement('div');
                modelBadge.style.fontSize = '9.5px';
                modelBadge.style.color = '#008f68';
                modelBadge.style.fontWeight = '600';
                modelBadge.style.marginTop = '6px';
                modelBadge.style.borderTop = '1px solid #f0f0f0';
                modelBadge.style.paddingTop = '4px';
                modelBadge.style.display = 'flex';
                modelBadge.style.alignItems = 'center';
                modelBadge.style.gap = '4px';
                
                const modelText = model === 'llama-3.3-70b-versatile' ? 'Llama 3.3 70B (Complex Medical)' : 'Llama 3.1 8B (Clinic Query)';
                modelBadge.innerHTML = `<span>🧠</span> <span>Routed to ${modelText}</span>`;
                msgDiv.appendChild(modelBadge);
            }
            
            const timeDiv = document.createElement('div');
            timeDiv.className = 'time';
            timeDiv.innerText = getTime();
            
            msgDiv.appendChild(timeDiv);
            messagesDiv.appendChild(msgDiv);
            scrollToBottom();
        }

        async function sendMessage() {
            const text = input.value.trim();
            if (!text) return;

            addMessage(text, 'user');
            input.value = '';
            sendBtn.disabled = true;
            
            messagesDiv.appendChild(typingIndicator); // Move to bottom
            typingIndicator.style.display = 'block';
            scrollToBottom();

            try {
                const response = await fetch('/demo/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text, phone: phone })
                });
                
                const data = await response.json();
                typingIndicator.style.display = 'none';
                
                if(data.response) {
                    addMessage(data.response, 'bot', data.model);
                } else {
                    addMessage("Error getting response.", 'bot');
                }
            } catch (err) {
                typingIndicator.style.display = 'none';
                addMessage("Network error.", 'bot');
            }
            
            sendBtn.disabled = false;
            input.focus();
        }

        sendBtn.addEventListener('click', sendMessage);
        input.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
"""

class ChatRequest(BaseModel):
    message: str
    phone: str

@router.get("/")
async def get_demo_ui():
    """Return the HTML chat interface."""
    return HTMLResponse(content=CHAT_HTML)

@router.post("/api/chat")
async def process_demo_chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Process message bypassing WhatsApp API."""
    try:
        user = await memory_service.get_or_create_user(db, req.phone, "Demo User")
        history = await memory_service.get_conversation_history(db, user.id)
        await memory_service.save_message(db, user.id, "user", req.message)
        
        conversation = history + [{"role": "user", "content": req.message}]
        ai_response, selected_model = await ai_service.generate_response(conversation, db=db)
        
        # Check for appointment data
        appointment_data = appointment_service.parse_appointment_from_response(ai_response)
        if appointment_data:
            await appointment_service.create_appointment(
                db=db,
                user_id=user.id,
                details=appointment_data,
                contact_number=req.phone,
            )
            logger.info(f"📅 Appointment captured from Demo UI for {req.phone}")
            
        # Clean tags to make it look nice in UI
        clean_response = appointment_service.clean_appointment_tags(ai_response)
        clean_response = clean_response.replace("[ESCALATE]", "").strip()
        
        # Handle empty/blank responses gracefully
        if not clean_response:
            if appointment_data:
                clean_response = (
                    f"Thank you, {appointment_data.get('name', 'there')}! I have registered your appointment details "
                    f"for {appointment_data.get('pain_type', 'treatment')} on {appointment_data.get('date', 'your requested date')} "
                    f"at {appointment_data.get('time', 'your requested time')}. Our team will review this and contact "
                    f"you shortly to confirm. 🙏"
                )
            else:
                clean_response = (
                    "Thank you! How can I help you today? If you have questions about "
                    "our treatments or want to book a consultation, just let me know. 🙏"
                )
        
        await memory_service.save_message(db, user.id, "assistant", clean_response)
        
        # Fire background learning analysis
        asyncio.create_task(
            _demo_background_learn(user.id),
            name=f"demo-learn-{str(user.id)[:8]}",
        )
        
        return {"response": clean_response, "model": selected_model}
        
    except Exception as e:
        logger.error(f"Demo chat error: {e}")
        await db.rollback()
        return {"response": "System error. Try again.", "model": "Unknown"}


async def _demo_background_learn(user_id) -> None:
    """Background learning task for demo conversations."""
    try:
        from app.database.connection import async_session_factory

        async with async_session_factory() as db:
            await learning_service.analyze_conversation(db, user_id)
            await db.commit()
    except Exception as e:
        logger.warning(f"\U0001f9e0 Demo background learning failed (non-blocking): {e}")
