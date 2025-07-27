"""
Game inference and Steam matching utilities
"""

import logging
from typing import Any

import requests

from .utils import extract_potential_game_names


class GameInferenceEngine:
    """Handles game name inference and Steam matching"""

    def search_steam_games(self, query: str) -> list[dict[str, Any]]:
        """Search Steam for games by name"""
        url = "https://store.steampowered.com/api/storesearch/"
        params = {
            'term': query,
            'l': 'english',
            'cc': 'US'
        }

        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                return items if isinstance(items, list) else []
        except Exception as e:
            logging.error(f"Error searching Steam for '{query}': {e}")

        return []

    def find_steam_match(self, game_name: str, confidence_threshold: float = 0.5) -> dict[str, Any] | None:
        """Find best Steam match for a game name with confidence scoring"""
        try:
            results = self.search_steam_games(game_name)
            if not results:
                return None

            best_match = None
            best_confidence = 0.0

            for result in results[:3]:  # Check top 3 results
                steam_game_name = result['name'].lower()
                search_name = game_name.lower()

                # Calculate similarity (simple word overlap)
                search_words = set(search_name.split())
                game_words = set(steam_game_name.split())
                overlap = len(search_words & game_words)
                confidence = overlap / max(len(search_words), len(game_words))

                if confidence > best_confidence and confidence > confidence_threshold:
                    best_match = result
                    best_confidence = confidence

            if best_match:
                return {
                    'app_id': str(best_match['id']),
                    'name': best_match['name'],
                    'confidence': best_confidence
                }

            return None

        except Exception as e:
            logging.error(f"Error finding Steam match for '{game_name}': {e}")
            return None

    def find_steam_match_interactive(self, game_name: str, confidence_threshold: float = 0.5) -> dict[str, Any] | None:
        """Find Steam match with interactive prompting for low confidence results"""
        try:
            results = self.search_steam_games(game_name)
            if not results:
                print(f"      ❌ No Steam search results for '{game_name}'")
                return None

            best_match = None
            best_confidence = 0.0
            low_confidence_matches = []

            # Check all results
            for result in results[:5]:  # Check top 5 instead of 3
                steam_game_name = result['name']
                search_name = game_name.lower()

                # Calculate similarity (same logic as find_steam_match)
                search_words = set(search_name.split())
                game_words = set(steam_game_name.lower().split())
                overlap = len(search_words & game_words)
                confidence = overlap / max(len(search_words), len(game_words))

                if confidence >= confidence_threshold:
                    if confidence > best_confidence:
                        best_match = result
                        best_confidence = confidence
                elif confidence >= 0.3:  # Low confidence but potentially valid
                    low_confidence_matches.append((result, confidence))

            # If we found a high confidence match, return it
            if best_match:
                return {
                    'app_id': str(best_match['id']),
                    'name': best_match['name'],
                    'confidence': best_confidence
                }

            # If no high confidence matches, prompt for low confidence ones
            if low_confidence_matches:
                print(f"      🤔 Found potential matches for '{game_name}' (low confidence):")
                for i, (result, conf) in enumerate(low_confidence_matches):
                    print(f"         {i+1}. {result['name']} (confidence: {conf:.2f})")

                print("         0. None of these / Skip")

                while True:
                    try:
                        choice = input(f"      Select match (0-{len(low_confidence_matches)}): ").strip()
                        choice_num = int(choice)

                        if choice_num == 0:
                            return None
                        elif 1 <= choice_num <= len(low_confidence_matches):
                            selected = low_confidence_matches[choice_num - 1]
                            return {
                                'app_id': str(selected[0]['id']),
                                'name': selected[0]['name'],
                                'confidence': selected[1]
                            }
                        else:
                            print("      Invalid choice, try again.")
                    except (ValueError, KeyboardInterrupt):
                        print("      Skipping this match...")
                        return None

            return None

        except Exception as e:
            logging.error(f"Error finding Steam match for '{game_name}': {e}")
            return None

    def extract_potential_game_names_from_title(self, title: str) -> list[str]:
        """Extract potential game names from video titles"""
        result = extract_potential_game_names(title)
        return result if isinstance(result, list) else []

    def check_steam_availability(self, app_id: str) -> str:
        """Check if Steam app is still available"""
        url = f"https://store.steampowered.com/app/{app_id}"
        try:
            response = requests.head(url, timeout=5)
            if response.status_code == 404:
                return "depublished"
            elif response.status_code == 200:
                return "available"
            else:
                return "unknown"
        except Exception:
            return "unknown"
