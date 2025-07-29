# Book Translation Guide for Vervelyn

## Current Situation

- **Book Key**: `https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO`
- **Client User ID**: `3a411a30-1653-4caf-acee-de257ff50e36`
- **Target**: Spanish to English translation

## The Challenge

The sparkjar-crew-api requires Python 3.11+ but your local environment has Python 3.8. The project uses specific dependency management through GitHub packages to avoid dependency hell.

## Options to Get Your Book Translated

### Option 1: Use the Railway Deployment (Recommended)

Since this service is designed for Railway deployment:

1. **If already deployed on Railway:**
   ```bash
   curl -X POST https://your-railway-url/crew_job \
     -H "Authorization: Bearer YOUR_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "job_key": "book_translation_crew",
       "request_data": {
         "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
         "actor_type": "client",
         "actor_id": "1d1c2154-242b-4f49-9ca8-e57129ddc823",
         "book_key": "https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO",
         "target_language": "en"
       }
     }'
   ```

2. **Deploy to Railway:**
   - Push this repo to Railway
   - Set all required environment variables from railway.json
   - Railway will use Python 3.11+ automatically

### Option 2: Set Up Local Environment Properly

1. **Install Python 3.11 or 3.12:**
   ```bash
   # On macOS with Homebrew:
   brew install python@3.11
   
   # Or use pyenv:
   brew install pyenv
   pyenv install 3.11.0
   pyenv local 3.11.0
   ```

2. **Create proper virtual environment:**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create `.env` file with all required variables (see railway.json)

4. **Run the translation:**
   ```bash
   python src/crews/book_translation_crew/main.py \
     --client_user_id "3a411a30-1653-4caf-acee-de257ff50e36" \
     --actor_type "client" \
     --actor_id "1d1c2154-242b-4f49-9ca8-e57129ddc823" \
     --book_key "https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO" \
     --target_language "en"
   ```

### Option 3: Check if Translation Already Exists

The book may already be translated in the database. To check and export:

1. **Query the database directly** (requires psycopg2 or database client)
2. **Use the API** (if deployed) to check job status

## Export to Markdown

Once translated, the pages will be in the `vervelyn.book_ingestions` table with:
- `version = "translation_en"` 
- `book_key = "https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO"`

The export script (`direct_query_and_export.py`) can then create the .md file.

## Important Notes

- **DO NOT** install random dependencies globally
- **DO NOT** try to bypass the dependency management
- The project uses `sparkjar-shared` from GitHub packages
- CrewAI version 0.148.0 requires Python 3.9+
- All dependencies are carefully managed in requirements.txt

## Next Steps

1. Choose one of the options above
2. If using Railway, ensure all environment variables are set
3. If running locally, ensure Python 3.11+ is installed first
4. The translation crew will process the book page by page
5. Once complete, use the export script to generate the .md file