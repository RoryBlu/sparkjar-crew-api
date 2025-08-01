"""
SparkJAR Tools - Redirects to sparkjar-shared

All tools have been moved to sparkjar-shared to avoid code duplication.
This module provides backward compatibility by re-exporting from the shared location.
"""

# Re-export everything from sparkjar-shared.tools
from sparkjar_shared.tools import *

# Provide a deprecation notice
import warnings
warnings.warn(
    f"Importing from {__name__} is deprecated. "
    f"Please import directly from sparkjar_shared.tools instead.",
    DeprecationWarning,
    stacklevel=2
)
