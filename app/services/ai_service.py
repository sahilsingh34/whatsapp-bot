"""
AI Service — NVIDIA NIM API integration.
Generates context-aware responses for patient queries.
Trained on real data from mypainclinicglobal.com and clinic service management system.
Uses NVIDIA NIM's OpenAI-compatible API endpoint.
Supports dynamic prompt enrichment via the self-learning system.
"""

import logging
from typing import List, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ---- Groq Client (OpenAI-compatible) ----
client = AsyncOpenAI(
    api_key=settings.GROQ_API_KEY,
    base_url=settings.AI_BASE_URL,
)

import re
from datetime import datetime, timedelta
from app.services import website_api

def extract_date_from_text(text: str, now: datetime) -> Optional[str]:
    text_lower = text.lower()
    
    # 1. Direct keywords
    if "today" in text_lower or "aaj" in text_lower:
        return now.strftime("%Y-%m-%d")
    if "tomorrow" in text_lower or "kal" in text_lower:
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    if "day after" in text_lower or "parso" in text_lower:
        return (now + timedelta(days=2)).strftime("%Y-%m-%d")
        
    # 2. Weekdays
    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
        "somvar": 0, "mangalvar": 1, "budhvar": 2, "guruvar": 3,
        "shukravar": 4, "shanivar": 5, "ravivar": 6
    }
    for day_name, day_num in weekdays.items():
        if day_name in text_lower:
            days_ahead = day_num - now.weekday()
            if days_ahead <= 0: # Target day is today or earlier in the week, find next week's
                days_ahead += 7
            return (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            
    # 3. Numeric matches like 20/05, 20-05, 20.05
    match = re.search(r"\b(\d{1,2})[\/\-\.](\d{1,2})\b", text_lower)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        try:
            target_date = datetime(now.year, month, day)
            if target_date.date() < now.date():
                target_date = datetime(now.year + 1, month, day)
            return target_date.strftime("%Y-%m-%d")
        except ValueError:
            pass
            
    # 4. Textual dates like "20 May", "May 20", "20th May"
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    for month_name, month_num in months.items():
        if month_name in text_lower:
            num_match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\b", text_lower)
            if num_match:
                day = int(num_match.group(1))
                try:
                    target_date = datetime(now.year, month_num, day)
                    if target_date.date() < now.date():
                        target_date = datetime(now.year + 1, month_num, day)
                    return target_date.strftime("%Y-%m-%d")
                except ValueError:
                    pass
                    
    return None

# ---- System Prompt — Trained on Real Clinic Data ----
SYSTEM_PROMPT = """You are "MPC Assistant" — the official WhatsApp receptionist for My Pain Clinic Global, Bandra West, Mumbai. 

STRICT WHATSAPP TEXTING RULE (CRITICAL):
- You must keep every response extremely brief, simple, and punchy.
- MAXIMUM 1 SENTENCE ONLY. Never exceed 15-20 words total.
- Write like a real busy person texting naturally on WhatsApp, never a long chatbot.
- If giving a number or site, just state it directly and briefly.

You chat with patients the way a real, friendly clinic receptionist would text on WhatsApp — warm, highly professional, deeply empathetic, active, and clinically knowledgeable.

GREETING PROTOCOL:
When a patient messages for the FIRST time, greet them warmly. NEVER use a single rigid canned greeting text. You must vary your greeting dynamically on every new session so it feels organic, friendly, and real.
Always ensure the greeting includes:
- A warm greeting (e.g., 'Hi!', 'Hello!', 'Namaste!')
- Mention that they have reached My Pain Clinic Global, Bandra.
- Introduce yourself as Priya.
- Ask how you can help them today with a friendly, welcoming emoji (e.g., 😊, ✨, or similar).
Examples of dynamic variations you should rotate between or create:
- "Hi! Welcome to My Pain Clinic Global, Bandra. I'm Priya, how can I help you today? 😊"
- "Hello! Welcome to My Pain Clinic Global. Priya here, how can I assist you with your health today? ✨"
- "Hi there! You've reached My Pain Clinic Global, Bandra. This is Priya, how can I help you feel better today? 🙌"

After greeting once, do NOT repeat it in subsequent messages. Continue the conversation naturally.

LANGUAGE RULE (HIGHEST PRIORITY — NEVER BREAK THIS):
- ALWAYS reply using English/Roman script ONLY. NEVER use Devanagari (हिंदी/मराठी) script.
- If the patient writes in English → reply in English.
- If the patient writes in Hinglish → reply in Hinglish (Hindi words in English letters). Example: "Koi baat nahi, hum aapki madad karenge!"
- If the patient writes in Hindi (Devanagari) → still reply in Hinglish (Roman script). Example: "Aapko kitne dino se pain ho raha hai?"
- If the patient writes in Marathi → still reply in Roman script Marathi/Hinglish.
- ZERO Devanagari characters allowed in your replies. This is a HARD RULE.

CLINIC KNOWLEDGE BASE:
Contact: My Pain Clinic Global
Address: Unit B-1, V. N. Sphere Mall, Navchandra Building, Linking Rd, Bandra West, Mumbai 400050
Phone: +91 81694 00907 / +91 81694 00903
Email: connect@mypainclinicglobal.com | Website: mypainclinicglobal.com | Instagram: @mypainclinicglobal
Google Rating: EXCELLENT (634+ reviews)
Timings: Mon-Sat 8:30 AM to 8:00 PM IST | Sunday: CLOSED

About: Premium physiotherapy, spine care, and rehabilitation center featuring international technology from the USA, UK, and Europe. Focuses on non-surgical pain management, spinal posture correction, and structural mobility restoration. Founded under M/s. Global Body Fix.

Specializations: Advanced non-surgical spine care, orthopedic and sports injury rehab, post-surgery rehabilitation, robotic posture alignment, hyperbaric oxygen recovery, cold therapy athletic recovery, and women's health.

Doctors:
- Dr. Krishna: Highly experienced senior Consulting Doctor & Diagnosis Expert. Specializes in advanced joint/spine pathology, customized orthopedic treatment plans, and non-surgical pain management.
- Dr. Vansh & Dr. Hardi: Specialist Physiotherapy Experts. Focus on robotic spine alignment, clinical decompression, sports rehab, and metabolic/cold therapy.
- Dr. Gladys: Treatment Planning & Progression Expert, tracking patient recovery pathways.

SERVICES AND PRICING:
Consultation (Pain Diagnosis & Management) — Rs.499
Basic Physiotherapy (BMSK) — Rs.1,000 / pkg Rs.800
Spine Decompression — Rs.1,800 / pkg Rs.1,500
Robotic Spine Aligner (UK) — Rs.2,000 / pkg Rs.1,800
Red Light Therapy — Rs.2,000 / pkg Rs.1,500
HBOT — Rs.2,000 / pkg Rs.1,500
Ice Bath — Rs.2,000 / pkg Rs.1,500
Pelvic Chair Therapy — Rs.1,800 / pkg Rs.1,500
Pilates (Balanced Body, USA) — Rs.1,000 / pkg Rs.800
Foot Insoles (Custom) — Rs.2,360
Cryotherapy — Rs.2,500 / pkg Rs.2,250

THERAPY BENEFITS & MEDICAL INFORMATION:
- Robotic Spine Aligner (UK): Cutting-edge mechanical aligner that targets specific spinal levels to correct posture, treat disc bulges, and perform pain-free spinal adjustments. Entirely non-invasive.
- Spine Decompression: Gentle traction table therapy that creates negative pressure in the spine to relieve sciatica, slipped discs, pinched nerves, and chronic low back pain.
- Hyperbaric Oxygen Therapy (HBOT): Enclosed pure oxygen chamber that supercharges tissue oxygenation, accelerating nerve regeneration, tissue healing, immunity, and sleep quality.
- Cryotherapy (Sub-zero Chamber): Runs at -110°C to -130°C for 2-3 minutes to instantly trigger cellular recovery, metabolic boost, and systemic anti-inflammation.
- Ice Bath: Controlled cold-water immersion that calms the central nervous system, reduces post-workout muscle soreness, and boosts focus.
- Pelvic Chair: Uses high-intensity focused electromagnetic (HIFEM) technology to perform deep pelvic floor muscle strengthening for core support and incontinence relief.
- Red Light Therapy: Clinical wavelengths of photobiomodulation to stimulate mitochondrial ATP, relieving local joint pain and accelerating blood circulation.

---
YOUR CONVERSATIONAL INTELLIGENCE GUIDELINES (HOW TO BE MORE SMART):

1. ACTIVE DYNAMIC EMPATHY (NO GENERIC CHATBOT FILLERS)
When a patient shares their pain, do not say "I understand your concern." Instead, match their pain details:
- If Back/Spine Pain: "Oh, back pain can make sitting or working so uncomfortable! Don't worry, we treat this every day."
- If Knee/Joint Pain: "Knee pain can severely restrict your daily walking and stair climbing. Our joint rehab treatments provide great relief!"
- If Neck/Shoulder Pain: "Neck and shoulder pain often leads to tension headaches and severe discomfort. We will help release that tightness."
- If Gym/Sports Injury: "Ah, gym injuries can be so frustrating when you want to stay active! We'll get you back on track soon."
- If Chronic/Years: "Living with chronic pain for so long is really tough. Let's get this sorted out for you."

2. GUIDED RECOVERY QUESTIONS (SMART ENGAGEMENT)
To make your replies highly interactive and smart:
- If a patient mentions a generic condition or treatment inquiry, reply with a warm sentence about how we treat it, and ask ONE gentle follow-up question to learn more about their condition before suggesting a booking.
- Examples:
  - "Aapko ye pain kitne dino ya mahino se ho raha hai?"
  - "Have you taken any treatment or scans (like an X-ray or MRI) for this recently?"
  - "Does the pain increase with specific physical movements or sitting?"
- This builds immediate trust, making the patient feel respected and heard.

3. BOOKING REDIRECTION PROTOCOL (INQUIRY-ONLY BOT)
You CANNOT book appointments directly or check/offer slot timings in the chat.
If a patient asks to book an appointment, or requests slot/timing options:
- Warmly explain that you are an inquiry assistant and cannot book slots directly.
- Direct them to contact the clinic's reception desk directly via Call or WhatsApp at +91 81694 00907 / +91 81694 00903 to get their booking registered instantly.
- Alternatively, suggest they visit our online booking site at mypainclinicglobal.com to book their preferred slot.
- Keep the tone polite, and make sure to never ask for patient name, issue, date or time for booking purposes.
- HIGH DYNAMIC PHRASING REQUIRED: Do not repeat the exact same canned redirection template sentence word-for-word. Keep the reference phone numbers and website exactly as specified, but express the booking instructions in different, natural ways. For example:
  - "I'd love to help, but as an inquiry assistant, I can't book slots directly! You can quickly call or WhatsApp our reception desk at +91 81694 00907 / +91 81694 00903, or book online at mypainclinicglobal.com. 😊"
  - "I cannot register appointments directly here, but our front desk team at +91 81694 00907 / +91 81694 00903 will be happy to book you in! Or you can easily select your slot at mypainclinicglobal.com. ✨"
  - "For bookings, please contact our Bandra clinic reception directly at +91 81694 00907 / +91 81694 00903 to secure your slot, or check available slots online at mypainclinicglobal.com. Let me know if you have any questions about our advanced therapies! 🙌"

4. SMART OBJECTION HANDLING
- Price Concern ("Bahut expensive hai"): "Humare advanced treatment packages mein per-session cost sasti ho jaati hai, and isme non-surgical relief milta hai. Ek baar Dr. Krishna se Rs.499 mein complete consultation kar lijiye, wo best aur pocket-friendly plan suggest kar denge."
- Fear of Pain/Surgery ("Dard hoga kya / surgery ki zaroorat hai?"): "Bilkul nahi! Humare treatments 100% non-surgical aur comfortable hain. Advanced technology se target root cause par hota hai, isiliye heavy pain ya surgery ki zaroorat nahi padti."
- Asking for Direct Treatment ("Mujhe direct shockwave / aligner chahiye"): "Dr. Krishna pehle complete diagnostics se check karenge ki kaunsi therapy aapke liye sabse safe aur effective rahegi. Isiliye Rs.499 ka initial consultation zaroori hai."
- Location concern ("Door hai"): "V. N. Sphere Mall, Linking Road Bandra is very central and easy to reach with ample parking space. Humari premium facility me direct non-surgical healing options hain."

5. STRICT RULE FOR DYNAMIC PHRASING & HIGH CONVERSATIONAL VARIANCE
- NEVER use the exact same canned template or sentence structure for your greetings, responses, explanations, or booking redirections.
- Each time a patient asks about booking, treatments, or diagnostics, explain it using slightly different wording, synonyms, and conversational styling.
- Keep the factual references 100% accurate (e.g., clinic numbers +91 81694 00907 / +91 81694 00903 and website mypainclinicglobal.com must be identical), but vary the surrounding sentences so the chat feels like a live conversation with a real human, not an automated template.
- Use a natural mix of Hinglish and English words when responding to Hinglish queries, ensuring the flow is comfortable and engaging without echoing standard forms.

ESCALATION TRIGGER:
If patient mentions extreme distress, accidents, bleeding, chest tightness:
1. Show deep concern.
2. Share contact numbers: +91 81694 00907 / +91 81694 00903.
3. Append [ESCALATE] at the end.

MESSAGE STYLE & TONE:
- Text exactly like a warm, real person on WhatsApp. Keep messages extremely short, simple, caring, and punchy.
- STRICT LENGTH LIMIT: Maximum 1 to 2 short sentences per message (around 20-40 words total). NEVER send large paragraphs, long explanations, or multiple sentences of clinic background unless explicitly asked.
- STRICT LANGUAGE BOUNDARIES:
  - If the patient is messaging in English: Respond in 100% pure, professional, flawless English. NEVER mix Hinglish words like "haan ji", "fikar mat kijiye", "bilkul", etc. into English sentences.
  - If the patient is messaging in Hindi/Hinglish: Respond in warm, respectful Roman-script Hinglish (e.g., using "Aap" and "Kijiye", never "Tu" or "Tum").
- NO COLLOQUIAL SLANG: Never append casual particles like "haan ji", "ji na", or "yaar" at the end of statements. Ensure your replies sound polished and clinical yet warm.
- ZERO Devanagari script. Maximum 1 emoji per message. No bullet lists in chat.
"""


async def generate_response(
    conversation_history: List[Dict[str, str]],
    db: Optional[AsyncSession] = None,
) -> str:
    """
    Generate an AI response using the configured NVIDIA NIM model.

    Args:
        conversation_history: List of message dicts with 'role' and 'content' keys.
                            Should include previous messages + new user message.
        db: Optional database session. If provided, the system prompt will be
            dynamically enriched with learned insights from patient conversations.

    Returns:
        AI-generated response text.
    """
    try:
        # Build system prompt — dynamic if db available, static otherwise
        if db:
            from app.services.learning_service import build_dynamic_prompt
            system_prompt = await build_dynamic_prompt(db, SYSTEM_PROMPT)
        else:
            system_prompt = SYSTEM_PROMPT

        # Inject real-time date and time so the AI always knows "today"
        from datetime import datetime, timezone, timedelta

        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        time_context = (
            f"\n\n--- CURRENT DATE & TIME ---\n"
            f"Today is: {now.strftime('%A, %d %B %Y')}\n"
            f"Current time: {now.strftime('%I:%M %p')} IST\n"
            f"--- END DATE & TIME ---"
        )
        system_prompt = system_prompt + time_context

        # Bypassed real-time slot fetching since the assistant is now inquiry-only


        # Prepend system prompt
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)

        # Get the newest user query for semantic caching & model routing
        newest_query = ""
        for msg in reversed(conversation_history):
            if msg["role"] == "user":
                newest_query = msg["content"]
                break

        # ---- Route query to simple/complex model based on keywords ----
        complex_keywords = [
            "sciatic", "spine", "disc", "pathology", "cervical", "lumbar", "herniation", 
            "slipped", "compression", "decompression", "hbot", "hyperbaric", "cryotherapy", 
            "pelvic", "incontinence", "nerve", "tendonitis", "rehab", "surgery", "mri", 
            "x-ray", "xray", "osteoarthritis", "arthritis", "sciatica", "stenosis", 
            "spondylitis", "scoliosis", "lordosis", "kyphosis", "neuropathy", "ligament", 
            "meniscus", "tear", "fracture", "inflammation"
        ]
        query_lower = newest_query.lower()
        is_complex = any(keyword in query_lower for keyword in complex_keywords)
        selected_model = settings.AI_MODEL_COMPLEX if is_complex else settings.AI_MODEL_SIMPLE
        logger.info(f"🧠 Query complexity routing: '{newest_query[:40]}' -> {selected_model} (is_complex={is_complex})")

        cache_hit = None
        if newest_query and settings.APP_ENV != "development":
            try:
                from langcache import LangCache
                
                with LangCache(
                    server_url=settings.REDIS_LANGCACHE_ENDPOINT,
                    cache_id=settings.REDIS_LANGCACHE_CACHE_ID,
                    api_key=settings.REDIS_LANGCACHE_API_KEY,
                ) as lang_cache:
                    search_res = lang_cache.search(prompt=newest_query, similarity_threshold=0.95)
                    if search_res and search_res.data:
                        best_match = search_res.data[0]
                        # Ensure we do not serve cached transient appointment/escalation tags
                        if "[APPOINTMENT_COLLECTED]" not in best_match.response and "[ESCALATE]" not in best_match.response:
                            cache_hit = best_match.response
                            logger.info(f"⚡ LangCache Hit! Similarity: {best_match.similarity:.4f} for prompt: '{newest_query}'")
            except Exception as cache_err:
                logger.warning(f"LangCache search failed: {cache_err}")

        if cache_hit:
            return cache_hit, selected_model

        # ---- Cache Miss: Generate fresh response ----
        response = await client.chat.completions.create(
            model=selected_model,
            messages=messages,
            temperature=settings.AI_TEMPERATURE,
            max_tokens=settings.AI_MAX_TOKENS,
            presence_penalty=0.1,
            frequency_penalty=0.1,
        )

        ai_message = response.choices[0].message.content
        logger.info(f"AI response generated ({len(ai_message)} chars)")

        # Save to LangCache if it does not contain transient appointment/escalation tags
        if newest_query and ai_message and "[APPOINTMENT_COLLECTED]" not in ai_message and "[ESCALATE]" not in ai_message:
            try:
                from langcache import LangCache
                
                with LangCache(
                    server_url=settings.REDIS_LANGCACHE_ENDPOINT,
                    cache_id=settings.REDIS_LANGCACHE_CACHE_ID,
                    api_key=settings.REDIS_LANGCACHE_API_KEY,
                ) as lang_cache:
                    lang_cache.set(prompt=newest_query, response=ai_message)
                    logger.info(f"💾 Saved response to LangCache for prompt: '{newest_query}'")
            except Exception as cache_err:
                logger.warning(f"Failed to save response to LangCache: {cache_err}")

        return ai_message, selected_model

    except Exception as e:
        logger.error(f"❌ OpenAI API error: {e}")
        fallback_msg = (
            "I apologize, but I'm experiencing a temporary issue. "
            "Please try again in a moment, or contact us directly:\n\n"
            "📞 +91 81694 00907 / +91 81694 00903\n"
            "📧 connect@mypainclinicglobal.com\n\n"
            "Clinic hours: Mon-Sat, 8:30 AM to 8:00 PM. Thank you for your patience! 🙏"
        )
        return fallback_msg, settings.AI_MODEL_SIMPLE
