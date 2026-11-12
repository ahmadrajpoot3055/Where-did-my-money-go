import re
from datetime import date
from typing import Optional

def normalize_description(text: Optional[str]) -> str:
    """Normalize transaction description for rules & ML matching."""
    if not text:
        return ""
    # Convert to uppercase for standard keyword comparison, strip extra spaces
    cleaned = re.sub(r'[^\w\s\.\-]', ' ', str(text))
    cleaned = re.sub(r'\s+', ' ', cleaned).strip().upper()
    return cleaned

def prevent_formula_injection(value: str) -> str:
    """Neutralize spreadsheet formula injection characters (=, +, -, @)."""
    if not value:
        return ""
    val_str = str(value).strip()
    if val_str and val_str[0] in ('=', '+', '-', '@'):
        return f"'{val_str}"
    return val_str

def is_valid_currency(currency_code: str) -> bool:
    """Check standard 3-letter currency code."""
    if not currency_code or len(currency_code) != 3:
        return False
    return currency_code.isalpha() and currency_code.isupper()

