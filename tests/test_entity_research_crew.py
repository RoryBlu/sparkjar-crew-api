import os
import sys
from unittest.mock import Mock, patch

# Add project root to path

from services.crew_api.src.crews.entity_research_crew import kickoff

def test_kickoff_runs():
    """kickoff should build the crew and execute without errors."""
    with patch("src.crews.entity_research_crew.crew.build_crew") as mock_build:
        crew = Mock()
        crew.kickoff.return_value = {"result": "ok"}
        mock_build.return_value = crew

        inputs = {"entity_name": "Acme", "entity_domain": "testing"}
        result = kickoff(inputs)

        assert result == {"result": "ok"}
        crew.kickoff.assert_called_once_with(inputs=inputs)
