"""
Steam Game Changes Analyzer

Analyzes changes in steam_games.json over git history.
"""

import json
import logging
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar


@dataclass
class GameChange:
    """Represents a single change to a game field."""
    game_id: str
    field_name: str
    old_value: Any
    new_value: Any
    change_type: str  # 'ADDED', 'REMOVED', 'CHANGED', 'STUBBED', 'RESTORED'
    formatted_description: str


@dataclass
class GameData:
    """Represents Steam game data with strong typing."""
    game_id: str
    name: str
    price_eur: int | str | None = None
    price_usd: int | str | None = None
    original_price_eur: int | str | None = None
    original_price_usd: int | str | None = None
    discount_percent: int | None = None
    is_free: bool = False
    release_date: str = ""
    coming_soon: bool = False
    tags: list[str] | None = None
    genres: list[str] | None = None
    categories: list[str] | None = None
    developers: list[str] | None = None
    publishers: list[str] | None = None
    positive_review_percentage: int | None = None
    review_count: int | None = None
    review_summary: str | None = None
    recent_review_percentage: int | None = None
    recent_review_count: int | None = None
    recent_review_summary: str | None = None
    insufficient_reviews: bool = False
    planned_release_date: str | None = None
    itch_url: str | None = None
    steam_url: str = ""
    has_demo: bool = False
    demo_app_id: str | None = None
    is_demo: bool = False
    full_game_app_id: str | None = None
    is_early_access: bool = False

    @classmethod
    def from_dict(cls, game_id: str, data: dict[str, Any]) -> 'GameData':
        """Create GameData from dictionary representation."""
        return cls(
            game_id=game_id,
            name=data.get('name', 'Unknown'),
            price_eur=data.get('price_eur'),
            price_usd=data.get('price_usd'),
            original_price_eur=data.get('original_price_eur'),
            original_price_usd=data.get('original_price_usd'),
            discount_percent=data.get('discount_percent'),
            is_free=data.get('is_free', False),
            release_date=data.get('release_date', ''),
            coming_soon=data.get('coming_soon', False),
            tags=data.get('tags'),
            genres=data.get('genres'),
            categories=data.get('categories'),
            developers=data.get('developers'),
            publishers=data.get('publishers'),
            positive_review_percentage=data.get('positive_review_percentage'),
            review_count=data.get('review_count'),
            review_summary=data.get('review_summary'),
            recent_review_percentage=data.get('recent_review_percentage'),
            recent_review_count=data.get('recent_review_count'),
            recent_review_summary=data.get('recent_review_summary'),
            insufficient_reviews=data.get('insufficient_reviews', False),
            planned_release_date=data.get('planned_release_date'),
            itch_url=data.get('itch_url'),
            steam_url=data.get('steam_url', ''),
            has_demo=data.get('has_demo', False),
            demo_app_id=data.get('demo_app_id'),
            is_demo=data.get('is_demo', False),
            full_game_app_id=data.get('full_game_app_id'),
            is_early_access=data.get('is_early_access', False)
        )


@dataclass
class CommitInfo:
    """Represents git commit information."""
    hash: str
    date: str
    short_hash: str

    @property
    def formatted_date(self) -> str:
        """Get formatted date for display."""
        try:
            dt = datetime.fromisoformat(self.date.replace(' +', '+').replace(' -', '-'))
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return self.date


class PriceChangeFormatter:
    """Handles formatting of price changes with discount logic."""

    def __init__(self, analyzer: 'SteamChangesAnalyzer'):
        self.analyzer = analyzer

    def _get_game_field(self, game: GameData | dict[str, Any], field: str) -> Any:
        """Get field value from GameData object or dict."""
        if isinstance(game, GameData):
            return getattr(game, field, None)
        else:
            return game.get(field)

    def format_price_change_with_discount(self, price_changes: dict[str, tuple[str, str]],
                                         currency: str, new_game: GameData | dict[str, Any], old_game: GameData | dict[str, Any]) -> str | None:
        """Format price changes considering discounts for a specific currency."""
        currency_upper = currency.upper()
        price_field = f'price_{currency}'
        original_price_field = f'original_price_{currency}'

        # Get current values from game data
        new_original = self._get_game_field(new_game, original_price_field)
        new_discount_percent = self._get_game_field(new_game, 'discount_percent')

        old_original = self._get_game_field(old_game, original_price_field)
        old_discount_percent = self._get_game_field(old_game, 'discount_percent')

        # Check if this currency had any changes
        has_price_change = price_field in price_changes
        has_original_change = original_price_field in price_changes
        has_discount_change = 'discount_percent' in price_changes

        if not (has_price_change or has_original_change or has_discount_change):
            return None

        # Determine if we're dealing with a sale scenario
        new_has_sale = new_original and new_discount_percent and int(str(new_discount_percent)) > 0
        old_has_sale = old_original and old_discount_percent and int(str(old_discount_percent)) > 0

        # Format the change based on sale status
        if new_has_sale:
            # New state has a sale - show base price and discount
            base_price = self.analyzer._format_price(str(new_original), currency_upper)
            discount_rate = f"-{new_discount_percent}%"

            if old_has_sale:
                # Was on sale, still on sale - show change if significant
                old_base_price = self.analyzer._format_price(str(old_original), currency_upper)
                old_discount_rate = f"-{old_discount_percent}%"

                if old_base_price != base_price or old_discount_rate != discount_rate:
                    return f"{old_base_price} {old_discount_rate} → {base_price} {discount_rate}"
                else:
                    return None  # No meaningful change
            else:
                # Went on sale - just show base price and discount rate
                return f"{base_price} {discount_rate}"

        elif old_has_sale and not new_has_sale:
            # Sale ended - show the change from discounted to regular price
            if has_price_change:
                old_base_price = self.analyzer._format_price(str(old_original), currency_upper)
                old_discount_rate = f"-{old_discount_percent}%"
                new_formatted = self.analyzer._format_price(price_changes[price_field][1], currency_upper)
                return f"{old_base_price} {old_discount_rate} → {new_formatted} (sale ended)"
            else:
                return "(sale ended)"

        elif has_price_change:
            # Regular price change (no sales involved)
            old_formatted = self.analyzer._format_price(price_changes[price_field][0], currency_upper)
            new_formatted = self.analyzer._format_price(price_changes[price_field][1], currency_upper)
            return f"{old_formatted} → {new_formatted}"

        return None

    def format_individual_price_change(self, price_changes: dict[str, tuple[str, str]],
                                      currency: str, new_game: GameData | dict[str, Any], old_game: GameData | dict[str, Any]) -> str | None:
        """Format individual currency price changes without discount logic."""
        currency_upper = currency.upper()
        price_field = f'price_{currency}'
        original_price_field = f'original_price_{currency}'

        # Check if this currency had any changes
        has_price_change = price_field in price_changes
        has_original_change = original_price_field in price_changes

        if not (has_price_change or has_original_change):
            return None

        # For price changes, show the base price (original if on sale, otherwise current price)
        if has_price_change:
            old_val, new_val = price_changes[price_field]

            # Check if new state is on sale - if so, show original price instead
            new_original = self._get_game_field(new_game, original_price_field)
            new_discount_percent = self._get_game_field(new_game, 'discount_percent')
            is_on_sale = new_original and new_discount_percent and int(str(new_discount_percent)) > 0

            if is_on_sale:
                # Show original (base) price instead of discounted price
                new_formatted = self.analyzer._format_price(str(new_original), currency_upper)
            else:
                new_formatted = self.analyzer._format_price(new_val, currency_upper)

            # Check if old state was on sale
            old_original = self._get_game_field(old_game, original_price_field)
            old_discount_percent = self._get_game_field(old_game, 'discount_percent')
            was_on_sale = old_original and old_discount_percent and int(str(old_discount_percent)) > 0

            if was_on_sale:
                old_formatted = self.analyzer._format_price(str(old_original), currency_upper)
            else:
                old_formatted = self.analyzer._format_price(old_val, currency_upper)

            if old_formatted != new_formatted:
                return f"{old_formatted} → {new_formatted}"

        # Handle original price changes (base price changes while on sale)
        elif has_original_change:
            old_val, new_val = price_changes[original_price_field]
            old_formatted = self.analyzer._format_price(old_val, currency_upper)
            new_formatted = self.analyzer._format_price(new_val, currency_upper)
            return f"{old_formatted} → {new_formatted}"

        return None


class SteamChangesAnalyzer:
    """Analyzes changes in steam_games.json over git history"""

    # Display constants
    GAME_ID_WIDTH: ClassVar[int] = 10
    GAME_NAME_WIDTH: ClassVar[int] = 40
    LIST_FIELDS: ClassVar[list[str]] = ['tags', 'genres', 'categories', 'developers', 'publishers']

    # Field configuration constants
    MONITORED_FIELDS: ClassVar[list[str]] = [
        'name', 'release_date', 'price', 'tags', 'description',
        'steam_url', 'is_free', 'coming_soon', 'genres', 'categories',
        'developers', 'publishers', 'price_eur', 'price_usd',
        'original_price_eur', 'original_price_usd', 'discount_percent',
        'has_demo', 'demo_app_id', 'is_demo', 'full_game_app_id', 'is_early_access',
        'positive_review_percentage', 'review_count', 'review_summary',
        'recent_review_percentage', 'recent_review_count', 'recent_review_summary',
        'insufficient_reviews', 'planned_release_date', 'itch_url'
    ]
    PRICE_FIELDS: ClassVar[set[str]] = {
        'price', 'price_eur', 'price_usd', 'original_price_eur',
        'original_price_usd', 'discount_percent', 'is_free'
    }
    REVIEW_FIELDS: ClassVar[set[str]] = {
        'positive_review_percentage', 'review_count', 'review_summary',
        'recent_review_percentage', 'recent_review_count', 'recent_review_summary'
    }
    GENERAL_FIELDS: ClassVar[list[str]] = [
        'name', 'release_date', 'steam_url', 'coming_soon', 'has_demo',
        'demo_app_id', 'is_demo', 'full_game_app_id', 'is_early_access',
        'insufficient_reviews', 'planned_release_date', 'itch_url',
        'tags', 'genres', 'categories', 'developers', 'publishers'
    ]
    MAX_FIELD_LENGTH: ClassVar[int] = 50

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.steam_games_path = project_root / "data" / "steam_games.json"
        self.price_formatter = PriceChangeFormatter(self)

        # ANSI color codes
        self.colors = {
            'green': '\033[92m',
            'red': '\033[91m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'cyan': '\033[96m',
            'reset': '\033[0m',
            'bold': '\033[1m'
        }

    def get_git_log(self, since_date: str) -> list[tuple[str, str]]:
        """Get list of commits that modified steam_games.json since given date."""
        cmd = [
            "git", "log",
            f"--since={since_date}",
            "--pretty=format:%H|%ci|%s",
            "--",
            str(self.steam_games_path.relative_to(self.project_root))
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=30  # Add timeout to prevent hanging
            )

            if result.returncode != 0:
                logging.error(f"Error running git log: {result.stderr}")
                return []

            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 2)
                    if len(parts) >= 2:
                        commit_hash = parts[0]
                        commit_date = parts[1]
                        commits.append((commit_hash, commit_date))
                    else:
                        logging.warning(f"Malformed git log line: {line}")

            return commits
        except subprocess.TimeoutExpired:
            logging.error(f"Timeout running git log for {since_date}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error running git log: {e}")
            return []

    def get_file_at_commit(self, commit_hash: str) -> dict[str, Any] | None:
        """Get steam_games.json content at specific commit."""
        relative_path = self.steam_games_path.relative_to(self.project_root)
        cmd = ["git", "show", f"{commit_hash}:{relative_path}"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=30  # Add timeout to prevent hanging
            )

            if result.returncode != 0:
                logging.error(f"Git show failed for {commit_hash}: {result.stderr}")
                return None

            data = json.loads(result.stdout)
            # Validate that we got a dict as expected
            if not isinstance(data, dict):
                logging.error(f"Expected dict from steam_games.json at {commit_hash}, got {type(data)}")
                return None
            return data
        except subprocess.TimeoutExpired:
            logging.error(f"Timeout getting file at commit {commit_hash}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error for commit {commit_hash}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error getting file at commit {commit_hash}: {e}")
            return None

    def get_multiple_files_at_commits(self, commits: list[tuple[str, str]]) -> dict[str, dict[str, Any]]:
        """Get steam_games.json content for multiple commits in a single operation."""
        if not commits:
            return {}

        relative_path = self.steam_games_path.relative_to(self.project_root)
        results = {}

        # Batch process commits to reduce subprocess overhead
        batch_size = 10  # Process commits in batches to avoid too-long command lines
        for i in range(0, len(commits), batch_size):
            batch = commits[i:i + batch_size]
            batch_results = self._process_commit_batch(batch, relative_path)
            results.update(batch_results)

        return results

    def _process_commit_batch(self, commits: list[tuple[str, str]], relative_path: Path) -> dict[str, dict[str, Any]]:
        """Process a batch of commits using git batch commands."""
        results = {}

        for commit_hash, _ in commits:
            try:
                # Use git cat-file for better performance than git show
                cmd = ["git", "cat-file", "blob", f"{commit_hash}:{relative_path}"]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(self.project_root),
                    timeout=15  # Shorter timeout for individual operations
                )

                if result.returncode == 0:
                    try:
                        data = json.loads(result.stdout)
                        if isinstance(data, dict):
                            results[commit_hash] = data
                        else:
                            logging.warning(f"Invalid data type from {commit_hash}: {type(data)}")
                    except json.JSONDecodeError as e:
                        logging.warning(f"JSON decode error for {commit_hash}: {e}")
                else:
                    # Fallback to git show for edge cases
                    fallback_data = self.get_file_at_commit(commit_hash)
                    if fallback_data:
                        results[commit_hash] = fallback_data

            except subprocess.TimeoutExpired:
                logging.warning(f"Timeout processing commit {commit_hash}")
                continue
            except Exception as e:
                logging.warning(f"Error processing commit {commit_hash}: {e}")
                continue

        return results

    def is_stubbed(self, name: str) -> bool:
        """Check if a game name indicates it's been stubbed/failed."""
        return name.startswith('[FAILED FETCH]') or name.startswith('[REDIRECT]')

    def _safe_str(self, value: Any) -> str:
        """Convert value to string, using 'null' for None values."""
        return str(value) if value is not None else "null"

    def extract_redirect_info(self, name: str) -> tuple[str | None, str | None]:
        """Extract redirect target ID and name from a redirect stub."""
        # Pattern: [REDIRECT] 3636780 -> 2068280
        match = re.match(r'\[REDIRECT\]\s*(\d+)\s*->\s*(\d+)', name)
        if match:
            return match.group(1), match.group(2)
        return None, None

    def _format_price(self, value: str, currency: str) -> str:
        """Format price value from cents to currency display."""
        if value == "null" or value is None:
            return "null"

        try:
            cents = int(value)
            if cents == 0:
                return "Free"

            # Convert cents to decimal amount
            amount = cents / 100

            if currency == 'EUR':
                return f"€{amount:.2f}"
            elif currency == 'USD':
                return f"${amount:.2f}"
            else:
                return f"{amount:.2f}"
        except (ValueError, TypeError):
            return value



    def _find_added_games(self, old_games: dict[str, Any], new_games: dict[str, Any]) -> list[str]:
        """Find games that were added in the new version."""
        changes = []
        for game_id, game_data in new_games.items():
            if game_id not in old_games:
                name = game_data.get('name', 'Unknown')
                if not self.is_stubbed(name):
                    # Get release info and normalize it
                    release_date = game_data.get('release_date', '')
                    if release_date:
                        # Normalize date string to consistent length
                        # Pad single-digit days with a space instead of zero
                        normalized_date = re.sub(r'\b(\d) ([A-Za-z]+, \d{4})', r' \1 \2', release_date)
                        changes.append(f"NEW\t{game_id}\t{name}\t{normalized_date}")
                    else:
                        changes.append(f"NEW\t{game_id}\t{name}\tNo release date")
        return changes

    def _find_removed_and_stubbed_games(self, old_games: dict[str, Any], new_games: dict[str, Any]) -> list[str]:
        """Find games that were removed or became stubbed."""
        changes = []
        for game_id, game_data in old_games.items():
            old_name = game_data.get('name', 'Unknown')

            if game_id not in new_games:
                # Completely removed
                changes.append(f"REMOVED\t{game_id}\t{old_name}")
            elif game_id in new_games:
                new_name = new_games[game_id].get('name', 'Unknown')
                # Check if it became stubbed
                if not self.is_stubbed(old_name) and self.is_stubbed(new_name):
                    if new_name.startswith('[REDIRECT]'):
                        _, redirect_target = self.extract_redirect_info(new_name)
                        if redirect_target:
                            changes.append(f"STUBBED\t{game_id}\t{old_name}\tRedirected to {redirect_target}")
                        else:
                            changes.append(f"STUBBED\t{game_id}\t{old_name}\tRedirect (unknown target)")
                    else:
                        changes.append(f"STUBBED\t{game_id}\t{old_name}\tFailed to fetch")
        return changes

    def _find_modified_games(self, old_games: dict[str, Any], new_games: dict[str, Any]) -> list[str]:
        """Find games that were modified."""
        changes = []

        for game_id in set(old_games.keys()) & set(new_games.keys()):
            game_changes = self._analyze_single_game_changes(game_id, old_games[game_id], new_games[game_id])
            changes.extend(game_changes)

        return changes

    def _analyze_single_game_changes(self, game_id: str, old_game: dict[str, Any], new_game: dict[str, Any]) -> list[str]:
        """Analyze changes for a single game."""
        old_name = old_game.get('name', 'Unknown')
        new_name = new_game.get('name', 'Unknown')

        # Handle special cases first
        if not self.is_stubbed(old_name) and self.is_stubbed(new_name):
            return []  # Skip stub transitions (handled elsewhere)

        if self.is_stubbed(old_name) and not self.is_stubbed(new_name):
            return [f"RESTORED\t{game_id}\t{new_name}\tPreviously: {old_name}"]

        # Analyze field changes
        game_changes = []
        price_changes, review_changes = self._collect_field_changes(old_game, new_game)

        # Process non-price, non-review field changes
        game_changes.extend(self._process_general_field_changes(old_game, new_game))

        # Process consolidated price changes
        if price_changes:
            price_summary = self._format_consolidated_price_changes(price_changes, old_game, new_game)
            if price_summary:
                game_changes.append(f"PRICE: {price_summary}")

        # Process consolidated review changes
        if review_changes:
            review_summary = self._format_consolidated_review_changes(review_changes)
            if review_summary:
                game_changes.append(f"REVIEWS: {review_summary}")

        return [f"CHANGED\t{game_id}\t{new_name}\t{change}" for change in game_changes] if game_changes else []

    def _collect_field_changes(self, old_game: dict[str, Any], new_game: dict[str, Any]) -> tuple[dict[str, tuple[str, str]], dict[str, tuple[Any, str]]]:
        """Collect price and review changes from field differences."""
        price_changes = {}
        review_changes = {}

        for field in self.MONITORED_FIELDS:
            old_val = old_game.get(field)
            new_val = new_game.get(field)

            if old_val != new_val:
                if field in self.PRICE_FIELDS:
                    price_changes[field] = (self._safe_str(old_val), self._safe_str(new_val))
                elif field in self.REVIEW_FIELDS:
                    review_changes[field] = self._format_review_change(field, old_val, new_val)

        return price_changes, review_changes

    def _process_general_field_changes(self, old_game: dict[str, Any], new_game: dict[str, Any]) -> list[str]:
        """Process non-price, non-review field changes."""
        changes = []

        for field in self.GENERAL_FIELDS:
            old_val = old_game.get(field)
            new_val = new_game.get(field)

            if old_val != new_val:
                if field in self.LIST_FIELDS:
                    change = self._format_list_field_change(field, old_val, new_val)
                    if change:
                        changes.append(change)
                elif field not in self.PRICE_FIELDS and field not in self.REVIEW_FIELDS:
                    changes.append(self._format_simple_field_change(field, old_val, new_val))

        return changes

    def _format_list_field_change(self, field: str, old_val: Any, new_val: Any) -> str | None:
        """Format changes in list fields (tags, genres, etc.)."""
        old_items = set(old_val) if old_val else set()
        new_items = set(new_val) if new_val else set()
        added_items = new_items - old_items
        removed_items = old_items - new_items

        if added_items or removed_items:
            item_parts = []
            if added_items:
                item_parts.append(f"+[{', '.join(sorted(added_items))}]")
            if removed_items:
                item_parts.append(f"-[{', '.join(sorted(removed_items))}]")
            return f"{field}: {' '.join(item_parts)}"
        return None

    def _format_simple_field_change(self, field: str, old_val: Any, new_val: Any) -> str:
        """Format simple field changes with truncation."""
        old_str = self._safe_str(old_val)
        new_str = self._safe_str(new_val)

        # Truncate long values
        if len(old_str) > self.MAX_FIELD_LENGTH:
            old_str = old_str[:self.MAX_FIELD_LENGTH - 3] + "..."
        if len(new_str) > self.MAX_FIELD_LENGTH:
            new_str = new_str[:self.MAX_FIELD_LENGTH - 3] + "..."

        return f"{field}: {old_str} → {new_str}"

    def _format_review_change(self, field: str, old_val: Any, new_val: Any) -> tuple[Any, str]:
        """Format review field changes with delta calculation."""
        if field in ['positive_review_percentage', 'review_count', 'recent_review_percentage', 'recent_review_count'] and old_val is not None and new_val is not None:
            try:
                old_num = int(old_val)
                new_num = int(new_val)
                delta = new_num - old_num
                sign = '+' if delta > 0 else ''
                return (new_num, f"({sign}{delta})")
            except (ValueError, TypeError):
                return (old_val, f"→ {new_val}")
        else:
            return (old_val, f"→ {new_val}")

    def _format_consolidated_price_changes(self, price_changes: dict[str, tuple[str, str]], old_game: dict[str, Any], new_game: dict[str, Any]) -> str:
        """Format consolidated price changes including currency and discount logic."""
        price_parts = []

        # Handle individual currency price changes
        for currency in ['eur', 'usd']:
            currency_part = self.price_formatter.format_individual_price_change(price_changes, currency, new_game, old_game)
            if currency_part:
                price_parts.append(currency_part)

        # Handle discount state changes
        discount_part = self._format_discount_changes(old_game, new_game)
        if discount_part:
            price_parts.append(discount_part)

        # Handle other price fields
        for field, (old_val, new_val) in price_changes.items():
            if field not in ['price_eur', 'price_usd', 'original_price_eur', 'original_price_usd', 'discount_percent']:
                if field == 'is_free':
                    price_parts.append(f"free: {old_val} → {new_val}")
                else:
                    price_parts.append(f"{field}: {old_val} → {new_val}")

        return ', '.join(price_parts)

    def _format_discount_changes(self, old_game: dict[str, Any], new_game: dict[str, Any]) -> str | None:
        """Format discount state changes."""
        old_has_real_discount = bool(old_game.get('original_price_eur') or old_game.get('original_price_usd'))
        new_has_real_discount = bool(new_game.get('original_price_eur') or new_game.get('original_price_usd'))

        old_discount_percent = old_game.get('discount_percent', 0)
        new_discount_percent = new_game.get('discount_percent', 0)

        old_discount_int = int(str(old_discount_percent)) if old_discount_percent else 0
        new_discount_int = int(str(new_discount_percent)) if new_discount_percent else 0

        # Check if discount state actually changed
        if old_has_real_discount != new_has_real_discount or (old_has_real_discount and new_has_real_discount and old_discount_int != new_discount_int):
            if not old_has_real_discount and new_has_real_discount:
                # Discount introduced
                base_prices = []
                for currency, field in [('EUR', 'original_price_eur'), ('USD', 'original_price_usd')]:
                    original_price = new_game.get(field)
                    if original_price:
                        base_prices.append(self._format_price(str(original_price), currency))

                if base_prices:
                    return f"{', '.join(base_prices)}, discount: 0% → -{new_discount_int}%"
                else:
                    return f"discount: 0% → -{new_discount_int}%"

            elif old_has_real_discount and not new_has_real_discount:
                # Discount removed
                final_prices = []
                for currency, field in [('EUR', 'price_eur'), ('USD', 'price_usd')]:
                    price = new_game.get(field)
                    if price:
                        final_prices.append(self._format_price(str(price), currency))

                if final_prices:
                    return f"{', '.join(final_prices)}, discount: -{old_discount_int}% → 0%"
                else:
                    return f"discount: -{old_discount_int}% → 0%"

            elif old_has_real_discount and new_has_real_discount and old_discount_int != new_discount_int:
                # Discount percentage changed
                return f"discount: -{old_discount_int}% → -{new_discount_int}%"

        return None

    def _format_consolidated_review_changes(self, review_changes: dict[str, tuple[Any, str]]) -> str:
        """Format consolidated review changes."""
        review_parts = []
        review_order = ['positive_review_percentage', 'review_count', 'recent_review_percentage',
                       'recent_review_count', 'review_summary', 'recent_review_summary']

        for field in review_order:
            if field in review_changes:
                value_tuple = review_changes[field]
                if isinstance(value_tuple, tuple):
                    value, delta = value_tuple
                    if field == 'positive_review_percentage':
                        review_parts.append(f"overall%: {value} {delta}")
                    elif field == 'review_count':
                        review_parts.append(f"overall№: {value} {delta}")
                    elif field == 'recent_review_percentage':
                        review_parts.append(f"recent%: {value} {delta}")
                    elif field == 'recent_review_count':
                        review_parts.append(f"recent№: {value} {delta}")
                    else:
                        review_parts.append(f"{field.replace('_', '-')}: {value} {delta}")
                else:
                    # Fallback for old format
                    if field == 'review_summary':
                        review_parts.append(f"summary: {value_tuple}")
                    elif field == 'recent_review_summary':
                        review_parts.append(f"recent-summary: {value_tuple}")

        return ', '.join(review_parts)

    def compare_games(self, old_data: dict[str, Any] | None, new_data: dict[str, Any] | None) -> list[str]:
        """Compare two versions of steam_games.json and return changes."""
        if old_data is None:
            old_games = {}
        else:
            old_games = old_data.get('games', {})

        if new_data is None:
            new_games = {}
        else:
            new_games = new_data.get('games', {})

        changes = []

        # Find added games (excluding stubs)
        changes.extend(self._find_added_games(old_games, new_games))

        # Find removed games and stubbed games
        changes.extend(self._find_removed_and_stubbed_games(old_games, new_games))

        # Find modified games
        changes.extend(self._find_modified_games(old_games, new_games))


        return changes

    def _get_field_colors(self) -> dict[str, str]:
        """Get field color mapping for display formatting."""
        return {
            # Consolidated fields
            'PRICE': self.colors['green'],
            'REVIEWS': self.colors['blue'],

            # Review fields - blue
            'positive_review_percentage': self.colors['blue'],
            'review_count': self.colors['blue'],
            'review_summary': self.colors['blue'],
            'recent_review_percentage': self.colors['blue'],
            'recent_review_count': self.colors['blue'],
            'recent_review_summary': self.colors['blue'],
            'insufficient_reviews': self.colors['blue'],

            # Price fields - green
            'price': self.colors['green'],
            'price_eur': self.colors['green'],
            'price_usd': self.colors['green'],
            'discount': self.colors['green'],
            'is_free': self.colors['green'],

            # List fields - yellow
            'tags': self.colors['yellow'],
            'genres': self.colors['yellow'],
            'categories': self.colors['yellow'],
            'developers': self.colors['yellow'],
            'publishers': self.colors['yellow'],

            # Release/demo fields - cyan
            'release_date': self.colors['cyan'],
            'coming_soon': self.colors['cyan'],
            'planned_release_date': self.colors['cyan'],
            'has_demo': self.colors['cyan'],
            'demo_app_id': self.colors['cyan'],
            'is_demo': self.colors['cyan'],
            'full_game_app_id': self.colors['cyan'],
            'is_early_access': self.colors['cyan'],
        }

    def _is_list_field_change(self, colored_desc: str) -> bool:
        """Check if this is a list field change that needs special coloring."""
        yellow_color = self.colors['yellow']
        return any(f"{yellow_color}{field}" in colored_desc for field in self.LIST_FIELDS)

    def _format_change_description(self, field_name: str | None, change_desc: str) -> str:
        """Format a change description with proper coloring."""
        if field_name and ':' in change_desc:
            field_name, rest = change_desc.split(':', 1)
            field_colors = self._get_field_colors()
            field_color = field_colors.get(field_name, '')
            colored_desc = f"{field_color}{field_name}{self.colors['reset']}:{rest}"
        else:
            colored_desc = change_desc

        # Special handling for consolidated fields
        if field_name == 'PRICE':
            colored_desc = colored_desc.replace('free:', f'{self.colors["bold"]}free:{self.colors["reset"]}')
            colored_desc = colored_desc.replace('discount:', f'{self.colors["bold"]}discount:{self.colors["reset"]}')
        elif field_name == 'REVIEWS':
            # Color review labels and highlight positive/negative changes
            review_labels = ['overall%:', 'overall№:', 'recent%:', 'recent№:', 'summary:', 'recent-summary:']
            for label in review_labels:
                colored_desc = colored_desc.replace(label, f'{self.colors["bold"]}{label}{self.colors["reset"]}')

            # Color positive deltas green and negative deltas red
            colored_desc = re.sub(r'\(\+(\d+)\)', rf'({self.colors["green"]}+\1{self.colors["reset"]})', colored_desc)
            colored_desc = re.sub(r'\((-\d+)\)', rf'({self.colors["red"]}\1{self.colors["reset"]})', colored_desc)

        # Color the arrow in change descriptions
        colored_desc = colored_desc.replace(' → ', f' {self.colors["cyan"]}→{self.colors["reset"]} ')

        # Special coloring for list field changes
        if self._is_list_field_change(colored_desc):
            colored_desc = colored_desc.replace('+[', f'{self.colors["green"]}+[')
            colored_desc = colored_desc.replace('] -[', f']{self.colors["reset"]} {self.colors["red"]}-[')
            colored_desc = colored_desc.replace(']', f']{self.colors["reset"]}')
            if not colored_desc.endswith(f'{self.colors["reset"]}'):
                colored_desc += self.colors["reset"]

        return colored_desc

    def _print_change_group(self, change_type: str, color: str, parts_list: list[list[str]]) -> None:
        """Print a group of changes with proper formatting."""
        print(f"\n  {color}{change_type}:{self.colors['reset']}")

        for parts in parts_list:
            if change_type == 'NEW':
                if len(parts) >= 3:
                    game_id, name, release_info = parts
                    if release_info == 'No release date' or 'Coming soon' in release_info:
                        color_code = self.colors['yellow']
                    else:
                        color_code = self.colors['cyan']
                    colored_release = f"{color_code}({release_info}){self.colors['reset']}"
                    print(f"    {game_id:<{self.GAME_ID_WIDTH}} {name:<{self.GAME_NAME_WIDTH}} {colored_release}")
                else:
                    game_id, name = parts
                    print(f"    {game_id:<{self.GAME_ID_WIDTH}} {name}")
            elif change_type == 'REMOVED':
                game_id, name = parts
                print(f"    {game_id:<{self.GAME_ID_WIDTH}} {name}")
            elif change_type in ['STUBBED', 'RESTORED']:
                if len(parts) >= 3:
                    game_id, name, info = parts
                    print(f"    {game_id:<{self.GAME_ID_WIDTH}} {name:<{self.GAME_NAME_WIDTH}} {self.colors['cyan']}{info}{self.colors['reset']}")
                else:
                    game_id, name = parts
                    print(f"    {game_id:<{self.GAME_ID_WIDTH}} {name}")
            else:  # CHANGED
                game_id, name, change_desc = parts
                field_name = change_desc.split(':', 1)[0] if ':' in change_desc else None
                colored_desc = self._format_change_description(field_name, change_desc)
                print(f"    {game_id:<{self.GAME_ID_WIDTH}} {name:<{self.GAME_NAME_WIDTH}} {colored_desc}")

    def _process_commits_for_changes(self, commits: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """Process commits and return structured change data."""
        all_changes = []

        # Performance optimization: batch fetch all commit data
        logging.debug(f"Batch fetching data for {len(commits)} commits")
        commit_data = self.get_multiple_files_at_commits(commits)

        # Get initial state for the first commit
        prev_data = None
        if commits:
            first_commit_hash = commits[0][0]
            parent_hash = self._get_parent_commit(first_commit_hash)
            if parent_hash:
                try:
                    prev_data = self.get_file_at_commit(parent_hash)
                except Exception as e:
                    logging.warning(f"Could not get initial state from parent {parent_hash}: {e}")
                    prev_data = None

        for commit_hash, commit_date in commits:
            try:
                current_data = commit_data.get(commit_hash)
                if current_data is not None:
                    changes = self.compare_games(prev_data, current_data)
                    if changes:
                        commit_info = CommitInfo(
                            hash=commit_hash,
                            date=commit_date,
                            short_hash=commit_hash[:8]
                        )

                        all_changes.append({
                            'date': commit_info.formatted_date,
                            'commit': commit_info.short_hash,
                            'changes': changes
                        })
                    prev_data = current_data
                else:
                    logging.warning(f"No data retrieved for commit {commit_hash}")
            except Exception as e:
                logging.error(f"Error processing commit {commit_hash}: {e}")
                continue

        return all_changes

    def _display_changes(self, commits_with_changes: list[dict[str, Any]]) -> None:
        """Display formatted changes with color coding."""
        if not commits_with_changes:
            print("No changes found in steam_games.json")
            return

        for commit_changes in commits_with_changes:
            # Print commit header
            print(f"\n{self.colors['bold']}{self.colors['blue']}{commit_changes['date']} ({commit_changes['commit']}){self.colors['reset']}")
            print("-" * 80)

            # Group changes by type
            grouped = defaultdict(list)
            for change in commit_changes['changes']:
                parts = change.split('\t')
                change_type = parts[0]
                grouped[change_type].append(parts[1:])

            # Print grouped changes with colors
            change_type_config = [
                ('NEW', self.colors['green']),
                ('REMOVED', self.colors['red']),
                ('STUBBED', self.colors['red']),
                ('RESTORED', self.colors['cyan']),
                ('CHANGED', self.colors['yellow'])
            ]

            for change_type, color in change_type_config:
                if change_type in grouped:
                    self._print_change_group(change_type, color, grouped[change_type])

    def analyze_last_commit(self) -> None:
        """Analyze and print changes in steam_games.json for only the last commit."""
        print("Analyzing changes in the last commit")
        print("-" * 80)

        try:
            # Get only the last commit
            commits = self.get_git_log("HEAD~1..HEAD")

            if not commits:
                print("No commits found modifying steam_games.json")
                return

            # Process the single commit and display results
            commits_data = self._process_commits_for_changes(commits[:1])
            self._display_changes(commits_data)

        except Exception as e:
            logging.error(f"Error analyzing last commit: {e}")
            print(f"Error: Could not analyze last commit - {e}")
            return

    def _get_parent_commit(self, commit_hash: str) -> str | None:
        """Get the parent commit hash for a given commit."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', f'{commit_hash}^'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
                timeout=10  # Add timeout to prevent hanging
            )
            parent_hash = result.stdout.strip()
            if not parent_hash:
                logging.warning(f"Empty parent hash for commit {commit_hash}")
                return None
            return parent_hash
        except subprocess.CalledProcessError as e:
            # No parent commit (e.g., initial commit) or other git error
            logging.debug(f"Could not get parent for commit {commit_hash}: {e}")
            return None
        except subprocess.TimeoutExpired:
            logging.error(f"Timeout getting parent commit for {commit_hash}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error getting parent commit for {commit_hash}: {e}")
            return None

    def analyze_changes(self, since_date: str = "1 week ago") -> None:
        """Analyze and print changes in steam_games.json since the given date.

        Args:
            since_date: Date to analyze changes from
        """
        print(f"Analyzing changes since: {since_date}")
        print("-" * 80)

        try:
            commits = self.get_git_log(since_date)

            if not commits:
                print("No commits found modifying steam_games.json")
                return

            # Git log returns newest first, but we want to process chronologically (oldest first)
            commits.reverse()

            # Process commits and display results
            commits_data = self._process_commits_for_changes(commits)
            self._display_changes(commits_data)

        except Exception as e:
            logging.error(f"Error analyzing changes since {since_date}: {e}")
            print(f"Error: Could not analyze changes - {e}")
            return
