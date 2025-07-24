class NameDisambiguatorAgent:
    """Simple agent for selecting or creating entities based on name similarity."""

    def __init__(self, confidence_threshold: float = 0.8):
        self.confidence_threshold = confidence_threshold

    def disambiguate(self, name: str, candidates: list[dict]) -> dict:
        """Decide whether to create a new entity, use an existing one, or create an alias.

        Args:
            name: The name to disambiguate.
            candidates: List of candidate matches with ``entity_id`` and ``similarity``.

        Returns:
            Dict with action and associated data.
        """
        if not candidates:
            return {"action": "create_entity", "entity_name": name}

        best = max(candidates, key=lambda c: c.get("similarity", 0))
        if best.get("similarity", 0) >= self.confidence_threshold:
            return {"action": "select_entity", "entity_id": best["entity_id"]}

        return {
            "action": "create_alias",
            "entity_id": best["entity_id"],
            "alias": name,
        }
