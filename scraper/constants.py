"""
Centralized constants for the scraper application
"""

# Steam Bulk Price Refresh Configuration
STEAM_BULK_DEFAULTS = {
    'default_batch_size': 500,
    'max_retries': 10,

    # Server Error (500) Configuration
    'server_error_batch_reduction': 0.8,  # Reduce batch size by 20% on server overload
    'server_error_max_delay': 30,  # Maximum delay in seconds for server error retries

    # Rate Limit (429) Configuration
    'rate_limit_delay': 10,  # Base delay for rate limits
    'rate_limit_max_delay': 300,  # Max 5 minutes for rate limits

    # Network Error Configuration
    'network_error_base_delay': 5,  # Start at 5 seconds
    'network_error_delay_increment': 3,  # Add 3 seconds per attempt
    'network_error_max_delay': 60,  # Max 1 minute for network errors
}

# HTTP Configuration
HTTP_TIMEOUT_SECONDS = 30
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# Video Processing Configuration
DEFAULT_MAX_VIDEOS_PER_CHANNEL = 50
CONSECUTIVE_KNOWN_BATCHES_THRESHOLD = 3
