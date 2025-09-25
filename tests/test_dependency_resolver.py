"""
Unit tests for the SquadDependencyResolver class.
Tests dependency checking, automatic assistant deployment, and error handling.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

from vapi_manager.core.dependency_resolver import SquadDependencyResolver
from vapi_manager.core.exceptions.vapi_exceptions import VAPIException


class TestSquadDependencyResolver:
    """Test suite for SquadDependencyResolver."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def mock_squad_config(self):
        """Create a mock squad configuration."""
        return {
            'name': 'test_squad',
            'description': 'Test squad',
            'members': [
                {'assistant_name': 'assistant1', 'role': 'primary'},
                {'assistant_name': 'assistant2', 'role': 'secondary'},
                {'assistant_name': 'assistant3', 'role': 'tertiary'}
            ]
        }

    @pytest.fixture
    def resolver(self, temp_dir):
        """Create a SquadDependencyResolver instance."""
        squads_dir = Path(temp_dir) / "squads"
        assistants_dir = Path(temp_dir) / "assistants"
        squads_dir.mkdir(parents=True, exist_ok=True)
        assistants_dir.mkdir(parents=True, exist_ok=True)
        return SquadDependencyResolver(str(squads_dir), str(assistants_dir))

    @pytest.mark.asyncio
    async def test_check_missing_assistants_all_deployed(self, resolver):
        """Test checking missing assistants when all are deployed."""
        with patch.object(resolver.squad_config_loader, 'load_squad') as mock_load:
            with patch.object(resolver.deployment_state_manager, 'get_deployment_info') as mock_deployment:
                # Setup mocks
                mock_load.return_value = Mock(members=[
                    {'assistant_name': 'assistant1'},
                    {'assistant_name': 'assistant2'}
                ])

                # Mock all assistants as deployed
                mock_deployment.return_value = Mock(is_deployed=True)

                # Check missing assistants
                missing = await resolver.check_missing_assistants('test_squad', 'development')

                # Assert no missing assistants
                assert missing == []
                assert mock_deployment.call_count == 2

    @pytest.mark.asyncio
    async def test_check_missing_assistants_some_missing(self, resolver):
        """Test checking missing assistants when some are not deployed."""
        with patch.object(resolver.squad_config_loader, 'load_squad') as mock_load:
            with patch.object(resolver.deployment_state_manager, 'get_deployment_info') as mock_deployment:
                # Setup mocks
                mock_load.return_value = Mock(members=[
                    {'assistant_name': 'assistant1'},
                    {'assistant_name': 'assistant2'},
                    {'assistant_name': 'assistant3'}
                ])

                # Mock deployment status
                def deployment_side_effect(name, env):
                    if name == 'assistant2':
                        return Mock(is_deployed=False)
                    return Mock(is_deployed=True)

                mock_deployment.side_effect = deployment_side_effect

                # Check missing assistants
                missing = await resolver.check_missing_assistants('test_squad', 'development')

                # Assert only assistant2 is missing
                assert missing == ['assistant2']
                assert mock_deployment.call_count == 3

    @pytest.mark.asyncio
    async def test_check_missing_assistants_configuration_error(self, resolver):
        """Test error handling when squad configuration cannot be loaded."""
        with patch.object(resolver.squad_config_loader, 'load_squad') as mock_load:
            mock_load.side_effect = Exception("Config not found")

            # Should raise VAPIException
            with pytest.raises(VAPIException) as exc_info:
                await resolver.check_missing_assistants('invalid_squad', 'development')

            assert "Error checking assistant dependencies" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_dependency_status(self, resolver):
        """Test getting deployment status for all dependencies."""
        with patch.object(resolver.squad_config_loader, 'load_squad') as mock_load:
            with patch.object(resolver.deployment_state_manager, 'get_deployment_info') as mock_deployment:
                # Setup mocks
                mock_load.return_value = Mock(members=[
                    {'assistant_name': 'assistant1'},
                    {'assistant_name': 'assistant2'},
                    {'assistant_name': 'assistant3'}
                ])

                # Mock deployment status
                def deployment_side_effect(name, env):
                    if name == 'assistant1':
                        return Mock(is_deployed=True)
                    elif name == 'assistant2':
                        return Mock(is_deployed=False)
                    else:
                        return Mock(is_deployed=True)

                mock_deployment.side_effect = deployment_side_effect

                # Get dependency status
                status = await resolver.get_dependency_status('test_squad', 'development')

                # Assert correct status
                assert status == {
                    'assistant1': True,
                    'assistant2': False,
                    'assistant3': True
                }

    @pytest.mark.asyncio
    async def test_deploy_assistant_success(self, resolver, temp_dir):
        """Test successful deployment of a single assistant."""
        assistant_name = 'test_assistant'
        assistant_path = Path(temp_dir) / "assistants" / assistant_name
        assistant_path.mkdir(parents=True)

        # Create mock assistant configuration
        with open(assistant_path / "assistant.yaml", "w") as f:
            f.write("name: test_assistant\n")

        with patch('vapi_manager.core.assistant_config.AssistantConfigLoader') as MockLoader:
            with patch('vapi_manager.core.assistant_config.AssistantBuilder') as MockBuilder:
                with patch.object(resolver.assistant_service, 'create_assistant') as mock_create:
                    with patch.object(resolver.deployment_state_manager, 'mark_deployed') as mock_mark:
                        # Setup mocks
                        mock_config = Mock()
                        MockLoader.return_value.load_assistant.return_value = mock_config
                        MockLoader.return_value.validate_assistant_config.return_value = None
                        MockBuilder.return_value.build_assistant_request.return_value = Mock()

                        mock_assistant = Mock(
                            id='assistant-123',
                            name=assistant_name,
                            version=1,
                            created_at=datetime.now()
                        )
                        mock_create.return_value = mock_assistant

                        # Deploy assistant
                        assistant_id = await resolver.deploy_assistant(assistant_name, 'development')

                        # Assert successful deployment
                        assert assistant_id == 'assistant-123'
                        mock_create.assert_called_once()
                        mock_mark.assert_called_once_with(
                            assistant_name,
                            'development',
                            'assistant-123',
                            1
                        )

    @pytest.mark.asyncio
    async def test_deploy_assistant_not_found(self, resolver, temp_dir):
        """Test deployment failure when assistant configuration doesn't exist."""
        assistant_name = 'non_existent'

        # Deploy assistant (should fail)
        assistant_id = await resolver.deploy_assistant(assistant_name, 'development')

        # Assert deployment failed
        assert assistant_id is None

    @pytest.mark.asyncio
    async def test_deploy_assistant_api_failure(self, resolver, temp_dir):
        """Test deployment failure when VAPI API call fails."""
        assistant_name = 'test_assistant'
        assistant_path = Path(temp_dir) / "assistants" / assistant_name
        assistant_path.mkdir(parents=True)

        # Create mock assistant configuration
        with open(assistant_path / "assistant.yaml", "w") as f:
            f.write("name: test_assistant\n")

        with patch('vapi_manager.core.assistant_config.AssistantConfigLoader') as MockLoader:
            with patch('vapi_manager.core.assistant_config.AssistantBuilder') as MockBuilder:
                with patch.object(resolver.assistant_service, 'create_assistant') as mock_create:
                    # Setup mocks
                    mock_config = Mock()
                    MockLoader.return_value.load_assistant.return_value = mock_config
                    MockLoader.return_value.validate_assistant_config.return_value = None
                    MockBuilder.return_value.build_assistant_request.return_value = Mock()

                    # Mock API failure
                    mock_create.return_value = None

                    # Deploy assistant
                    assistant_id = await resolver.deploy_assistant(assistant_name, 'development')

                    # Assert deployment failed
                    assert assistant_id is None

    @pytest.mark.asyncio
    async def test_deploy_missing_assistants_with_confirmation(self, resolver):
        """Test deploying missing assistants with user confirmation."""
        with patch.object(resolver, 'check_missing_assistants') as mock_check:
            with patch.object(resolver, 'deploy_assistant') as mock_deploy:
                with patch('rich.prompt.Confirm.ask') as mock_confirm:
                    # Setup mocks
                    mock_check.return_value = ['assistant1', 'assistant2']
                    mock_deploy.side_effect = ['id1', 'id2']  # Both succeed
                    mock_confirm.return_value = True  # User confirms

                    # Deploy missing assistants
                    success, failed = await resolver.deploy_missing_assistants(
                        'test_squad',
                        'development',
                        force=False
                    )

                    # Assert all deployed successfully
                    assert success == ['assistant1', 'assistant2']
                    assert failed == []
                    assert mock_deploy.call_count == 2
                    mock_confirm.assert_called_once()

    @pytest.mark.asyncio
    async def test_deploy_missing_assistants_force(self, resolver):
        """Test deploying missing assistants with force flag (no confirmation)."""
        with patch.object(resolver, 'check_missing_assistants') as mock_check:
            with patch.object(resolver, 'deploy_assistant') as mock_deploy:
                with patch('rich.prompt.Confirm.ask') as mock_confirm:
                    # Setup mocks
                    mock_check.return_value = ['assistant1']
                    mock_deploy.return_value = 'id1'

                    # Deploy missing assistants with force
                    success, failed = await resolver.deploy_missing_assistants(
                        'test_squad',
                        'development',
                        force=True
                    )

                    # Assert deployed without confirmation
                    assert success == ['assistant1']
                    assert failed == []
                    mock_confirm.assert_not_called()

    @pytest.mark.asyncio
    async def test_deploy_missing_assistants_partial_failure(self, resolver):
        """Test deploying missing assistants with partial failures."""
        with patch.object(resolver, 'check_missing_assistants') as mock_check:
            with patch.object(resolver, 'deploy_assistant') as mock_deploy:
                # Setup mocks
                mock_check.return_value = ['assistant1', 'assistant2', 'assistant3']
                mock_deploy.side_effect = ['id1', None, 'id3']  # assistant2 fails

                # Deploy missing assistants
                success, failed = await resolver.deploy_missing_assistants(
                    'test_squad',
                    'development',
                    force=True
                )

                # Assert partial success
                assert success == ['assistant1', 'assistant3']
                assert failed == ['assistant2']

    @pytest.mark.asyncio
    async def test_deploy_missing_assistants_user_cancels(self, resolver):
        """Test user cancellation of assistant deployment."""
        with patch.object(resolver, 'check_missing_assistants') as mock_check:
            with patch('rich.prompt.Confirm.ask') as mock_confirm:
                # Setup mocks
                mock_check.return_value = ['assistant1']
                mock_confirm.return_value = False  # User cancels

                # Deploy missing assistants
                success, failed = await resolver.deploy_missing_assistants(
                    'test_squad',
                    'development',
                    force=False
                )

                # Assert nothing deployed
                assert success == []
                assert failed == ['assistant1']

    @pytest.mark.asyncio
    async def test_ensure_squad_dependencies_all_met(self, resolver):
        """Test ensuring dependencies when all are already met."""
        with patch.object(resolver, 'check_missing_assistants') as mock_check:
            # No missing assistants
            mock_check.return_value = []

            # Ensure dependencies
            result = await resolver.ensure_squad_dependencies(
                'test_squad',
                'development',
                auto_deploy=False
            )

            # Assert dependencies are met
            assert result is True
            mock_check.assert_called_once_with('test_squad', 'development')

    @pytest.mark.asyncio
    async def test_ensure_squad_dependencies_auto_deploy_success(self, resolver):
        """Test ensuring dependencies with auto-deployment success."""
        with patch.object(resolver, 'check_missing_assistants') as mock_check:
            with patch.object(resolver, 'deploy_missing_assistants') as mock_deploy:
                # Setup mocks
                mock_check.return_value = ['assistant1', 'assistant2']
                mock_deploy.return_value = (['assistant1', 'assistant2'], [])  # All succeed

                # Ensure dependencies with auto-deploy
                result = await resolver.ensure_squad_dependencies(
                    'test_squad',
                    'development',
                    auto_deploy=True,
                    force=True
                )

                # Assert dependencies are met after deployment
                assert result is True
                mock_deploy.assert_called_once_with('test_squad', 'development', True)

    @pytest.mark.asyncio
    async def test_ensure_squad_dependencies_auto_deploy_failure(self, resolver):
        """Test ensuring dependencies with auto-deployment failure."""
        with patch.object(resolver, 'check_missing_assistants') as mock_check:
            with patch.object(resolver, 'deploy_missing_assistants') as mock_deploy:
                # Setup mocks
                mock_check.return_value = ['assistant1', 'assistant2']
                mock_deploy.return_value = (['assistant1'], ['assistant2'])  # One fails

                # Ensure dependencies with auto-deploy
                result = await resolver.ensure_squad_dependencies(
                    'test_squad',
                    'development',
                    auto_deploy=True,
                    force=True
                )

                # Assert dependencies are not met due to failure
                assert result is False

    @pytest.mark.asyncio
    async def test_ensure_squad_dependencies_no_auto_deploy(self, resolver):
        """Test ensuring dependencies without auto-deployment."""
        with patch.object(resolver, 'check_missing_assistants') as mock_check:
            # Setup mocks
            mock_check.return_value = ['assistant1']

            # Ensure dependencies without auto-deploy
            result = await resolver.ensure_squad_dependencies(
                'test_squad',
                'development',
                auto_deploy=False
            )

            # Assert dependencies are not met
            assert result is False

    def test_get_all_squad_assistants_success(self, resolver):
        """Test getting all assistant names from a squad."""
        with patch.object(resolver.squad_config_loader, 'load_squad') as mock_load:
            # Setup mock
            mock_load.return_value = Mock(members=[
                {'assistant_name': 'assistant1'},
                {'assistant_name': 'assistant2'},
                {'assistant_name': 'assistant1'},  # Duplicate
                {'assistant_name': 'assistant3'}
            ])

            # Get all assistants
            assistants = resolver.get_all_squad_assistants('test_squad')

            # Assert unique set of assistants
            assert assistants == {'assistant1', 'assistant2', 'assistant3'}

    def test_get_all_squad_assistants_error_handling(self, resolver):
        """Test error handling when getting squad assistants."""
        with patch.object(resolver.squad_config_loader, 'load_squad') as mock_load:
            # Setup mock to raise exception
            mock_load.side_effect = Exception("Squad not found")

            # Get all assistants (should handle error gracefully)
            assistants = resolver.get_all_squad_assistants('invalid_squad')

            # Assert empty set returned on error
            assert assistants == set()


class TestIntegrationSquadDependencyResolver:
    """Integration tests for SquadDependencyResolver with actual file system."""

    @pytest.fixture
    def integration_setup(self):
        """Set up integration test environment."""
        temp_path = tempfile.mkdtemp()
        squads_dir = Path(temp_path) / "squads"
        assistants_dir = Path(temp_path) / "assistants"

        # Create directories
        squads_dir.mkdir(parents=True)
        assistants_dir.mkdir(parents=True)

        # Create test squad
        squad_dir = squads_dir / "test_squad"
        squad_dir.mkdir()

        # Create squad configuration
        squad_config = {
            "name": "test_squad",
            "description": "Test squad for integration testing",
            "members": [
                {"assistant_name": "assistant1", "role": "primary"},
                {"assistant_name": "assistant2", "role": "secondary"}
            ]
        }

        with open(squad_dir / "squad.yaml", "w") as f:
            import yaml
            yaml.dump(squad_config, f)

        with open(squad_dir / "members.yaml", "w") as f:
            yaml.dump({"members": squad_config["members"]}, f)

        # Create assistant configurations
        for i in range(1, 3):
            assistant_dir = assistants_dir / f"assistant{i}"
            assistant_dir.mkdir()

            assistant_config = {
                "name": f"assistant{i}",
                "description": f"Test assistant {i}",
                "model": {"provider": "openai", "model": "gpt-3.5-turbo"},
                "voice": {"provider": "elevenlabs", "voiceId": "test"},
                "_vapi": {
                    "environments": {
                        "development": {
                            "id": None if i == 2 else f"assistant{i}-id",
                            "deployed_at": None if i == 2 else "2024-01-01T00:00:00Z",
                            "version": 0 if i == 2 else 1
                        }
                    }
                }
            }

            with open(assistant_dir / "assistant.yaml", "w") as f:
                yaml.dump(assistant_config, f)

        yield {
            "temp_path": temp_path,
            "squads_dir": str(squads_dir),
            "assistants_dir": str(assistants_dir)
        }

        # Cleanup
        shutil.rmtree(temp_path)

    @pytest.mark.asyncio
    async def test_integration_check_missing_assistants(self, integration_setup):
        """Integration test for checking missing assistants with real files."""
        resolver = SquadDependencyResolver(
            integration_setup["squads_dir"],
            integration_setup["assistants_dir"]
        )

        # Check missing assistants
        missing = await resolver.check_missing_assistants('test_squad', 'development')

        # Assert only assistant2 is missing (based on setup)
        assert missing == ['assistant2']

    @pytest.mark.asyncio
    async def test_integration_get_dependency_status(self, integration_setup):
        """Integration test for getting dependency status with real files."""
        resolver = SquadDependencyResolver(
            integration_setup["squads_dir"],
            integration_setup["assistants_dir"]
        )

        # Get dependency status
        status = await resolver.get_dependency_status('test_squad', 'development')

        # Assert correct status based on setup
        assert status == {
            'assistant1': True,  # Has deployment ID in setup
            'assistant2': False  # No deployment ID in setup
        }

    def test_integration_get_all_squad_assistants(self, integration_setup):
        """Integration test for getting all squad assistants with real files."""
        resolver = SquadDependencyResolver(
            integration_setup["squads_dir"],
            integration_setup["assistants_dir"]
        )

        # Get all assistants
        assistants = resolver.get_all_squad_assistants('test_squad')

        # Assert correct assistants
        assert assistants == {'assistant1', 'assistant2'}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])