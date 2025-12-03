"""
Tests for MCP Lazy Orchestrator

Run with: pytest tests/
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_orchestrator.server import (
    MCP_SERVER_REGISTRY,
    MCPServerConfig,
    OrchestratorState,
    run_docker_mcp_command,
)


class TestServerRegistry:
    """Tests for the server registry"""
    
    def test_registry_has_expected_servers(self):
        """Verify all expected servers are registered"""
        expected = {
            "context7", "playwright", "github", "fetch",
            "desktop-commander", "postgres", "redis", "sequential-thinking"
        }
        assert expected == set(MCP_SERVER_REGISTRY.keys())
    
    def test_server_configs_have_required_fields(self):
        """Verify all configs have required fields"""
        for name, config in MCP_SERVER_REGISTRY.items():
            assert isinstance(config, MCPServerConfig)
            assert config.name == name
            assert config.description
            assert config.tools_summary
            assert config.category
            assert config.estimated_tools > 0


class TestOrchestratorState:
    """Tests for state management"""
    
    def test_initial_state_is_empty(self):
        """Verify initial state is empty"""
        state = OrchestratorState()
        assert len(state.active_servers) == 0
        assert len(state.server_tools_cache) == 0
        assert state.last_error is None
    
    def test_active_servers_tracking(self):
        """Test adding/removing servers"""
        state = OrchestratorState()
        
        state.active_servers.add("playwright")
        assert "playwright" in state.active_servers
        
        state.active_servers.discard("playwright")
        assert "playwright" not in state.active_servers


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


class TestServerCategories:
    """Tests for server categorization"""
    
    def test_multiple_categories_exist(self):
        """Verify multiple categories"""
        categories = {c.category for c in MCP_SERVER_REGISTRY.values()}
        assert len(categories) > 1
    
    def test_auth_requirements(self):
        """Verify auth settings"""
        github = MCP_SERVER_REGISTRY["github"]
        assert github.requires_auth is True
        assert github.auth_type == "oauth"
        
        playwright = MCP_SERVER_REGISTRY["playwright"]
        assert playwright.requires_auth is False


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
