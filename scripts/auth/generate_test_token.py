#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""Generate a test token for API testing."""

from .api.auth import create_token

# Generate token with sparkjar_internal scope
token = create_token(
    user_id="587f8370-825f-4f0c-8846-2e6d70782989",  # Same user_id from test
    scopes=["sparkjar_internal"],
    expires_in_hours=24
)

logger.info(f"Token: {token}")
logger.info(f"\nUse this curl command:")
logger.info(f'curl -X POST http://localhost:8000/crew_job \\')
logger.info(f'  -H "Authorization: Bearer {token}" \\')
logger.info(f'  -H "Content-Type: application/json" \\')
logger.info(f'  -d @/Users/r.t.rawlings/sparkjar-crew/test_entity_research_crew.json')