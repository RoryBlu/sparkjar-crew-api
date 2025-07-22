# API Field Requirements for Crew Jobs

## Required Fields

### actor_type
**Valid values**: `"human"` or `"synth"` (lowercase only)
- `"human"` - For human actors
- `"synth"` - For synthetic/AI actors

**Example**: `"actor_type": "synth"`

### actor_id
**Format**: Valid UUID
- For testing/synth: `"b9af0667-5c92-4892-a7c5-947ed0cab0db"`

**Example**: `"actor_id": "b9af0667-5c92-4892-a7c5-947ed0cab0db"`

### language
**Format**: ISO 639-1 language codes (2-letter codes)
**Common values**:
- `"en"` - English
- `"es"` - Spanish  
- `"fr"` - French
- `"de"` - German
- `"it"` - Italian
- `"pt"` - Portuguese
- `"zh"` - Chinese
- `"ja"` - Japanese

**Example**: `"language": "es"`

## Complete Example Payload

```json
{
  "data": {
    "job_key": "book_ingestion_crew",
    "actor_type": "synth",
    "actor_id": "b9af0667-5c92-4892-a7c5-947ed0cab0db",
    "google_drive_folder_path": "0AM0PEUhIEQFUUk9PVA/vervelyn/castor gonzalez/book 1/",
    "client_user_id": "587f8370-825f-4f0c-8846-2e6d70782989",
    "language": "es",
    "confidence_threshold": 0.85
  }
}
```

## Common Mistakes to Avoid

1. ❌ `"actor_type": "User"` or `"actor_type": "Human"` 
   ✅ `"actor_type": "human"` (lowercase)

2. ❌ `"language": "spanish"` or `"language": "English"`
   ✅ `"language": "es"` or `"language": "en"` (ISO codes)

3. ❌ `"actor_id": "test_user"` (not a valid UUID)
   ✅ `"actor_id": "b9af0667-5c92-4892-a7c5-947ed0cab0db"` (valid UUID)