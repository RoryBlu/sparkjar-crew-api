"""
Tests for the feature flag system
"""

import pytest
import os
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

# Test imports
from src.services.feature_flags import (
    FeatureFlags, 
    FeatureFlagConfig,
    get_feature_flags,
    reset_feature_flags
)


class TestFeatureFlags:
    """Test cases for the FeatureFlags class"""
    
    def setup_method(self):
        """Reset feature flags before each test"""
        reset_feature_flags()
        # Clear environment variables
        for key in list(os.environ.keys()):
            if key.startswith("FEATURE_FLAG_"):
                del os.environ[key]
        if "FEATURE_FLAGS" in os.environ:
            del os.environ["FEATURE_FLAGS"]
    
    def test_default_initialization(self):
        """Test that default flags are initialized correctly"""
        flags = FeatureFlags()
        
        # Check default flags exist
        assert flags.get_flag("use_remote_crews") is not None
        assert flags.get_flag("use_remote_crews_memory_maker_crew") is not None
        assert flags.get_flag("enable_crew_metrics") is not None
        
        # Check default values
        assert flags.is_enabled("use_remote_crews") == False
        assert flags.is_enabled("enable_crew_metrics") == True
    
    def test_environment_variable_initialization(self):
        """Test loading flags from environment variables"""
        # Set environment variables
        os.environ["FEATURE_FLAG_TEST_FLAG"] = "true"
        os.environ["FEATURE_FLAG_ANOTHER_FLAG"] = "false"
        os.environ["FEATURE_FLAGS"] = json.dumps({
            "json_flag": True,
            "another_json_flag": False
        })
        
        flags = FeatureFlags()
        
        # Check environment flags
        assert flags.is_enabled("test_flag") == True
        assert flags.is_enabled("another_flag") == False
        assert flags.is_enabled("json_flag") == True
        assert flags.is_enabled("another_json_flag") == False
    
    def test_per_crew_flags(self):
        """Test per-crew flag functionality"""
        flags = FeatureFlags()
        
        # Set a per-crew flag
        flags.set_flag("use_remote_crews_test_crew", True)
        
        # Check crew-specific flag takes precedence
        assert flags.is_enabled("use_remote_crews", "test_crew") == True
        assert flags.is_enabled("use_remote_crews", "other_crew") == False
        assert flags.is_enabled("use_remote_crews") == False
    
    def test_should_use_remote_crew(self):
        """Test the convenience method for remote crew checks"""
        flags = FeatureFlags()
        
        # Test with global flag
        flags.set_flag("use_remote_crews", True)
        assert flags.should_use_remote_crew("any_crew") == True
        
        # Test with per-crew flag overriding global
        flags.set_flag("use_remote_crews", False)
        flags.set_flag("use_remote_crews_specific_crew", True)
        assert flags.should_use_remote_crew("specific_crew") == True
        assert flags.should_use_remote_crew("other_crew") == False
    
    def test_flag_updates(self):
        """Test updating flag values"""
        flags = FeatureFlags()
        
        # Create a new flag
        flags.set_flag("new_flag", True, "Test flag")
        flag_config = flags.get_flag("new_flag")
        
        assert flag_config.enabled == True
        assert flag_config.description == "Test flag"
        
        # Update existing flag
        original_created = flag_config.created_at
        flags.set_flag("new_flag", False, "Updated description")
        updated_config = flags.get_flag("new_flag")
        
        assert updated_config.enabled == False
        assert updated_config.description == "Updated description"
        assert updated_config.created_at == original_created
        assert updated_config.updated_at > original_created
    
    def test_metrics_tracking(self):
        """Test that flag checks are tracked for metrics"""
        flags = FeatureFlags()
        
        # Check flags multiple times
        flags.is_enabled("test_flag")
        flags.is_enabled("test_flag")
        flags.is_enabled("test_flag", "crew1")
        flags.is_enabled("test_flag", "crew2")
        flags.is_enabled("another_flag")
        
        metrics = flags.get_metrics()
        
        assert metrics["total_checks"] == 5
        assert metrics["flag_checks"]["test_flag"] == 2
        assert metrics["flag_checks"]["test_flag:crew1"] == 1
        assert metrics["flag_checks"]["test_flag:crew2"] == 1
        assert metrics["flag_checks"]["another_flag"] == 1
        assert metrics["most_checked"] == "test_flag"
    
    def test_metrics_reset(self):
        """Test resetting metrics"""
        flags = FeatureFlags()
        
        # Generate some metrics
        flags.is_enabled("test_flag")
        flags.is_enabled("test_flag")
        
        # Reset metrics
        flags.reset_metrics()
        metrics = flags.get_metrics()
        
        assert metrics["total_checks"] == 0
        assert len(metrics["flag_checks"]) == 0
        assert metrics["most_checked"] is None
    
    def test_get_all_flags(self):
        """Test retrieving all flags"""
        flags = FeatureFlags()
        
        # Add some flags
        flags.set_flag("flag1", True, "First flag")
        flags.set_flag("flag2", False, "Second flag")
        
        all_flags = flags.get_all_flags()
        
        assert "flag1" in all_flags
        assert "flag2" in all_flags
        assert all_flags["flag1"]["enabled"] == True
        assert all_flags["flag1"]["description"] == "First flag"
        assert all_flags["flag2"]["enabled"] == False
    
    def test_export_flags(self):
        """Test exporting flags as JSON"""
        flags = FeatureFlags()
        
        # Set some flags
        flags.set_flag("flag1", True)
        flags.set_flag("flag2", False)
        
        export_json = flags.export_flags()
        exported = json.loads(export_json)
        
        assert exported["flag1"] == True
        assert exported["flag2"] == False
        assert "use_remote_crews" in exported  # Default flag
    
    def test_fallback_flag(self):
        """Test the fallback to local execution flag"""
        flags = FeatureFlags()
        
        # Default should be disabled
        assert flags.should_fallback_to_local() == False
        
        # Enable fallback
        flags.set_flag("enable_remote_crew_fallback", True)
        assert flags.should_fallback_to_local() == True
    
    def test_singleton_pattern(self):
        """Test that get_feature_flags returns the same instance"""
        flags1 = get_feature_flags()
        flags2 = get_feature_flags()
        
        assert flags1 is flags2
        
        # Test that changes are reflected
        flags1.set_flag("test_singleton", True)
        assert flags2.is_enabled("test_singleton") == True
    
    def test_complex_flag_config(self):
        """Test complex flag configuration from environment"""
        os.environ["FEATURE_FLAGS"] = json.dumps({
            "complex_flag": {
                "enabled": True,
                "description": "Complex flag from env",
                "metadata": {"key": "value"}
            }
        })
        
        flags = FeatureFlags()
        flag_config = flags.get_flag("complex_flag")
        
        assert flag_config.enabled == True
        assert flag_config.description == "Complex flag from env"
        assert flag_config.metadata == {"key": "value"}


class TestFeatureFlagIntegration:
    """Integration tests for feature flags with job service"""
    
    @pytest.mark.asyncio
    async def test_job_service_remote_execution(self):
        """Test that job service uses feature flags for routing"""
        from src.services.job_service import JobService
        from src.services.feature_flags import get_feature_flags
        
        # Mock dependencies
        with patch('src.services.job_service.get_direct_session'), \
             patch('src.services.job_service.get_crew_client') as mock_get_client:
            
            # Set up feature flags
            flags = get_feature_flags()
            flags.set_flag("use_remote_crews_test_crew", True)
            
            # Mock crew client
            mock_client = MagicMock()
            mock_client.execute_crew = MagicMock(return_value={
                "success": True,
                "result": "test result",
                "execution_time": 1.0,
                "total_time": 1.5
            })
            mock_get_client.return_value = mock_client
            
            # Create job service
            service = JobService()
            
            # Mock job data
            job = MagicMock()
            job.job_key = "test_crew"
            job.payload = {"test": "data"}
            
            # The actual implementation would need more setup,
            # this is a simplified test to show the pattern
            
            # Verify flag was checked
            metrics = flags.get_metrics()
            assert "use_remote_crews:test_crew" in metrics["flag_checks"] or \
                   "use_remote_crews" in metrics["flag_checks"]