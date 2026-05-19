"""
Website API Integration Service — Connects the WhatsApp bot directly to the main My Pain Clinic Global booking system.
Exposes endpoints to fetch available doctor slots and submit real-time bookings.
"""

import httpx
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# Replace with your main website's API endpoint base
API_BASE_URL = "https://admin.mypainclinicglobal.com/api" 
# Example auth token if your API requires Bearer/API Key authentication
API_AUTH_TOKEN = "your_secure_bearer_or_api_key_here"

def get_headers() -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if API_AUTH_TOKEN and API_AUTH_TOKEN != "your_secure_bearer_or_api_key_here":
        headers["Authorization"] = f"Bearer {API_AUTH_TOKEN}"
    return headers

async def fetch_available_slots(date_str: str, branch_id: int = 13) -> List[Dict[str, Any]]:
    """
    Fetches real-time doctor availability slots from the main clinic website.
    Corresponds to: GET /slots?date=YYYY-MM-DD&branch_id=13
    """
    url = f"{API_BASE_URL}/slots"
    params = {
        "date": date_str,
        "branch_id": branch_id,
        "show_todays_fullslots": 1,
        "limit": 100
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            logger.info(f"🌐 Fetching available slots from main site for date: {date_str}")
            response = await client.get(url, params=params, headers=get_headers())
            
            if response.status_code == 200:
                data = response.json()
                # Adjust based on the actual JSON structure returned by your website
                return data.get("slots", []) if isinstance(data, dict) else data
            else:
                logger.error(f"❌ Failed to fetch slots: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"❌ Error communicating with website slot API: {e}", exc_info=True)
            return []

async def create_remote_booking(
    patient_name: str,
    phone: str,
    date_str: str,
    time_slot: str,
    pain_type: str,
    doctor_id: Optional[int] = None,
    service_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Submits a finalized patient booking directly to the main clinic website booking system.
    Corresponds to: POST /bookings
    """
    url = f"{API_BASE_URL}/bookings"
    
    # Custom payload matching your website's booking table requirements
    payload = {
        "patient_name": patient_name,
        "phone": phone,
        "date": date_str,
        "slot_time": time_slot,
        "pain_type": pain_type,
        "booking_status": "booked",  # Marks as confirmed/booked
        "branch_id": 13,             # Default branch (Bandra)
        "doctor_id": doctor_id,      # Optional doctor ID if selected
        "service_id": service_id,    # Optional service ID
        "source": "whatsapp_bot"     # Tracks attribution
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            logger.info(f"🌐 Submitting booking for {patient_name} to main site...")
            response = await client.post(url, json=payload, headers=get_headers())
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Website booking successful for {patient_name}")
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"❌ Website booking rejected: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
        except Exception as e:
            logger.error(f"❌ Error sending booking to main website: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
