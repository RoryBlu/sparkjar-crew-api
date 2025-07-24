# Contact Form Crew

A production-ready CrewAI implementation that processes contact form submissions from the `crew_message_api` endpoint with full memory persistence and CRM integration.

## Overview

The Contact Form Crew provides intelligent processing of customer inquiries with:
- Structured data extraction using Pydantic models
- Memory system integration for contact tracking
- Odoo CRM integration via MCP
- Multi-tenant support with proper data isolation
- Comprehensive error handling and fallbacks

## Architecture

### Agents

1. **Inquiry Processing Specialist**
   - Tools: `SJSequentialThinkingTool`, `SJMemoryTool`
   - Analyzes inquiries for intent, urgency, and business intelligence
   - Generates professional responses based on analysis

2. **Contact Management Specialist**
   - Tools: `SJMemoryTool`, Odoo MCP tools (when available)
   - Manages contact entities and relationships in memory
   - Integrates with Odoo CRM for lead/contact management

## API Endpoint

This crew is triggered via the `/crew_message_api` endpoint using API key authentication.

### Request Format

```json
{
  "api_key": "your-sparkjar-api-key",
  "inquiry_type": "contact_form",
  "contact": {
    "name": "John Doe",
    "email": "john@example.com",
    "company": "Acme Corp",
    "phone": "+1-555-1234"
  },
  "message": "Your inquiry message here",
  "metadata": {
    "source_site": "n3xusiq.com",
    "source_locale": "en_US",
    "timestamp": "2025-01-07T10:30:00Z",
    "user_agent": "Mozilla/5.0...",
    "ip_address": "192.168.1.1",
    "referrer": "https://google.com"
  }
}
```

## Authentication

The endpoint uses API key authentication. The API key must be stored in the `client_secrets` table with:
- `secret_key` = "SPARKJAR_API_KEY"
- `secret_value` = your actual API key
- `client_id` = the client UUID

## Output

The crew returns:
- Inquiry analysis (intent, urgency, sentiment, topics)
- Suggested response email
- Recommended follow-up actions
- Processing metadata

### Task Flow

1. **Analyze Inquiry** → Extracts structured data using `ContactAnalysis` model
2. **Manage Contact** → Creates/updates contact in memory and Odoo
3. **Store Inquiry** → Creates observations with proper tagging
4. **Generate Response** → Produces suggested response and next actions

## Data Models

### Input Schema
Validated against `contact_form` schema in `object_schemas` table.

### Output Models (Pydantic)
- `ContactAnalysis` - Structured analysis results
- `ContactEntity` - Memory entity information
- `OdooRecord` - CRM integration results
- `InquiryStorage` - Observation storage details
- `ContactFormResult` - Complete crew output

## Integration Points

### Memory System
- Creates contact entities with type 'person'
- Stores inquiry observations with rich metadata
- Tracks relationships between contacts and clients
- Enables semantic search on past interactions

### Odoo CRM (via MCP)
- Creates/updates contact records
- Creates leads with proper categorization
- Sets priority based on urgency analysis
- Returns direct URLs to CRM records

## Error Handling

- Graceful fallback if Odoo MCP is unavailable
- Structured error reporting in output
- Transaction-safe operations
- Comprehensive logging at each step

## Testing

1. Ensure schema is seeded:
```bash
python scripts/seed_contact_form_schema.py
```

2. Test with provided JSON:
```bash
python scripts/test_crew_message_api.py
```

3. Check results:
- Memory entity created
- Observations stored
- Odoo records created (if available)
- Structured output with all IDs

## Performance

- Typical execution: 30-60 seconds
- Rate limited to 20 RPM for API protection
- Async MCP loading for efficiency
- Structured outputs reduce parsing overhead