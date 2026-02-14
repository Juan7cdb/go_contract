from supabase import create_client, Client
from functools import lru_cache
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


@lru_cache()
def get_supabase_client() -> Client:
    """
    Returns a cached Supabase client instance.
    Uses lru_cache to ensure we don't create multiple clients.
    """
    try:
        client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Error initializing Supabase client: {e}")
        raise e


# For backward compatibility - but prefer using get_supabase_client() directly
supabase: Client = get_supabase_client()
