#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""
Seed script for blog writing schemas in the object_schemas table.
These schemas define the structure for blog-related memory entities, observations, and relationships.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to Python path

from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session, sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import from shared modules
from sparkjar_crew.shared.database.models import ObjectSchemas
from sparkjar_crew.shared.config.config import DATABASE_URL_DIRECT

# Create synchronous engine for this script
engine = create_engine(DATABASE_URL_DIRECT.replace('postgresql+asyncpg', 'postgresql'))
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Skill Module Schema (needed for future skill modules)
SKILL_MODULE_SCHEMA = {
    "name": "skill_module",
    "object_type": "memory_entity_metadata",
    "schema": {
        "type": "object",
        "properties": {
            "module_type": {
                "type": "string",
                "enum": ["erp_sales", "erp_finance", "erp_manufacturing", "productivity_suite", "crm_system", "analytics_tool"],
                "description": "Category of skill module"
            },
            "vendor": {
                "type": "string",
                "description": "Software vendor (e.g., Microsoft, Google, SAP, Odoo)"
            },
            "version": {
                "type": "string",
                "description": "Version of the software"
            },
            "modules": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Sub-modules or components included"
            },
            "capabilities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "What the module enables synths to do"
            },
            "integration_points": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Other systems this integrates with"
            },
            "complete_knowledge": {
                "type": "boolean",
                "default": True,
                "description": "Always true - we provide complete knowledge, not partial"
            }
        },
        "required": ["module_type", "vendor"],
        "additionalProperties": True
    },
    "description": "Schema for swappable tool knowledge modules (e.g., ERP systems, productivity suites)"
}

# Blog Entity Schemas (object_type: memory_entity_metadata)
BLOG_ENTITY_SCHEMAS = [
    {
        "name": "procedure_template",
        "object_type": "memory_entity_metadata",
        "schema": {
            "type": "object",
            "properties": {
                "procedure_type": {
                    "type": "string",
                    "description": "Type of procedure (e.g., blog_writing, content_editing)"
                },
                "version": {
                    "type": "string",
                    "description": "Version number of the procedure"
                },
                "synth_class": {
                    "type": "integer",
                    "description": "ID of the synth class this procedure belongs to"
                },
                "phases": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of phases in the procedure"
                },
                "total_duration": {
                    "type": "string",
                    "description": "Estimated total duration for the procedure"
                },
                "prerequisites": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Required knowledge or tools"
                },
                "deliverables": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Expected outputs from following this procedure"
                }
            },
            "required": ["procedure_type", "version", "synth_class"],
            "additionalProperties": True
        },
        "description": "Schema for procedure templates that define step-by-step processes"
    },
    {
        "name": "checklist_template",
        "object_type": "memory_entity_metadata",
        "schema": {
            "type": "object",
            "properties": {
                "checklist_type": {
                    "type": "string",
                    "description": "Type of checklist (e.g., quality_assurance, pre_publish)"
                },
                "version": {
                    "type": "string",
                    "description": "Version number of the checklist"
                },
                "synth_class": {
                    "type": "integer",
                    "description": "ID of the synth class this checklist belongs to"
                },
                "categories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "weight": {"type": "number"},
                            "required_score": {"type": "number"}
                        }
                    },
                    "description": "Categories within the checklist"
                },
                "passing_score": {
                    "type": "number",
                    "description": "Minimum score to pass the checklist"
                },
                "related_procedure": {
                    "type": "string",
                    "format": "uuid",
                    "description": "ID of related procedure template"
                }
            },
            "required": ["checklist_type", "version", "synth_class"],
            "additionalProperties": True
        },
        "description": "Schema for quality checklists and validation templates"
    },
    {
        "name": "style_guide",
        "object_type": "memory_entity_metadata",
        "schema": {
            "type": "object",
            "properties": {
                "guide_type": {
                    "type": "string",
                    "description": "Type of style guide (e.g., writing, formatting)"
                },
                "synth_class": {
                    "type": "integer",
                    "description": "ID of the synth class this guide belongs to"
                },
                "voice": {
                    "type": "string",
                    "description": "Overall voice characteristics"
                },
                "tone_variations": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "string"
                    },
                    "description": "Different tones for different contexts"
                },
                "principles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"}
                        }
                    },
                    "description": "Core writing principles"
                },
                "examples": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "good": {"type": "string"},
                            "bad": {"type": "string"},
                            "explanation": {"type": "string"}
                        }
                    },
                    "description": "Examples of good vs bad writing"
                }
            },
            "required": ["guide_type", "synth_class"],
            "additionalProperties": True
        },
        "description": "Schema for writing and formatting style guides"
    },
    {
        "name": "content_output",
        "object_type": "memory_entity_metadata",
        "schema": {
            "type": "object",
            "properties": {
                "content_type": {
                    "type": "string",
                    "description": "Type of content (e.g., blog_post, article, guide)"
                },
                "topic": {
                    "type": "string",
                    "description": "Main topic or subject"
                },
                "word_count": {
                    "type": "integer",
                    "description": "Total word count"
                },
                "target_keywords": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "SEO keywords targeted"
                },
                "quality_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Overall quality score"
                },
                "performance_metrics": {
                    "type": "object",
                    "properties": {
                        "views": {"type": "integer"},
                        "engagement_rate": {"type": "number"},
                        "conversion_rate": {"type": "number"}
                    },
                    "description": "Performance tracking data"
                },
                "followed_procedure": {
                    "type": "string",
                    "format": "uuid",
                    "description": "ID of procedure template followed"
                },
                "synth_class": {
                    "type": "integer",
                    "description": "Synth class that created this content"
                }
            },
            "required": ["content_type", "topic"],
            "additionalProperties": True
        },
        "description": "Schema for content outputs like blog posts"
    }
]

# Blog Observation Schemas (object_type: memory_observation)
BLOG_OBSERVATION_SCHEMAS = [
    {
        "name": "procedure_phase",
        "object_type": "memory_observation",
        "schema": {
            "type": "object",
            "properties": {
                "phase": {
                    "type": "integer",
                    "description": "Phase number in the procedure"
                },
                "name": {
                    "type": "string",
                    "description": "Name of the phase"
                },
                "duration": {
                    "type": "string",
                    "description": "Estimated duration"
                },
                "objectives": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Goals for this phase"
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step": {"type": "string"},
                            "action": {"type": "string"},
                            "description": {"type": "string"},
                            "tools": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    },
                    "description": "Detailed steps in the phase"
                },
                "deliverables": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Expected outputs from this phase"
                },
                "quality_criteria": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "Quality standards for phase completion"
                }
            },
            "required": ["phase", "name", "objectives"],
            "additionalProperties": True
        },
        "description": "Schema for procedure phase observations"
    },
    {
        "name": "writing_technique",
        "object_type": "memory_observation",
        "schema": {
            "type": "object",
            "properties": {
                "technique_type": {
                    "type": "string",
                    "description": "Type of writing technique"
                },
                "category": {
                    "type": "string",
                    "description": "Category (e.g., engagement, clarity, persuasion)"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the technique"
                },
                "examples": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Examples of the technique in use"
                },
                "when_to_use": {
                    "type": "string",
                    "description": "Situations where this technique is effective"
                },
                "effectiveness_rating": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Effectiveness rating based on results"
                }
            },
            "required": ["technique_type", "category", "description"],
            "additionalProperties": True
        },
        "description": "Schema for writing technique observations"
    },
    {
        "name": "quality_assessment",
        "object_type": "memory_observation",
        "schema": {
            "type": "object",
            "properties": {
                "assessment_type": {
                    "type": "string",
                    "description": "Type of quality assessment"
                },
                "scores": {
                    "type": "object",
                    "properties": {
                        "content_quality": {"type": "number"},
                        "seo_optimization": {"type": "number"},
                        "user_experience": {"type": "number"},
                        "technical_performance": {"type": "number"},
                        "overall": {"type": "number"}
                    },
                    "description": "Quality scores by category"
                },
                "strengths": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Identified strengths"
                },
                "improvements": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Areas for improvement"
                },
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Specific recommendations"
                },
                "passed": {
                    "type": "boolean",
                    "description": "Whether quality standards were met"
                }
            },
            "required": ["assessment_type", "scores", "passed"],
            "additionalProperties": True
        },
        "description": "Schema for quality assessment observations"
    },
    {
        "name": "content_structure",
        "object_type": "memory_observation",
        "schema": {
            "type": "object",
            "properties": {
                "structure_type": {
                    "type": "string",
                    "description": "Type of content structure"
                },
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "purpose": {"type": "string"},
                            "word_count_target": {"type": "integer"},
                            "key_elements": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    },
                    "description": "Sections in the structure"
                },
                "flow_pattern": {
                    "type": "string",
                    "description": "How sections flow together"
                },
                "engagement_hooks": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Techniques to maintain engagement"
                }
            },
            "required": ["structure_type", "sections"],
            "additionalProperties": True
        },
        "description": "Schema for content structure observations"
    }
]

# Blog Relationship Schemas (object_type: memory_relationship)
BLOG_RELATIONSHIP_SCHEMAS = [
    {
        "name": "followed_procedure",
        "object_type": "memory_relationship",
        "schema": {
            "type": "object",
            "properties": {
                "compliance_rate": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Percentage of procedure steps followed"
                },
                "deviations": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Any deviations from the procedure"
                },
                "adaptations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "original_step": {"type": "string"},
                            "adaptation": {"type": "string"},
                            "reason": {"type": "string"}
                        }
                    },
                    "description": "Adaptations made to the procedure"
                },
                "effectiveness": {
                    "type": "string",
                    "enum": ["highly_effective", "effective", "moderately_effective", "ineffective"],
                    "description": "How effective was following this procedure"
                }
            },
            "required": ["compliance_rate"],
            "additionalProperties": True
        },
        "description": "Relationship between content output and procedure template"
    },
    {
        "name": "enhances",
        "object_type": "memory_relationship",
        "schema": {
            "type": "object",
            "properties": {
                "enhancement_type": {
                    "type": "string",
                    "description": "Type of enhancement provided"
                },
                "value_added": {
                    "type": "string",
                    "description": "Description of value added"
                },
                "tested": {
                    "type": "boolean",
                    "description": "Whether enhancement has been tested"
                },
                "results": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "Results from testing the enhancement"
                },
                "adoption_rate": {
                    "type": "number",
                    "description": "How often this enhancement is used"
                }
            },
            "required": ["enhancement_type", "value_added"],
            "additionalProperties": True
        },
        "description": "Relationship showing how one entity enhances another"
    },
    {
        "name": "requires",
        "object_type": "memory_relationship",
        "schema": {
            "type": "object",
            "properties": {
                "requirement_type": {
                    "type": "string",
                    "description": "Type of requirement"
                },
                "criticality": {
                    "type": "string",
                    "enum": ["mandatory", "recommended", "optional"],
                    "description": "How critical is this requirement"
                },
                "reason": {
                    "type": "string",
                    "description": "Why this is required"
                },
                "alternatives": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Alternative options if available"
                }
            },
            "required": ["requirement_type", "criticality"],
            "additionalProperties": True
        },
        "description": "Relationship showing dependencies between entities"
    },
    {
        "name": "supersedes",
        "object_type": "memory_relationship",
        "schema": {
            "type": "object",
            "properties": {
                "version_change": {
                    "type": "string",
                    "description": "Version change (e.g., 2.0 -> 3.0)"
                },
                "changes_made": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of changes in new version"
                },
                "migration_notes": {
                    "type": "string",
                    "description": "Notes for migrating from old to new"
                },
                "backward_compatible": {
                    "type": "boolean",
                    "description": "Whether old version can still be used"
                },
                "deprecation_date": {
                    "type": "string",
                    "format": "date",
                    "description": "When old version will be deprecated"
                }
            },
            "required": ["version_change", "changes_made"],
            "additionalProperties": True
        },
        "description": "Relationship showing version succession"
    }
]

def seed_blog_schemas():
    """Seed blog writing schemas into the database."""
    
    logger.info("🚀 Seeding blog writing schemas...")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Combine all schemas (including skill_module schema)
        all_schemas = [SKILL_MODULE_SCHEMA] + BLOG_ENTITY_SCHEMAS + BLOG_OBSERVATION_SCHEMAS + BLOG_RELATIONSHIP_SCHEMAS
        
        # Check for existing schemas and insert new ones
        inserted_count = 0
        for schema_data in all_schemas:
            # Check if schema already exists
            existing = db.query(ObjectSchemas).filter(
                ObjectSchemas.name == schema_data["name"],
                ObjectSchemas.object_type == schema_data["object_type"]
            ).first()
            
            if existing:
                logger.info(f"  ⚠️  Schema '{schema_data['name']}' ({schema_data['object_type']}) already exists")
                continue
            
            # Create new schema
            new_schema = ObjectSchemas(**schema_data)
            db.add(new_schema)
            inserted_count += 1
            logger.info(f"  ✅ Created schema '{schema_data['name']}' ({schema_data['object_type']})")
        
        # Commit changes
        db.commit()
        
        logger.info(f"\n📊 Summary:")
        logger.info(f"  - Total schemas processed: {len(all_schemas)}")
        logger.info(f"  - New schemas inserted: {inserted_count}")
        logger.info(f"  - Entity schemas: {len(BLOG_ENTITY_SCHEMAS)}")
        logger.info(f"  - Observation schemas: {len(BLOG_OBSERVATION_SCHEMAS)}")
        logger.info(f"  - Relationship schemas: {len(BLOG_RELATIONSHIP_SCHEMAS)}")
        
    except Exception as e:
        logger.error(f"❌ Error seeding schemas: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_blog_schemas()