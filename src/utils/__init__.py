"""
SparkJAR Utils - Redirects to sparkjar-shared

All utils have been moved to sparkjar-shared to avoid code duplication.
This module provides backward compatibility by re-exporting from the shared location.
"""

# Re-export everything from sparkjar-shared.utils
from sparkjar_shared.utils import *

# Provide a deprecation notice
import warnings
warnings.warn(
    f"Importing from {__name__} is deprecated. "
    f"Please import directly from sparkjar_shared.utils instead.",
    DeprecationWarning,
    stacklevel=2
)
