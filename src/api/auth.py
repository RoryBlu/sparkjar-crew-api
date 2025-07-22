"""
Authentication utilities for API endpoints.
Handles bearer token verification with configurable scopes and expiration.
"""
from typing import Dict, Any, List
import jwt
from datetime import datetime, timedelta
import logging
from sparkjar_crew.shared.config.shared_settings import (
    JWT_SECRET_KEY, JWT_ALGORITHM, TOKEN_DEFAULT_EXPIRY_HOURS, 
    TOKEN_MAX_EXPIRY_HOURS, TOKEN_AVAILABLE_SCOPES, TOKEN_DEFAULT_SCOPES,
    ENVIRONMENT
)

logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

def validate_token_request(scopes: List[str], expires_in_hours: int) -> None:
    """
    Validate token creation request against environment constraints.
    
    Args:
        scopes: Requested scopes
        expires_in_hours: Requested expiration time
        
    Raises:
        ValueError: If request violates environment constraints
    """
    # Validate scopes
    invalid_scopes = [scope for scope in scopes if scope not in TOKEN_AVAILABLE_SCOPES]
    if invalid_scopes:
        raise ValueError(f"Invalid scopes for {ENVIRONMENT} environment: {invalid_scopes}. "
                        f"Available scopes: {TOKEN_AVAILABLE_SCOPES}")
    
    # Validate expiration time
    if expires_in_hours > TOKEN_MAX_EXPIRY_HOURS:
        raise ValueError(f"Token expiration {expires_in_hours}h exceeds maximum {TOKEN_MAX_EXPIRY_HOURS}h "
                        f"for {ENVIRONMENT} environment")
    
    if expires_in_hours <= 0:
        raise ValueError("Token expiration must be positive")

def create_token(user_id: str, scopes: List[str] = None, expires_in_hours: int = None) -> str:
    """
    Create a JWT token with specified scopes and configurable expiration.
    
    Args:
        user_id: User identifier
        scopes: List of permission scopes (defaults to environment default)
        expires_in_hours: Token expiration time in hours (defaults to environment default)
        
    Returns:
        JWT token string
        
    Raises:
        ValueError: If scopes or expiration violate environment constraints
    """
    # Use environment defaults if not specified
    if scopes is None:
        scopes = TOKEN_DEFAULT_SCOPES.copy()
    if expires_in_hours is None:
        expires_in_hours = TOKEN_DEFAULT_EXPIRY_HOURS
    
    # Validate request
    validate_token_request(scopes, expires_in_hours)
    
    payload = {
        "user_id": user_id,
        "scopes": scopes,
        "exp": datetime.utcnow() + timedelta(hours=expires_in_hours),
        "iat": datetime.utcnow(),
        "environment": ENVIRONMENT
    }
    
    logger.info(f"Creating token for user '{user_id}' with scopes {scopes} "
               f"(expires in {expires_in_hours}h)")
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        # Decode and verify token - jwt.decode automatically checks expiration
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Additional validation for environment consistency
        token_env = payload.get("environment")
        if token_env and token_env != ENVIRONMENT:
            logger.warning(f"Token environment mismatch: token={token_env}, current={ENVIRONMENT}")
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise AuthenticationError("Token verification failed")

def has_scope(token_data: Dict[str, Any], required_scope: str) -> bool:
    """
    Check if token has required scope.
    
    Args:
        token_data: Decoded token payload
        required_scope: Required permission scope
        
    Returns:
        True if token has the required scope
    """
    scopes = token_data.get("scopes", [])
    return required_scope in scopes

def create_internal_token() -> str:
    """
    Create a token with sparkjar_internal scope for internal service communication.
    Uses environment-specific internal token expiration settings.
    
    Returns:
        JWT token with internal permissions
    """
    from sparkjar_crew.shared.config.shared_settings import TOKEN_INTERNAL_EXPIRY_HOURS
    
    return create_token(
        user_id="system",
        scopes=["sparkjar_internal"],
        expires_in_hours=TOKEN_INTERNAL_EXPIRY_HOURS
    )

# For development/testing purposes
def create_dev_token() -> str:
    """
    Create a development token with all scopes.
    Only use in development environment!
    
    Returns:
        JWT token with all permissions
    """
    return create_token(
        user_id="dev_user",
        scopes=["sparkjar_internal", "admin", "user"],
        expires_in_hours=24
    )
