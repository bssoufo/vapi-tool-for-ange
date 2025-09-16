from typing import Dict, Any, Optional
import json
from datetime import datetime


def pretty_print_json(data: Dict[str, Any]) -> str:
    """Pretty print JSON data."""
    return json.dumps(data, indent=2, default=str)


def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime to readable string."""
    if not dt:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def truncate_string(text: str, max_length: int = 50) -> str:
    """Truncate string to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def validate_id_format(entity_id: str, entity_type: str = "ID") -> bool:
    """Basic validation for entity IDs."""
    if not entity_id or not isinstance(entity_id, str):
        return False

    # UUID format check (basic)
    if len(entity_id) < 10:
        return False

    return True


def safe_get_nested(data: Dict[str, Any], keys: list, default: Any = None) -> Any:
    """Safely get nested dictionary values."""
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current