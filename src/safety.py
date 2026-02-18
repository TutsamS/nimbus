"""
Safety layer for destructive AWS operations.

Provides confirmation gating so destructive actions (delete bucket, delete object)
require explicit user approval before execution. The CLI checks this layer after
every agent response and prompts the user with a y/n before proceeding.
"""

from tools import DESTRUCTIVE_TOOLS

# Maps each destructive tool name to a warning template. The {target}
# placeholder is replaced with the tool's input (e.g. bucket name).
CONFIRMATION_MESSAGES = {
    "delete_s3_bucket": "WARNING: About to delete bucket '{target}' and ALL its contents. This cannot be undone.",
    "delete_s3_object": "About to delete object '{target}'. This cannot be undone.",
}


def requires_confirmation(tool_name: str) -> bool:
    """Return True if the given tool is registered as destructive."""
    return tool_name in DESTRUCTIVE_TOOLS


def format_confirmation_prompt(tool_name: str, tool_input: str) -> str:
    """Build a human-readable warning string for a destructive action,
    falling back to a generic message if the tool has no custom template.
    """
    template = CONFIRMATION_MESSAGES.get(tool_name)
    if template:
        return template.format(target=tool_input) + " Confirm? (y/n): "
    return f"About to execute '{tool_name}' with input '{tool_input}'. Confirm? (y/n): "
