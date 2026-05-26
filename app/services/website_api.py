import httpx
import logging
import json
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# Replace with your main website's API endpoint base
API_BASE_URL = "https://api.mypainclinicglobal.com/api" 
# Example auth token if your API requires Bearer/API Key authentication
API_AUTH_TOKEN = "your_secure_bearer_or_api_key_here"

# Global HTTPX AsyncClient for connection pooling (prevents handshake delays)
_async_client: Optional[httpx.AsyncClient] = None

def get_http_client() -> httpx.AsyncClient:
    global _async_client
    if _async_client is None or _async_client.is_closed:
        _async_client = httpx.AsyncClient(
            timeout=10.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
    return _async_client

def get_headers() -> Dict[str, str]:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if API_AUTH_TOKEN and API_AUTH_TOKEN != "your_secure_bearer_or_api_key_here":
        headers["Authorization"] = f"Bearer {API_AUTH_TOKEN}"
    return headers

async def fetch_available_slots(date_str: str, branch_id: int = 13) -> List[Dict[str, Any]]:
    """
    Fetches real-time doctor availability slots from the main clinic website.
    Uses Redis cache first (5-minute TTL) to ensure ultra-low latency.
    """
    # 1. Try Redis cache first
    try:
        from app.database.redis import get_redis
        redis = get_redis()
        cache_key = f"slots_cache:{date_str}"
        cached = await redis.get(cache_key)
        if cached:
            logger.info(f"⚡ Slots cache hit in Redis for date: {date_str}")
            return json.loads(cached)
    except Exception as cache_err:
        logger.warning(f"Failed to read slots from Redis cache: {cache_err}")

    # 2. Cache miss: Fetch from live website using connection pool
    url = f"{API_BASE_URL}/slots"
    params = {
        "date": date_str,
        "branch_id": branch_id,
        "show_todays_fullslots": 1,
        "limit": 100
    }
    
    client = get_http_client()
    try:
        logger.info(f"🌐 Fetching available slots from main site for date: {date_str}")
        response = await client.get(url, params=params, headers=get_headers())
        
        if response.status_code == 200:
            data = response.json()
            slots = data.get("data", []) if isinstance(data, dict) else data
            
            # 3. Cache in Redis (5-minute TTL to keep slot counts reasonably fresh)
            try:
                from app.database.redis import get_redis
                redis = get_redis()
                cache_key = f"slots_cache:{date_str}"
                await redis.setex(cache_key, 300, json.dumps(slots))
                logger.info(f"💾 Cached {len(slots)} slots in Redis for date: {date_str}")
            except Exception as cache_err:
                logger.warning(f"Failed to write slots to Redis cache: {cache_err}")
                
            return slots
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
    """
    url = f"{API_BASE_URL}/bookings"
    
    payload = {
        "patient_name": patient_name,
        "phone": phone,
        "date": date_str,
        "slot_time": time_slot,
        "pain_type": pain_type,
        "booking_status": "booked",
        "branch_id": 13,
        "doctor_id": doctor_id,
        "service_id": service_id,
        "source": "whatsapp_bot"
    }
    
    client = get_http_client()
    try:
        logger.info(f"🌐 Submitting booking for {patient_name} to main site...")
        response = await client.post(url, json=payload, headers=get_headers())
        
        if response.status_code in [200, 201]:
            logger.info(f"✅ Website booking successful for {patient_name}")
            
            # Invalidate slots cache so the booked slot is updated immediately on next query
            try:
                from app.database.redis import get_redis
                redis = get_redis()
                cache_key = f"slots_cache:{date_str}"
                await redis.delete(cache_key)
                logger.info(f"🗑️ Invalidated slots cache for {date_str} due to new booking")
            except Exception as cache_err:
                logger.warning(f"Failed to invalidate slots cache: {cache_err}")
                
            return {"success": True, "data": response.json()}
        else:
            logger.error(f"❌ Website booking rejected: {response.status_code} - {response.text}")
            return {"success": False, "error": response.text}
    except Exception as e:
        logger.error(f"❌ Error sending booking to main website: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
