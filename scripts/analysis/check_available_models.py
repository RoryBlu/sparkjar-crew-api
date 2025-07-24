#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""Check what OpenAI models are actually available."""
import openai
from dotenv import load_dotenv
load_dotenv()

client = openai.OpenAI()

logger.info("Available OpenAI Models:")
logger.info("=" * 60)

try:
    models = client.models.list()
    for model in models.data:
        if 'gpt' in model.id:
            logger.info(f"- {model.id}")
except Exception as e:
    logger.error(f"Error: {e}")