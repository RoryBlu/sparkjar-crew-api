"""Book Ingestion Crew module."""

from .book_ingestion_crew_handler import BookIngestionCrewHandler

import logging
logger = logging.getLogger(__name__)

__all__ = ["BookIngestionCrewHandler"]