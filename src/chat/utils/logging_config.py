"""
Logging configuration for Chat Interface Service
"""

import logging
import sys
import json
from typing import Dict, Any
from datetime import datetime

from src.chatconfig import get_settings


def setup_logging():
    """Setup logging configuration"""
    settings = get_settings()
    
    # Configure standard library logging
    if settings.log_format == "json":
        # JSON formatter for structured logging
        formatter = JSONFormatter()
    else:
        # Standard formatter for console output
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


class ChatInterfaceLogger:
    """Custom logger for Chat Interface Service"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_request(self, method: str, path: str, client_ip: str, user_agent: str = None):
        """Log incoming request"""
        self.logger.info(
            f"incoming_request - method={method} path={path} client_ip={client_ip} "
            f"user_agent={user_agent} timestamp={datetime.utcnow().isoformat()}"
        )
    
    def log_response(self, method: str, path: str, status_code: int, duration_ms: float):
        """Log outgoing response"""
        self.logger.info(
            f"outgoing_response - method={method} path={path} status_code={status_code} "
            f"duration_ms={duration_ms} timestamp={datetime.utcnow().isoformat()}"
        )
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log error with context"""
        context_str = json.dumps(context) if context else "{}"
        self.logger.error(
            f"service_error - error={str(error)} error_type={type(error).__name__} "
            f"context={context_str} timestamp={datetime.utcnow().isoformat()}",
            exc_info=True
        )
    
    def log_conversation_start(self, session_id: str, client_user_id: str, actor_id: str):
        """Log conversation start"""
        self.logger.info(
            f"conversation_started - session_id={session_id} client_user_id={client_user_id} "
            f"actor_id={actor_id} timestamp={datetime.utcnow().isoformat()}"
        )
    
    def log_conversation_end(self, session_id: str, message_count: int, duration_minutes: float):
        """Log conversation end"""
        self.logger.info(
            f"conversation_ended - session_id={session_id} message_count={message_count} "
            f"duration_minutes={duration_minutes} timestamp={datetime.utcnow().isoformat()}"
        )
    
    def log_memory_consolidation(self, session_id: str, crew_job_id: str, status: str):
        """Log memory consolidation event"""
        self.logger.info(
            f"memory_consolidation - session_id={session_id} crew_job_id={crew_job_id} "
            f"status={status} timestamp={datetime.utcnow().isoformat()}"
        )