# Memory Import Crew

A CrewAI-based system for importing data into the SparkJAR memory system.

## Overview

The Memory Import Crew automates the process of analyzing, transforming, and importing data into the memory system. It consists of three specialized agents working together to ensure high-quality data import.

## Agents

### 1. Memory Data Analyst
- **Role**: Analyzes and validates memory data for import
- **Responsibilities**:
  - Analyze data structure and content
  - Identify entities and relationships
  - Assess data quality
  - Generate analysis reports

### 2. Data Transformation Specialist
- **Role**: Transforms raw data into memory system format
- **Responsibilities**:
  - Map data to entity schemas
  - Format observations with metadata
  - Establish entity relationships
  - Handle data type conversions

### 3. Memory Import Coordinator
- **Role**: Executes the import into the memory system
- **Responsibilities**:
  - Create entities in memory system
  - Add observations to entities
  - Handle duplicates and conflicts
  - Generate import reports

## Usage

### As a Module

```python
from crews.memory_import_crew.src.crew import MemoryImportCrew

# Initialize the crew
crew = MemoryImportCrew()

# Prepare your data
memory_data = {
    "entities": [
        {
            "name": "John Doe",
            "type": "person",
            "observations": [
                "CEO of TechCorp",
                "Founded the company in 2020"
            ]
        }
    ]
}

# Run the import
result = crew.kickoff({"memory_data": memory_data})
```

### Command Line

```bash
# Import from file
python src/main.py --data-file data.json

# Import from JSON string
python src/main.py --data '{"entities": [...]}'

# With custom configuration
python src/main.py --data-file data.json --config '{"batch_size": 50}'
```

## Input Format

The crew accepts memory data in the following format:

```json
{
  "entities": [
    {
      "name": "Entity Name",
      "type": "person|company|product|other",
      "metadata": {
        "key": "value"
      },
      "observations": [
        "Observation text 1",
        "Observation text 2"
      ],
      "relationships": [
        {
          "target": "Other Entity Name",
          "type": "works_for|founded|invested_in|partners_with"
        }
      ]
    }
  ]
}
```

### Example Crew Request

Below is a sample request payload demonstrating the required core fields and a
small set of memory data. This JSON can be posted directly to the Memory Import
Crew API.

```json
{
  "job_key": "memory_import_crew",
  "client_user_id": "2b4ccc56-cfe9-42d0-8378-1805db211446",
  "actor_type": "synth",
  "actor_id": "1131ca9d-35d8-4ad1-ad77-0485b0239b86",
  "object_type": "crew",
  "memory_data": {
    "entities": [
      {
        "name": "Mary Carol Knight Rawlings-Pankey",
        "type": "person",
        "metadata": { "notes": "initial interview" },
        "observations": [
          "Born in Wisconsin",
          "Mother died when she was 11",
          "Father became central after mother's death"
        ],
        "relationships": [
          { "target": "Taylor Rawlings", "type": "married_to" },
          { "target": "Russell Pankey", "type": "married_to" }
        ]
      },
      {
        "name": "Taylor Rawlings",
        "type": "person",
        "metadata": { "born_in": "Mile City, Montana" },
        "observations": [
          "Joined the Navy at 16 during WWII",
          "Homesteaded in Alaska with Mary"
        ],
        "relationships": [
          { "target": "Mary Carol Knight Rawlings-Pankey", "type": "married_to" }
        ]
      },
      {
        "name": "Russell Pankey",
        "type": "person",
        "observations": [
          "Met Mary through church",
          "Traveled together in Arizona"
        ],
        "relationships": [
          { "target": "Mary Carol Knight Rawlings-Pankey", "type": "married_to" }
        ]
      }
    ]
  },
  "import_config": {
    "batch_size": 100,
    "deduplicate": true
  }
}
```

## Configuration Options

```json
{
  "batch_size": 100,
  "deduplicate": true,
  "merge_strategy": "latest|combine|skip",
  "validation_level": "strict|moderate|lenient"
}
```

## Output

The crew returns a comprehensive import report:

```json
{
  "status": "completed",
  "result": {
    "entities_created": 10,
    "observations_added": 45,
    "relationships_established": 8,
    "duplicates_found": 2,
    "errors": []
  },
  "summary": {
    "total_processing_time": "2m 15s",
    "data_quality_score": 0.95
  }
}
```

## Integration with SparkJAR

This crew integrates seamlessly with the SparkJAR memory system:

1. **Entity Creation**: Uses the `sj_memory` tool to create entities
2. **Observation Storage**: Adds contextual observations to entities
3. **Relationship Mapping**: Establishes connections between entities
4. **Deduplication**: Automatically handles duplicate entities

## Best Practices

1. **Data Preparation**: Ensure your data is well-structured before import
2. **Batch Processing**: For large datasets, use appropriate batch sizes
3. **Validation**: Always review the analysis report before proceeding
4. **Error Handling**: Check the import report for any errors or conflicts
5. **Incremental Import**: For updates, use merge strategies to preserve existing data

## Troubleshooting

### Common Issues

1. **Invalid Data Format**: Ensure your JSON follows the expected schema
2. **Memory Tool Errors**: Check that the memory service is accessible
3. **Duplicate Entities**: Use deduplication options or merge strategies
4. **Large Datasets**: Increase batch size or split into multiple imports

### Debug Mode

Enable verbose logging for troubleshooting:

```python
crew = MemoryImportCrew()
crew.crew().verbose = True
```

## Future Enhancements

- Support for CSV and Excel file imports
- Automatic entity type detection
- Bulk relationship inference
- Real-time import progress tracking
- Import rollback capabilities