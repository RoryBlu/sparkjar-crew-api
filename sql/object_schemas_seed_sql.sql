-- Seed the object_schemas table with SparkJar Memory System schemas
-- Run this after creating your object_schemas table

INSERT INTO object_schemas (schema_name, schema_version, schema_definition, is_active, created_at, updated_at) VALUES

-- Base observation schema (fallback for any observation)
('base_observation', '1.0.0', '{
  "$id": "base_observation",
  "type": "object",
  "title": "Base Observation Schema",
  "properties": {
    "content": {
      "type": "string",
      "minLength": 1,
      "maxLength": 10000
    },
    "source": {
      "type": "string"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "uniqueItems": true
    }
  },
  "required": ["content"],
  "additionalProperties": true
}'::jsonb, true, NOW(), NOW()),

-- Skill observation schema
('skill_observation', '1.0.0', '{
  "$id": "skill_observation",
  "type": "object",
  "title": "Skill Observation Schema",
  "allOf": [{"$ref": "#/schemas/base_observation"}],
  "properties": {
    "skill_name": {
      "type": "string",
      "maxLength": 100
    },
    "skill_category": {
      "type": "string",
      "enum": ["technical", "creative", "analytical", "communication", "leadership", "other"]
    },
    "proficiency_level": {
      "type": "string",
      "enum": ["beginner", "intermediate", "advanced", "expert"]
    },
    "evidence": {
      "type": "array",
      "items": {"type": "string"}
    }
  },
  "required": ["skill_name", "skill_category"]
}'::jsonb, true, NOW(), NOW()),

-- Database reference observation schema
('database_ref_observation', '1.0.0', '{
  "$id": "database_ref_observation",
  "type": "object",
  "title": "Database Reference Observation Schema",
  "allOf": [{"$ref": "#/schemas/base_observation"}],
  "properties": {
    "table_name": {
      "type": "string",
      "maxLength": 100
    },
    "record_id": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    },
    "relationship_type": {
      "type": "string",
      "enum": ["created", "modified", "referenced", "derived_from", "related_to"]
    },
    "key_fields": {
      "type": "object",
      "additionalProperties": true
    }
  },
  "required": ["table_name", "record_id", "relationship_type"]
}'::jsonb, true, NOW(), NOW()),

-- Writing pattern observation schema
('writing_pattern_observation', '1.0.0', '{
  "$id": "writing_pattern_observation",
  "type": "object",
  "title": "Writing Pattern Observation Schema",
  "allOf": [{"$ref": "#/schemas/base_observation"}],
  "properties": {
    "pattern_type": {
      "type": "string",
      "enum": ["style", "workflow", "structure", "habit", "preference"]
    },
    "content_type": {
      "type": "string",
      "enum": ["blog", "article", "email", "documentation", "social", "other"]
    },
    "frequency": {
      "type": "string",
      "enum": ["always", "usually", "sometimes", "rarely"]
    },
    "description": {
      "type": "string",
      "maxLength": 500
    }
  },
  "required": ["pattern_type", "content_type"]
}'::jsonb, true, NOW(), NOW()),

-- Person entity metadata schema
('person_entity_metadata', '1.0.0', '{
  "$id": "person_entity_metadata",
  "type": "object",
  "title": "Person Entity Metadata Schema",
  "properties": {
    "role": {
      "type": "string",
      "maxLength": 100
    },
    "organization": {
      "type": "string",
      "maxLength": 200
    },
    "email": {
      "type": "string",
      "format": "email"
    },
    "relationship": {
      "type": "string",
      "enum": ["colleague", "client", "collaborator", "friend", "other"]
    },
    "last_contact": {
      "type": "string",
      "format": "date-time"
    },
    "expertise": {
      "type": "array",
      "items": {"type": "string"}
    }
  },
  "additionalProperties": true
}'::jsonb, true, NOW(), NOW()),

-- Synth entity metadata schema
('synth_entity_metadata', '1.0.0', '{
  "$id": "synth_entity_metadata",
  "type": "object",
  "title": "Synth Entity Metadata Schema",
  "properties": {
    "agent_type": {
      "type": "string",
      "enum": ["crewai_agent", "langchain_agent", "custom_agent", "ai_assistant", "other"]
    },
    "model_name": {
      "type": "string"
    },
    "version": {
      "type": "string"
    },
    "capabilities": {
      "type": "array",
      "items": {"type": "string"}
    },
    "last_active": {
      "type": "string",
      "format": "date-time"
    }
  },
  "required": ["agent_type"],
  "additionalProperties": true
}'::jsonb, true, NOW(), NOW());

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_object_schemas_name_active 
ON object_schemas (schema_name, is_active) 
WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_object_schemas_version 
ON object_schemas (schema_name, schema_version);
