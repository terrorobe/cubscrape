"""
Cross-Reference and Data Integrity Validator

Validates relationships and consistency across all data models and JSON files.
"""

import logging
from dataclasses import dataclass

from .data_manager import DataManager, OtherGamesDataDict, SteamDataDict, VideosDataDict
from .models import VideoData


@dataclass
class ValidationError:
    """Represents a validation error"""
    error_type: str
    message: str
    entity_id: str
    entity_type: str
    severity: str = "error"  # "error", "warning", "info"


class ReferenceValidator:
    """Validates cross-references and data integrity across all game data"""

    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.errors: list[ValidationError] = []

    def validate_all(self, channel_ids: list[str]) -> list[ValidationError]:
        """Run comprehensive validation across all data"""
        self.errors.clear()

        # Load all data
        steam_data = self.data_manager.load_steam_data()
        other_games_data = self.data_manager.load_other_games_data()
        videos_data = {}
        for channel_id in channel_ids:
            videos_data[channel_id] = self.data_manager.load_videos_data(channel_id)

        logging.info("Running comprehensive reference validation...")

        # Run all validation checks
        self._validate_steam_cross_references(steam_data)
        self._validate_steam_business_logic(steam_data)
        self._validate_cross_platform_symmetry(steam_data, other_games_data)
        self._validate_resolution_chains(steam_data, other_games_data)
        self._validate_video_references(videos_data, steam_data, other_games_data)

        # Log summary
        errors = [e for e in self.errors if e.severity == "error"]
        warnings = [e for e in self.errors if e.severity == "warning"]
        logging.info(f"Validation complete: {len(errors)} errors, {len(warnings)} warnings")

        return self.errors

    def _validate_steam_cross_references(self, steam_data: SteamDataDict) -> None:
        """Validate bidirectional demo-game relationships in Steam data"""
        logging.info("Validating Steam cross-references...")

        games = steam_data['games']

        for app_id, game in games.items():
            # Check demo_app_id bidirectionality
            if game.demo_app_id:
                if game.demo_app_id not in games:
                    self.errors.append(ValidationError(
                        error_type="missing_demo_reference",
                        message=f"Demo app ID '{game.demo_app_id}' not found in Steam games",
                        entity_id=app_id,
                        entity_type="steam_game",
                        severity="error"
                    ))
                else:
                    demo_game = games[game.demo_app_id]
                    if demo_game.full_game_app_id != app_id:
                        self.errors.append(ValidationError(
                            error_type="broken_demo_bidirectionality",
                            message=f"Demo '{game.demo_app_id}' full_game_app_id is '{demo_game.full_game_app_id}', expected '{app_id}'",
                            entity_id=app_id,
                            entity_type="steam_game",
                            severity="error"
                        ))

            # Check full_game_app_id bidirectionality
            if game.full_game_app_id:
                if game.full_game_app_id not in games:
                    self.errors.append(ValidationError(
                        error_type="missing_full_game_reference",
                        message=f"Full game app ID '{game.full_game_app_id}' not found in Steam games",
                        entity_id=app_id,
                        entity_type="steam_game",
                        severity="error"
                    ))
                else:
                    full_game = games[game.full_game_app_id]
                    if full_game.demo_app_id != app_id:
                        self.errors.append(ValidationError(
                            error_type="broken_full_game_bidirectionality",
                            message=f"Full game '{game.full_game_app_id}' demo_app_id is '{full_game.demo_app_id}', expected '{app_id}'",
                            entity_id=app_id,
                            entity_type="steam_game",
                            severity="error"
                        ))

    def _validate_steam_business_logic(self, steam_data: SteamDataDict) -> None:
        """Validate business logic rules for Steam games"""
        logging.info("Validating Steam business logic...")

        games = steam_data['games']

        for app_id, game in games.items():
            # Demo games must have is_demo=True and valid full_game_app_id
            if game.is_demo:
                if not game.full_game_app_id:
                    self.errors.append(ValidationError(
                        error_type="demo_missing_full_game",
                        message="Demo game must have full_game_app_id",
                        entity_id=app_id,
                        entity_type="steam_game",
                        severity="error"
                    ))
                elif game.full_game_app_id not in games:
                    self.errors.append(ValidationError(
                        error_type="demo_invalid_full_game",
                        message=f"Demo references non-existent full game '{game.full_game_app_id}'",
                        entity_id=app_id,
                        entity_type="steam_game",
                        severity="error"
                    ))

            # Games with has_demo=True must have valid demo_app_id
            if game.has_demo:
                if not game.demo_app_id:
                    self.errors.append(ValidationError(
                        error_type="has_demo_missing_app_id",
                        message="Game with has_demo=True must have demo_app_id",
                        entity_id=app_id,
                        entity_type="steam_game",
                        severity="error"
                    ))
                elif game.demo_app_id not in games:
                    self.errors.append(ValidationError(
                        error_type="has_demo_invalid_app_id",
                        message=f"Game references non-existent demo '{game.demo_app_id}'",
                        entity_id=app_id,
                        entity_type="steam_game",
                        severity="error"
                    ))
                else:
                    demo_game = games[game.demo_app_id]
                    if not demo_game.is_demo:
                        self.errors.append(ValidationError(
                            error_type="demo_app_not_marked_as_demo",
                            message=f"Referenced demo '{game.demo_app_id}' has is_demo=False",
                            entity_id=app_id,
                            entity_type="steam_game",
                            severity="warning"
                        ))

            # Games with demo_app_id should have has_demo=True
            if game.demo_app_id and not game.has_demo:
                self.errors.append(ValidationError(
                    error_type="demo_app_id_without_has_demo",
                    message="Game has demo_app_id but has_demo=False",
                    entity_id=app_id,
                    entity_type="steam_game",
                    severity="warning"
                ))

    def _validate_cross_platform_symmetry(self, steam_data: SteamDataDict, other_games_data: OtherGamesDataDict) -> None:
        """Validate symmetry between Steam itch_url and Itch steam_url"""
        logging.info("Validating cross-platform symmetry...")

        steam_games = steam_data['games']
        other_games = other_games_data['games']

        # Check Steam games with itch_url
        for app_id, game in steam_games.items():
            if game.itch_url:
                # Find corresponding Itch game
                itch_game = None
                for itch_data in other_games.values():
                    if itch_data.url == game.itch_url:
                        itch_game = itch_data
                        break

                if not itch_game:
                    self.errors.append(ValidationError(
                        error_type="steam_itch_url_no_match",
                        message=f"Steam game references Itch URL '{game.itch_url}' but no corresponding Itch game found",
                        entity_id=app_id,
                        entity_type="steam_game",
                        severity="error"
                    ))
                else:
                    # Check if Itch game references back to Steam
                    expected_steam_url = f"https://store.steampowered.com/app/{app_id}"
                    if itch_game.steam_url != expected_steam_url:
                        self.errors.append(ValidationError(
                            error_type="asymmetric_cross_platform_reference",
                            message=f"Steam game references '{game.itch_url}' but Itch game steam_url is '{itch_game.steam_url}', expected '{expected_steam_url}'",
                            entity_id=app_id,
                            entity_type="steam_game",
                            severity="error"
                        ))

        # Check Itch games with steam_url
        for itch_id, itch_game in other_games.items():
            if itch_game.steam_url:
                # Extract Steam app ID from URL
                import re
                steam_app_match = re.search(r'/app/(\d+)', itch_game.steam_url)
                if not steam_app_match:
                    self.errors.append(ValidationError(
                        error_type="invalid_steam_url_format",
                        message=f"Invalid Steam URL format: '{itch_game.steam_url}'",
                        entity_id=itch_id,
                        entity_type="other_game",
                        severity="error"
                    ))
                    continue

                steam_app_id = steam_app_match.group(1)
                if steam_app_id not in steam_games:
                    self.errors.append(ValidationError(
                        error_type="itch_steam_url_no_match",
                        message=f"Itch game references Steam app '{steam_app_id}' but no corresponding Steam game found",
                        entity_id=itch_id,
                        entity_type="other_game",
                        severity="error"
                    ))
                else:
                    steam_game = steam_games[steam_app_id]
                    if steam_game.itch_url != itch_game.url:
                        self.errors.append(ValidationError(
                            error_type="asymmetric_cross_platform_reference",
                            message=f"Itch game references Steam app '{steam_app_id}' but Steam game itch_url is '{steam_game.itch_url}', expected '{itch_game.url}'",
                            entity_id=itch_id,
                            entity_type="other_game",
                            severity="error"
                        ))

    def _validate_resolution_chains(self, steam_data: SteamDataDict, other_games_data: OtherGamesDataDict) -> None:
        """Validate resolution chains are not circular and targets exist"""
        logging.info("Validating resolution chains...")

        # Validate Steam resolution chains
        steam_games = steam_data['games']
        for app_id, game in steam_games.items():
            if game.resolved_to:
                if game.resolved_to not in steam_games:
                    self.errors.append(ValidationError(
                        error_type="invalid_resolution_target",
                        message=f"Steam game resolves to non-existent app '{game.resolved_to}'",
                        entity_id=app_id,
                        entity_type="steam_game",
                        severity="error"
                    ))
                else:
                    # Check for circular references
                    visited = {app_id}
                    current: str | None = game.resolved_to
                    while current and current in steam_games:
                        if current in visited:
                            self.errors.append(ValidationError(
                                error_type="circular_resolution_chain",
                                message=f"Circular resolution chain detected: {' -> '.join(visited)} -> {current}",
                                entity_id=app_id,
                                entity_type="steam_game",
                                severity="error"
                            ))
                            break
                        visited.add(current)
                        next_game = steam_games[current]
                        current = next_game.resolved_to

        # Validate other games resolution chains
        other_games = other_games_data['games']
        for game_id, other_game in other_games.items():
            if other_game.resolved_to:
                if other_game.resolved_to not in other_games:
                    self.errors.append(ValidationError(
                        error_type="invalid_resolution_target",
                        message=f"Other game resolves to non-existent game '{other_game.resolved_to}'",
                        entity_id=game_id,
                        entity_type="other_game",
                        severity="error"
                    ))
                else:
                    # Check for circular references
                    visited = {game_id}
                    current_target: str | None = other_game.resolved_to
                    while current_target and current_target in other_games:
                        if current_target in visited:
                            self.errors.append(ValidationError(
                                error_type="circular_resolution_chain",
                                message=f"Circular resolution chain detected: {' -> '.join(visited)} -> {current_target}",
                                entity_id=game_id,
                                entity_type="other_game",
                                severity="error"
                            ))
                            break
                        visited.add(current_target)
                        next_other_game = other_games[current_target]
                        current_target = next_other_game.resolved_to

    def _validate_video_references(self, videos_data: dict[str, VideosDataDict],
                                 steam_data: SteamDataDict, other_games_data: OtherGamesDataDict) -> None:
        """Validate video game references exist in corresponding game files"""
        logging.info("Validating video game references...")

        steam_games = steam_data['games']
        other_games = other_games_data['games']

        for channel_id, channel_videos in videos_data.items():
            if not channel_videos or 'videos' not in channel_videos:
                continue

            for video_id, video in channel_videos['videos'].items():
                if not isinstance(video, VideoData):
                    continue

                for ref in video.game_references:
                    if ref.platform == 'steam':
                        if ref.platform_id not in steam_games:
                            self.errors.append(ValidationError(
                                error_type="video_references_missing_steam_game",
                                message=f"Video references non-existent Steam app '{ref.platform_id}'",
                                entity_id=f"{channel_id}:{video_id}",
                                entity_type="video",
                                severity="error"
                            ))
                    elif ref.platform == 'itch':
                        # Find Itch game by URL
                        itch_game_found = False
                        for itch_game in other_games.values():
                            if itch_game.url == ref.platform_id:
                                itch_game_found = True
                                break

                        if not itch_game_found:
                            self.errors.append(ValidationError(
                                error_type="video_references_missing_itch_game",
                                message=f"Video references non-existent Itch game '{ref.platform_id}'",
                                entity_id=f"{channel_id}:{video_id}",
                                entity_type="video",
                                severity="error"
                            ))
                    elif ref.platform == 'crazygames':
                        # Find CrazyGames by URL
                        crazygames_found = False
                        for game in other_games.values():
                            if game.platform == 'crazygames' and game.url == ref.platform_id:
                                crazygames_found = True
                                break

                        if not crazygames_found:
                            self.errors.append(ValidationError(
                                error_type="video_references_missing_crazygames_game",
                                message=f"Video references non-existent CrazyGames game '{ref.platform_id}'",
                                entity_id=f"{channel_id}:{video_id}",
                                entity_type="video",
                                severity="error"
                            ))

    def print_validation_report(self) -> None:
        """Print a formatted validation report"""
        if not self.errors:
            print("✅ All validation checks passed!")
            return

        errors = [e for e in self.errors if e.severity == "error"]
        warnings = [e for e in self.errors if e.severity == "warning"]

        print("\n📊 Validation Report")
        print(f"{'='*50}")
        print(f"Total issues: {len(self.errors)}")
        print(f"Errors: {len(errors)}")
        print(f"Warnings: {len(warnings)}")

        if errors:
            print(f"\n❌ ERRORS ({len(errors)}):")
            print("-" * 30)
            for error in errors:
                print(f"  • [{error.entity_type}:{error.entity_id}] {error.error_type}")
                print(f"    {error.message}")

        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            print("-" * 30)
            for warning in warnings:
                print(f"  • [{warning.entity_type}:{warning.entity_id}] {warning.error_type}")
                print(f"    {warning.message}")

        print()

