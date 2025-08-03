"""
Centralized constants for the scraper application
"""

# Steam Bulk Price Refresh Configuration
STEAM_BULK_DEFAULTS = {
    'default_batch_size': 500,
    'batch_size_reduction_factor': 0.8,  # Reduce by 20% on each retry
    'min_batch_size': 50,
    'rate_limit_delay': 2.5,
    'max_retries': 3
}

# HTTP Configuration
HTTP_TIMEOUT_SECONDS = 30
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# Video Processing Configuration
DEFAULT_MAX_VIDEOS_PER_CHANNEL = 50
CONSECUTIVE_KNOWN_BATCHES_THRESHOLD = 3
