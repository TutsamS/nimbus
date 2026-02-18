"""
Utility functions for the AWS Agent.
"""

import os
from typing import Dict, Any


def validate_aws_credentials() -> bool:
    """Validate that AWS credentials are properly configured."""
    required_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    return all(os.getenv(var) for var in required_vars)


def validate_openai_key() -> bool:
    """Validate that OpenAI API key is configured."""
    return bool(os.getenv("OPENAI_API_KEY"))


def format_response(title: str, data: Dict[str, Any]) -> str:
    """Format a response with a title and data."""
    lines = [f"\n{'='*50}", f"📋 {title}", f"{'='*50}"]
    for key, value in data.items():
        lines.append(f"{key}: {value}")
    lines.append("")
    return "\n".join(lines)
