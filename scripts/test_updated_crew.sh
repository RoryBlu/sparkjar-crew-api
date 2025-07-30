#!/bin/bash
# Test the updated crew by creating a job via API

# Start the API server in background
echo "Starting API server..."
.venv/bin/python main.py &
API_PID=$!

# Wait for server to start
sleep 5

# Create a test job
echo -e "\nCreating test job..."
curl -X POST http://localhost:8000/crew_job \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN:-test-token-required}" \
  -d '{
    "job_key": "book_ingestion_crew",
    "request_data": {
      "client_user_id": "587f8370-825f-4f0c-8846-2e6d70782989",
      "google_drive_folder_path": "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1",
      "language": "es"
    }
  }' | jq

# Wait a bit
echo -e "\nWaiting for job to process..."
sleep 30

# Kill the server
echo -e "\nStopping API server..."
kill $API_PID

echo "Check the logs and Google Drive for results."