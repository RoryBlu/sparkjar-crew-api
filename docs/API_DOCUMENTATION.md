# SparkJAR COS API

This document lists the public endpoints provided by the FastAPI server.

## Authentication

All routes expect a bearer token with the `sparkjar_internal` scope. Role-based access control is not implemented in the server. Use an external gateway or future RBAC extension if you need fine-grained restrictions.

## POST `/crew_job`

Queue a crew for asynchronous execution.

### Required fields

- `job_key`: identifies the crew to run.
- `client_user_id`: user requesting the job.
- `actor_type`: `synth` or `human`.
- `actor_id`: ID of the synth or human actor.

Additional fields depend on the chosen `job_key`. See the functional requirement files under `crew/` for detailed schemas. The `crew_builder` schema is documented in `crew/crew_builder/crew_builder_functional_reqs_as_built.md`.

### Example
```json
{
  "job_key": "crew_builder",
  "client_user_id": "user-uuid",
  "actor_type": "synth",
  "actor_id": "synth-uuid",
  "crew_name": "demo",
  "crew_purpose": "Create a demo crew that sends a status email."
}
```
Response:
```json
{
  "job_id": "uuid",
  "status": "queued"
}
```

## GET `/health`

Returns service status and environment configuration flags.

Example response:
```json
{
  "status": "healthy",
  "service": "crew_job_api",
  "environment": "development"
}
```

## GET `/test_chroma`

Checks ChromaDB connectivity and lists collections. Useful for verifying deployment.

Example response:
```json
{
  "status": "success",
  "collections": [],
  "chroma_url": "http://localhost:8000"
}
```

## Job Status

The API does not yet expose a dedicated status endpoint. Jobs are stored in the `crew_jobs` table with a `status` field and related events in `crew_job_event`. Poll the database or use Supabase realtime to watch for updates. A `GET /crew_job/{id}` endpoint is planned.