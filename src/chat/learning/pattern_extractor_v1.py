"""
Pattern Extraction for Learning Loop.

KISS principles:
- Simple pattern identification from conversations
- Basic success metric calculation
- No complex ML or NLP
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from src.chat.models import ChatResponseV1, ChatSessionV1

logger = logging.getLogger(__name__)


class PatternExtractor:
    """
    Extracts successful interaction patterns from conversations.
    
    KISS: Look for simple patterns that worked well.
    """
    
    def __init__(self):
        """Initialize pattern extractor."""
        self.success_indicators = {
            "positive_feedback": [
                "thank you", "thanks", "perfect", "exactly",
                "that helps", "great", "understood", "got it"
            ],
            "completion_markers": [
                "solved", "fixed", "working", "done",
                "completed", "finished"
            ],
            "learning_progress": [
                "i understand", "makes sense", "i see",
                "now i get it", "clear now"
            ]
        }
        
    def extract_patterns(
        self,
        conversation_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract patterns from conversation history.
        
        Args:
            conversation_history: List of message/response pairs
            
        Returns:
            List of identified patterns
        """
        patterns = []
        
        for i, exchange in enumerate(conversation_history):
            # Analyze each exchange
            pattern = self._analyze_exchange(exchange, i)
            if pattern:
                patterns.append(pattern)
                
        # Group similar patterns
        grouped_patterns = self._group_patterns(patterns)
        
        return grouped_patterns
        
    def calculate_success_metrics(
        self,
        response: ChatResponseV1,
        user_feedback: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate success metrics for a response.
        
        Args:
            response: Chat response to evaluate
            user_feedback: Optional user feedback message
            
        Returns:
            Success metrics dictionary
        """
        metrics = {
            "response_quality": 0.0,
            "memory_relevance": 0.0,
            "task_completion": 0.0,
            "user_satisfaction": 0.0
        }
        
        # Response quality based on length and structure
        if len(response.response) > 100:
            metrics["response_quality"] += 0.3
        if response.response.count("\n") > 2:  # Structured response
            metrics["response_quality"] += 0.2
        if response.memory_context_used:
            metrics["response_quality"] += 0.5
            
        # Memory relevance
        if response.memory_context_used:
            memory_count = len(response.memory_context_used)
            metrics["memory_relevance"] = min(1.0, memory_count / 5.0)
            
        # Task completion (for agent mode)
        if response.mode_used == "agent" and response.task_context:
            if response.task_context.get("procedures_followed"):
                metrics["task_completion"] = 0.8
            if "completed" in response.response.lower():
                metrics["task_completion"] = 1.0
                
        # User satisfaction from feedback
        if user_feedback:
            satisfaction = self._calculate_satisfaction(user_feedback)
            metrics["user_satisfaction"] = satisfaction
            
        return metrics
        
    def identify_successful_patterns(
        self,
        patterns: List[Dict[str, Any]],
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Filter patterns by success threshold.
        
        Args:
            patterns: All extracted patterns
            threshold: Minimum success score
            
        Returns:
            Successful patterns above threshold
        """
        successful = []
        
        for pattern in patterns:
            success_score = pattern.get("success_score", 0.0)
            if success_score >= threshold:
                successful.append(pattern)
                
        # Sort by success score
        successful.sort(key=lambda x: x["success_score"], reverse=True)
        
        return successful
        
    def create_pattern_entity(
        self,
        pattern: Dict[str, Any],
        session_id: UUID
    ) -> Dict[str, Any]:
        """
        Create memory entity for successful pattern.
        
        Args:
            pattern: Successful pattern
            session_id: Source session
            
        Returns:
            Entity structure for memory storage
        """
        return {
            "entity": {
                "name": f"pattern_{pattern['type']}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "type": "interaction_pattern",
                "metadata": {
                    "pattern_type": pattern["type"],
                    "success_score": pattern["success_score"],
                    "session_id": str(session_id),
                    "extracted_at": datetime.utcnow().isoformat()
                }
            },
            "observations": [
                {
                    "type": "pattern_description",
                    "value": {
                        "description": pattern["description"],
                        "trigger": pattern.get("trigger", ""),
                        "response_approach": pattern.get("approach", ""),
                        "outcome": pattern.get("outcome", "")
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "relationships": self._create_pattern_relationships(pattern)
        }
        
    def _analyze_exchange(
        self,
        exchange: Dict[str, Any],
        index: int
    ) -> Optional[Dict[str, Any]]:
        """Analyze single exchange for patterns."""
        message = exchange.get("message", "").lower()
        response = exchange.get("response", {})
        
        # Check for successful task completion
        if self._is_successful_completion(message, response):
            return {
                "type": "task_completion",
                "trigger": self._extract_trigger(message),
                "approach": self._extract_approach(response),
                "outcome": "successful",
                "success_score": 0.9,
                "description": f"Successfully completed task: {self._extract_trigger(message)}"
            }
            
        # Check for learning progress
        if self._is_learning_progress(exchange):
            return {
                "type": "learning_progress",
                "trigger": "confusion or question",
                "approach": "progressive explanation",
                "outcome": "understanding achieved",
                "success_score": 0.8,
                "description": "User progressed in understanding"
            }
            
        return None
        
    def _is_successful_completion(
        self,
        message: str,
        response: Dict[str, Any]
    ) -> bool:
        """Check if exchange shows successful completion."""
        # Check response text
        response_text = response.get("response", "").lower()
        
        # Look for completion markers
        for marker in self.success_indicators["completion_markers"]:
            if marker in response_text:
                return True
                
        # Check if procedures were followed
        task_context = response.get("task_context", {})
        if task_context.get("procedures_followed"):
            return True
            
        return False
        
    def _is_learning_progress(
        self,
        exchange: Dict[str, Any]
    ) -> bool:
        """Check if exchange shows learning progress."""
        # In tutor mode with understanding level increase
        response = exchange.get("response", {})
        if response.get("mode_used") == "tutor":
            learning_context = response.get("learning_context", {})
            if learning_context.get("understanding_level", 0) > 3:
                return True
                
        return False
        
    def _extract_trigger(self, message: str) -> str:
        """Extract trigger pattern from message."""
        # Simple extraction of question type
        if "how do i" in message:
            return "how-to question"
        elif "what is" in message:
            return "definition question"
        elif "error" in message or "problem" in message:
            return "troubleshooting request"
        elif "create" in message or "make" in message:
            return "creation task"
        else:
            return "general query"
            
    def _extract_approach(self, response: Dict[str, Any]) -> str:
        """Extract approach used in response."""
        if response.get("memory_context_used"):
            return "memory-guided response"
        elif response.get("mode_used") == "tutor":
            return "educational approach"
        elif response.get("task_context", {}).get("procedures_followed"):
            return "procedure-following approach"
        else:
            return "general response"
            
    def _calculate_satisfaction(self, feedback: str) -> float:
        """Calculate user satisfaction from feedback."""
        feedback_lower = feedback.lower()
        score = 0.5  # Neutral baseline
        
        # Positive indicators
        for indicator in self.success_indicators["positive_feedback"]:
            if indicator in feedback_lower:
                score = min(1.0, score + 0.2)
                
        # Negative indicators
        negative_indicators = [
            "doesn't work", "still broken", "confused",
            "don't understand", "wrong", "incorrect"
        ]
        for indicator in negative_indicators:
            if indicator in feedback_lower:
                score = max(0.0, score - 0.3)
                
        return score
        
    def _group_patterns(
        self,
        patterns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Group similar patterns together."""
        # Simple grouping by type and trigger
        grouped = {}
        
        for pattern in patterns:
            key = f"{pattern['type']}:{pattern['trigger']}"
            if key not in grouped:
                grouped[key] = pattern
                grouped[key]["occurrences"] = 1
            else:
                # Merge patterns
                grouped[key]["occurrences"] += 1
                grouped[key]["success_score"] = (
                    grouped[key]["success_score"] + pattern["success_score"]
                ) / 2
                
        return list(grouped.values())
        
    def _create_pattern_relationships(
        self,
        pattern: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create relationships for pattern entity."""
        relationships = []
        
        # Link to pattern type
        relationships.append({
            "type": "instance_of",
            "to_entity": f"pattern_type_{pattern['type']}",
            "metadata": {
                "confidence": pattern["success_score"]
            }
        })
        
        return relationships