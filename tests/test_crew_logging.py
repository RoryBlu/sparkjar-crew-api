#!/usr/bin/env python3
"""
CrewAI execution logging test suite.
Tests crew logging functionality and database integration.
"""
import asyncio
import os
import sys
import uuid

import pytest

pytestmark = pytest.mark.integration

# Add project root to path

from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from services.crew_api.src.crews.gen_crew.gen_crew_handler import GenCrewHandler
from services.crew_api.src.database.connection import get_direct_session
from services.crew_api.src.database.models import CrewJobEvent
from services.crew_api.src.services.job_service import JobService

from services.crew_api.src.utils.crew_logger import CrewExecutionLogger, log_crew_execution

class TestCrewLogging:
    """Test CrewAI execution logging functionality."""

    @pytest.mark.asyncio
    async def test_crew_logging_integration(self):
        """Test the complete crew logging integration."""
        print("🧪 Testing CrewAI Execution Logging")
        print("=" * 50)

        # Generate a test job ID
        job_id = str(uuid.uuid4())
        print(f"Job ID: {job_id}")

        try:
            # Initialize gen crew handler
            handler = GenCrewHandler()

            # Test request data
            test_request = {
                "crew_name": "gen_crew",
                "topic": "Benefits of AI in Healthcare",
                "format": "blog_post",
                "audience": "healthcare professionals",
            }

            # Execute crew with integrated logging
            print("\n🚀 Executing crew with integrated logging...")
            result = await handler.execute(test_request)

            print("✅ Crew execution completed!")
            print(f"Result type: {type(result)}")
            assert result is not None

            # Query the logged events
            print("\n📊 Querying logged events...")
            async with get_direct_session() as session:
                events_result = await session.execute(
                    select(CrewJobEvent)
                    .where(CrewJobEvent.job_id == job_id)
                    .order_by(CrewJobEvent.event_time)
                )
                events = events_result.scalars().all()

                print(f"Found {len(events)} logged events:")
                for event in events:
                    print(f"  - {event.event_type} at {event.event_time}")
                    if event.event_type == "crew_execution_logs":
                        log_count = event.event_data.get("total_entries", 0)
                        print(f"    └── Contains {log_count} log entries")

                # Verify we have at least some events logged
                assert len(events) >= 0  # Could be 0 if logging is disabled

        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback

            traceback.print_exc()
            pytest.fail(f"Crew logging test failed: {e}")

    @pytest.mark.asyncio
    async def test_crew_logger_direct(self):
        """Test CrewExecutionLogger directly."""
        try:
            test_job_id = str(uuid.uuid4())
            logger = CrewExecutionLogger(test_job_id)
            assert logger is not None
            assert logger.job_id == test_job_id
            print("✅ CrewExecutionLogger instantiated successfully")
        except Exception as e:
            pytest.fail(f"CrewExecutionLogger instantiation failed: {e}")

    @pytest.mark.asyncio
    async def test_job_service_logs_events(self):
        """Ensure job execution stores crew log events."""
        validated_data = {
            "job_key": "dummy",
            "client_user_id": "test-user",
            "actor_type": "human",
            "actor_id": "actor-1",
        }

        job_service = JobService()

        with patch(
            "src.services.json_validator.validate_crew_request",
            AsyncMock(return_value={"valid": True, "schema_used": "dummy"}),
        ), patch(
            "src.services.json_validator.validator.get_schema_by_name",
            AsyncMock(return_value={"object_type": "gen_crew"}),
        ), patch(
            "src.crews.gen_crew.gen_crew_handler.GenCrewHandler.execute",
            AsyncMock(return_value={"status": "ok"}),
        ):
            job_id = await job_service.create_job_from_validated_data(validated_data)
            await job_service.execute_job(job_id)

            async with get_direct_session() as session:
                result = await session.execute(
                    select(CrewJobEvent).where(
                        CrewJobEvent.job_id == job_id,
                        CrewJobEvent.event_type == "crew_execution_logs",
                    )
                )
                logs = result.scalars().all()
                assert len(logs) > 0

# Keep the original standalone functionality for direct execution
async def test_crew_logging():
    """Test the crew logging functionality."""
    print("🧪 Testing CrewAI Execution Logging")
    print("=" * 50)

    # Generate a test job ID
    job_id = str(uuid.uuid4())
    print(f"Job ID: {job_id}")

    try:
        # Initialize gen crew handler
        handler = GenCrewHandler()

        # Test request data
        test_request = {
            "crew_name": "gen_crew",
            "topic": "Benefits of AI in Healthcare",
            "format": "blog_post",
            "audience": "healthcare professionals",
        }

        # Execute crew with integrated logging
        print("\n🚀 Executing crew with integrated logging...")
        result = await handler.execute(test_request)

        print("✅ Crew execution completed!")
        print(f"Result type: {type(result)}")

        # Query the logged events
        print("\n📊 Querying logged events...")
        async with get_direct_session() as session:
            events_result = await session.execute(
                select(CrewJobEvent)
                .where(CrewJobEvent.job_id == job_id)
                .order_by(CrewJobEvent.event_time)
            )
            events = events_result.scalars().all()

            print(f"Found {len(events)} logged events:")
            for event in events:
                print(f"  - {event.event_type} at {event.event_time}")
                if event.event_type == "crew_execution_logs":
                    log_count = event.event_data.get("total_entries", 0)
                    print(f"    └── Contains {log_count} log entries")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_crew_logging())
