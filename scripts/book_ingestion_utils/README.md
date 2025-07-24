# Book Ingestion Utilities

This directory contains utilities for monitoring and checking book ingestion jobs.

## Scripts

### check_book_ingestion_status.py

Check the status of book ingestion jobs and database records.

```bash
# List recent jobs
python check_book_ingestion_status.py --jobs

# Check specific job events
python check_book_ingestion_status.py --job-id <job_id>

# List recent ingested pages
python check_book_ingestion_status.py --pages

# Get summary for a specific book
python check_book_ingestion_status.py --summary --book-key "sparkjar/vervelyn/castor gonzalez/book 1/"

# Combine options
python check_book_ingestion_status.py --pages --book-key "sparkjar/vervelyn/castor gonzalez/book 1/" --limit 20
```

### monitor_book_ingestion.py

Real-time monitoring of book ingestion progress.

```bash
# Monitor a specific job
python monitor_book_ingestion.py --job-id <job_id>

# Monitor book ingestion progress
python monitor_book_ingestion.py --book-key "sparkjar/vervelyn/castor gonzalez/book 1/"

# Adjust update interval
python monitor_book_ingestion.py --job-id <job_id> --interval 5
```

## Book Key Format

Book keys follow this pattern:
```
sparkjar/<client>/<author>/<book_title>/
```

Example:
```
sparkjar/vervelyn/castor gonzalez/book 1/
```

## Database Tables

These utilities query the following tables:
- `crew_jobs` - Job execution status
- `crew_job_event` - Detailed job events
- `BookIngestions` - Ingested book pages

## Requirements

- Python 3.8+
- SQLAlchemy
- python-dotenv
- PostgreSQL connection via DATABASE_URL_DIRECT