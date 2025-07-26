"""
Steam Game Changes Analyzer

Analyzes changes in steam_games.json over git history.
"""

import json
import logging
import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


class SteamChangesAnalyzer:
    """Analyzes changes in steam_games.json over git history"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.steam_games_path = project_root / "data" / "steam_games.json"

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

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )

        if result.returncode != 0:
            logging.error(f"Error running git log: {result.stderr}")
            return []

        commits = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|', 2)
                commit_hash = parts[0]
                commit_date = parts[1]
                commits.append((commit_hash, commit_date))

        return commits

    def get_file_at_commit(self, commit_hash: str) -> dict | None:
        """Get steam_games.json content at specific commit."""
        relative_path = self.steam_games_path.relative_to(self.project_root)
        cmd = ["git", "show", f"{commit_hash}:{relative_path}"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )

        if result.returncode != 0:
            return None

        try:
            data: dict = json.loads(result.stdout)
            return data
        except json.JSONDecodeError:
            return None

    def is_stubbed(self, name: str) -> bool:
        """Check if a game name indicates it's been stubbed/failed."""
        return name.startswith('[FAILED FETCH]') or name.startswith('[REDIRECT]')

    def extract_redirect_info(self, name: str) -> tuple[str | None, str | None]:
        """Extract redirect target ID and name from a redirect stub."""
        # Pattern: [REDIRECT] 3636780 -> 2068280
        match = re.match(r'\[REDIRECT\]\s*(\d+)\s*->\s*(\d+)', name)
        if match:
            return match.group(1), match.group(2)
        return None, None

    def compare_games(self, old_data: dict | None, new_data: dict | None) -> list[str]:
        """Compare two versions of steam_games.json and return changes."""
        changes = []

        if old_data is None:
            old_games = {}
        else:
            old_games = old_data.get('games', {})

        if new_data is None:
            new_games = {}
        else:
            new_games = new_data.get('games', {})

        # Find added games (excluding stubs)
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

        # Find removed games and stubbed games
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

        # Find modified games (excluding stub transitions which are handled above)
        for game_id in set(old_games.keys()) & set(new_games.keys()):
            old_game = old_games[game_id]
            new_game = new_games[game_id]
            old_name = old_game.get('name', 'Unknown')
            new_name = new_game.get('name', 'Unknown')

            # Skip if this is a stub transition (already handled)
            if not self.is_stubbed(old_name) and self.is_stubbed(new_name):
                continue

            # Skip if it was unstubbed (treat as new)
            if self.is_stubbed(old_name) and not self.is_stubbed(new_name):
                changes.append(f"RESTORED\t{game_id}\t{new_name}\tPreviously: {old_name}")
                continue

            game_changes = []
            price_changes = {}
            review_changes = {}

            # Check all fields except stub fields, last_updated, and header_image
            fields_to_check = [
                'name', 'release_date', 'price', 'discount', 'tags', 'description',
                'steam_url', 'is_free', 'coming_soon', 'genres', 'categories',
                'developers', 'publishers', 'price_eur', 'price_usd',
                'has_demo', 'demo_app_id', 'is_demo', 'full_game_app_id', 'is_early_access',
                'positive_review_percentage', 'review_count', 'review_summary',
                'recent_review_percentage', 'recent_review_count', 'recent_review_summary',
                'insufficient_reviews', 'planned_release_date', 'itch_url'
            ]

            price_fields = ['price', 'price_eur', 'price_usd', 'discount', 'is_free']
            review_fields = ['positive_review_percentage', 'review_count', 'review_summary',
                           'recent_review_percentage', 'recent_review_count', 'recent_review_summary']

            for field in fields_to_check:
                old_val = old_game.get(field)
                new_val = new_game.get(field)

                if old_val != new_val:
                    if field in ['tags', 'genres', 'categories', 'developers', 'publishers']:
                        # Handle list fields specially - combine into one entry
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
                            game_changes.append(f"{field}: {' '.join(item_parts)}")
                    elif field in price_fields:
                        # Collect price changes
                        old_str = str(old_val) if old_val is not None else "null"
                        new_str = str(new_val) if new_val is not None else "null"
                        price_changes[field] = (old_str, new_str)
                    elif field in review_fields:
                        # Collect review changes
                        if field in ['positive_review_percentage', 'review_count',
                                   'recent_review_percentage', 'recent_review_count'] and old_val is not None and new_val is not None:
                            try:
                                old_num = int(old_val)
                                new_num = int(new_val)
                                delta = new_num - old_num
                                sign = '+' if delta > 0 else ''
                                # Store just the raw value and delta - formatting will be done later
                                review_changes[field] = (new_num, f"({sign}{delta})")
                            except (ValueError, TypeError):
                                review_changes[field] = (old_val, f"→ {new_val}")
                        else:
                            review_changes[field] = (old_val, f"→ {new_val}")
                    else:
                        # Other fields remain as individual changes
                        # Truncate long values for other fields
                        old_str = str(old_val) if old_val is not None else "null"
                        new_str = str(new_val) if new_val is not None else "null"

                        if len(old_str) > 50:
                            old_str = old_str[:47] + "..."
                        if len(new_str) > 50:
                            new_str = new_str[:47] + "..."

                        game_changes.append(f"{field}: {old_str} → {new_str}")

            # Add consolidated price changes
            if price_changes:
                price_parts = []
                for field, (old_val, new_val) in price_changes.items():
                    # Format with arrow for later coloring
                    if field == 'price_eur':
                        price_parts.append(f"EUR: {old_val} → {new_val}")
                    elif field == 'price_usd':
                        price_parts.append(f"USD: {old_val} → {new_val}")
                    elif field == 'is_free':
                        price_parts.append(f"free: {old_val} → {new_val}")
                    elif field == 'discount':
                        price_parts.append(f"discount: {old_val} → {new_val}")
                    else:
                        price_parts.append(f"{field}: {old_val} → {new_val}")
                game_changes.append(f"PRICE: {', '.join(price_parts)}")

            # Add consolidated review changes
            if review_changes:
                review_parts = []
                # Order matters for readability
                review_order = ['positive_review_percentage', 'review_count', 'recent_review_percentage',
                              'recent_review_count', 'review_summary', 'recent_review_summary']
                for field in review_order:
                    if field in review_changes:
                        value_tuple = review_changes[field]
                        if isinstance(value_tuple, tuple):
                            value, delta = value_tuple  # type: ignore[assignment]
                            if field == 'positive_review_percentage':
                                review_parts.append(f"overall%: {value} {delta}")
                            elif field == 'review_count':
                                review_parts.append(f"overall№: {value} {delta}")
                            elif field == 'recent_review_percentage':
                                review_parts.append(f"recent%: {value} {delta}")
                            elif field == 'recent_review_count':
                                review_parts.append(f"recent№: {value} {delta}")
                            else:
                                # For summary fields that don't have numeric deltas
                                review_parts.append(f"{field.replace('_', '-')}: {value} {delta}")
                        else:
                            # Fallback for old format
                            if field == 'review_summary':
                                review_parts.append(f"summary: {value_tuple}")
                            elif field == 'recent_review_summary':
                                review_parts.append(f"recent-summary: {value_tuple}")
                game_changes.append(f"REVIEWS: {', '.join(review_parts)}")

            if game_changes:
                changes.extend(f"CHANGED\t{game_id}\t{new_name}\t{change}" for change in game_changes)

        return changes

    def analyze_changes(self, since_date: str = "1 week ago") -> None:
        """Analyze and print changes in steam_games.json since the given date.

        Args:
            since_date: Date to analyze changes from
        """
        print(f"Analyzing changes since: {since_date}")
        print("-" * 80)

        commits = self.get_git_log(since_date)

        if not commits:
            print("No commits found modifying steam_games.json")
            return

        # Git log returns newest first, but we want to process chronologically (oldest first)
        commits.reverse()

        # Process commits
        prev_data = None
        all_changes = []

        # Get initial state (commit before our range)
        if commits:
            # After reversal logic above, first commit is always the oldest one we'll process
            oldest_commit = commits[0][0]
            cmd = ["git", "rev-parse", f"{oldest_commit}^"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )
            if result.returncode == 0:
                parent_commit = result.stdout.strip()
                prev_data = self.get_file_at_commit(parent_commit)

        for commit_hash, commit_date in commits:
            current_data = self.get_file_at_commit(commit_hash)

            if current_data is not None:
                # Compare in the correct order: what changed FROM prev TO current
                changes = self.compare_games(prev_data, current_data)

                if changes:
                    # Parse and format date
                    dt = datetime.fromisoformat(commit_date.replace(' +', '+').replace(' -', '-'))
                    date_str = dt.strftime("%Y-%m-%d %H:%M")

                    all_changes.append({
                        'date': date_str,
                        'commit': commit_hash[:8],
                        'changes': changes
                    })

                prev_data = current_data

        # Print changes with nice formatting and colors
        for commit_changes in all_changes:
            # Print commit header in bold blue
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
                    print(f"\n  {color}{change_type}:{self.colors['reset']}")
                    for parts in grouped[change_type]:
                        if change_type == 'NEW':
                            if len(parts) >= 3:
                                game_id, name, release_info = parts
                                # Determine color based on release info
                                if release_info == 'No release date' or 'Coming soon' in release_info:
                                    color_code = self.colors['yellow']
                                else:
                                    color_code = self.colors['cyan']
                                # Simple formatting with color
                                colored_release = f"{color_code}({release_info}){self.colors['reset']}"
                                print(f"    {game_id:<10} {name:<40} {colored_release}")
                            else:
                                game_id, name = parts
                                print(f"    {game_id:<10} {name}")
                        elif change_type == 'REMOVED':
                            game_id, name = parts
                            print(f"    {game_id:<10} {name}")
                        elif change_type in ['STUBBED', 'RESTORED']:
                            if len(parts) >= 3:
                                game_id, name, info = parts
                                print(f"    {game_id:<10} {name:<40} {self.colors['cyan']}{info}{self.colors['reset']}")
                            else:
                                game_id, name = parts
                                print(f"    {game_id:<10} {name}")
                        else:  # CHANGED
                            game_id, name, change_desc = parts

                            # Extract field name and rest of description
                            if ':' in change_desc:
                                field_name, rest = change_desc.split(':', 1)

                                # Color code field names by category
                                field_colors = {
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

                                field_color = field_colors.get(field_name, '')  # No color for other fields
                                colored_desc = f"{field_color}{field_name}{self.colors['reset']}:{rest}"
                            else:
                                colored_desc = change_desc

                            # Special handling for consolidated fields
                            if field_name == 'PRICE':
                                # Color individual currency labels
                                colored_desc = colored_desc.replace('EUR:', f'{self.colors["bold"]}EUR:{self.colors["reset"]}')
                                colored_desc = colored_desc.replace('USD:', f'{self.colors["bold"]}USD:{self.colors["reset"]}')
                                colored_desc = colored_desc.replace('free:', f'{self.colors["bold"]}free:{self.colors["reset"]}')
                                colored_desc = colored_desc.replace('discount:', f'{self.colors["bold"]}discount:{self.colors["reset"]}')
                            elif field_name == 'REVIEWS':
                                # Color review labels and highlight positive/negative changes
                                colored_desc = colored_desc.replace('overall%:', f'{self.colors["bold"]}overall%:{self.colors["reset"]}')
                                colored_desc = colored_desc.replace('overall№:', f'{self.colors["bold"]}overall№:{self.colors["reset"]}')
                                colored_desc = colored_desc.replace('recent%:', f'{self.colors["bold"]}recent%:{self.colors["reset"]}')
                                colored_desc = colored_desc.replace('recent№:', f'{self.colors["bold"]}recent№:{self.colors["reset"]}')
                                colored_desc = colored_desc.replace('summary:', f'{self.colors["bold"]}summary:{self.colors["reset"]}')
                                colored_desc = colored_desc.replace('recent-summary:', f'{self.colors["bold"]}recent-summary:{self.colors["reset"]}')

                                # Color positive deltas green and negative deltas red
                                import re
                                # Match patterns like (+123) or (-45)
                                colored_desc = re.sub(r'\(\+(\d+)\)', rf'({self.colors["green"]}+\1{self.colors["reset"]})', colored_desc)
                                colored_desc = re.sub(r'\((-\d+)\)', rf'({self.colors["red"]}\1{self.colors["reset"]})', colored_desc)

                            # Color the arrow in change descriptions
                            colored_desc = colored_desc.replace(' → ', f' {self.colors["cyan"]}→{self.colors["reset"]} ')

                            # Special coloring for list field changes (tags, genres, categories, etc.)
                            if any(f"{field_color}{field}" in colored_desc for field in ['tags', 'genres', 'categories', 'developers', 'publishers'] for field_color in [self.colors['yellow']]):
                                # Color + items green and - items red
                                colored_desc = colored_desc.replace('+[', f'{self.colors["green"]}+[')
                                colored_desc = colored_desc.replace('] -[', f']{self.colors["reset"]} {self.colors["red"]}-[')
                                colored_desc = colored_desc.replace(']', f']{self.colors["reset"]}')
                                # Make sure standalone brackets get reset too
                                if not colored_desc.endswith(f'{self.colors["reset"]}'):
                                    colored_desc += self.colors["reset"]

                            print(f"    {game_id:<10} {name:<40} {colored_desc}")
