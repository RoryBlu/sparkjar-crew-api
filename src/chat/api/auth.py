"""
Authentication and authorization utilities for the chat service.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from src.chat.config import get_settings

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


class TokenData(BaseModel):
    """JWT token payload data."""
    client_user_id: UUID
    actor_type: str
    actor_id: UUID
    scopes: list[str] = []
    exp: Optional[datetime] = None


class AuthError(Exception):
    """Authentication error."""
    pass


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Token payload data
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    settings = get_settings()
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
        
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """
    Verify JWT token and extract token data.
    
    Args:
        credentials: HTTP bearer credentials
        
    Returns:
        Decoded token data
        
    Raises:
        HTTPException: On invalid token
    """
    settings = get_settings()
    token = credentials.credentials
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Extract required fields
        client_user_id = payload.get("client_user_id")
        actor_type = payload.get("actor_type")
        actor_id = payload.get("actor_id")
        scopes = payload.get("scopes", [])
        
        if not all([client_user_id, actor_type, actor_id]):
            logger.warning("Token missing required fields")
            raise credentials_exception
            
        token_data = TokenData(
            client_user_id=UUID(client_user_id),
            actor_type=actor_type,
            actor_id=UUID(actor_id),
            scopes=scopes
        )
        
        # Verify actor type is valid
        if actor_type not in ["synth", "human", "system"]:
            logger.warning(f"Invalid actor type: {actor_type}")
            raise credentials_exception
            
        return token_data
        
    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise credentials_exception
    except ValueError as e:
        logger.error(f"Invalid UUID in token: {e}")
        raise credentials_exception


async def verify_synth_access(token_data: TokenData = Depends(verify_token)) -> TokenData:
    """
    Verify the token belongs to a SYNTH actor.
    
    Args:
        token_data: Decoded token data
        
    Returns:
        Token data if valid
        
    Raises:
        HTTPException: If not a SYNTH actor
    """
    if token_data.actor_type != "synth":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to SYNTH actors"
        )
        
    return token_data


async def verify_scope(
    required_scope: str,
    token_data: TokenData = Depends(verify_token)
) -> TokenData:
    """
    Verify the token has a required scope.
    
    Args:
        required_scope: Scope to check for
        token_data: Decoded token data
        
    Returns:
        Token data if valid
        
    Raises:
        HTTPException: If scope not present
    """
    if required_scope not in token_data.scopes and "admin" not in token_data.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required scope: {required_scope}"
        )
        
    return token_data


# Dependency for chat endpoints
async def verify_chat_access(token_data: TokenData = Depends(verify_token)) -> TokenData:
    """
    Verify access to chat endpoints.
    
    For MVP, we just verify valid token. In production, we'd check:
    - SYNTH ownership
    - Client permissions
    - Rate limits
    
    Args:
        token_data: Decoded token data
        
    Returns:
        Token data if valid
    """
    # For MVP, just ensure valid token
    # In production, add more sophisticated checks
    return token_data
