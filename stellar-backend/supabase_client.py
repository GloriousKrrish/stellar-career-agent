"""
Supabase Client and Connection Verification.
"""
from __future__ import annotations
import os
import requests
from supabase import create_client, Client
from config import get_settings
from logger import get_logger

log = get_logger("Supabase")
settings = get_settings()

# Read from settings or environment variables
SUPABASE_URL = settings.supabase_url or os.getenv("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = settings.supabase_anon_key or os.getenv("SUPABASE_ANON_KEY", "").strip()
SUPABASE_SERVICE_ROLE_KEY = settings.supabase_service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

# Initialize Supabase flags
SUPABASE_ENABLED = False
supabase: Client | None = None

# Validate configuration presence
missing = []
if not SUPABASE_URL:
    missing.append("SUPABASE_URL")
if not SUPABASE_ANON_KEY:
    missing.append("SUPABASE_ANON_KEY")
if not SUPABASE_SERVICE_ROLE_KEY:
    missing.append("SUPABASE_SERVICE_ROLE_KEY")

if missing:
    log.info(f"Supabase connection disabled. Missing required variables: {', '.join(missing)}. Falling back to local SQLite database.")
else:
    # Verify format
    if not SUPABASE_URL.startswith("http://") and not SUPABASE_URL.startswith("https://"):
        log.warning(f"Invalid SUPABASE_URL: '{SUPABASE_URL}'. Must start with http:// or https://. Falling back to local SQLite.")
    else:
        log.info(f"Attempting to verify connection to Supabase at: {SUPABASE_URL}")
        # Test connection via REST API
        try:
            headers = {
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
            }
            response = requests.get(f"{SUPABASE_URL}/rest/v1/", headers=headers, timeout=5)
            if response.status_code not in (200, 204):
                log.warning(f"Supabase connection test failed. URL returned status {response.status_code}: {response.text}. Falling back to local SQLite.")
            else:
                log.info("Supabase connection verification: SUCCESS")
                # Initialize Supabase client
                # Using the Service Role Key so backend operations (like profile upserts) bypass RLS restrictions
                supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                SUPABASE_ENABLED = True
        except Exception as e:
            log.warning(f"Failed to connect to Supabase: {str(e)}. Falling back to local SQLite.")
