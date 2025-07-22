#!/usr/bin/env python

import logging
logger = logging.getLogger(__name__)

"""Generate a test JWT token for API testing."""

import sys
import os

from .api.auth import create_token

# Generate a test token with sparkjar_internal scope
token = create_token(
    user_id="test-user",
    scopes=["sparkjar_internal"]
)

logger.info("Test JWT Token:")
logger.info(token)
logger.info("\nUse this token in the Authorization header:")
logger.info(f"Authorization: Bearer {token}")