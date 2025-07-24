#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""
Seed the contact_form schema into object_schemas table.
This schema is used for the crew_message_api endpoint.
"""

import asyncio
import json
import sys
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add project paths
project_root = os.path.join(os.path.dirname(__file__), '..')

from services.crew_api.src.database.connection import get_direct_session
from services.crew_api.src.database.models import ObjectSchemas

contact_form_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "N3xusIQ Inquiry",
    "description": "Schema for contact form inquiries sent to SparkJar Crew API",
    "type": "object",
    "required": [
        "api_key",
        "inquiry_type",
        "contact",
        "message",
        "metadata"
    ],
    "properties": {
        "api_key": {
            "type": "string",
            "description": "SparkJar API key for authentication",
            "minLength": 1
        },
        "inquiry_type": {
            "type": "string",
            "description": "Type of inquiry",
            "enum": ["contact_form", "demo_request", "early_access"]
        },
        "contact": {
            "type": "object",
            "description": "Contact information",
            "required": ["name", "email"],
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Full name of the person",
                    "minLength": 1
                },
                "email": {
                    "type": "string",
                    "description": "Email address",
                    "format": "email"
                },
                "company": {
                    "type": "string",
                    "description": "Company name (optional)"
                },
                "phone": {
                    "type": "string",
                    "description": "Phone number (optional)"
                }
            }
        },
        "message": {
            "type": "string",
            "description": "The inquiry message",
            "minLength": 1
        },
        "metadata": {
            "type": "object",
            "description": "Additional metadata about the inquiry",
            "required": ["source_site", "source_locale", "timestamp"],
            "properties": {
                "source_site": {
                    "type": "string",
                    "description": "Which site the inquiry came from",
                    "enum": ["n3xusiq.com", "n3xusiq.mx"]
                },
                "source_locale": {
                    "type": "string",
                    "description": "Locale of the source site",
                    "enum": ["en_US", "es_MX"]
                },
                "timestamp": {
                    "type": "string",
                    "description": "ISO 8601 timestamp of submission",
                    "format": "date-time"
                },
                "user_agent": {
                    "type": "string",
                    "description": "Browser user agent"
                },
                "ip_address": {
                    "type": "string",
                    "description": "Client IP address"
                },
                "referrer": {
                    "type": "string",
                    "description": "HTTP referrer if available"
                }
            }
        }
    }
}

async def seed_contact_form_schema():
    """Seed the contact_form schema into the database."""
    async with get_direct_session() as session:
        # Check if schema already exists
        existing = await session.execute(
            select(ObjectSchemas).where(
                ObjectSchemas.name == "contact_form",
                ObjectSchemas.object_type == "crew"
            )
        )
        
        if existing.scalar():
            logger.info("Contact form schema already exists in database")
            # Update the existing schema
            schema_obj = existing.scalar()
            schema_obj.schema = contact_form_schema
            schema_obj.description = "Schema for contact form inquiries via crew_message_api"
            await session.commit()
            logger.info("Updated existing contact_form schema")
        else:
            # Create new schema
            new_schema = ObjectSchemas(
                name="contact_form",
                object_type="crew",
                schema=contact_form_schema,
                description="Schema for contact form inquiries via crew_message_api"
            )
            session.add(new_schema)
            await session.commit()
            logger.info("Successfully created contact_form schema")
        
        # Verify the schema was saved
        result = await session.execute(
            select(ObjectSchemas).where(
                ObjectSchemas.name == "contact_form",
                ObjectSchemas.object_type == "crew"
            )
        )
        saved_schema = result.scalar_one()
        logger.info(f"\nSaved schema details:")
        logger.info(f"  ID: {saved_schema.id}")
        logger.info(f"  Name: {saved_schema.name}")
        logger.info(f"  Type: {saved_schema.object_type}")
        logger.info(f"  Description: {saved_schema.description}")
        logger.info(f"  Schema keys: {list(saved_schema.schema.get('properties', {}).keys())}")

if __name__ == "__main__":
    asyncio.run(seed_contact_form_schema())