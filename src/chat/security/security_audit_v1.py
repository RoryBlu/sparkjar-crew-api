"""
Security Audit Implementation for Chat with Memory v1.

KISS principles:
- Simple security checks
- Clear validation rules
- Proper error handling
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import ValidationError

from src.chat.models import ChatRequestV1

logger = logging.getLogger(__name__)


class SecurityAuditor:
    """
    Security audit and validation for chat system.
    
    KISS: Validate inputs, check authorization, log security events.
    """
    
    def __init__(self):
        """Initialize security auditor."""
        self.security_events = []
        
        # Simple patterns for dangerous content
        self.dangerous_patterns = [
            r"<script.*?>.*?</script>",  # Script injection
            r"javascript:",  # JavaScript protocol
            r"on\w+\s*=",  # Event handlers
            r"union\s+select",  # SQL injection
            r"drop\s+table",  # SQL injection
            r"\$\{.*?\}",  # Template injection
            r"__.*__",  # Python magic methods
            r"eval\s*\(",  # Code execution
            r"exec\s*\(",  # Code execution
        ]
        
    def audit_request(
        self,
        request: ChatRequestV1,
        user_context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Audit incoming chat request for security issues.
        
        Args:
            request: Chat request to audit
            user_context: User authentication context
            
        Returns:
            Tuple of (is_safe, error_message)
        """
        # 1. Validate authentication
        if not self._validate_authentication(user_context):
            self._log_security_event("auth_failure", user_context)
            return False, "Authentication required"
            
        # 2. Validate authorization
        if not self._validate_authorization(request, user_context):
            self._log_security_event("authz_failure", user_context)
            return False, "Unauthorized access"
            
        # 3. Validate input
        if not self._validate_input(request):
            self._log_security_event("input_validation_failure", user_context)
            return False, "Invalid input detected"
            
        # 4. Check for dangerous content
        if self._contains_dangerous_content(request.message):
            self._log_security_event("dangerous_content", user_context)
            return False, "Potentially dangerous content detected"
            
        # 5. Validate request size
        if not self._validate_request_size(request):
            self._log_security_event("oversized_request", user_context)
            return False, "Request too large"
            
        return True, None
        
    def audit_response(
        self,
        response: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Audit outgoing response for security issues.
        
        Args:
            response: Response data
            user_context: User context
            
        Returns:
            Tuple of (is_safe, error_message)
        """
        # 1. Check for data leakage
        if self._contains_sensitive_data(response):
            self._log_security_event("data_leakage", user_context)
            return False, "Response contains sensitive data"
            
        # 2. Validate response structure
        if not self._validate_response_structure(response):
            return False, "Invalid response structure"
            
        return True, None
        
    def validate_session_access(
        self,
        session_id: UUID,
        user_id: UUID,
        session_user_id: UUID
    ) -> bool:
        """
        Validate user has access to session.
        
        Args:
            session_id: Session being accessed
            user_id: User making request
            session_user_id: Owner of session
            
        Returns:
            True if access allowed
        """
        # Simple ownership check
        if user_id != session_user_id:
            self._log_security_event(
                "unauthorized_session_access",
                {
                    "user_id": str(user_id),
                    "session_id": str(session_id),
                    "session_owner": str(session_user_id)
                }
            )
            return False
            
        return True
        
    def validate_memory_realm_access(
        self,
        user_context: Dict[str, Any],
        requested_realms: Dict[str, bool]
    ) -> Dict[str, bool]:
        """
        Validate and filter memory realm access.
        
        Args:
            user_context: User authentication context
            requested_realms: Requested realm access
            
        Returns:
            Filtered realms user can access
        """
        allowed_realms = requested_realms.copy()
        
        # Check user permissions
        user_scopes = user_context.get("scopes", [])
        
        # CLIENT realm requires special permission
        if requested_realms.get("include_client", False):
            if "client_admin" not in user_scopes:
                allowed_realms["include_client"] = False
                self._log_security_event(
                    "client_realm_denied",
                    user_context
                )
                
        return allowed_realms
        
    def get_security_report(self) -> Dict[str, Any]:
        """
        Get security audit report.
        
        Returns:
            Security event summary
        """
        event_counts = {}
        for event in self.security_events:
            event_type = event["type"]
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
        return {
            "total_events": len(self.security_events),
            "event_counts": event_counts,
            "recent_events": self.security_events[-10:]  # Last 10 events
        }
        
    def _validate_authentication(
        self,
        user_context: Dict[str, Any]
    ) -> bool:
        """Validate user is authenticated."""
        # Check required fields
        required = ["user_id", "client_id", "scopes"]
        for field in required:
            if field not in user_context:
                return False
                
        # Validate user_id format
        try:
            UUID(user_context["user_id"])
            UUID(user_context["client_id"])
        except (ValueError, TypeError):
            return False
            
        return True
        
    def _validate_authorization(
        self,
        request: ChatRequestV1,
        user_context: Dict[str, Any]
    ) -> bool:
        """Validate user is authorized for request."""
        # Check basic scope
        scopes = user_context.get("scopes", [])
        if "sparkjar_internal" not in scopes:
            return False
            
        # Additional checks could go here
        return True
        
    def _validate_input(
        self,
        request: ChatRequestV1
    ) -> bool:
        """Validate request input."""
        try:
            # Pydantic validation
            request.dict()
            
            # Additional validation
            if not request.message or len(request.message.strip()) == 0:
                return False
                
            # Check mode
            if request.mode not in ["tutor", "agent"]:
                return False
                
            return True
            
        except ValidationError:
            return False
            
    def _contains_dangerous_content(
        self,
        text: str
    ) -> bool:
        """Check for dangerous patterns in text."""
        text_lower = text.lower()
        
        for pattern in self.dangerous_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
                
        return False
        
    def _validate_request_size(
        self,
        request: ChatRequestV1
    ) -> bool:
        """Validate request size limits."""
        # Message size limit (10KB)
        if len(request.message) > 10240:
            return False
            
        # Learning preferences size
        if request.learning_preferences:
            pref_str = str(request.learning_preferences)
            if len(pref_str) > 1024:
                return False
                
        return True
        
    def _contains_sensitive_data(
        self,
        response: Dict[str, Any]
    ) -> bool:
        """Check for sensitive data in response."""
        # Convert to string for checking
        response_str = str(response).lower()
        
        # Check for common sensitive patterns
        sensitive_patterns = [
            r"password\s*[:=]",
            r"api[_-]?key\s*[:=]",
            r"secret\s*[:=]",
            r"token\s*[:=]",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, response_str, re.IGNORECASE):
                return True
                
        return False
        
    def _validate_response_structure(
        self,
        response: Dict[str, Any]
    ) -> bool:
        """Validate response has expected structure."""
        # Check required fields
        required_fields = ["session_id", "message_id", "response"]
        for field in required_fields:
            if field not in response:
                return False
                
        return True
        
    def _log_security_event(
        self,
        event_type: str,
        context: Dict[str, Any]
    ):
        """Log security event."""
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context
        }
        
        self.security_events.append(event)
        logger.warning(f"Security event: {event_type} - {context}")


from datetime import datetime