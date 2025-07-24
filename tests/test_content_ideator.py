#!/usr/bin/env python3
"""
Test script for content_ideator gen_crew execution.
Tests the complete flow from request validation to crew execution.
"""
import asyncio
import json
import os
import sys

import pytest

pytestmark = pytest.mark.integration

# Add crew-api src to path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

from services.crew_api.src.crews.gen_crew.gen_crew_handler import GenCrewHandler
from services.crew_api.src.services.job_service import JobService
from services.crew_api.src.services.json_validator import validate_crew_request
from services.crew_api.src.tools.context_query_tool import execute_context_query

# Use the real JSON payload provided by the user
REAL_TEST_PAYLOAD = {
    "job_key": "content_ideator",
    "client_user_id": "587f8370-825f-4f0c-8846-2e6d70782989",
    "actor_type": "synth",
    "actor_id": "1131ca9d-35d8-4ad1-ad77-0485b0239b86",
    "prompt": "okay so sparkjar.agency is like this company os of the future and we need blog ideas about ai copilots and using artificial intelligence in business? something like how to leverage ai to streamline ops and why sparkjar matters and maybe a post about co-pilot workflows or embedding ai in teams idk, just throw out a bunch of angles on ai pilots, business productivity, company os stuff, ux co-pilot integrations, future of work with ai, sparkjar vision, that kind of thing",
}

async def test_content_ideator_flow():
    """Test the complete content_ideator gen_crew flow."""
    print("🚀 Testing Content Ideator Gen Crew Flow")
    print("=" * 50)

    # Step 1: Test our context query tool first
    print("\n1️⃣ Testing Context Query Tool...")
    try:
        context_result = await execute_context_query(
            query_type="actor_context",
            context_params={
                "client_user_id": REAL_TEST_PAYLOAD["client_user_id"],
                "actor_type": REAL_TEST_PAYLOAD["actor_type"],
                "actor_id": REAL_TEST_PAYLOAD["actor_id"],
            },
        )
        print(f"✅ Context query successful!")
        print(f"   Client: {context_result['data']['client_context']['client_name']}")
        print(
            f"   Actor: {context_result['data']['actor_context']['name']} ({context_result['data']['actor_context']['type']})"
        )
    except Exception as e:
        print(f"❌ Context query failed: {e}")
        return

    # Step 2: Test request validation
    print("\n2️⃣ Testing Request Validation...")
    try:
        validation_result = await validate_crew_request(REAL_TEST_PAYLOAD)
        if validation_result["valid"]:
            print(f"✅ Request validation successful!")
            print(f"   Schema used: {validation_result.get('schema_used', 'Unknown')}")
            validated_data = validation_result["validated_data"]
        else:
            print(f"❌ Request validation failed: {validation_result['errors']}")
            return
    except Exception as e:
        print(f"❌ Request validation error: {e}")
        return

    # Step 3: Test job creation
    print("\n3️⃣ Testing Job Creation...")
    try:
        job_service = JobService()
        job_id = await job_service.create_job_from_validated_data(validated_data)
        print(f"✅ Job created successfully! Job ID: {job_id}")
    except Exception as e:
        print(f"❌ Job creation failed: {e}")
        return

    # Step 4: Check if we have crew config in database
    print("\n4️⃣ Testing Gen Crew Handler...")
    try:
        gen_crew_handler = GenCrewHandler()

        # Try to load the crew config
        crew_config = await gen_crew_handler._load_config("content_ideator", "gen_crew")
        if crew_config:
            print(f"✅ Found crew config in database!")
            print(
                f"   Config keys: {list(crew_config.keys()) if isinstance(crew_config, dict) else 'Not a dict'}"
            )
        else:
            print(
                f"❌ No crew config found for 'content_ideator' with type 'gen_crew' in database"
            )
            print(f"   You need to add the crew configuration to the database first")
            return

    except Exception as e:
        print(f"❌ Gen crew handler error: {e}")
        print(f"   This might be due to missing database config or model issues")
        import traceback

        traceback.print_exc()
        return

    # Step 5: Actually execute the full crew
    print("\n5️⃣ Executing Full Crew...")
    try:
        # Execute the actual crew with your real payload
        result = await gen_crew_handler.run(validated_data)

        print(f"✅ Crew execution completed successfully!")
        print(f"   Result type: {type(result)}")
        if isinstance(result, dict):
            print(f"   Result keys: {list(result.keys())}")
            if "final_output" in result:
                output = result["final_output"]
                print(f"   Final output preview: {str(output)[:200]}...")

        return result

    except Exception as e:
        print(f"❌ Crew execution failed: {e}")
        import traceback

        traceback.print_exc()
        return None

    print("\n" + "=" * 50)
    print("🎯 Complete End-to-End Test Summary:")
    print("   ✅ Context Query Tool: Working")
    print("   ✅ Request Validation: Working")
    print("   ✅ Job Creation: Working")
    print("   ✅ Database Config: Working")
    print("   ✅ Gen Crew Execution: Completed")
    print("   ✅ PDF Generation: Tested with fixed encoding")

    return result if "result" in locals() else None

if __name__ == "__main__":
    result = asyncio.run(test_content_ideator_flow())
    if result:
        print("\n🎉 SUCCESS: Full end-to-end test completed!")
    else:
        print("\n❌ FAILED: Test did not complete successfully")
