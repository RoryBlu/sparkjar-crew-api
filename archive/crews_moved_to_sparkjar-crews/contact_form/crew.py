"""
Contact Form Crew Handler
Processes contact form inquiries from the crew_message_api endpoint.
Integrates with Memory system and Odoo MCP for proper data persistence.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import time

from crewai import Agent, Task, Crew, Process
from pydantic import ValidationError

# Import our models
from .models import (
    ContactAnalysis, ContactEntity, OdooRecord, 
    InquiryStorage, ContactFormResult, InquiryIntent,
    UrgencyLevel, Sentiment
)

# Import tools
from src.tools.sj_memory_tool import SJMemoryTool
from src.tools.sj_sequential_thinking_tool import SJSequentialThinkingTool
from services.mcp_service import mcp_service

logger = logging.getLogger(__name__)

def kickoff(inputs: dict, logger=None):
    """
    Entry point for the contact form crew.
    Processes contact form submissions with memory persistence and Odoo integration.
    
    Args:
        inputs: Dictionary containing the contact form data
        logger: Optional enhanced logger instance
        
    Returns:
        ContactFormResult as a dictionary
    """
    start_time = time.time()
    errors = []
    
    try:
        # Extract input data
        job_id = inputs.get('job_id', 'unknown')
        client_id = inputs.get('client_user_id')  # This is actually client_id from API key lookup
        inquiry_type = inputs.get('inquiry_type', 'contact_form')
        contact = inputs.get('contact', {})
        message = inputs.get('message', '')
        metadata = inputs.get('metadata', {})
        
        if logger:
            logger.log_event("CREW_START", {
                "crew_type": "contact_form",
                "inquiry_type": inquiry_type,
                "contact_email": contact.get('email'),
                "client_id": client_id
            })
        
        # Initialize tools
        memory_tool = SJMemoryTool(client_user_id=client_id)
        thinking_tool = SJSequentialThinkingTool()
        
        # Load MCP tools for Odoo integration
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(mcp_service.load_all_mcp_tools())
            odoo_tools = [tool for tool in mcp_service.get_available_tools() 
                         if 'odoo' in getattr(tool, 'name', '').lower()]
            logger.info(f"Loaded {len(odoo_tools)} Odoo MCP tools")
        except Exception as e:
            logger.warning(f"Failed to load Odoo MCP tools: {e}")
            errors.append(f"Odoo integration unavailable: {str(e)}")
            odoo_tools = []
        finally:
            loop.close()
        
        # Create agents with appropriate tools
        inquiry_agent = Agent(
            role="Inquiry Processing Specialist",
            goal="Analyze customer inquiries to extract actionable intelligence and generate appropriate responses",
            backstory="""You are an expert at understanding customer needs from their messages. 
            You excel at identifying intent, urgency, sentiment, and extracting key business intelligence.
            You use sequential thinking to structure your analysis and ensure nothing is missed.""",
            tools=[thinking_tool, memory_tool],
            verbose=True,
            allow_delegation=False
        )
        
        contact_manager = Agent(
            role="Contact Management Specialist", 
            goal="Manage contact data in memory system and CRM integrations ensuring data consistency",
            backstory="""You are a data management expert who ensures all contact information is properly 
            stored, deduplicated, and synchronized across systems. You excel at using the memory system
            to track entities and relationships, and integrating with external CRM systems like Odoo.""",
            tools=[memory_tool] + odoo_tools,
            verbose=True,
            allow_delegation=False
        )
        
        # Task 1: Process inquiry with memory chunk extraction
        analyze_task = Task(
            description=f"""Analyze this customer inquiry and extract key information into memory:
            
            Contact Information:
            - Name: {contact.get('name')}
            - Email: {contact.get('email')}
            - Company: {contact.get('company', 'Not provided')}
            - Phone: {contact.get('phone', 'Not provided')}
            
            Message: {message}
            
            Metadata:
            - Source: {metadata.get('source_site')} ({metadata.get('source_locale')})
            - Timestamp: {metadata.get('timestamp')}
            - Referrer: {metadata.get('referrer', 'Direct')}
            
            First, use the memory tool's process_text_chunk operation to extract entities and relationships
            from the message. This will automatically:
            - Extract people, companies, and concepts mentioned
            - Identify relationships between entities
            - Search existing memory for context
            - Store everything for future reference
            
            Then use sequential thinking to:
            1. Identify the primary intent (demo_request, pricing_inquiry, technical_question, etc.)
            2. Assess urgency level based on language and context
            3. Extract key topics and technologies mentioned
            4. Analyze sentiment
            5. Identify any mentioned products or services
            6. Look for company size, budget, or timeline indicators
            7. Recommend the appropriate response type and follow-up priority
            
            Be thorough and extract all relevant business intelligence.""",
            expected_output="A comprehensive ContactAnalysis with all fields populated",
            agent=inquiry_agent,
            output_pydantic=ContactAnalysis
        )
        
        # Task 2: Manage contact in memory and CRM
        manage_contact_task = Task(
            description=f"""Manage the contact information in our systems:
            
            1. Search memory for existing contact entity with email: {contact.get('email')}
            2. If found:
               - Retrieve the entity and any previous interactions
               - Update with new information if needed
            3. If not found:
               - Create new contact entity with type 'person'
               - Include all contact information in metadata
            4. Create a relationship between the contact and client (ID: {client_id})
            
            5. If Odoo tools are available:
               - Search for existing contact in Odoo by email
               - Create or update contact in Odoo
               - Create a new lead with the inquiry information
               - Set lead priority based on the urgency from analysis
               - Return the Odoo record IDs and URLs
            
            Use the analysis results from the previous task to enrich the data.""",
            expected_output="ContactEntity with memory IDs and OdooRecord with CRM IDs",
            agent=contact_manager,
            context=[analyze_task],
            output_json=True  # We'll parse this into our models
        )
        
        # Task 3: Store inquiry details
        store_inquiry_task = Task(
            description=f"""Store the inquiry details in memory for future reference:
            
            1. Create observations for the contact entity:
               - Observation type: 'inquiry'
               - Include the full message and metadata
               - Add tags based on the analysis (intent, urgency, topics)
            
            2. Create additional observations for key insights:
               - Technologies mentioned
               - Products of interest
               - Company information
               - Timeline or budget indicators
            
            3. If this is a follow-up to previous interactions, create appropriate relationships
            
            4. Return a list of all created observation IDs and applied tags
            
            Ensure all data is properly structured and tagged for future retrieval.""",
            expected_output="InquiryStorage with observation IDs and tags",
            agent=contact_manager,
            context=[analyze_task, manage_contact_task],
            output_json=True
        )
        
        # Task 4: Generate response and next actions
        response_task = Task(
            description=f"""Based on all previous analysis and actions, generate the final response:
            
            1. Create a suggested email response that:
               - Acknowledges their specific inquiry
               - Addresses their primary intent
               - Maintains appropriate tone for the urgency level
               - Includes relevant next steps
               - Is personalized for {contact.get('name')}
               - Considers the locale: {metadata.get('source_locale')}
            
            2. Define concrete next actions for the team:
               - Specific follow-up tasks with timelines
               - Who should be notified (based on intent and urgency)
               - What materials or information to prepare
               - When to follow up
            
            3. Compile all results into a comprehensive summary
            
            Use all the information gathered in previous tasks to create a complete response.""",
            expected_output="A professional email response and list of concrete next actions",
            agent=inquiry_agent,
            context=[analyze_task, manage_contact_task, store_inquiry_task],
            output_json=True
        )
        
        # Create and execute the crew
        crew = Crew(
            agents=[inquiry_agent, contact_manager],
            tasks=[analyze_task, manage_contact_task, store_inquiry_task, response_task],
            process=Process.sequential,
            verbose=True,
            memory=True,
            max_rpm=20  # Rate limiting for API calls
        )
        
        # Set logger callbacks if available
        if logger and hasattr(logger, 'get_callbacks'):
            callbacks = logger.get_callbacks()
            for callback in callbacks:
                crew.callbacks.append(callback)
        
        # Execute the crew
        result = crew.kickoff()
        
        # Parse the results from each task
        try:
            # Task outputs are stored in crew.tasks[i].output
            analysis = analyze_task.output.pydantic if hasattr(analyze_task.output, 'pydantic') else ContactAnalysis(
                primary_intent=InquiryIntent.GENERAL_INQUIRY,
                urgency_level=UrgencyLevel.MEDIUM,
                key_topics=["general inquiry"],
                sentiment=Sentiment.NEUTRAL,
                recommended_response_type="send_info",
                follow_up_priority=5
            )
            
            # Parse JSON outputs for other tasks
            contact_data = json.loads(manage_contact_task.output.raw) if hasattr(manage_contact_task.output, 'raw') else {}
            storage_data = json.loads(store_inquiry_task.output.raw) if hasattr(store_inquiry_task.output, 'raw') else {}
            response_data = json.loads(response_task.output.raw) if hasattr(response_task.output, 'raw') else {}
            
            # Build structured result
            contact_entity = ContactEntity(
                entity_id=contact_data.get('entity_id', 'unknown'),
                is_new_contact=contact_data.get('is_new', True),
                previous_interactions=contact_data.get('previous_interactions', 0),
                existing_relationships=contact_data.get('relationships', [])
            )
            
            odoo_record = OdooRecord(
                lead_id=contact_data.get('odoo_lead_id'),
                contact_id=contact_data.get('odoo_contact_id'),
                record_url=contact_data.get('odoo_url'),
                error=contact_data.get('odoo_error')
            )
            
            inquiry_storage = InquiryStorage(
                observation_ids=storage_data.get('observation_ids', []),
                document_id=storage_data.get('document_id'),
                tags_applied=storage_data.get('tags', [])
            )
            
            # Create final result
            final_result = ContactFormResult(
                job_id=job_id,
                processing_time_seconds=time.time() - start_time,
                analysis=analysis,
                contact_entity=contact_entity,
                odoo_record=odoo_record,
                inquiry_storage=inquiry_storage,
                suggested_response=response_data.get('suggested_response', ''),
                next_actions=response_data.get('next_actions', []),
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Error parsing crew outputs: {e}")
            # Create a basic result with error
            final_result = ContactFormResult(
                job_id=job_id,
                processing_time_seconds=time.time() - start_time,
                analysis=ContactAnalysis(
                    primary_intent=InquiryIntent.GENERAL_INQUIRY,
                    urgency_level=UrgencyLevel.MEDIUM,
                    key_topics=[inquiry_type],
                    sentiment=Sentiment.NEUTRAL,
                    recommended_response_type="manual_review",
                    follow_up_priority=8
                ),
                contact_entity=ContactEntity(
                    entity_id="error",
                    is_new_contact=True
                ),
                odoo_record=OdooRecord(error=str(e)),
                inquiry_storage=InquiryStorage(observation_ids=[]),
                suggested_response="Thank you for your inquiry. Our team will review and respond shortly.",
                next_actions=["Manual review required due to processing error"],
                status="completed_with_errors",
                errors=errors + [f"Output parsing error: {str(e)}"]
            )
        
        if logger:
            logger.log_event("CREW_COMPLETE", {
                "success": True,
                "processing_time": final_result.processing_time_seconds,
                "errors": len(final_result.errors)
            })
        
        # Return as dictionary for job service
        return final_result.dict()
        
    except Exception as e:
        if logger:
            logger.log_event("ERROR_OCCURRED", {
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
        
        # Return error result
        error_result = ContactFormResult(
            job_id=inputs.get('job_id', 'unknown'),
            processing_time_seconds=time.time() - start_time,
            analysis=ContactAnalysis(
                primary_intent=InquiryIntent.GENERAL_INQUIRY,
                urgency_level=UrgencyLevel.HIGH,
                key_topics=["error"],
                sentiment=Sentiment.NEUTRAL,
                recommended_response_type="urgent_manual_review",
                follow_up_priority=10
            ),
            contact_entity=ContactEntity(entity_id="error", is_new_contact=True),
            odoo_record=OdooRecord(error=str(e)),
            inquiry_storage=InquiryStorage(observation_ids=[]),
            suggested_response="",
            next_actions=["Urgent: Manual processing required due to system error"],
            status="failed",
            errors=[str(e)]
        )
        
        return error_result.dict()