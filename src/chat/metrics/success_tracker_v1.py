"""
Success Metrics Tracking for Learning Effectiveness.

KISS principles:
- Simple metric collection
- Basic aggregation
- Clear reporting
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)


class SuccessMetricsTracker:
    """
    Tracks success metrics for learning effectiveness.
    
    KISS: Count successes, calculate rates, report trends.
    """
    
    def __init__(self):
        """Initialize metrics tracker."""
        # In-memory metrics storage (in production, use database)
        self.interaction_metrics = []
        self.pattern_metrics = []
        self.learning_metrics = []
        
    def track_interaction(
        self,
        session_id: UUID,
        mode: str,
        response_time_ms: int,
        memories_used: int,
        user_satisfaction: Optional[float] = None
    ):
        """
        Track individual interaction metrics.
        
        Args:
            session_id: Chat session
            mode: Chat mode (tutor/agent)
            response_time_ms: Response generation time
            memories_used: Number of memories accessed
            user_satisfaction: Optional satisfaction score (0-1)
        """
        metric = {
            "session_id": str(session_id),
            "mode": mode,
            "timestamp": datetime.utcnow(),
            "response_time_ms": response_time_ms,
            "memories_used": memories_used,
            "user_satisfaction": user_satisfaction
        }
        
        self.interaction_metrics.append(metric)
        
        # Keep only recent metrics (last 7 days)
        self._cleanup_old_metrics()
        
    def track_pattern_success(
        self,
        pattern_type: str,
        success_score: float,
        occurrences: int
    ):
        """
        Track successful pattern usage.
        
        Args:
            pattern_type: Type of pattern
            success_score: Pattern success score (0-1)
            occurrences: Number of times used
        """
        metric = {
            "pattern_type": pattern_type,
            "success_score": success_score,
            "occurrences": occurrences,
            "timestamp": datetime.utcnow()
        }
        
        self.pattern_metrics.append(metric)
        
    def track_learning_progress(
        self,
        session_id: UUID,
        understanding_change: int,
        topics_covered: int,
        completion_rate: float
    ):
        """
        Track learning progress in tutor mode.
        
        Args:
            session_id: Tutor session
            understanding_change: Change in understanding level
            topics_covered: Number of topics explored
            completion_rate: Learning objective completion (0-1)
        """
        metric = {
            "session_id": str(session_id),
            "understanding_change": understanding_change,
            "topics_covered": topics_covered,
            "completion_rate": completion_rate,
            "timestamp": datetime.utcnow()
        }
        
        self.learning_metrics.append(metric)
        
    def get_performance_summary(
        self,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get performance summary for time window.
        
        Args:
            time_window_hours: Hours to look back
            
        Returns:
            Performance metrics summary
        """
        cutoff = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        # Filter metrics by time window
        recent_interactions = [
            m for m in self.interaction_metrics
            if m["timestamp"] > cutoff
        ]
        
        if not recent_interactions:
            return {
                "time_window_hours": time_window_hours,
                "total_interactions": 0,
                "status": "no_data"
            }
            
        # Calculate averages
        avg_response_time = sum(m["response_time_ms"] for m in recent_interactions) / len(recent_interactions)
        avg_memories_used = sum(m["memories_used"] for m in recent_interactions) / len(recent_interactions)
        
        # Satisfaction metrics
        satisfaction_scores = [
            m["user_satisfaction"] for m in recent_interactions
            if m["user_satisfaction"] is not None
        ]
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else None
        
        # Mode breakdown
        mode_counts = {}
        for m in recent_interactions:
            mode = m["mode"]
            mode_counts[mode] = mode_counts.get(mode, 0) + 1
            
        return {
            "time_window_hours": time_window_hours,
            "total_interactions": len(recent_interactions),
            "average_response_time_ms": round(avg_response_time, 2),
            "average_memories_used": round(avg_memories_used, 2),
            "average_satisfaction": round(avg_satisfaction, 2) if avg_satisfaction else None,
            "mode_distribution": mode_counts,
            "performance_trend": self._calculate_trend(recent_interactions)
        }
        
    def get_learning_effectiveness(self) -> Dict[str, Any]:
        """
        Get learning effectiveness metrics.
        
        Returns:
            Learning metrics summary
        """
        if not self.learning_metrics:
            return {
                "status": "no_learning_data"
            }
            
        # Understanding improvements
        positive_changes = sum(
            1 for m in self.learning_metrics
            if m["understanding_change"] > 0
        )
        
        # Average topics per session
        avg_topics = sum(m["topics_covered"] for m in self.learning_metrics) / len(self.learning_metrics)
        
        # Completion rates
        avg_completion = sum(m["completion_rate"] for m in self.learning_metrics) / len(self.learning_metrics)
        
        return {
            "total_learning_sessions": len(self.learning_metrics),
            "sessions_with_progress": positive_changes,
            "progress_rate": positive_changes / len(self.learning_metrics),
            "average_topics_per_session": round(avg_topics, 2),
            "average_completion_rate": round(avg_completion, 2),
            "effectiveness_score": self._calculate_effectiveness_score()
        }
        
    def get_pattern_effectiveness(self) -> Dict[str, Any]:
        """
        Get pattern usage effectiveness.
        
        Returns:
            Pattern metrics summary
        """
        if not self.pattern_metrics:
            return {
                "status": "no_pattern_data"
            }
            
        # Group by pattern type
        pattern_summary = {}
        for metric in self.pattern_metrics:
            pattern_type = metric["pattern_type"]
            if pattern_type not in pattern_summary:
                pattern_summary[pattern_type] = {
                    "total_occurrences": 0,
                    "average_score": 0,
                    "scores": []
                }
            
            summary = pattern_summary[pattern_type]
            summary["total_occurrences"] += metric["occurrences"]
            summary["scores"].append(metric["success_score"])
            
        # Calculate averages
        for pattern_type, summary in pattern_summary.items():
            scores = summary.pop("scores")
            summary["average_score"] = round(sum(scores) / len(scores), 2)
            
        # Find most effective patterns
        sorted_patterns = sorted(
            pattern_summary.items(),
            key=lambda x: x[1]["average_score"],
            reverse=True
        )
        
        return {
            "total_pattern_types": len(pattern_summary),
            "pattern_effectiveness": dict(sorted_patterns),
            "most_effective_pattern": sorted_patterns[0] if sorted_patterns else None,
            "total_pattern_uses": sum(
                s["total_occurrences"] for s in pattern_summary.values()
            )
        }
        
    def export_metrics_report(self) -> Dict[str, Any]:
        """
        Export comprehensive metrics report.
        
        Returns:
            Full metrics report
        """
        return {
            "report_generated": datetime.utcnow().isoformat(),
            "performance_summary": {
                "last_24h": self.get_performance_summary(24),
                "last_7d": self.get_performance_summary(168)
            },
            "learning_effectiveness": self.get_learning_effectiveness(),
            "pattern_effectiveness": self.get_pattern_effectiveness(),
            "recommendations": self._generate_recommendations()
        }
        
    def _calculate_trend(
        self,
        metrics: List[Dict[str, Any]]
    ) -> str:
        """Calculate performance trend."""
        if len(metrics) < 10:
            return "insufficient_data"
            
        # Split into halves and compare
        mid = len(metrics) // 2
        first_half = metrics[:mid]
        second_half = metrics[mid:]
        
        # Compare average response times
        avg_first = sum(m["response_time_ms"] for m in first_half) / len(first_half)
        avg_second = sum(m["response_time_ms"] for m in second_half) / len(second_half)
        
        if avg_second < avg_first * 0.9:
            return "improving"
        elif avg_second > avg_first * 1.1:
            return "degrading"
        else:
            return "stable"
            
    def _calculate_effectiveness_score(self) -> float:
        """Calculate overall effectiveness score."""
        if not self.learning_metrics:
            return 0.0
            
        # Weighted score based on multiple factors
        progress_weight = 0.4
        completion_weight = 0.4
        topic_weight = 0.2
        
        # Progress rate
        progress_rate = sum(
            1 for m in self.learning_metrics
            if m["understanding_change"] > 0
        ) / len(self.learning_metrics)
        
        # Completion rate
        avg_completion = sum(
            m["completion_rate"] for m in self.learning_metrics
        ) / len(self.learning_metrics)
        
        # Topic coverage (normalized)
        avg_topics = sum(
            m["topics_covered"] for m in self.learning_metrics
        ) / len(self.learning_metrics)
        topic_score = min(1.0, avg_topics / 5)  # Normalize to 5 topics
        
        score = (
            progress_rate * progress_weight +
            avg_completion * completion_weight +
            topic_score * topic_weight
        )
        
        return round(score, 2)
        
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on metrics."""
        recommendations = []
        
        # Check response times
        perf_summary = self.get_performance_summary(24)
        if perf_summary.get("average_response_time_ms", 0) > 2000:
            recommendations.append("Response times are high. Consider optimizing memory searches.")
            
        # Check learning effectiveness
        learning = self.get_learning_effectiveness()
        if learning.get("progress_rate", 0) < 0.5:
            recommendations.append("Low learning progress rate. Review tutor mode explanations.")
            
        # Check pattern usage
        patterns = self.get_pattern_effectiveness()
        if patterns.get("total_pattern_types", 0) < 3:
            recommendations.append("Limited pattern diversity. Analyze more conversations for patterns.")
            
        if not recommendations:
            recommendations.append("System performing well. Continue monitoring.")
            
        return recommendations
        
    def _cleanup_old_metrics(self):
        """Remove metrics older than 7 days."""
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        self.interaction_metrics = [
            m for m in self.interaction_metrics
            if m["timestamp"] > cutoff
        ]
        
        self.pattern_metrics = [
            m for m in self.pattern_metrics
            if m["timestamp"] > cutoff
        ]
        
        self.learning_metrics = [
            m for m in self.learning_metrics
            if m["timestamp"] > cutoff
        ]