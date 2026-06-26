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

# Validate configuration presence
missing = []
if not SUPABASE_URL:
    missing.append("SUPABASE_URL")
if not SUPABASE_ANON_KEY:
    missing.append("SUPABASE_ANON_KEY")
if not SUPABASE_SERVICE_ROLE_KEY:
    missing.append("SUPABASE_SERVICE_ROLE_KEY")

if missing:
    error_msg = f"Missing required Supabase environment variables: {', '.join(missing)}. Please check your .env file."
    log.error(error_msg)
    raise ValueError(error_msg)

# Verify format
if not SUPABASE_URL.startswith("http://") and not SUPABASE_URL.startswith("https://"):
    error_msg = f"Invalid SUPABASE_URL: '{SUPABASE_URL}'. Must start with http:// or https://"
    log.error(error_msg)
    raise ValueError(error_msg)

log.info(f"Connecting to Supabase at: {SUPABASE_URL}")

# Test connection via REST API
try:
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
    response = requests.get(f"{SUPABASE_URL}/rest/v1/", headers=headers, timeout=5)
    if response.status_code not in (200, 204):
        error_msg = f"Supabase connection test failed. URL returned status {response.status_code}: {response.text}"
        log.error(error_msg)
        raise ValueError(error_msg)
    log.info("Supabase connection verification: SUCCESS")
except Exception as e:
    error_msg = f"Failed to connect to Supabase: {str(e)}"
    log.error(error_msg)
    raise ValueError(error_msg)

# Initialize Supabase client
# Using the Service Role Key so backend operations (like profile upserts) bypass RLS restrictions
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
