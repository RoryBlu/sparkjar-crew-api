import os
import sys

# Ensure crew-api service modules are on path

from services.crew_api.src.agents.name_disambiguator_agent import NameDisambiguatorAgent

def test_create_new_entity_when_no_match():
    agent = NameDisambiguatorAgent(confidence_threshold=0.8)
    result = agent.disambiguate("Alice", [])
    assert result == {"action": "create_entity", "entity_name": "Alice"}

def test_select_existing_entity_high_confidence():
    agent = NameDisambiguatorAgent(confidence_threshold=0.8)
    candidates = [
        {"entity_id": "id1", "similarity": 0.9},
        {"entity_id": "id2", "similarity": 0.85},
    ]
    result = agent.disambiguate("Alice", candidates)
    assert result == {"action": "select_entity", "entity_id": "id1"}

def test_alias_entity_creation_below_threshold():
    agent = NameDisambiguatorAgent(confidence_threshold=0.8)
    candidates = [{"entity_id": "id1", "similarity": 0.5}]
    result = agent.disambiguate("Alice", candidates)
    assert result == {
        "action": "create_alias",
        "entity_id": "id1",
        "alias": "Alice",
    }

