# Entity Research Crew

## Overview

The Entity Research Crew is a specialized CrewAI implementation designed to conduct comprehensive public information research about entities (individuals, organizations, or concepts). It leverages multiple agents working together to gather, analyze, and synthesize information from various public sources.

## Purpose

This crew automates the process of:
- Gathering public information from web sources
- Analyzing documents and extracting key insights
- Mapping relationships and networks
- Compiling professional research reports
- Archiving findings in organizational memory
- Delivering reports to stakeholders

## Agents

1. **Lead Research Strategist**
   - Develops research strategy
   - Coordinates the research team
   - Ensures findings are documented in memory

2. **Web Intelligence Analyst**
   - Conducts deep web searches
   - Identifies relevant sources
   - Gathers public information

3. **Document Analysis Specialist**
   - Extracts information from documents
   - Analyzes web pages and PDFs
   - Synthesizes key findings

4. **Relationship Mapper**
   - Identifies connections and networks
   - Maps organizational relationships
   - Creates relationship graphs

5. **Report Compiler**
   - Creates comprehensive reports
   - Structures findings professionally
   - Ensures quality output

6. **Document Archivist**
   - Saves reports to document service
   - Updates memory with references
   - Sends notifications to stakeholders

## Workflow

1. **Research Strategy** - Plan the investigation approach
2. **Web Intelligence** - Gather information from public sources
3. **Document Analysis** - Extract insights from discovered documents
4. **Relationship Mapping** - Identify and map connections
5. **Report Compilation** - Create comprehensive report
6. **Archive & Notify** - Save report and notify stakeholders

## API Usage

To execute this crew via the SparkJAR API:

```bash
curl -X POST https://your-api-url/crew_job \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "crew_name": "entity_research_crew",
    "context": {
      "entity_name": "Company XYZ",
      "entity_domain": "technology"
    }
  }'
```

## Required Context

- `entity_name` (required): Name of the entity to research
- `entity_domain` (optional): Domain/industry of the entity (default: "general")

## Output

The crew produces:
- Comprehensive research report in markdown and PDF formats
- Memory entities for discovered information
- Relationship mappings
- Email notification with report access link

## Integration Points

- **Memory Service**: Stores entities, observations, and relationships
- **Sequential Thinking**: Plans research strategy
- **Document Service**: Archives final reports
- **Email Service**: Sends notifications

## Event Logging

The crew logs events to `crew_job_events` table:
- Crew initialization
- Tool initialization
- Context preparation
- Agent creation
- Task execution
- Completion or errors

## Error Handling

The crew includes comprehensive error handling:
- Validates required inputs
- Handles missing email addresses
- Logs all errors to event table
- Returns structured error responses