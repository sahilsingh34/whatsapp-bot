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

async def test_web_search_fallback():
    output_lines = []
    output_lines.append("=== Testing AI Web Search Fallback ===\n")
    try:
        from app.services.ai_service import generate_response
        
        # Test query that requires recent/specific info
        conversation = [
            {"role": "user", "content": "Who won the most recent cricket IPL tournament?"}
        ]
        
        output_lines.append("🤖 Generating AI response for: 'Who won the most recent cricket IPL tournament?'...")
        ai_reply, model = await generate_response(conversation)
        
        output_lines.append("\n📝 --- RECEIVED AI RESPONSE ---")
        output_lines.append(f"Model used: {model}")
        output_lines.append(ai_reply)
        output_lines.append("--------------------------------\n")
        
        # Test another query that should NOT trigger web search (e.g. clinic hours)
        conversation_clinic = [
            {"role": "user", "content": "Hi, what are your clinic timings?"}
        ]
        output_lines.append("🤖 Generating AI response for general question: 'Hi, what are your clinic timings?'...")
        ai_reply_clinic, model_clinic = await generate_response(conversation_clinic)
        output_lines.append("\n📝 --- RECEIVED AI CLINIC RESPONSE ---")
        output_lines.append(f"Model used: {model_clinic}")
        output_lines.append(ai_reply_clinic)
        output_lines.append("--------------------------------\n")
        
    except Exception as e:
        output_lines.append(f"❌ Test failed with error: {e}")
        import traceback
        output_lines.append(traceback.format_exc())

    with open(r"c:\Users\DELL\Documents\whatsapp bot mpc\test_search_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

if __name__ == "__main__":
    asyncio.run(test_web_search_fallback())
