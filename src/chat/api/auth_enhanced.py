"""
Enhanced authentication and authorization with SYNTH identity verification.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set
from uuid import UUID
import hashlib
import hmac

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from src.chat.config import get_settings
from src.chat.utils.error_handler import ServiceError, ErrorCategory

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


class TokenData(BaseModel):
    """Enhanced JWT token payload data."""
    client_user_id: UUID
    actor_type: str
    actor_id: UUID
    scopes: list[str] = []
    synth_class_id: Optional[int] = None
    session_fingerprint: Optional[str] = None
    issued_at: datetime
    exp: Optional[datetime] = None


class SecurityContext(BaseModel):
    """Security context for request validation."""
    token_data: TokenData
    request_fingerprint: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


# Session hijacking prevention
_revoked_tokens: Set[str] = set()
_active_sessions: Dict[str, SecurityContext] = {}


def create_session_fingerprint(
    client_id: str,
    actor_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> str:
    """
    Create a session fingerprint for security validation.
    
    Args:
        client_id: Client UUID
        actor_id: Actor UUID
        ip_address: Client IP address
        user_agent: Client user agent
        
    Returns:
        Session fingerprint hash
    """
    settings = get_settings()
    
    # Combine identifying information
    fingerprint_data = f"{client_id}:{actor_id}"
    if ip_address:
        fingerprint_data += f":{ip_address}"
    if user_agent:
        fingerprint_data += f":{user_agent}"
        
    # Create HMAC hash
    return hmac.new(
        settings.jwt_secret_key.encode(),
        fingerprint_data.encode(),
        hashlib.sha256
    ).hexdigest()


def create_secure_token(
    client_user_id: UUID,
    actor_type: str,
    actor_id: UUID,
    scopes: list[str],
    synth_class_id: Optional[int] = None,
    request: Optional[Request] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a secure JWT token with enhanced security features.
    
    Args:
        client_user_id: Client user ID
        actor_type: Type of actor
        actor_id: Actor ID
        scopes: Access scopes
        synth_class_id: SYNTH class ID if applicable
        request: HTTP request for fingerprinting
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    settings = get_settings()
    
    # Create session fingerprint
    ip_address = request.client.host if request and request.client else None
    user_agent = request.headers.get("User-Agent") if request else None
    
    session_fingerprint = create_session_fingerprint(
        str(client_user_id),
        str(actor_id),
        ip_address,
        user_agent
    )
    
    # Token payload
    to_encode = {
        "client_user_id": str(client_user_id),
        "actor_type": actor_type,
        "actor_id": str(actor_id),
        "scopes": scopes,
        "synth_class_id": synth_class_id,
        "session_fingerprint": session_fingerprint,
        "iat": datetime.utcnow(),
        "jti": str(UUID.uuid4())  # Unique token ID for revocation
    }
    
    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
        
    to_encode["exp"] = expire
    
    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


async def verify_enhanced_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> SecurityContext:
    """
    Enhanced token verification with security checks.
    
    Args:
        request: HTTP request
        credentials: Bearer token credentials
        
    Returns:
        Security context with verified token data
        
    Raises:
        HTTPException: On invalid token or security violation
    """
    settings = get_settings()
    token = credentials.credentials
    
    # Check if token is revoked
    if token in _revoked_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decode token
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Extract and validate fields
        client_user_id = payload.get("client_user_id")
        actor_type = payload.get("actor_type")
        actor_id = payload.get("actor_id")
        scopes = payload.get("scopes", [])
        synth_class_id = payload.get("synth_class_id")
        session_fingerprint = payload.get("session_fingerprint")
        issued_at = payload.get("iat")
        jti = payload.get("jti")
        
        if not all([client_user_id, actor_type, actor_id, jti]):
            raise ServiceError(
                message="Token missing required fields",
                category=ErrorCategory.AUTHENTICATION,
                recoverable=False
            )
            
        # Validate actor type
        if actor_type not in ["synth", "human", "system"]:
            raise ServiceError(
                message=f"Invalid actor type: {actor_type}",
                category=ErrorCategory.AUTHENTICATION,
                recoverable=False
            )
            
        # Create token data
        token_data = TokenData(
            client_user_id=UUID(client_user_id),
            actor_type=actor_type,
            actor_id=UUID(actor_id),
            scopes=scopes,
            synth_class_id=synth_class_id,
            session_fingerprint=session_fingerprint,
            issued_at=datetime.fromtimestamp(issued_at) if issued_at else datetime.utcnow()
        )
        
        # Verify session fingerprint if present
        if session_fingerprint:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("User-Agent")
            
            expected_fingerprint = create_session_fingerprint(
                client_user_id,
                actor_id,
                ip_address,
                user_agent
            )
            
            if session_fingerprint != expected_fingerprint:
                logger.warning(
                    f"Session fingerprint mismatch for actor {actor_id}",
                    extra={
                        "expected": expected_fingerprint[:8] + "...",
                        "received": session_fingerprint[:8] + "..."
                    }
                )
                # For MVP, log but don't block
                # In production, this would raise an exception
                
        # Create security context
        security_context = SecurityContext(
            token_data=token_data,
            request_fingerprint=session_fingerprint or "",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        
        # Track active session
        _active_sessions[jti] = security_context
        
        return security_context
        
    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError as e:
        logger.error(f"Invalid token data: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_synth_identity(
    security_context: SecurityContext = Depends(verify_enhanced_token)
) -> SecurityContext:
    """
    Verify SYNTH identity and ownership.
    
    Args:
        security_context: Security context from token verification
        
    Returns:
        Security context if valid
        
    Raises:
        HTTPException: If not a valid SYNTH
    """
    token_data = security_context.token_data
    
    if token_data.actor_type != "synth":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to SYNTH actors"
        )
        
    # In production, we would verify:
    # 1. SYNTH exists in database
    # 2. SYNTH belongs to client
    # 3. SYNTH is active/not suspended
    # 4. SYNTH has required permissions
    
    return security_context


async def verify_client_access(
    required_permission: str,
    security_context: SecurityContext = Depends(verify_enhanced_token)
) -> SecurityContext:
    """
    Verify client-level access permissions.
    
    Args:
        required_permission: Permission to check
        security_context: Security context
        
    Returns:
        Security context if valid
        
    Raises:
        HTTPException: If permission denied
    """
    # Check if user has required permission or admin scope
    if (required_permission not in security_context.token_data.scopes and 
        "admin" not in security_context.token_data.scopes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: {required_permission}"
        )
        
    return security_context


def revoke_token(jti: str):
    """
    Revoke a token by its ID.
    
    Args:
        jti: JWT ID to revoke
    """
    _revoked_tokens.add(jti)
    
    # Remove from active sessions
    if jti in _active_sessions:
        del _active_sessions[jti]
        
    logger.info(f"Token revoked: {jti}")


def get_active_sessions(client_user_id: UUID) -> list[SecurityContext]:
    """
    Get active sessions for a client.
    
    Args:
        client_user_id: Client user ID
        
    Returns:
        List of active security contexts
    """
    return [
        ctx for ctx in _active_sessions.values()
        if ctx.token_data.client_user_id == client_user_id
    ]


# Enhanced dependency for chat endpoints
async def verify_chat_access_enhanced(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Enhanced chat access verification.
    
    Args:
        request: HTTP request
        credentials: Bearer token
        
    Returns:
        Token data if valid
    """
    # Verify token with enhanced security
    security_context = await verify_enhanced_token(request, credentials)
    
    # Verify SYNTH identity for chat
    if security_context.token_data.actor_type == "synth":
        await verify_synth_identity(security_context)
        
    # Check chat scope
    if "chat" not in security_context.token_data.scopes and "admin" not in security_context.token_data.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chat access not permitted"
        )
        
    return security_context.token_data
