"""
Learning Path Management for Tutor Mode.

KISS principles:
- Simple path tracking with Redis
- Basic progress calculation
- No complex graph algorithms
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from src.chat.models import ChatSessionV1
from src.chat.services.session_manager_v1 import RedisSessionManager

logger = logging.getLogger(__name__)


class LearningPathManager:
    """
    Manages learning paths for tutor mode sessions.
    
    KISS: Just track topics covered and suggest next ones.
    """
    
    def __init__(
        self,
        session_manager: RedisSessionManager
    ):
        """
        Initialize learning path manager.
        
        Args:
            session_manager: Redis session manager
        """
        self.session_manager = session_manager
        
    async def get_learning_path(
        self,
        session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get the complete learning path for a session.
        
        Args:
            session_id: Session UUID
            
        Returns:
            Learning path with topics and progress
        """
        session = await self.session_manager.get_session(session_id)
        if not session or session.mode != "tutor":
            return None
            
        path = session.learning_path or []
        
        return {
            "session_id": str(session_id),
            "current_topic": session.learning_topic,
            "understanding_level": session.understanding_level,
            "path": path,
            "topics_covered": len(path),
            "session_duration_minutes": self._calculate_duration(session),
            "progress_summary": self._calculate_progress(path)
        }
        
    async def add_to_path(
        self,
        session_id: UUID,
        topic: str,
        objective: Optional[str] = None
    ) -> bool:
        """
        Add a topic to the learning path.
        
        Args:
            session_id: Session UUID
            topic: Topic being learned
            objective: Optional learning objective
            
        Returns:
            True if added successfully
        """
        session = await self.session_manager.get_session(session_id)
        if not session or session.mode != "tutor":
            return False
            
        # Create path item
        path_item = topic
        if objective:
            path_item = f"{topic}: {objective}"
            
        # Update path
        await self.session_manager.update_learning_state(
            session_id=session_id,
            topic=topic,
            path_item=path_item
        )
        
        return True
        
    async def get_recommendations(
        self,
        session_id: UUID,
        available_topics: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get topic recommendations based on learning path.
        
        Args:
            session_id: Session UUID
            available_topics: Topics available in memory
            
        Returns:
            Recommended topics with reasons
        """
        session = await self.session_manager.get_session(session_id)
        if not session:
            return []
            
        path = session.learning_path or []
        covered_topics = self._extract_topics_from_path(path)
        
        recommendations = []
        
        # Filter out already covered topics
        for topic in available_topics:
            if topic not in covered_topics:
                recommendation = {
                    "topic": topic,
                    "reason": self._get_recommendation_reason(
                        topic,
                        session.learning_topic,
                        session.understanding_level
                    ),
                    "difficulty": self._estimate_difficulty(
                        topic,
                        session.understanding_level
                    )
                }
                recommendations.append(recommendation)
                
        # Sort by relevance
        recommendations.sort(
            key=lambda x: (
                x["reason"] != "natural_progression",
                abs(x["difficulty"] - (session.understanding_level or 3))
            )
        )
        
        return recommendations[:5]  # Top 5 recommendations
        
    async def export_learning_report(
        self,
        session_id: UUID
    ) -> Dict[str, Any]:
        """
        Export a learning progress report.
        
        Args:
            session_id: Session UUID
            
        Returns:
            Detailed learning report
        """
        session = await self.session_manager.get_session(session_id)
        if not session or session.mode != "tutor":
            return {"error": "Session not found or not in tutor mode"}
            
        path = session.learning_path or []
        topics = self._extract_topics_from_path(path)
        
        report = {
            "session_id": str(session_id),
            "report_generated": datetime.utcnow().isoformat(),
            "session_info": {
                "created": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "duration_minutes": self._calculate_duration(session),
                "message_count": session.message_count
            },
            "learning_progress": {
                "starting_topic": topics[0] if topics else None,
                "current_topic": session.learning_topic,
                "topics_covered": topics,
                "understanding_progression": self._track_understanding_changes(path),
                "final_understanding_level": session.understanding_level
            },
            "learning_path_visualization": self._create_path_visualization(path),
            "recommendations": {
                "strengths": self._identify_strengths(path),
                "areas_for_improvement": self._identify_improvements(path),
                "next_steps": self._suggest_next_steps(
                    session.learning_topic,
                    session.understanding_level
                )
            }
        }
        
        return report
        
    def _calculate_duration(self, session: ChatSessionV1) -> int:
        """Calculate session duration in minutes."""
        duration = session.last_activity - session.created_at
        return int(duration.total_seconds() / 60)
        
    def _calculate_progress(self, path: List[str]) -> Dict[str, Any]:
        """Calculate learning progress metrics."""
        if not path:
            return {"status": "just_started", "topics_explored": 0}
            
        return {
            "status": "in_progress",
            "topics_explored": len(path),
            "depth": self._estimate_learning_depth(path)
        }
        
    def _extract_topics_from_path(self, path: List[str]) -> List[str]:
        """Extract topic names from path items."""
        topics = []
        for item in path:
            # Handle "topic: objective" format
            if ":" in item:
                topic = item.split(":")[0].strip()
            else:
                topic = item
            topics.append(topic)
        return topics
        
    def _get_recommendation_reason(
        self,
        topic: str,
        current_topic: Optional[str],
        understanding_level: Optional[int]
    ) -> str:
        """Determine why a topic is recommended."""
        if not current_topic:
            return "starting_point"
            
        # Simple keyword matching for relationships
        current_lower = current_topic.lower()
        topic_lower = topic.lower()
        
        # Direct progression
        if any(word in topic_lower for word in ["advanced", "deep", "complex"]):
            if understanding_level and understanding_level >= 4:
                return "natural_progression"
            else:
                return "future_topic"
                
        # Related topics
        if any(word in current_lower and word in topic_lower 
               for word in ["database", "query", "index", "optimization"]):
            return "related_topic"
            
        return "explore_new_area"
        
    def _estimate_difficulty(
        self,
        topic: str,
        understanding_level: Optional[int]
    ) -> int:
        """Estimate topic difficulty (1-5 scale)."""
        topic_lower = topic.lower()
        
        # Basic difficulty estimation
        if any(word in topic_lower for word in ["basic", "intro", "beginner"]):
            return 1
        elif any(word in topic_lower for word in ["advanced", "complex", "deep"]):
            return 5
        elif any(word in topic_lower for word in ["intermediate", "practical"]):
            return 3
            
        # Default to middle
        return 3
        
    def _estimate_learning_depth(self, path: List[str]) -> str:
        """Estimate how deep the learning has gone."""
        if len(path) < 3:
            return "surface"
        elif len(path) < 7:
            return "moderate"
        else:
            return "deep"
            
    def _track_understanding_changes(self, path: List[str]) -> List[int]:
        """Track understanding level changes (simplified)."""
        # In reality, this would track actual understanding changes
        # For now, simulate progression
        levels = [3]  # Start at middle
        for i, item in enumerate(path):
            if "advanced" in item.lower():
                levels.append(min(5, levels[-1] + 1))
            elif "basic" in item.lower():
                levels.append(max(1, levels[-1] - 1))
            else:
                levels.append(levels[-1])
        return levels
        
    def _create_path_visualization(self, path: List[str]) -> str:
        """Create simple text visualization of path."""
        if not path:
            return "No path yet"
            
        visualization = "Learning Journey:\n"
        for i, item in enumerate(path):
            visualization += f"  {i+1}. {item}\n"
            if i < len(path) - 1:
                visualization += "     ↓\n"
                
        return visualization
        
    def _identify_strengths(self, path: List[str]) -> List[str]:
        """Identify learning strengths from path."""
        strengths = []
        
        if len(path) > 5:
            strengths.append("Consistent learning engagement")
            
        # Check for progression
        topics = self._extract_topics_from_path(path)
        if any("advanced" in t.lower() for t in topics):
            strengths.append("Progressing to advanced topics")
            
        if len(set(topics)) == len(topics):
            strengths.append("Exploring diverse topics")
            
        return strengths or ["Building foundation"]
        
    def _identify_improvements(self, path: List[str]) -> List[str]:
        """Identify areas for improvement."""
        improvements = []
        
        if len(path) < 3:
            improvements.append("Explore more topics for broader understanding")
            
        topics = self._extract_topics_from_path(path)
        if len(set(topics)) < len(topics) * 0.7:
            improvements.append("Try exploring new areas")
            
        return improvements or ["Keep up the great work!"]
        
    def _suggest_next_steps(
        self,
        current_topic: Optional[str],
        understanding_level: Optional[int]
    ) -> List[str]:
        """Suggest next learning steps."""
        steps = []
        
        if understanding_level and understanding_level >= 4:
            steps.append("Apply knowledge in practical projects")
            steps.append("Explore advanced techniques")
        elif understanding_level and understanding_level <= 2:
            steps.append("Review fundamentals")
            steps.append("Practice with simple examples")
        else:
            steps.append("Deepen current topic understanding")
            steps.append("Connect concepts together")
            
        return steps