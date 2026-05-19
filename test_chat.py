"""
Terminal Chat Tester for My Pain Clinic Global AI Assistant.
Test the AI directly from your terminal — no WhatsApp/Docker needed.

Usage:
    python test_chat.py

Type your messages as a patient would on WhatsApp.
Type 'quit' or 'exit' to end the session.
Type 'reset' to clear conversation history.
Type 'system' to view the system prompt length.
Type 'history' to view conversation so far.
"""

import asyncio
import os
import sys

# Fix Windows terminal encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from openai import AsyncOpenAI

# ---- Load config ----
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "meta/llama-3.3-70b-instruct")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://integrate.api.nvidia.com/v1")

if not NVIDIA_API_KEY:
    print("[ERROR] NVIDIA_API_KEY not found in .env file")
    print("   Make sure your .env file has: NVIDIA_API_KEY=your-nvidia-api-key")
    sys.exit(1)

# ---- Import system prompt ----
from app.services.ai_service import SYSTEM_PROMPT

# ---- NVIDIA NIM Client ----
client = AsyncOpenAI(
    api_key=NVIDIA_API_KEY,
    base_url=AI_BASE_URL,
)

# ---- Conversation history ----
conversation_history = []


async def get_ai_response(user_message: str) -> str:
    """Send a message and get AI response."""
    conversation_history.append({"role": "user", "content": user_message})

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(conversation_history)

    try:
        response = await client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            presence_penalty=0.1,
            frequency_penalty=0.1,
        )

        ai_message = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": ai_message})
        return ai_message

    except Exception as e:
        return f"[API ERROR] {e}"


def print_banner():
    """Print the welcome banner."""
    print()
    print("=" * 60)
    print("  My Pain Clinic Global - AI Assistant Tester")
    print("=" * 60)
    print(f"  Model   : {AI_MODEL}")
    print(f"  API     : NVIDIA NIM")
    print(f"  Endpoint: {AI_BASE_URL}")
    print(f"  Prompt  : {len(SYSTEM_PROMPT)} chars")
    print("-" * 60)
    print("  Commands:")
    print("    quit/exit  - end session")
    print("    reset      - clear conversation history")
    print("    system     - view system prompt stats")
    print("    history    - view conversation history")
    print("=" * 60)
    print()


async def main():
    """Main chat loop."""
    print_banner()

    print("[READY] Assistant is ready. Type as a patient would on WhatsApp.\n")

    while True:
        try:
            user_input = input("YOU: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        # ---- Commands ----
        if user_input.lower() in ("quit", "exit"):
            print("\nGoodbye!")
            break

        if user_input.lower() == "reset":
            conversation_history.clear()
            print("[RESET] Conversation history cleared.\n")
            continue

        if user_input.lower() == "system":
            print(f"\n--- SYSTEM PROMPT ({len(SYSTEM_PROMPT)} chars) ---")
            # Show first 1500 chars
            print(SYSTEM_PROMPT[:1500])
            if len(SYSTEM_PROMPT) > 1500:
                print(f"\n... truncated ({len(SYSTEM_PROMPT)} total chars)")
            print("--- END ---\n")
            continue

        if user_input.lower() == "history":
            if not conversation_history:
                print("[EMPTY] No conversation history yet.\n")
            else:
                print(f"\n--- HISTORY ({len(conversation_history)} messages) ---")
                for msg in conversation_history:
                    role = "YOU" if msg["role"] == "user" else "BOT"
                    preview = msg["content"][:120].replace("\n", " ")
                    print(f"  [{role}] {preview}...")
                print("--- END ---\n")
            continue

        # ---- Get AI response ----
        print("\n[Thinking...]", end="", flush=True)
        response = await get_ai_response(user_input)
        print("\r" + " " * 20 + "\r", end="")  # Clear "Thinking..."

        # ---- Check for internal tags ----
        tags = []
        if "[APPOINTMENT_COLLECTED]" in response:
            tags.append("[APPOINTMENT CAPTURED]")
        if "[ESCALATE]" in response:
            tags.append("[ESCALATION TRIGGERED]")

        # ---- Display response ----
        print(f"BOT: {response}\n")

        if tags:
            for tag in tags:
                print(f"   >> {tag}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
