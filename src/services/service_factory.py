"""
Service Factory for dependency injection following SOLID principles.

This module provides a factory for creating properly configured service instances
with their dependencies injected, following the Dependency Inversion Principle.
"""
from typing import Optional
from ..models import GameState
from .persistence_service import PersistenceService
from .timer_service import TimerService
from .analytics_service import AnalyticsService, GameReportExporter
from .player_service import (
    PlayerService, PlayerValidator, PlayerCSVHandler, 
    StandardPositionProvider
)


class ServiceFactory:
    """
    Factory for creating service instances with proper dependency injection.
    
    Follows SOLID principles:
    - SRP: Single responsibility for service creation
    - OCP: Extensible through configuration
    - LSP: All services adhere to their contracts
    - ISP: Focused interfaces for each service type
    - DIP: Depends on abstractions, creates concrete implementations
    """
    
    def __init__(self):
        """Initialize factory with default configurations."""
        self._persistence_service: Optional[PersistenceService] = None
        self._position_provider: Optional[StandardPositionProvider] = None
        self._export_service: Optional[GameReportExporter] = None
    
    def create_player_service(
        self,
        custom_validator: Optional[PlayerValidator] = None,
        custom_csv_handler: Optional[PlayerCSVHandler] = None
    ) -> PlayerService:
        """
        Create PlayerService with injected dependencies.
        
        Args:
            custom_validator: Optional custom validator
            custom_csv_handler: Optional custom CSV handler
            
        Returns:
            Configured PlayerService instance
        """
        persistence_service = self._get_persistence_service()
        
        if custom_validator is None:
            position_provider = self._get_position_provider()
            validator = PlayerValidator(position_provider=position_provider)
        else:
            validator = custom_validator
        
        csv_handler = custom_csv_handler or PlayerCSVHandler()
        
        return PlayerService(
            validator=validator,
            csv_handler=csv_handler,
            persistence_service=persistence_service
        )
    
    def create_timer_service(self, game_state: GameState) -> TimerService:
        """
        Create TimerService instance.
        
        Args:
            game_state: Game state to manage
            
        Returns:
            Configured TimerService instance
        """
        return TimerService(game_state)
    
    def create_analytics_service(
        self,
        game_state: GameState,
        timer_service: Optional[TimerService] = None
    ) -> AnalyticsService:
        """
        Create AnalyticsService with injected dependencies.
        
        Args:
            game_state: Game state to analyze
            timer_service: Optional timer service for time calculations
            
        Returns:
            Configured AnalyticsService instance
        """
        export_service = self._get_export_service()
        
        return AnalyticsService(
            game_state=game_state,
            timer_service=timer_service,
            export_service=export_service
        )
    
    def create_complete_service_suite(self, game_state: GameState) -> dict:
        """
        Create a complete suite of services with proper dependencies.
        
        Args:
            game_state: Game state for the services
            
        Returns:
            Dictionary containing all configured services
        """
        timer_service = self.create_timer_service(game_state)
        analytics_service = self.create_analytics_service(game_state, timer_service)
        player_service = self.create_player_service()
        
        return {
            'timer': timer_service,
            'analytics': analytics_service,
            'player': player_service,
            'persistence': self._get_persistence_service()
        }
    
    def _get_persistence_service(self) -> PersistenceService:
        """Get singleton persistence service."""
        if self._persistence_service is None:
            self._persistence_service = PersistenceService()
        return self._persistence_service
    
    def _get_position_provider(self) -> StandardPositionProvider:
        """Get singleton position provider."""
        if self._position_provider is None:
            self._position_provider = StandardPositionProvider()
        return self._position_provider
    
    def _get_export_service(self) -> GameReportExporter:
        """Get singleton export service."""
        if self._export_service is None:
            self._export_service = GameReportExporter()
        return self._export_service
    
    def configure_custom_position_provider(self, provider: StandardPositionProvider) -> None:
        """Configure custom position provider - supports OCP."""
        self._position_provider = provider
    
    def configure_custom_export_service(self, exporter: GameReportExporter) -> None:
        """Configure custom export service - supports OCP."""
        self._export_service = exporter