"""
Unit tests for Agent Mode Processor.

KISS: Test passive agent behavior with mocks.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.chat.models import ChatRequestV1, ChatSessionV1, MemorySearchResult
from src.chat.processors.agent_mode_v1 import AgentModeProcessor


class TestAgentModeProcessor:
    """Test agent mode processing."""
    
    @pytest.fixture
    def mock_memory_searcher(self):
        """Create mock memory searcher."""
        searcher = AsyncMock()
        searcher.search_with_precedence = AsyncMock()
        return searcher
        
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        return MagicMock()
        
    @pytest.fixture
    def processor(self, mock_memory_searcher, mock_llm_client):
        """Create agent processor."""
        return AgentModeProcessor(mock_memory_searcher, mock_llm_client)
        
    @pytest.fixture
    def sample_request(self):
        """Create sample request."""
        return ChatRequestV1(
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=uuid4(),
            message="How do I create a user in the database?",
            mode="agent"
        )
        
    @pytest.fixture
    def sample_session(self):
        """Create sample agent session."""
        return ChatSessionV1(
            session_id=uuid4(),
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=str(uuid4()),
            mode="agent"
        )
        
    async def test_process_request_with_procedure(
        self,
        processor,
        sample_request,
        sample_session,
        mock_memory_searcher
    ):
        """Test processing with procedure found."""
        # Mock memory with procedure
        mock_memory_searcher.search_with_precedence.return_value = MemorySearchResult(
            memories=[
                {
                    "entity_name": "create_user_sop",
                    "entity": {"type": "procedure"},
                    "observations": [
                        {"type": "step", "value": "1. Connect to database"},
                        {"type": "step", "value": "2. Run CREATE USER command"}
                    ],
                    "metadata": {}
                }
            ],
            realms_accessed={"synth": 1},
            relationships_traversed=1,
            query_time_ms=30
        )
        
        # Process request
        response = await processor.process_request(
            sample_request,
            sample_session,
            uuid4()
        )
        
        # Verify response
        assert response.mode_used == "agent"
        assert response.memory_context_used == ["create_user_sop"]
        assert response.task_context is not None
        assert "procedures_followed" in response.task_context
        assert len(response.task_context["procedures_followed"]) == 1
        
    async def test_process_request_with_client_policy(
        self,
        processor,
        sample_request,
        sample_session,
        mock_memory_searcher
    ):
        """Test CLIENT policies override everything."""
        # Mock memory with CLIENT policy
        mock_memory_searcher.search_with_precedence.return_value = MemorySearchResult(
            memories=[
                {
                    "entity_name": "security_policy",
                    "entity": {"type": "policy"},
                    "metadata": {"hierarchy_level": "client"},
                    "observations": [
                        {"type": "rule", "value": "All users must have strong passwords"}
                    ]
                }
            ],
            realms_accessed={"client": 1},
            relationships_traversed=0,
            query_time_ms=25
        )
        
        # Process request
        response = await processor.process_request(
            sample_request,
            sample_session,
            uuid4()
        )
        
        # Verify CLIENT policy was applied
        assert response.task_context["policies_applied"] == ["security_policy"]
        
    def test_analyze_intent_procedure(self, processor):
        """Test intent analysis for procedures."""
        intent = processor._analyze_intent("How to create a database backup?")
        
        assert intent["task_type"] == "procedure"
        assert intent["action"] == "create"
        
    def test_analyze_intent_troubleshooting(self, processor):
        """Test intent analysis for troubleshooting."""
        intent = processor._analyze_intent("Fix connection timeout error")
        
        assert intent["task_type"] == "troubleshooting"
        assert intent["action"] == "fix"
        
    def test_analyze_intent_with_entities(self, processor):
        """Test entity extraction from intent."""
        intent = processor._analyze_intent('Create table "users" with columns')
        
        assert "users" in intent["entities"]
        
    def test_extract_procedures(self, processor):
        """Test procedure extraction from memories."""
        memories = [
            {
                "entity_name": "backup_sop",
                "entity": {"type": "procedure"},
                "observations": [
                    {"type": "step", "value": "Step 1"},
                    {"type": "step", "value": "Step 2"}
                ]
            },
            {
                "entity_name": "not_a_procedure",
                "entity": {"type": "concept"},
                "observations": []
            }
        ]
        
        procedures = processor._extract_procedures(memories)
        
        assert len(procedures) == 1
        assert procedures[0]["name"] == "backup_sop"
        assert len(procedures[0]["steps"]) == 2
        
    def test_extract_client_policies(self, processor):
        """Test CLIENT policy extraction."""
        memories = [
            {
                "entity_name": "data_policy",
                "entity": {"type": "policy"},
                "metadata": {"hierarchy_level": "client"},
                "observations": [
                    {"type": "rule", "value": {"content": "Encrypt all data"}}
                ]
            },
            {
                "entity_name": "other_policy",
                "entity": {"type": "policy"},
                "metadata": {"hierarchy_level": "synth"},  # Not CLIENT
                "observations": []
            }
        ]
        
        policies = processor._extract_client_policies(memories)
        
        assert len(policies) == 1
        assert policies[0]["name"] == "data_policy"
        assert policies[0]["priority"] == "override"
        assert "Encrypt all data" in policies[0]["rules"]
        
    def test_create_task_summary(self, processor):
        """Test task summary creation."""
        intent = {
            "task_type": "procedure",
            "action": "create",
            "entities": ["users", "database"]
        }
        procedures = [{"name": "create_user_sop"}]
        
        summary = processor._create_task_summary(
            intent,
            procedures,
            "Created user successfully"
        )
        
        assert summary["task_type"] == "procedure"
        assert summary["action_taken"] == "create"
        assert summary["procedures_used"] == 1
        assert summary["entities_involved"] == ["users", "database"]
        
    def test_build_procedure_context(self, processor):
        """Test procedure context building."""
        procedures = [
            {
                "name": "backup_procedure",
                "steps": ["1. Stop service", "2. Copy files", "3. Restart"]
            }
        ]
        
        context = processor._build_procedure_context(procedures)
        
        assert "backup_procedure" in context
        assert "1. Stop service" in context
        assert "2. Copy files" in context