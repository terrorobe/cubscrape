"""
Batch Manager

Manages batch processing logic and size optimization.
Separated from HTTP and business logic for better maintainability.
"""

import logging
from typing import Any


class BatchManager:
    """Manages batch processing logic and size optimization"""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def create_batches(self, items: list[str], batch_size: int) -> list[list[str]]:
        """Create batches from a list of items"""
        if batch_size <= 0:
            raise ValueError("Batch size must be positive")

        batches = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batches.append(batch)

        return batches

    def reduce_batch_size_on_error(self, current_batch_size: int) -> int:
        """Reduce batch size when encountering server errors"""
        new_batch_size = max(
            int(current_batch_size * self.config['batch_size_reduction_factor']),
            int(self.config['min_batch_size'])
        )

        logging.warning(f"Reducing batch size: {current_batch_size} → {new_batch_size}")
        return new_batch_size

    def should_continue_with_batch_size(self, current_batch_size: int) -> bool:
        """Check if we should continue with the current batch size"""
        return current_batch_size >= self.config['min_batch_size']

    def get_initial_batch_size(self, requested_batch_size: int | None) -> int:
        """Get the initial batch size, using config default if none requested"""
        if requested_batch_size is not None:
            return int(requested_batch_size)
        return int(self.config['default_batch_size'])
