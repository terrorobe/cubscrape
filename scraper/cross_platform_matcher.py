"""
Cross-Platform Game Matcher

Handles automatic linking and unlinking of games across platforms (Steam, Itch.io, etc.)
with intelligent precedence rules to avoid conflicts.
"""

import json
import logging
from pathlib import Path


class CrossPlatformMatcher:
    """Handles cross-platform game matching and linking with precedence rules"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.data_dir = project_root / 'data'

    def normalize_name(self, name: str) -> str:
        """Normalize game name for comparison"""
        if not name:
            return ""

        # Convert to lowercase and remove extra whitespace
        normalized = name.lower().strip()

        # Remove common suffixes and prefixes
        suffixes_to_remove = [
            " (demo)", " demo", "- demo", " (prototype)", " prototype",
            " (early access)", " early access", " (alpha)", " (beta)",
            " - prologue", " prologue"
        ]

        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()

        # Remove special characters and extra spaces
        import re
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    def find_exact_name_matches(self, steam_games: dict, other_games: dict) -> list[tuple[str, str, str]]:
        """Find exact name matches between Steam and other platform games

        Returns:
            List of tuples: (steam_app_id, other_game_url, platform)
        """
        matches = []

        # Create normalized name lookup for Steam games
        steam_by_name = {}
        for app_id, game_data in steam_games.items():
            normalized_name = self.normalize_name(game_data.get('name', ''))
            if normalized_name:
                if normalized_name not in steam_by_name:
                    steam_by_name[normalized_name] = []
                steam_by_name[normalized_name].append((app_id, game_data))

        # Find matches with other platform games
        for game_url, game_data in other_games.items():
            platform = game_data.get('platform', 'unknown')
            normalized_name = self.normalize_name(game_data.get('name', ''))

            if normalized_name and normalized_name in steam_by_name:
                for steam_app_id, _steam_data in steam_by_name[normalized_name]:
                    matches.append((steam_app_id, game_url, platform))

        return matches

    def apply_precedence_rules(self, steam_games: dict, matches: list[tuple[str, str, str]]) -> dict[str, str]:
        """Apply precedence rules to determine which games should be linked

        Rules:
        1. Steam demos take precedence over Itch demos
        2. If Steam has both demo and main game, ignore Itch version
        3. Only link if Steam game doesn't already have that platform link

        Returns:
            Dict mapping other_game_url -> steam_app_id for approved links
        """
        approved_links = {}
        steam_game_matches = {}  # Group matches by Steam app ID

        # Group matches by Steam app ID
        for steam_app_id, other_game_url, platform in matches:
            if steam_app_id not in steam_game_matches:
                steam_game_matches[steam_app_id] = []
            steam_game_matches[steam_app_id].append((other_game_url, platform))

        # Apply rules for each Steam game
        for steam_app_id, other_matches in steam_game_matches.items():
            steam_game = steam_games.get(steam_app_id, {})

            # Check if Steam game is a demo
            is_steam_demo = steam_game.get('is_demo', False)

            # Check if Steam game has a corresponding demo/full game
            has_demo_pair = (
                steam_game.get('demo_app_id') or
                steam_game.get('full_game_app_id')
            )

            for other_game_url, platform in other_matches:
                platform_url_field = f"{platform}_url"

                # Skip if Steam game already has this platform linked
                if steam_game.get(platform_url_field):
                    logging.info(f"Steam game {steam_app_id} already has {platform} link, skipping")
                    continue

                # Apply precedence rules
                should_link = True

                if platform == 'itch':
                    # Rule: If Steam has demo+main game pair, ignore Itch version
                    if has_demo_pair and not is_steam_demo:
                        # This is a Steam main game with a demo - ignore Itch
                        should_link = False
                        logging.info(f"Steam game {steam_app_id} has demo pair, ignoring Itch version")
                    elif has_demo_pair and is_steam_demo:
                        # This is a Steam demo with main game - still ignore Itch
                        should_link = False
                        logging.info(f"Steam demo {steam_app_id} has main game pair, ignoring Itch version")

                if should_link:
                    approved_links[other_game_url] = steam_app_id
                    logging.info(f"Approved link: {platform} {other_game_url} -> Steam {steam_app_id}")

        return approved_links

    def update_cross_platform_links(self, approved_links: dict[str, str]) -> tuple[int, int]:
        """Update game data files with approved cross-platform links

        Returns:
            Tuple of (steam_games_updated, other_games_updated)
        """
        steam_updated = 0
        other_updated = 0

        if not approved_links:
            return steam_updated, other_updated

        # Load current data
        try:
            with (self.data_dir / 'steam_games.json').open() as f:
                steam_data = json.load(f)
        except FileNotFoundError:
            logging.warning("steam_games.json not found")
            return steam_updated, other_updated

        try:
            with (self.data_dir / 'other_games.json').open() as f:
                other_data = json.load(f)
        except FileNotFoundError:
            logging.warning("other_games.json not found")
            return steam_updated, other_updated

        steam_games = steam_data.get('games', {})
        other_games = other_data.get('games', {})

        # Update links
        for other_game_url, steam_app_id in approved_links.items():
            if other_game_url not in other_games or steam_app_id not in steam_games:
                continue

            other_game = other_games[other_game_url]
            steam_game = steam_games[steam_app_id]
            platform = other_game.get('platform', 'unknown')

            # Add platform URL to Steam game
            platform_url_field = f"{platform}_url"
            if not steam_game.get(platform_url_field):
                steam_game[platform_url_field] = other_game_url
                steam_updated += 1
                logging.info(f"Added {platform} link to Steam game {steam_app_id}")

            # Add Steam URL to other platform game
            if not other_game.get('steam_url'):
                other_game['steam_url'] = f"https://store.steampowered.com/app/{steam_app_id}"
                other_updated += 1
                logging.info(f"Added Steam link to {platform} game {other_game_url}")

        # Save updated data
        if steam_updated > 0:
            with (self.data_dir / 'steam_games.json').open('w') as f:
                json.dump(steam_data, f, indent=2)
            logging.info(f"Updated {steam_updated} Steam games with cross-platform links")

        if other_updated > 0:
            with (self.data_dir / 'other_games.json').open('w') as f:
                json.dump(other_data, f, indent=2)
            logging.info(f"Updated {other_updated} other platform games with Steam links")

        return steam_updated, other_updated

    def remove_conflicting_links(self, approved_links: dict[str, str]) -> int:
        """Remove conflicting links that violate precedence rules

        This prevents the Itch updater from re-linking games that should be ignored
        based on Steam demo precedence rules.

        Returns:
            Number of conflicting links removed
        """
        removed_count = 0

        try:
            with (self.data_dir / 'steam_games.json').open() as f:
                steam_data = json.load(f)
        except FileNotFoundError:
            return removed_count

        try:
            with (self.data_dir / 'other_games.json').open() as f:
                other_data = json.load(f)
        except FileNotFoundError:
            return removed_count

        steam_games = steam_data.get('games', {})
        other_games = other_data.get('games', {})

        # Find games that should be unlinked based on precedence rules
        for other_game_url, other_game in other_games.items():
            platform = other_game.get('platform', 'unknown')
            steam_url = other_game.get('steam_url', '')

            if not steam_url or other_game_url in approved_links:
                continue  # No link or approved link

            # Extract Steam app ID from URL
            import re
            match = re.search(r'/app/(\d+)', steam_url)
            if not match:
                continue

            steam_app_id = match.group(1)
            steam_game = steam_games.get(steam_app_id, {})

            if not steam_game:
                continue

            # Check if this link violates precedence rules
            has_demo_pair = (
                steam_game.get('demo_app_id') or
                steam_game.get('full_game_app_id')
            )

            should_remove = False

            if platform == 'itch' and has_demo_pair:
                # Steam has demo+main game pair, Itch link should be removed
                should_remove = True
                logging.info(f"Removing conflicting Itch link: {other_game_url} -> {steam_app_id} (Steam has demo pair)")

            if should_remove:
                # Remove steam_url from other game
                del other_game['steam_url']
                removed_count += 1

                # Remove platform_url from steam game if it exists
                platform_url_field = f"{platform}_url"
                if steam_game.get(platform_url_field) == other_game_url:
                    del steam_game[platform_url_field]

        # Save updated data if changes were made
        if removed_count > 0:
            with (self.data_dir / 'steam_games.json').open('w') as f:
                json.dump(steam_data, f, indent=2)

            with (self.data_dir / 'other_games.json').open('w') as f:
                json.dump(other_data, f, indent=2)

            logging.info(f"Removed {removed_count} conflicting cross-platform links")

        return removed_count

    def run_auto_linking(self) -> dict[str, int]:
        """Run the complete auto-linking process

        Returns:
            Dict with statistics about the linking process
        """
        logging.info("Starting cross-platform auto-linking process")

        # Load data
        try:
            with (self.data_dir / 'steam_games.json').open() as f:
                steam_data = json.load(f)
        except FileNotFoundError:
            logging.warning("steam_games.json not found, skipping auto-linking")
            return {'error': 'steam_games.json not found'}

        try:
            with (self.data_dir / 'other_games.json').open() as f:
                other_data = json.load(f)
        except FileNotFoundError:
            logging.warning("other_games.json not found, skipping auto-linking")
            return {'error': 'other_games.json not found'}

        steam_games = steam_data.get('games', {})
        other_games = other_data.get('games', {})

        # Find matches
        matches = self.find_exact_name_matches(steam_games, other_games)
        logging.info(f"Found {len(matches)} potential cross-platform matches")

        # Apply precedence rules
        approved_links = self.apply_precedence_rules(steam_games, matches)
        logging.info(f"Approved {len(approved_links)} links after applying precedence rules")

        # Remove conflicting links
        removed_count = self.remove_conflicting_links(approved_links)

        # Update links
        steam_updated, other_updated = self.update_cross_platform_links(approved_links)

        stats = {
            'potential_matches': len(matches),
            'approved_links': len(approved_links),
            'steam_games_updated': steam_updated,
            'other_games_updated': other_updated,
            'conflicting_links_removed': removed_count
        }

        logging.info(f"Auto-linking complete: {stats}")
        return stats


def run_cross_platform_matching(project_root: Path) -> dict[str, int]:
    """Convenience function to run cross-platform matching"""
    matcher = CrossPlatformMatcher(project_root)
    return matcher.run_auto_linking()

