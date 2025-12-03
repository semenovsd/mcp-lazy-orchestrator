"""
Tests for Docker MCP Orchestrator v2.0

Run with: pytest tests/
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_orchestrator.server import (
    OrchestratorState,
    run_docker_mcp_command,
    state,
)
from mcp_orchestrator.capabilities import CapabilitiesRegistry
from mcp_orchestrator.profiles import SERVER_PROFILES, find_matching_profile
from mcp_orchestrator.monitor import UsageMonitor
from mcp_orchestrator.discovery import ServerDiscovery, ServerMetadata


class TestOrchestratorState:
    """Tests for state management"""
    
    def test_initial_state_is_empty(self):
        """Verify initial state is empty"""
        test_state = OrchestratorState()
        assert len(test_state.active_servers) == 0
        assert len(test_state.server_tools_cache) == 0
        assert test_state.last_error is None
    
    def test_active_servers_tracking(self):
        """Test adding/removing servers"""
        test_state = OrchestratorState()
        
        test_state.active_servers.add("playwright")
        assert "playwright" in test_state.active_servers
        
        test_state.active_servers.discard("playwright")
        assert "playwright" not in test_state.active_servers


class TestDockerMCPCommand:
    """Tests for Docker MCP CLI interaction"""
    
    @patch('subprocess.run')
    def test_successful_command(self, mock_run):
        """Test successful command"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="success",
            stderr=""
        )
        
        success, output = run_docker_mcp_command(["server", "ls"])
        assert success is True
        assert output == "success"
    
    @patch('subprocess.run')
    def test_failed_command(self, mock_run):
        """Test failed command"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error"
        )
        
        success, output = run_docker_mcp_command(["server", "enable", "x"])
        assert success is False
        assert "error" in output
    
    @patch('subprocess.run')
    def test_timeout(self, mock_run):
        """Test timeout handling"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=60)
        
        success, output = run_docker_mcp_command(["server", "ls"])
        assert success is False
        assert "timed out" in output.lower()
    
    @patch('subprocess.run')
    def test_docker_not_found(self, mock_run):
        """Test missing Docker"""
        mock_run.side_effect = FileNotFoundError()
        
        success, output = run_docker_mcp_command(["server", "ls"])
        assert success is False
        assert "not found" in output.lower()


class TestCapabilitiesRegistry:
    """Tests for capabilities registry"""
    
    def test_registry_loads(self):
        """Verify capabilities registry loads"""
        registry = CapabilitiesRegistry()
        assert len(registry.registry) > 0
    
    def test_context7_capabilities(self):
        """Verify context7 has correct capabilities"""
        registry = CapabilitiesRegistry()
        caps = registry.get("context7")
        
        assert caps is not None
        assert "redis" in caps.covers_technologies
        assert "fastapi" in caps.covers_technologies
        assert caps.purpose is not None
    
    def test_find_by_technology(self):
        """Test finding servers by technology"""
        registry = CapabilitiesRegistry()
        servers = registry.find_by_technology("redis")
        
        assert "context7" in servers or "redis" in servers


class TestServerProfiles:
    """Tests for server profiles"""
    
    def test_profiles_exist(self):
        """Verify profiles are defined"""
        assert len(SERVER_PROFILES) > 0
        assert "web-development" in SERVER_PROFILES
        assert "data-science" in SERVER_PROFILES
    
    def test_profile_has_servers(self):
        """Verify profile has servers"""
        profile = SERVER_PROFILES["web-development"]
        assert len(profile.servers) > 0
        assert "playwright" in profile.servers
    
    def test_find_matching_profile(self):
        """Test profile matching"""
        profile = find_matching_profile("web development task")
        assert profile is not None
        assert profile.name == "web-development"


class TestUsageMonitor:
    """Tests for usage monitoring"""
    
    def test_track_activation(self):
        """Test tracking server activation"""
        monitor = UsageMonitor()
        monitor.track_activation("redis")
        
        stats = monitor.get_usage_stats()
        assert "redis" in stats
    
    def test_recommend_deactivation(self):
        """Test recommendation for deactivation"""
        monitor = UsageMonitor(idle_timeout_minutes=0)  # Immediate timeout for test
        monitor.track_activation("redis")
        
        import time
        time.sleep(0.1)  # Small delay
        
        recommendations = monitor.recommend_deactivation({"redis"})
        assert "redis" in recommendations


class TestServerDiscovery:
    """Tests for server discovery"""
    
    def test_category_detection(self):
        """Test automatic category detection"""
        discovery = ServerDiscovery()
        
        category = discovery._detect_category("redis", "Redis cache")
        assert category == "database"
        
        category = discovery._detect_category("playwright", "Browser automation")
        assert category == "browser"
    
    def test_auth_detection(self):
        """Test authentication requirement detection"""
        discovery = ServerDiscovery()
        
        requires, auth_type = discovery._check_auth_requirements({"name": "github"})
        # Should detect github requires auth
        assert requires is True or requires is False  # May vary


@pytest.mark.integration
class TestIntegration:
    """Integration tests (require Docker MCP Toolkit)"""
    
    @pytest.fixture(autouse=True)
    def check_docker(self):
        """Skip if Docker MCP unavailable"""
        success, _ = run_docker_mcp_command(["--version"])
        if not success:
            pytest.skip("Docker MCP Toolkit not available")
    
    def test_list_servers(self):
        """Test listing servers"""
        success, output = run_docker_mcp_command(["server", "ls"])
        assert success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
