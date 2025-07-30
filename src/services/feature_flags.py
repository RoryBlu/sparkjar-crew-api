"""
Feature flag system for gradual rollout of remote crew execution

This module provides a flexible feature flag system that allows for:
- Global flags (e.g., "use_remote_crews")
- Per-crew flags (e.g., "use_remote_crews_memory_maker_crew")
- Environment variable configuration
- Runtime flag updates
- Monitoring and metrics
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FeatureFlagConfig(BaseModel):
    """Configuration for individual feature flags"""
    enabled: bool = Field(default=False, description="Whether the flag is enabled")
    description: Optional[str] = Field(default=None, description="Description of what this flag controls")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class FeatureFlags:
    """
    Feature flag management system for controlling crew execution routing
    
    Supports:
    - Global flags (apply to all crews)
    - Per-crew flags (apply to specific crews)
    - Environment variable initialization
    - Runtime updates via admin API
    - Metrics tracking
    """
    
    def __init__(self):
        """Initialize feature flags from environment and defaults"""
        self._flags: Dict[str, FeatureFlagConfig] = {}
        self._flag_checks: Dict[str, int] = {}  # Track flag checks for metrics
        self._initialize_from_environment()
        self._initialize_defaults()
        
    def _initialize_from_environment(self):
        """Load feature flags from environment variables"""
        # Check for FEATURE_FLAGS environment variable (JSON format)
        env_flags = os.getenv("FEATURE_FLAGS")
        if env_flags:
            try:
                flags_data = json.loads(env_flags)
                for flag_name, flag_value in flags_data.items():
                    if isinstance(flag_value, bool):
                        self._flags[flag_name] = FeatureFlagConfig(enabled=flag_value)
                    elif isinstance(flag_value, dict):
                        self._flags[flag_name] = FeatureFlagConfig(**flag_value)
                logger.info(f"Loaded {len(flags_data)} feature flags from environment")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse FEATURE_FLAGS environment variable: {e}")
        
        # Check for individual flag environment variables
        # Format: FEATURE_FLAG_<FLAG_NAME>=true/false
        for key, value in os.environ.items():
            if key.startswith("FEATURE_FLAG_"):
                flag_name = key[13:].lower()  # Remove prefix and lowercase
                flag_enabled = value.lower() in ("true", "1", "yes", "on")
                self._flags[flag_name] = FeatureFlagConfig(
                    enabled=flag_enabled,
                    description=f"Set from environment variable {key}"
                )
                logger.info(f"Feature flag '{flag_name}' set to {flag_enabled} from environment")
    
    def _initialize_defaults(self):
        """Initialize default feature flags"""
        defaults = {
            "use_remote_crews": FeatureFlagConfig(
                enabled=False,
                description="Route all crew executions to remote crews service"
            ),
            "use_remote_crews_memory_maker_crew": FeatureFlagConfig(
                enabled=False,
                description="Route memory_maker_crew to remote service"
            ),
            "use_remote_crews_entity_research_crew": FeatureFlagConfig(
                enabled=False,
                description="Route entity_research_crew to remote service"
            ),
            "use_remote_crews_book_ingestion_crew": FeatureFlagConfig(
                enabled=False,
                description="Route book_ingestion_crew to remote service"
            ),
            "enable_crew_metrics": FeatureFlagConfig(
                enabled=True,
                description="Enable detailed metrics for crew execution"
            ),
            "enable_remote_crew_fallback": FeatureFlagConfig(
                enabled=False,
                description="Fallback to local execution if remote fails"
            )
        }
        
        # Only add defaults if not already set
        for flag_name, flag_config in defaults.items():
            if flag_name not in self._flags:
                self._flags[flag_name] = flag_config
        
        logger.info(f"Feature flags initialized with {len(self._flags)} flags")
    
    def is_enabled(self, flag_name: str, crew_name: Optional[str] = None) -> bool:
        """
        Check if a feature flag is enabled
        
        Args:
            flag_name: Name of the feature flag
            crew_name: Optional crew name for per-crew flags
            
        Returns:
            True if flag is enabled, False otherwise
        """
        # Track flag check for metrics
        check_key = f"{flag_name}:{crew_name}" if crew_name else flag_name
        self._flag_checks[check_key] = self._flag_checks.get(check_key, 0) + 1
        
        # Check crew-specific flag first if crew_name provided
        if crew_name:
            crew_flag_name = f"{flag_name}_{crew_name}"
            if crew_flag_name in self._flags:
                enabled = self._flags[crew_flag_name].enabled
                logger.debug(f"Feature flag '{crew_flag_name}' is {'enabled' if enabled else 'disabled'}")
                return enabled
        
        # Check global flag
        if flag_name in self._flags:
            enabled = self._flags[flag_name].enabled
            logger.debug(f"Feature flag '{flag_name}' is {'enabled' if enabled else 'disabled'}")
            return enabled
        
        # Default to disabled for unknown flags
        logger.debug(f"Feature flag '{flag_name}' not found, defaulting to disabled")
        return False
    
    def set_flag(self, flag_name: str, enabled: bool, description: Optional[str] = None) -> None:
        """
        Set or update a feature flag
        
        Args:
            flag_name: Name of the feature flag
            enabled: Whether to enable or disable the flag
            description: Optional description of the flag
        """
        if flag_name in self._flags:
            self._flags[flag_name].enabled = enabled
            self._flags[flag_name].updated_at = datetime.utcnow()
            if description:
                self._flags[flag_name].description = description
            logger.info(f"Updated feature flag '{flag_name}' to {enabled}")
        else:
            self._flags[flag_name] = FeatureFlagConfig(
                enabled=enabled,
                description=description
            )
            logger.info(f"Created feature flag '{flag_name}' with value {enabled}")
    
    def get_flag(self, flag_name: str) -> Optional[FeatureFlagConfig]:
        """Get configuration for a specific flag"""
        return self._flags.get(flag_name)
    
    def get_all_flags(self) -> Dict[str, Dict[str, Any]]:
        """Get all feature flags with their configurations"""
        return {
            name: {
                "enabled": config.enabled,
                "description": config.description,
                "created_at": config.created_at.isoformat(),
                "updated_at": config.updated_at.isoformat(),
                "metadata": config.metadata
            }
            for name, config in self._flags.items()
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics about feature flag usage"""
        total_checks = sum(self._flag_checks.values())
        enabled_flags = [name for name, config in self._flags.items() if config.enabled]
        
        return {
            "total_flags": len(self._flags),
            "enabled_flags": len(enabled_flags),
            "total_checks": total_checks,
            "flag_checks": dict(self._flag_checks),
            "enabled_flag_names": enabled_flags,
            "most_checked": max(self._flag_checks.items(), key=lambda x: x[1])[0] if self._flag_checks else None
        }
    
    def reset_metrics(self):
        """Reset flag check metrics"""
        self._flag_checks.clear()
        logger.info("Feature flag metrics reset")
    
    def should_use_remote_crew(self, crew_name: str) -> bool:
        """
        Convenience method to check if a crew should use remote execution
        
        Args:
            crew_name: Name of the crew
            
        Returns:
            True if crew should use remote execution
        """
        return self.is_enabled("use_remote_crews", crew_name)
    
    def should_fallback_to_local(self) -> bool:
        """Check if fallback to local execution is enabled"""
        return self.is_enabled("enable_remote_crew_fallback")
    
    def export_flags(self) -> str:
        """Export flags as JSON string (for environment variable)"""
        export_data = {
            name: config.enabled
            for name, config in self._flags.items()
        }
        return json.dumps(export_data)


# Global feature flags instance
_feature_flags = None


def get_feature_flags() -> FeatureFlags:
    """Get the global FeatureFlags instance"""
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlags()
    return _feature_flags


def reset_feature_flags():
    """Reset the global feature flags instance (mainly for testing)"""
    global _feature_flags
    _feature_flags = None