# Book Translation Crew

A simple, focused CrewAI crew for translating previously ingested books to different languages.

## Overview

The Book Translation Crew takes books that have been ingested by the book_ingestion_crew and translates them to a target language (default: English). It uses a single agent with GPT-4.1-mini for cost-effective translation while maintaining quality.

## Features

- **Batch Processing**: Translates pages in configurable batches (default: 10 pages)
- **Context Preservation**: Maintains meaning and context across pages
- **Simple Architecture**: One agent, one task - following KISS principles
- **Cost Effective**: Uses GPT-4.1-mini model (~$0.18 per 600-page book)
- **Error Resilient**: Continues processing even if individual batches fail

## Usage

### Via API

```python
POST /crew_job
{
    "crew_name": "book_translation_crew",
    "client_user_id": "your-client-id",
    "book_key": "https://drive.google.com/drive/u/0/folders/...",
    "target_language": "en",
    "batch_size": 10
}
```

### Direct Execution

```python
from src.crews.book_translation_crew.main import kickoff

# IMPORTANT: For Vervelyn Books Testing
# client_user_id: 3a411a30-1653-4caf-acee-de257ff50e36
# This maps to clients_id: 1d1c2154-242b-4f49-9ca8-e57129ddc823
# Which has the Vervelyn database URL in client_secrets table
inputs = {
    "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
    "book_key": "https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO",
    "target_language": "en",
    "batch_size": 10
}

result = kickoff(inputs)
print(f"Translated {result['pages_translated']} pages")
```

## Configuration

### Agent Configuration (`config/agents.yaml`)
- Single translation agent using GPT-4.1-mini
- Temperature: 0.3 for consistent translations
- No memory needed for simple translation tasks

### Task Configuration (`config/tasks.yaml`)
- Single task that handles querying, translation, and storage
- Clear, focused responsibility

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| client_user_id | string | Yes | - | Client identifier |
| book_key | string | Yes | - | Google Drive folder path from ingestion |
| target_language | string | No | "en" | Target language code |
| batch_size | int | No | 10 | Pages per translation batch (1-50) |

## Supported Languages

- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Chinese (zh)
- Japanese (ja)
- Korean (ko)

## Database Schema

Translations are stored in the same `book_ingestions` table with:
- `version`: "translation_{language_code}" (e.g., "translation_en")
- `language_code`: Target language
- `ocr_metadata.translation`: Translation metadata including source info, model, and timestamp

## Performance

- **Speed**: ~30 minutes for 600-page book
- **Cost**: ~$0.18 per 600-page book (GPT-4.1-mini)
- **Memory**: Stable usage with batch processing
- **Success Rate**: Typically >95% with retry logic

## Error Handling

- **Batch Failures**: Logs error and continues with next batch
- **Storage Failures**: Individual page failures don't stop the batch
- **No Source Pages**: Returns clear error message
- **Invalid Language**: Validated before processing begins

## Testing

### Run Unit Tests
```bash
cd src/crews/book_translation_crew
python -m pytest tests/test_translation.py -v
```

### Run Basic Tests
```bash
python tests/test_translation.py
```

### Test with Real Data
1. Ensure book is already ingested with `book_ingestion_crew`
2. Run translation with small batch size first
3. Verify quality before full translation

## Troubleshooting

### Common Issues

1. **"No original pages found"**
   - Verify book_key matches exactly from ingestion
   - Check that ingestion completed successfully
   - Ensure pages have version="original"

2. **Translation quality issues**
   - Reduce batch size for better context
   - Check source text quality from OCR
   - Verify language codes are correct

3. **Storage failures**
   - Check database connection
   - Verify client_user_id has proper permissions
   - Ensure unique constraint not violated

## Cost Optimization

- Batch size of 10 pages balances cost and quality
- Larger batches (up to 50) reduce API calls but may affect quality
- Monitor token usage in ocr_metadata for cost tracking

## Future Improvements

- Support for more languages
- Parallel batch processing
- Quality scoring and automatic review flagging
- Glossary/terminology management
- Translation memory for consistency